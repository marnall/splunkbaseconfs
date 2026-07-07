from splunk.persistconn.application import PersistentServerConnectionApplication
import json
import sys, os
import six
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".", "BaseClient"))
from baseclient import BaseClient
import endpoints


class Indexes(PersistentServerConnectionApplication, BaseClient):

    def __init__(self, command_line, command_arg):
        self.session = ()
        self.url = ''
        self.baseurl = ''
        self.res = None
        self.indexs = []
        self.outputmode = {
            'output_mode': 'json'
        }
        self.data = {
            'max_count': '50000',
            'status_buckets': '300',
            'search': '| eventcount summarize=false index=* index=_* | dedup index | fields index',
            'output_mode': 'json'
        }
        self.endpoint = "results/"
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        args = json.loads(in_string)
        content = json.loads(args['payload'])
        self.url = content['url']
        self.session = (content['username'], content['password'])
        endpoints.verify_ssl = content.get('verify_ssl')
        url = self.url + endpoints.const_conf
        ssl = {
            'value': endpoints.verify_ssl
        }
        self.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=ssl, method='POST', auth=self.session)
        self.baseurl = content['url'] + endpoints.baseurl
        self.get_indexes()
        return {'payload': self.indexs,
                'status': 200}

    def get_indexes(self):
        """This function gets a list of all index in splunk enterprise"""
        query = {'search': '| eventcount summarize=false index=* index=_* | dedup index | fields index'}
        data = endpoints.data
        data.update(query)
        search_job = self.http_method(url=self.baseurl, verify_ssl=endpoints.verify_ssl, data=data, auth=self.session,
                                      method='POST')
        search_job = search_job.json()
        self.baseurl = self.baseurl + search_job['sid'] + '/'
        search_job = self.http_method(url=self.baseurl, verify_ssl=endpoints.verify_ssl, data=self.outputmode,
                                      method='GET', auth=self.session)
        self.res = search_job.json()
        while not self.res['entry'][0]['content']['isDone']:
            search_job = self.http_method(url=self.baseurl, verify_ssl=endpoints.verify_ssl, data=self.outputmode,
                                          method='GET', auth=self.session)
            self.res = search_job.json()
        else:
            self.baseurl = self.baseurl + self.endpoint
            search_job = self.http_method(url=self.baseurl, verify_ssl=endpoints.verify_ssl, data=self.outputmode,
                                          method='GET', auth=self.session)
            self.res = search_job.json()
            self.res = self.res['results']

        for x in self.res:
            self.indexs.append(x['index'])
