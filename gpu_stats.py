import json
import time
import queue
import docker
import logging
import threading
import re
import nvml

logger = logging.getLogger(__name__)
docker_client = docker.from_env(version="auto", timeout=5)
monitors = {}
devices = nvml.get_devices()


def start(container_stats):
    global monitors
    monitor = GPUMonitor(monitors, container_stats)
    monitor.start()


class GPUMonitor(threading.Thread):
    
    def __init__(self, monitors, stats_queue):
        super(GPUMonitor, self).__init__()
        self.monitors = monitors
        self.stop = False
        self.stats_queue = stats_queue
        self.daemon = True
        
    def run(self):
        while True:
            time.sleep(1)
            for gpu_m, (c_id, gpu_in_c) in self.monitors.items():
               handle = devices[gpu_m]['handle']
               stats = nvml.get_device_stats(handle)
               print(c_id, gpu_in_c, stats)


def stop_container_monitors(container_ids):
    for c_id in container_ids:
        gpus = get_container_gpus(c_id)
        for gpu_m, gpu_in_c in gpus:
            if gpu_m in monitors:
                del monitors[gpu_m]
            else:
                logger.warn("Tried stopping non-existent container monitor: %s " % c_id)


def get_container_gpus(container_id):
    gpus = []
    devices = docker_client.api.inspect_container(container_id)['HostConfig']['Devices']
    for dev in devices:
        if re.match(r'/dev/nvidia[0-9]+', dev['PathOnHost']):
            gpus.append((int(dev['PathOnHost'][len('/dev/nvidia'):]), dev['PathInContainer']))
    return gpus


def monitor_containers(container_ids, container_stats, stop_others=False):
    if stop_others:
        others = set(current_threads.keys()) - set(container_ids)
        for o in others:
            o.stop = True
        current_threads.clear()
    for c_id in container_ids:
        gpus = get_container_gpus(c_id)
        for gpu_m, gpu_in_c in gpus:
            if gpu_m not in monitors:
                monitors[gpu_m] = (c_id, gpu_in_c)


if __name__ == '__main__':
    import queue
    import sys
    print(nvml.get_versions())
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    if len(sys.argv) == 2:
        containers = [sys.argv[1]]
    else:
        containers = [docker_client.containers.list()[0].id]
    container_stats = queue.Queue()
    monitor_containers(containers, container_stats)
    time.sleep(10)
    stop_container_monitors(containers)
    time.sleep(2)