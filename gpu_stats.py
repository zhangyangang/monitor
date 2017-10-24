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
monitors_lock = threading.Lock()
monitor_thread = None
devices = nvml.get_devices()


class GPUMonitor(threading.Thread):
    
    def __init__(self, monitors, stats_queue):
        super(GPUMonitor, self).__init__()
        self.monitors = monitors
        self.devices = nvml.get_devices()
        self.stop = False
        self.stats_queue = stats_queue
        self.daemon = True
        
    def run(self):
        logger.info("Start watching GPU statistics")
        while not self.stop:
            try:
                with monitors_lock:
                    for c_id, (job_id, gpus) in self.monitors.items():
                        gpus_stats = {}
                        for gpu_in_h, gpu_in_c in gpus:
                            dev = self.devices[gpu_in_h]
                            stats = nvml.get_device_stats(dev['handle'], dev['bus_id'],
                                                        dev['name'])
                            gpus_stats[gpu_in_c] = stats
                        millis = int(round(time.time() * 1000))
                        self.stats_queue.put((job_id, {'timestamp': millis, 
                                                    'gpus': gpus_stats}))
                time.sleep(1)
            except Exception as e:
                logger.error(e)
        logger.info("Stopped watching GPU statistics")


def stop_container_monitors(container_ids):
    for c_id, _ in container_ids:
        if c_id in monitors:
            with monitors_lock:
                del monitors[c_id]
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
    if nvml.nvml_initialized:
        if monitor_thread is None:
            monitor_thread = GPUMonitor(monitors, container_stats)
            monitor_thread.start()
        elif not monitor_thread.is_alive():
            logger.error('GPU monitor thread not running. Restarting...')
            monitor_thread = GPUMonitor(monitors, container_stats)
            monitor_thread.start()
    new_monitors = {}
    for c_id, job_id in container_ids:
        gpus = get_container_gpus(c_id)
        if gpus:
            new_monitors[c_id] = (job_id, gpus)
            logger.info("Monitoring GPU stats for container: %s" % c_id)
    with monitors_lock:
        if stop_others:
            monitors.clear()
        monitors.update(new_monitors)


if __name__ == '__main__':
    import queue
    import sys
    print(nvml.get_versions())
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    container_stats = queue.Queue()
    monitor_thread = GPUMonitor(monitors, container_stats)   
    monitor_thread.start()
    monitors['container_id'] = ('test_job', [('/dev/nvidia0', '/dev/nvidia0')])
    for _ in range(10):
        try:
            stats = container_stats.get(block=False)
            print(json.dumps(stats, indent=2))
        except queue.Empty:
            pass
        time.sleep(1)
