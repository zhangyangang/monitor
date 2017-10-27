import logging
import sys
import os
from monitor import loop

log_level = logging.DEBUG if os.environ.get('DEBUG') == '1' else logging.INFO 
log_format = '%(name)s - %(levelname)s - %(message)s'
logging.basicConfig(stream=sys.stdout, level=log_level, format=log_format)

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info('Starting monitoring loop...')
    loop.start()
    logger.info('Monitoring loop exited.')