import logging
import sys
import os
import time
import queue
from k8s import ContainerWatch

# from https://github.com/NVIDIA/nvidia-docker/wiki/GPU-isolation
# "If the device minor number is N, the device file is simply /dev/nvidiaN"

# on startup, initialize map from device name -> nvml handle
# for new containers, check for mapped devices
# add new containers to list of reports
# for each report each second, query cpu, mem, gpu stats
# remove reports from containers

container_events = queue.Queue()

logger = logging.getLogger(__name__)

# configuring logger
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

nodename = os.environ.get('NODENAME')
namespace = "riseml"
label_selector = "role=train"
field_selector =  'spec.nodeName=%s' % nodename

pod_watch = ContainerWatch(namespace, label_selector, field_selector, container_events)            
pod_watch.start()
while True:
    while not container_events.empty():
        m = container_events.pop()
        print(m)
    time.sleep(1)

pod_watch.join()