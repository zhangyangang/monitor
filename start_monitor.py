import logging
import sys
import os
from monitor import loop, config

log_level = logging.DEBUG if os.environ.get('DEBUG') == '1' else logging.INFO 
log_format = '%(levelname)s: %(message)s'
logging.basicConfig(stream=sys.stdout, level=log_level, format=log_format)

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    if not config.CLUSTER_ID and config.ENVIRONMENT not in ['development', 'test']:
        logger.error("No cluster id set!")
        sys.exit(1)

    if config.ENVIRONMENT not in ['development', 'test']:
        rollbar.init(
            config.CLUSTER_ID, # Use cluster id as access token
            config.ENVIRONMENT,
            endpoint=config.ROLLBAR_ENDPOINT,
            root=os.path.dirname(os.path.realpath(__file__)))

        try:
            loop.start()
        except:
            rollbar.report_exc_info()
            raise
    else:
        loop.start()