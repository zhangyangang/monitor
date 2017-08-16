import logging
import sys
import os
import time
import queue
import json
import requests
import pika
import nvml
from k8s import ContainerWatch, ContainerEvent
import docker_stats
import gpu_stats
from amqp import AMQPWrapper
import sysinfo

logger = logging.getLogger(__name__)
nodename = os.environ.get('NODENAME')
amqp_url = os.environ.get('AMQP_URL')
api_url = os.environ.get('RISEML_API_URL')
api_key = os.environ.get('RISEML_APIKEY')

namespace = "riseml"
label_selector = "role=train"
field_selector = 'spec.nodeName=%s' % nodename
current_node_info = {}


def send_stats(amqp, stats):
    job_id, job_stats = stats
    logger.info('sending stats for job %s: %s' % (job_id, job_stats))
    stats['job_id'] = job_id
    stats_exchange = 'monitor-%s' % job_id
    channel = amqp.get_channel()
    channel.exchange_declare(exchange=stats_exchange,
                             type='fanout', durable=False)

    channel.basic_publish(exchange=stats_exchange,
                          routing_key='',
                          body=json.dumps(job_stats),
                          properties=pika.BasicProperties(content_type='text/plain',
                                                          delivery_mode=1))


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
    new_info = {'name': nodename,
                'nvidia_driver': nvidia_versions.get('driver_version', 'NOT FOUND'),
                'cpu_model': sys_info['cpu_model'],
                'mem': sys_info['mem_total'],
                'gpus': gpus}
    if current_node_info == new_info:
        logger.info('Node information did not change. Skipping update to server.')
        return
    try:
        logger.info("Updating node info: %s." % new_info)
        headers = {'Authorization': api_key}
        headers.update({ 'Content-Type': 'application/json' })
        res = requests.put('%s/nodes' % (api_url),
                            headers=headers,
                            json=new_info)
        res.raise_for_status()
        current_node_info = new_info
    except (requests.ConnectionError, requests.HTTPError) as err:
         logger.warn("RiseML API connection error %s" % err)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)    
    logger.info("Docker client version: %s" % docker_stats.docker_client.version())
    container_events = queue.Queue()
    container_stats = queue.Queue()
    pod_watch = ContainerWatch(namespace, label_selector, field_selector, container_events)
    pod_watch.start()
    amqp = AMQPWrapper(amqp_url)
    max_messages_loop = 100
    last_node_update = 0
    node_udpate_interval_s = 120
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
            update_node_info()
            last_node_update = time.time()
    pod_watch.join()
