import logging
import sys
import os
import time
import queue
from k8s import ContainerWatch, ContainerEvent
import docker_stats

# from https://github.com/NVIDIA/nvidia-docker/wiki/GPU-isolation
# "If the device minor number is N, the device file is simply /dev/nvidiaN"

# on startup, initialize map from device name -> nvml handle
# for new containers, check for mapped devices
# add new containers to list of reports
# for each report each second, query cpu, mem, gpu stats
# remove reports from containers

container_events = queue.Queue()
container_stats = queue.Queue()

logger = logging.getLogger(__name__)

# configuring logger
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

nodename = os.environ.get('NODENAME')
namespace = "riseml"
label_selector = "role=train"
field_selector =  'spec.nodeName=%s' % nodename

pod_watch = ContainerWatch(namespace, label_selector, field_selector, container_events)            
pod_watch.start()
gpu_containers = set()

while True:
    while not container_events.empty():
        msg = container_events.get()
        logger.info(msg)       
        for event, ev_containers in msg.items():
            if event == ContainerEvent.RUNNING:
                containers = ev_containers
                docker_stats.monitor_containers(ev_containers, container_stats, stop_others=True)
            elif event == ContainerEvent.STOPPED:
                docker_stats.stop_container_monitors(ev_containers)
            elif event == ContainerEvent.STARTED:
                docker_stats.monitor_containers(ev_containers, container_stats)
        logger.info(containers)
pod_watch.join()