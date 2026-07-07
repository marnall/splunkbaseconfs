import sys

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from api import AvalonAPI
from urllib.parse import urlparse

from util import init_logger


logger = init_logger('base.conf')

@Configuration()
class GetURL(GeneratingCommand):

    def generate(self):
        avalon = AvalonAPI.from_config(
            self, '/configs/inputs/avalon_nodes')
        try:
            yield {'api_url': urlparse(avalon.base_url).netloc}
        except:
            #incase of exception directy using default API URL.
            yield {'api_url': 'avalon.kingandunion.com'}
            sys.stdout.write("API URL not defined in Configuration tab --> Add-on settings." + '\n')
            sys.stderr.write("API URL not defined in Configuration tab --> Add-on settings." + '\n')
            sys.exit(1)

if __name__ == '__main__':
    dispatch(GetURL, sys.argv, sys.stdin, sys.stdout, __name__)
