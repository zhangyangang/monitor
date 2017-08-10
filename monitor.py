import logging
import sys
import os
import time
import queue
import json
import pika
from k8s import ContainerWatch, ContainerEvent
import docker_stats
from amqp import AMQPWrapper
import sysinfo
import threading

logger = logging.getLogger(__name__)
nodename = os.environ.get('NODENAME')
amqp_url = os.environ.get('AMQP_URL')
namespace = "riseml"
label_selector = "role=train"
field_selector =  'spec.nodeName=%s' % nodename

def send_stats(channel, stats):
    job_id, job_stats = stats
    logger.info('sending stats for job %s: %s' % (job_id, job_stats))
    stats_queue = 'utilization-%s' % job_id
    channel.queue_declare(queue=stats_queue)
    channel.basic_publish(exchange='',
                          routing_key=stats_queue,
                          body=json.dumps(job_stats),
                          properties=pika.BasicProperties(content_type='text/plain',
                                                          delivery_mode=1))


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)    
    container_events = queue.Queue()
    container_stats = queue.Queue()
    pod_watch = ContainerWatch(namespace, label_selector, field_selector, container_events)
    pod_watch.start()
    amqp = AMQPWrapper(amqp_url)
    channel = amqp.connection.channel()
    max_messages_loop = 100
    while True:
        while not container_events.empty():
            msg = container_events.get()
            for event, ev_containers in msg.items():
                if event == ContainerEvent.RUNNING:
                    docker_stats.monitor_containers(ev_containers, container_stats, stop_others=True)
                elif event == ContainerEvent.STOPPED:
                    docker_stats.stop_container_monitors(ev_containers)
                elif event == ContainerEvent.STARTED:
                    docker_stats.monitor_containers(ev_containers, container_stats)
        messages_sent = 0
        while not container_stats.empty():
            stats = container_stats.get()
            send_stats(channel, stats)
            messages_sent += 1           
            # interrupt sending messages so we can consume container events
            if messages_sent == max_messages_loop:
                break
        if messages_sent == 0:
            time.sleep(0.1)
    pod_watch.join()