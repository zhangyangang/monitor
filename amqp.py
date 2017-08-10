import logging
import pika
from pika import exceptions
from retrying import retry

logger = logging.getLogger(__name__)

retry_conf = {
    'retry_on_exception':
        lambda exc: isinstance(exc, exceptions.AMQPConnectionError),
    'wait_exponential_multiplier': 1000,
    'wait_exponential_max': 10000,
    'stop_max_attempt_number': 5
}


class AMQPWrapper():

    def __init__(self, url):
        self.url = url
        self.connection = None
        self._init_connection()

    @retry(**retry_conf)
    def _init_connection(self):
        logger.info('Connection attempt to %s' % self.url)
        self.connection = pika.BlockingConnection(
            pika.URLParameters(self.url)
        )
        logger.info('Successfully connected to AMQP')