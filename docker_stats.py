import json
import time
import docker
import logging
logger = logging.getLogger(__name__)
import threading

docker_client = docker.from_env(version="auto", timeout=5)
current_threads = dict()

class ContainerMonitor(threading.Thread):
    
    def __init__(self, container_id, stats_queue):
        super(ContainerMonitor, self).__init__()
        self.container = docker_client.containers.get(container_id)
        self.stop = False
        self.stats_queue = stats_queue
        

    def run(self):
        logger.info("Start monitoring container %s" % self.container.id)
        stats = self.container.stats(decode=True, stream=True)
        for s in stats:
            if self.stop:
                logger.info("Stopped monitoring container %s" % self.container.id)
                break
            logger.info("%s: %s " % (self.container.id, s))


def stop_container_monitors(container_ids):
    for c_id in container_ids:
        if c_id in current_threads:
            current_threads[c_id].stop = True
        else:
            logger.warn("Tried stopping non-existent container monitor: %s " % c_id)


def monitor_containers(container_ids, container_stats, stop_others=False):
    if stop_others:
        others = set(current_threads.keys()) - set(container_ids)
        for o in others:
            o.stop = True
        current_threads.clear()
    for c_id in container_ids:
        if c_id not in current_threads:
            monitor = ContainerMonitor(c_id, container_stats)
            monitor.start()
            current_threads[c_id] = monitor


if __name__ == '__main__':
    import queue
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    container_stats = queue.Queue()
    containers = [docker_client.containers.list()[0].id]
    monitor_containers(containers, container_stats)
    time.sleep(10)
    stop_container_monitors(containers)
    time.sleep(2)
