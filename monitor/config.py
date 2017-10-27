import os

INITIAL_UPDATE_INTERVAL_SEC = int(os.environ.get('INITIAL_UPDATE_INTERVAL_SEC', 10))
UPDATE_INTERVAL_SEC = int(os.environ.get('UPDATE_INTERVAL_SEC', 1800))
NODENAME = os.environ.get('NODENAME')
AMQP_URL = os.environ.get('AMQP_URL')
RISEML_API_URL = os.environ.get('RISEML_API_URL')
RISEML_APIKEY = os.environ.get('RISEML_APIKEY')
NAMESPACE = "riseml"
LABEL_SELECTOR = "kind=batch"
FIELD_SELECTOR = 'spec.nodeName=%s' % NODENAME
