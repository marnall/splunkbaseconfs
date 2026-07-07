import sys

try:
    from VaronisSearchBase import VaronisSearchBase
except ImportError:
    from bin.VaronisSearchBase import VaronisSearchBase
    
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

import logging

logger = logging.getLogger('splunk.VaronisSearch')
logger.setLevel(logging.DEBUG)


@Configuration()
class VaronisSearch(VaronisSearchBase):
    query = Option(require=True)

    def get_query(self):
        logger.debug("building query: ")

        return self.query


if __name__ == "__main__":
    dispatch(VaronisSearch, sys.argv, sys.stdin, sys.stdout, __name__)
