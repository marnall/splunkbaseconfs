# coding=utf-8
from time import time
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'niddel2_imports'))

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration
from magnetsdk2 import Connection
from niddelutil import get_api_key, get_proxy_config, get_app_config, get_splunk_version

@Configuration(type='eventing', retainsevents=True, streaming=False, local=True)
class NiddelOrganizations(GeneratingCommand):
    def __init__(self):
        super(NiddelOrganizations, self).__init__()
        self._connection = None

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
            defaultOrganizationId = self.connection.get_me().get('defaultOrganizationId', None)
            for org in self.connection.iter_organizations():
                if defaultOrganizationId and org['id'] == defaultOrganizationId:
                    org['default'] = True
                else:
                    org['default'] = False
                org['_raw'] = json.dumps(org)
                org['_time'] = time()
                yield org
        except Exception as e:
            self.logger.exception("unable to generate events")
            raise e


dispatch(NiddelOrganizations, sys.argv, sys.stdin, sys.stdout, __name__)
