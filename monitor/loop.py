import logging
import sys
import os
import time
import queue
import json
import requests
import pika

from .amqp import AMQPWrapper
from .k8s import ContainerWatch, ContainerEvent
from . import nvml, docker_stats, gpu_stats, sysinfo, config

logger = logging.getLogger(__name__)

current_node_info = {}


def send_stats(amqp, stats):
    job_id, job_stats = stats
    job_stats['job_id'] = job_id
    #logger.info('sending stats for job %s: %s' % (job_id, job_stats))
    stats_exchange = 'monitor-%s' % job_id
    try:
        channel = amqp.get_channel()
        channel.exchange_declare(exchange=stats_exchange,
                                 exchange_type='fanout', durable=False)
        channel.basic_publish(exchange=stats_exchange,
                              routing_key='',
                              body=json.dumps(job_stats),
                              properties=pika.BasicProperties(content_type='text/plain',
                                                              delivery_mode=1))
    except pika.exceptions.ConnectionClosed as e:
        logger.info('Reconnecting amqp..')
        amqp.reconnect()


def update_node_info():
    global current_node_info
    sys_info = sysinfo.get_system_info()
    nvidia_versions = nvml.get_versions()
    nvidia_devices = nvml.get_devices()
    gpus = []
    for dev_name, dev_info in nvidia_devices.items():
        gpus.append({'name': dev_info['name'],
                     'mem': dev_info['mem_total'],
                     'serial': dev_info['serial'],
                     'device': dev_name})
    new_info = {'name': config.NODENAME,
                'nvidia_driver': nvidia_versions.get('driver_version', 'NOT FOUND'),
                'cpu_model': sys_info['cpu_model'],
                'memory': sys_info['memory_total'],
                'cpus': sys_info['num_cores'],
                'gpus': gpus}
    # disable check for now
    #if current_node_info == new_info:
    #    logger.info('Node information did not change. Skipping update to server.')
    #    return
    try:
        logger.info("Updating node info: %s." % new_info)
        headers = {'Authorization': config.RISEML_APIKEY}
        headers.update({ 'Content-Type': 'application/json' })
        res = requests.put('%s/nodes' % (config.RISEML_API_URL),
                            headers=headers,
                            json=new_info)
        res.raise_for_status()
        current_node_info = new_info
        return True
    except (requests.ConnectionError, requests.HTTPError) as err:
         logger.warn("RiseML API connection error %s" % err)
         return False


def start():
    logger.info("Docker client version: %s" % docker_stats.docker_client.version())
    logger.info("GPUs: %s" % nvml.get_devices())
    container_events = queue.Queue()
    container_stats = queue.Queue()
    pod_watch = ContainerWatch(config.NAMESPACE, config.LABEL_SELECTOR,
                               'spec.nodeName=%s' % config.NODENAME,
                               container_events)
    pod_watch.start()
    amqp = AMQPWrapper(config.AMQP_URL)
    max_messages_loop = 100
    last_node_update = 0
    node_udpate_interval_s = config.INITIAL_UPDATE_INTERVAL_SEC
    
    while True:
        while not container_events.empty():
            msg = container_events.get()
            for event, ev_containers in msg.items():
                if event == ContainerEvent.RUNNING:
                    docker_stats.monitor_containers(ev_containers, container_stats, stop_others=True)
                    gpu_stats.monitor_containers(ev_containers, container_stats, stop_others=True)
                elif event == ContainerEvent.STOPPED:
                    docker_stats.stop_container_monitors(ev_containers)
                    gpu_stats.stop_container_monitors(ev_containers)
                elif event == ContainerEvent.STARTED:
                    docker_stats.monitor_containers(ev_containers, container_stats)
                    gpu_stats.monitor_containers(ev_containers, container_stats)
        messages_sent = 0
        while not container_stats.empty():
            stats = container_stats.get()
            send_stats(amqp, stats)
            messages_sent += 1           
            # interrupt sending messages so we can consume container events
            if messages_sent == max_messages_loop:
                break
        if messages_sent == 0:
            time.sleep(0.1)
        if time.time() - last_node_update > node_udpate_interval_s:
            updated = update_node_info()
            last_node_update = time.time()
            if updated:
                node_udpate_interval_s = config.UPDATE_INTERVAL_SEC
    pod_watch.join()
