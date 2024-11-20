import logging

LOG_FORMAT = ('%(levelname) -10s %(name) -45s '
              ': %(message)s')

LOGGER = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
