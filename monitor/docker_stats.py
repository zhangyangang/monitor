import json
import time
import docker
import logging
import threading
import urllib3
import socket

logger = logging.getLogger(__name__)
docker_client = docker.from_env(version="auto", timeout=10)
current_threads = dict()


class ContainerMonitor(threading.Thread):
    
    def __init__(self, container_id, job_id, stats_queue):
        super(ContainerMonitor, self).__init__()
        self.container = docker_client.containers.get(container_id)
        self.job_id = job_id
        self.stop = False
        self.stats_queue = stats_queue
        self.daemon = True
        
    def run(self):
        logger.info("Start monitoring container %s" % self.container.id)
        def monitor():
            stats_stream = self.container.stats(decode=True, stream=True)
            for n, s in enumerate(stats_stream):
                if self.stop:
                    break
                # first stats don't contain all info
                if n == 0:
                    continue   
                try:
                    cpu_percent, percpu_percent = calculate_cpu_percent(s)
                    memory_used = int(s['memory_stats']['usage'])
                    memory_limit = int(s['memory_stats']['limit'])
                except Exception as e:
                    logger.exception('Docker sent malformed stats: %s' % str(e))
                    continue
                millis = int(round(time.time() * 1000))                
                self.stats_queue.put((self.job_id, 
                                     {'timestamp': millis,
                                      'cpu_percent': cpu_percent, 
                                      'memory_used': memory_used, 
                                      'memory_limit': memory_limit, 
                                      'percpu_percent': percpu_percent}))
        try:
            monitor()
        except (urllib3.exceptions.ReadTimeoutError, socket.timeout) as e:
            logger.error('Timeout waiting for stats. Maybe container was stopped: %s' % str(e))
        except Exception as e:
            logger.exception('Error in monitoring: %s' % str(e))
            #raise(e)
        finally:
            logger.info("Stopped monitoring container %s" % self.container.id)


# according to: https://github.com/moby/moby/blob/eb131c5383db8cac633919f82abad86c99bffbe5/cli/command/container/stats_helpers.go#L175-L188
def calculate_cpu_percent(stats):
    cpu_percent = 0.0
    previous_cpu = float(stats['precpu_stats']['cpu_usage']['total_usage'])
    previous_system = float(stats['precpu_stats']['system_cpu_usage'])
    percpu_usage = stats['cpu_stats']['cpu_usage']['percpu_usage']
    num_cpus = len(percpu_usage)
    percpu_percent = [0.0 for _ in range(num_cpus)]
    total_usage = float(stats['cpu_stats']['cpu_usage']['total_usage'])
    cpu_delta = total_usage - previous_cpu
    system_delta = float(stats['cpu_stats']['system_cpu_usage']) - previous_system
    if system_delta > 0 and cpu_delta > 0:
        cpu_percent = (cpu_delta / system_delta) * float(num_cpus) * 100.0
        percpu_percent = [percpu / total_usage * cpu_percent for percpu in percpu_usage]
    return cpu_percent, percpu_percent


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
            current_threads[o].stop = True
            del current_threads[o]
    for c_id, job_id in container_ids:
        if (c_id, job_id) not in current_threads:
            monitor = ContainerMonitor(c_id, job_id, container_stats)
            monitor.start()
            current_threads[(c_id, job_id)] = monitor


if __name__ == '__main__':
    import queue
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    container_stats = queue.Queue()
    print(len(sys.argv))
    if len(sys.argv) == 2:
        containers = [sys.argv[1]]
    else:
        containers = [docker_client.containers.list()[0].id]
    monitor_containers(containers, container_stats)
    time.sleep(10)
    stop_container_monitors(containers)
    time.sleep(2)
