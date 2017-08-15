import logging
import pika
from pika import exceptions

logger = logging.getLogger(__name__)


class AMQPWrapper():

    def __init__(self, url):
        self.url = url
        self.connection = None
        self.channel = None
        self.ensure_connection()

    def _init_connection(self):
        connection = None
        while connection is None:
            logger.info('Connection attempt to %s' % self.url)
            params = pika.URLParameters(self.url)
            params.heartbeat = 10
            params.socket_timeout = 20
            params.blocked_connection_timeout = 20
            connection = pika.BlockingConnection(
                params
            )
            logger.info('Successfully connected to AMQP')
        self.connection = connection
    
    def ensure_connection(self):
        if self.connection is None or self.connection.is_closed:
            self._init_connection()
            self.channel = self.connection.channel()
        return self.connection

    def get_channel(self):
        self.ensure_connection()
        return self.channel