from kubernetes import client, config, watch
import logging
import sys
import threading
import os
from kubernetes.client.rest import ApiException
from urllib3.exceptions import HTTPError
logger = logging.getLogger(__name__)


def get_container_states(pods, container_name='job'):
    running = set()
    stopped = set()
    for pod in pods:
        if pod.status.container_statuses is not None:
            for container_status in pod.status.container_statuses:
                if container_status.name != container_name:
                    continue
                if container_status.state.running is not None:
                    running.add(container_status.container_id)
                else:
                    stopped.add(container_status.container_id)
    return running, stopped


def query_running_containers(namespace, label_selector, field_selector):    
    client = get_client()
    pods = client.list_namespaced_pod(namespace=namespace,
                                      field_selector=field_selector,
                                      label_selector=label_selector)
    rv = pods.metadata.resource_version
    running, _ = get_container_states(pods.items)
    return running


def get_client():
    config.load_incluster_config()
    #beta_api = client.ExtensionsV1beta1Api()
    v1_api = client.CoreV1Api()
    return v1_api


class ContainerWatch(threading.Thread):
    daemon = True

    def __init__(self, namespace, label_selector, field_selector, queue):
        super(ContainerWatch, self).__init__()
        self.namespace = namespace
        self.label_selector = label_selector
        self.field_selector = field_selector
        self.stopped = set()
        self.queue = queue
        self.running = set()



    def run(self):
        while True:
            try:
                self.running = query_running_containers(self.namespace, self.label_selector, 
                                                        self.field_selector)
                self.queue.put({'running': self.running.copy()})
                self.watch()
                time.sleep(0.5)
            except (ApiException, HTTPError) as e:
                logger.info("K8S connection error %s" % e)
                logger.info("Reconnecting to API...")
                time.sleep(1)

    def watch(self):
        logger.info("Start watching pods %s in namespace %s" % (self.label_selector, self.namespace))
        w = watch.Watch()
        client = get_client()
        for event in w.stream(client.list_namespaced_pod,
                              namespace=self.namespace, _request_timeout=200,
                              timeout_seconds=200,
                              field_selector=self.field_selector,
                              label_selector=self.label_selector):
                pod = event['object']
                # Ignore irrelevant events.
                if pod is None or pod.metadata is None or pod.metadata.resource_version is None:
                    logger.info('received empty pod event: %s' % self.resource_version)
                    continue
                self.handle_pod_event(event)

    def handle_pod_event(self, e):
        now_running, now_stopped = get_container_states([e['object']])
        just_started = now_running - self.running
        just_stopped = now_stopped & self.running
        if just_started:
            logger.info("Now started: %s" % just_started)
            self.running = self.running | now_running
            self.queue.put({'now_running': just_started.copy()})
        if just_stopped:
            logger.info("Now stopped: %s" % just_stopped)
            running = running - now_stopped
            self.queue.put({'now_stopped': just_stopped.copy()})