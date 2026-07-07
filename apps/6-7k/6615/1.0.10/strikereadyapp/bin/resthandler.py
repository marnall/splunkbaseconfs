from splunk.persistconn.application import PersistentServerConnectionApplication
from multiprocessing import Process

import json
import threading
import time
import copy
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".", "BaseClient"))
from baseclient import BaseClient
import endpoints


class StrikeReady(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        self.search_ioc = SearchIoc()
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        search_process = Process(target=self.search_ioc.start_search, args=(in_string,))
        search_process.start()
        return {'payload': {'status': "SEARCH IN PROGRESS"},
                'status': 200
                }


class SearchIoc(BaseClient):

    def __init__(self):
        self.user = ''
        self.passw = ''
        self.session = None
        self.url = ''
        self.baseurl = endpoints.baseurl
        self.sids = []
        self.ioc = []
        self.matched_ioc = []
        self.endpoint = "results/"
        self.outputmode = {
            'output_mode': 'json'
        }
        self.minutes = 'minutesago={}'
        self.days = 'daysago={}'
        self.job_tag = {
            'job_tag': "Prioritize IOC"
        }
        self.thread = []
        self.index = []

    def start_search(self, in_string):
        args = json.loads(in_string)
        content = json.loads(args['payload'])

        self.user = content['username']
        self.passw = content['password']
        endpoints.verify_ssl = content.get('verify_ssl')
        self.session = (self.user, self.passw)
        self.url = content['url']
        url = self.url + endpoints.const_conf
        ssl = {
            'value': endpoints.verify_ssl
        }
        self.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=ssl, method='POST', auth=self.session)
        self.baseurl = self.url + self.baseurl
        self.index = content['index']
        self.make_searches(content)

    def make_searches(self, content):

        ioc_values = content['ioc']

        self.create_pass_conf()
        self.create_collections()

        ioc_values = self.ioc_chunking(ioc_values, 10000)

        for i in ioc_values:
            i = self.ioc_chunking(i, 500)
            self.thread.clear()
            for sub_list in i:
                self.init_search(sub_list, content)
            for t in self.thread:
                t.join()

            d = {
                'script': '//$SPLUNK_HOME/etc/apps/strikereadyapp/bin/database.py'
            }
            url = self.url + endpoints.database_restart
            self.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=d, method='POST', auth=self.session)

    def search_iocs(self, sublist, content):
        search = self.query_const()

        if content['time'] == 'day':
            self.days = self.days.format(content['duration'])
            search = search + self.days

        if content['time'] == 'minutes':
            self.minutes = self.minutes.format(content['duration'])
            search = search + self.minutes

        search2 = ' | stats '
        s = '({})'
        s1 = ""

        for x in sublist:
            v = x['value']
            x.update(self.job_tag)
            d = {
                'ioc': x,
            }
            url = self.url + endpoints.ioc_collection
            self.http_method(url=url, verify_ssl=endpoints.verify_ssl, req_json=d, method='POST',
                             auth=self.session)

            search1 = '"{}" OR '
            search1 = search1.format(v)
            s1 = s1 + search1
            search3 = 'count(eval(searchmatch("{}"))) as {} ,'
            search3 = search3.format(v, v)
            search2 = search2 + search3

        s1 = s1.rstrip("OR ")
        s = s.format(s1)
        search2 = search2.rstrip(" ,")
        search = search + s + search2
        data = {
            'max_count': '50000',
            'status_buckets': '300',
            'search': search,
            'output_mode': 'json'
        }

        searchjob = self.http_method(url=self.baseurl, verify_ssl=endpoints.verify_ssl, data=data,
                                     method='POST', auth=self.session)
        searchjob = searchjob.json()

        res = self.get_result(searchjob['sid'])
        for a in res:
            if res[a] != '0':
                self.matched_ioc.append(a)
                self.get_events(a)

    def get_result(self, sid):
        url = endpoints.get_result
        url = url.format(sid)
        url = self.url + url
        search_job = self.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=self.outputmode,
                                      method='GET', auth=self.session)
        res = search_job.json()

        while not res['entry'][0]['content']['isDone']:
            time.sleep(5)
            search_job = self.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=self.outputmode,
                                          method='GET', auth=self.session)
            res = search_job.json()
        else:
            url1 = url + self.endpoint
            search_job = self.http_method(url=url1, verify_ssl=endpoints.verify_ssl, data=self.outputmode,
                                          method='GET', auth=self.session)
            res = search_job.json()
            return res['results'][0]

    def ioc_chunking(self, ioc, ioc_count):
        """Creates chunks of list based on ioc count"""
        return [ioc[i:i + ioc_count] for i in range(0, len(ioc), ioc_count)]

    def init_search(self, sub_list, content):
        tg = threading.Thread(target=self.search_iocs, args=[sub_list, content])
        self.thread.append(tg)
        tg.start()

    def create_collections(self):
        url = self.url + endpoints.create_collection
        d = {
            'name': 'IOC',
        }
        self.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=d, method='POST', auth=self.session)

        d = {
            'name': 'result',
        }
        self.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=d, method='POST', auth=self.session)

        d = {
            'name': 'Index',
        }
        self.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=d, method='POST', auth=self.session)

        url = self.url + endpoints.index_collection
        index = self.http_method(url=url, verify_ssl=endpoints.verify_ssl, req_json=self.outputmode, method='GET',
                                 auth=self.session)

        index = index.json()
        ind = []
        if len(index) == 0:
            ind = self.index
        else:
            for x in index:
                ind.append(x['index'])
            temp = set(self.index).intersection(ind)
            ind = copy.deepcopy(self.index)
            for n in temp:
                ind.remove(n)
        for x in ind:
            dat = {
                'index': x,
            }
            url = self.url + endpoints.index_collection
            self.http_method(url=url, verify_ssl=endpoints.verify_ssl, req_json=dat, method='POST', auth=self.session)

    def create_pass_conf(self):
        sec = {
            'name': self.user,
            'password': self.passw,
            'realm': self.url,
            'output_mode': 'json'
        }
        url = self.url + endpoints.password_conf
        self.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=sec, method='POST', auth=self.session)

    def query_const(self):
        search = 'search index={} '
        inde = ""



        for index in self.index:
            ind = ' "{}" OR'
            ind = ind.format(index)
            inde = inde + ind

        inde = inde.rstrip('OR')
        search = search.format(inde)
        return search

    def get_events(self, ioc):
        search = self.query_const()
        sid = " {}"
        sid = sid.format(ioc)
        search = search + sid
        data = {
            'max_count': '50000',
            'status_buckets': '300',
            'search': search,
            'output_mode': 'json'
        }

        searchjob = self.http_method(url=self.baseurl, verify_ssl=endpoints.verify_ssl, data=data,
                                     method='POST', auth=self.session)

        searchjob = searchjob.json()
        res = self.get_result(searchjob['sid'])
        self.store_results(ioc, res)

    def store_results(self, ioc, result):
        d = {
            ioc: result,
        }
        url = self.url + endpoints.result_collection
        self.http_method(url=url, verify_ssl=endpoints.verify_ssl, req_json=d, method='POST',
                         auth=self.session)
