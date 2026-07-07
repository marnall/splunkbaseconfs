# coding=utf-8
from time import time
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'niddel2_imports'))

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from magnetsdk2 import Connection
from niddelutil import get_api_key, get_proxy_config, get_app_config, get_splunk_version

@Configuration()
class NiddelOrganizationTopology(GeneratingCommand):
    orgid = Option(require=True)

    def __init__(self):
        super(NiddelOrganizationTopology, self).__init__()
        self._connection = None
        self._connectionRegion = None
        self._region = None

    @property
    def connection(self):
        if not self._connection:
            api_key = get_api_key(self.service)
            if not api_key:
                raise Exception("API key was not found, please configure the Niddel app before using this command")
            appcfg = get_app_config()
            splversion = get_splunk_version()
            _user_agent = "Splunk App/v%s-build_%s; %s" % (appcfg['app_version'], appcfg['app_build'], str(splversion))
            self._connection = Connection(api_key=api_key, user_agent=_user_agent)
            proxy = get_proxy_config(self.service)
            if proxy:
                self._connection.set_proxy(**proxy)
        return self._connection

    def generate(self):
        try:
            for top in self.connection.get_organization_topology(self.orgid):
                yield top    
        except Exception as e:
            self.logger.exception("unable to generate events")
            raise e

dispatch(NiddelOrganizationTopology, sys.argv, sys.stdin, sys.stdout, __name__)