from splunk.persistconn.application import PersistentServerConnectionApplication
import six
import json
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".", "BaseClient"))
from baseclient import BaseClient
import endpoints


class SearchResults(PersistentServerConnectionApplication, BaseClient):

    def __init__(self, command_line, command_arg):
        self.session = ()
        self.url = ''
        self.baseurl = ''
        self.res = None
        self.outputmode = {
            'output_mode': 'json'
        }
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        args = json.loads(in_string)
        content = json.loads(args['payload'])
        self.session = (content['username'], content['password'])
        self.url = content['url']
        endpoints.verify_ssl = content.get('verify_ssl')
        url = self.url + endpoints.const_conf
        ssl = {
            'value': endpoints.verify_ssl
        }
        self.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=ssl, method='POST', auth=self.session)
        self.baseurl = content['url'] + endpoints.result_collection
        self.get_search_results()
        return {'payload': self.res,
                'status': 200}

    def get_search_results(self):

        results = self.http_method(url=self.baseurl, verify_ssl=endpoints.verify_ssl, data=self.outputmode,
                         method='GET', auth=self.session)
        self.res = results.json()
        self.delete_collection()

    def delete_collection(self):
        self.http_method(url=self.baseurl, verify_ssl=endpoints.verify_ssl, data=self.outputmode,
                         method='DELETE', auth=self.session)

