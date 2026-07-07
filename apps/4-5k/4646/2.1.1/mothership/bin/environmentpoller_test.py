import json
import uuid
import time
from time import sleep
from six.moves.urllib.parse import urlparse
import splunklib.client as client
import splunk.auth as auth
import test_runner
import environment_searches_schema

username = ''
password = ''
mgmt_scheme_host_port = ''

class Test(test_runner.TestRESTHandler):
    #### SETUP AND TEARDOWN #####
    def setUp(self):
        self.session_key = auth.getSessionKey(username, password)

        # parse splunkd management host port scheme
        parsed_url = urlparse(mgmt_scheme_host_port)
        environment_host = parsed_url.netloc.split(':')[0]
        environment_port = parsed_url.port
        environment_scheme = parsed_url.scheme

        # create sdk service
        self.service = client.connect(
            host=environment_host,
            port=environment_port,
            username=username,
            password=password,
            scheme=environment_scheme,
            app='mothership',
            owner=username,
        )

        self.name = uuid.uuid4().hex
        environment_postargs = {
            'name': self.name,
            'mgmt_scheme_host_port': mgmt_scheme_host_port,
            'username': username,
            'password': password,
        }
        response, content = self.create_helper('environments', environment_postargs)
        payload = json.loads(content)
        self.environment_link_alternate = payload['entry'][0]['links']['alternate']

    def test_search_command_with_transforming_environment_search_timeout(self):
        # create transforming environment search
        environment_search_postargs = {
            'name': self.name,
            'label': self.name,
            'search': '| makeresults | eval field="value" | fields - _time | sleepy seconds=300',
            'type': 'inline',
            'environment_link_alternate': self.environment_link_alternate
        }
        response, content = self.create_helper('environment_searches', environment_search_postargs)
        payload = json.loads(content)
        environment_search_link_alternate = payload['entry'][0]['links']['alternate']

        # search to run
        search_string = """
                | environmentpoller environment_search_link_alternate=%s
                """ % environment_search_link_alternate
        search_params = {
            'exec_mode': 'normal',
            'count': 0,
            'earliest_time': '-1d',
            'latest_time': 'now',
        }

        # dispatch search and wait for completion
        did_timeout = False
        try:
            job = self.search_job(search_string, search_params)
        except Exception as e:
            did_timeout = True

        self.assertTrue(did_timeout, msg='Did timeout')

    def test_search_command_with_transforming_environment_search(self):
        # create transforming environment search
        environment_search_postargs = {
            'name': self.name,
            'label': self.name,
            'search': '| makeresults count=2 | eval field="value"',
            'type': 'inline',
            'environment_link_alternate': self.environment_link_alternate
        }
        response, content = self.create_helper('environment_searches', environment_search_postargs)
        payload = json.loads(content)
        environment_search_link_alternate = payload['entry'][0]['links']['alternate']

        # search to run
        search_string = """
        | environmentpoller environment_search_link_alternate=%s
        """ % environment_search_link_alternate
        search_params = {
            'exec_mode': 'normal',
            'count': 0,
            'earliest_time': '-1d',
            'latest_time': 'now',
        }

        # dispatch search and wait for completion
        job = self.search_job(search_string, search_params)

        # retrieve results
        result = job.results(count='0', offset=0, output_mode='json', time_format='%s')
        response = json.loads(result.read())
        result = response['results'][0]

        # test results are expected values
        self.assertEqual(result.get('environment_link_alternate'), self.environment_link_alternate, msg='environment link alternate is expected value.')
        self.assertEqual(result.get('environment_searches_link_alternate'), environment_search_link_alternate, msg='environment search link alternate is expected value.')
        self.assertEqual(result.get('report_search'), '1', msg='Report search returned from environment search.')
        self.assertEqual(result.get('results_count'), '2', msg='Two results returned from environment search.')

        # retrieve environment search and meta information
        response, content = self.read_helper('environment_searches', self.name)
        payload = json.loads(content)
        lookup_name = payload['entry'][0]['content']['lookup_name']

        # run search against lookup
        search_string = "| inputlookup %s" % lookup_name
        job = self.search_job(search_string, search_params)

        # assert results are expected values
        result = job.results(count='0', offset=0, output_mode='json', time_format='%s')
        response = json.loads(result.read())
        self.assertEqual(len(response['results']), 2, 'results length is correct')
        self.assertEqual(response['results'][0].get('field'), 'value', 'first result has expected field')
        self.assertEqual(response['results'][1].get('field'), 'value', 'second result has expected field')

    def test_search_command_with_non_transforming_environment_search(self):
        # create transforming environment search
        environment_search_postargs = {
            'name': self.name,
            'label': self.name,
            'search': 'index="_internal" sourcetype=splunkd component=Metrics log_level=INFO | head 2',
            'type': 'inline',
            'environment_link_alternate': self.environment_link_alternate
        }
        response, content = self.create_helper('environment_searches', environment_search_postargs)
        payload = json.loads(content)
        environment_search_link_alternate = payload['entry'][0]['links']['alternate']

        # search to run
        search_string = """
        | environmentpoller environment_search_link_alternate=%s
        """ % environment_search_link_alternate
        search_params = {
            'exec_mode': 'normal',
            'count': 0,
            'earliest_time': '-1d',
            'latest_time': 'now',
            'rf': '*',
        }

        # dispatch search and wait for completion
        job = self.search_job(search_string, search_params)

        # retrieve results
        result = job.results(count='0', offset=0, output_mode='json', time_format='%s')
        response = json.loads(result.read())
        result = response['results'][0]

        # test results are expected values
        self.assertEqual(result.get('environment_link_alternate'), self.environment_link_alternate, msg='environment link alternate is expected value.')
        self.assertEqual(result.get('environment_searches_link_alternate'), environment_search_link_alternate, msg='environment search link alternate is expected value.')
        self.assertEqual(result.get('report_search'), '0', msg='Report search returned from environment search.')
        self.assertEqual(result.get('results_count'), '2', msg='Two results returned from environment search.')

        # retrieve environment search and meta information
        response, content = self.read_helper('environment_searches', self.name)
        payload = json.loads(content)
        index_name = payload['entry'][0]['content']['index']

        # run search against lookup
        search_string = 'search index="%s" | head 2' % index_name
        job = self.search_job(search_string, search_params)

        # assert results are expected values
        result = job.results(count='0', offset=0, output_mode='json', time_format='%s')
        response = json.loads(result.read())

        self.assertEqual(len(response['results']), 2, 'results length is correct')
        self.assertEqual(response['results'][0].get('log_level'), 'INFO', 'first result has expected field')
        self.assertEqual(response['results'][1].get('log_level'), 'INFO', 'second result has expected field')

    def search_job(self, search_string, search_params):
        # dispatch search and wait for completion
        job = self.service.jobs.create(search_string, **search_params)
        while True:
            while not job.is_ready():
                pass
            if job["isDone"] == "1":
                break
            sleep(1)
        return job

    def tearDown(self):
        # Delete environment
        response, content = self.delete_helper('environments', self.name)
        response, content = self.delete_helper('environment_searches', self.name)

if __name__ == '__main__':
    args = test_runner.cli_arguments()
    username = args.username
    password = args.password
    mgmt_scheme_host_port = args.mgmt_scheme_host_port
    test_runner.run_test(Test)
