from kubernetes import client, config, watch
import logging
import sys
import threading
import os
import time
from kubernetes.client.rest import ApiException
from urllib3.exceptions import HTTPError
logger = logging.getLogger(__name__)


class ContainerEvent:
    RUNNING = 'running'
    STARTED = 'started'
    STOPPED = 'stopped'


def normalize_container_id(container_id):
    if container_id.startswith('docker://'):
        return container_id[len('docker://'):]
    return container_id


def get_container_states(pods, container_name='job'):
    running = set()
    stopped = set()
    for pod in pods:
        if pod.status.container_statuses is not None:
            for container_status in pod.status.container_statuses:
                if container_status.name != container_name:
                    continue
                container_id = normalize_container_id(str(container_status.container_id))
                job_id = pod.metadata.labels['job_id']
                if container_status.state.running is not None:
                    running.add((container_id, job_id))
                else:
                    stopped.add((container_id, job_id))
    return running, stopped


def query_running_containers(namespace, label_selector, field_selector):    
    client = get_client()
    pods = client.list_namespaced_pod(namespace=namespace,
                                      field_selector=field_selector,
                                      label_selector=label_selector)
    rv = pods.metadata.resource_version
    running, _ = get_container_states(pods.items)
    return running, rv


def get_client():
    config.load_incluster_config()
    #beta_api = client.ExtensionsV1beta1Api()
    v1_api = client.CoreV1Api()
    return v1_api


class ContainerWatch(threading.Thread):
    
    def __init__(self, namespace, label_selector, field_selector, queue):
        super(ContainerWatch, self).__init__()
        self.namespace = namespace
        self.daemon = True
        self.label_selector = label_selector
        self.field_selector = field_selector
        self.stopped = set()
        self.queue = queue
        self.running = set()
        self.client = get_client()

    def run(self):
        while True:
            try:
                self.running, rv = query_running_containers(self.namespace, self.label_selector, 
                                                            self.field_selector)
                self.queue.put({ContainerEvent.RUNNING: self.running.copy()})
                self.watch(rv)
            except (ApiException, HTTPError) as e:
                logger.info("K8S connection error %s" % e)
                logger.info("Reconnecting to API...")
                time.sleep(1)
            finally:
                logger.info("Restart watching for pods...")
                
    def watch(self, resource_version):
        logger.info("Start watching pods %s in namespace %s" % (self.label_selector, self.namespace))
        w = watch.Watch()
        for event in w.stream(self.client.list_namespaced_pod,
                              namespace=self.namespace, _request_timeout=1800,
                              timeout_seconds=3600, resource_version=resource_version,
                              field_selector=self.field_selector,
                              label_selector=self.label_selector):
                pod = event['object']
                # Ignore irrelevant events.
                if pod is None or pod.metadata is None or pod.metadata.resource_version is None:
                    logger.info('received empty pod event')
                    continue
                self.handle_pod_event(event)

    def handle_pod_event(self, event):
        now_running, now_stopped = get_container_states([event['object']])
        just_started = now_running - self.running
        just_stopped = now_stopped & self.running
        msg = {}
        if just_started:
            for c_id, job_id in just_started:
                logger.info("Container %s started for job %s" % (c_id, job_id))
            self.running = self.running | just_started
            msg[ContainerEvent.STARTED] = just_started.copy()
        if just_stopped:
            for c_id, job_id in just_stopped:
                logger.info("Container %s stopped for job %s" % (c_id, job_id))
            self.running = self.running - just_stopped
            msg[ContainerEvent.STOPPED] = just_stopped.copy()
        if msg:
            self.queue.put(msg)