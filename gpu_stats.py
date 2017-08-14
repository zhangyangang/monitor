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
monitor_thread = None
devices = nvml.get_devices()


class GPUMonitor(threading.Thread):
    
    def __init__(self, monitors, stats_queue):
        super(GPUMonitor, self).__init__()
        self.monitors = monitors
        self.stop = False
        self.stats_queue = stats_queue
        self.daemon = True
        
    def run(self):
        while not self.stop:
            for gpu_m, (c_id, job_id, gpu_in_c) in self.monitors.items():
                handle = devices[gpu_m]['handle']
                stats = nvml.get_device_stats(handle)
                millis = int(round(time.time() * 1000))
                self.stats_queue.put((job_id, {'timestamp': millis, gpu_in_c: stats}))
            time.sleep(1)


def stop_container_monitors(container_ids):
    for c_id, job_id in container_ids:
        gpus = get_container_gpus(c_id)
        for gpu_in_h, gpu_in_c in gpus:
            if gpu_in_h in monitors:
                del monitors[gpu_in_h]
            else:
                logger.warn("Tried stopping non-existent container monitor: %s " % c_id)


def get_container_gpus(container_id):
    gpus = []
    devices = docker_client.api.inspect_container(container_id)['HostConfig']['Devices']
    for dev in devices:
        if re.match(r'/dev/nvidia[0-9]+', dev['PathOnHost']):
            gpus.append((dev['PathOnHost'], dev['PathInContainer']))
    return gpus


def monitor_containers(container_ids, container_stats, stop_others=False):
    global monitors
    global monitor_thread
    if monitor_thread is None:
        monitor_thread = GPUMonitor(monitors, container_stats)
        monitor_thread.start()
    new_monitors = {}
    for c_id, job_id in container_ids:
        gpus = get_container_gpus(c_id)
        for gpu_in_h, gpu_in_c in gpus:
            new_monitors[gpu_in_h] = (c_id, job_id, gpu_in_c)
    if stop_others:
        monitors = new_monitors
    else:
        monitors.update(new_monitors)


if __name__ == '__main__':
    import queue
    import sys
    print(nvml.get_versions())
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    if len(sys.argv) == 2:
        containers = [sys.argv[1]]
    else:
        containers = [(docker_client.containers.list()[0].id, 123)]
    container_stats = queue.Queue()
    monitor_containers(containers, container_stats)
    time.sleep(10)
    stop_container_monitors(containers)
    time.sleep(2)
