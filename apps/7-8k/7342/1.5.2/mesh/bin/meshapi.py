import http.client
import json
import os
import platform
import ssl
import sys
import uuid

# TODO: For Now
from pprint import pprint

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import xmltodict

from splunklib.results import \
    Message, ResultsReader

class meshAPI:
    argument = False

    def __init__(self, service, query, cmd, method='GET'):
        self.argument = False
        self.attr1 = False
        self.method = method
        self.settings = {}

        if '/' in query:
            complex_query = query.split('/')

            self.query = complex_query[0]

            if 1 < len(complex_query):
                self.argument = complex_query[1]

            if 2 < len(complex_query):
                self.attr1 = complex_query[2]

        else:
            self.query = query

        self.certificate_file = os.path.join(sys.path[0], '..', 'auth', 'mesh.crt')
        self.certificate_keyfile = os.path.join(sys.path[0], '..', 'auth', 'mesh.key')

        storage_passwords = service.storage_passwords

        credential_name = "mesh:mesh:"
        self.credential = False

        for storage_password in storage_passwords.list():
            if storage_password.name == credential_name:
                self.credential = storage_password['clear_password']

        self.service = service
        self.cmd = cmd

        # Load the settings
        jobs = self.service.jobs

        kwargs_blockingsearch = {"exec_mode": "blocking"}
        searchquery_blocking = "| savedsearch meshMungedSettings | fields id value"

        job = jobs.create(searchquery_blocking, **kwargs_blockingsearch)

        while not job.is_done():
            sleep(.2)

        results = ResultsReader(job.results())

        for result in results:
            if isinstance(result, dict):
                self.settings[result['id']] = result['value']

        if self.settings['mesh_active_env'] in self.settings:
            self.host = self.settings[self.settings['mesh_active_env']]
        else:
            self.host = False

        appinfo = service.apps["mesh"]

        ua_string = "mesh/%s (%s)" % (appinfo['state']['content']['version'], platform.platform())

        self.ua = ua_string

    def queryAPI(self, payload=False):
        # Holy shit. So this isn't documented and we learned how to identify this with 3 hours of trial-and-error
        # Good thing we can see the Splunk logs, the API logs, and the search command logs... oof.

        search_username = self.cmd._metadata.searchinfo.username

        api_username = None

        if search_username == 'splunk-system-user':
            api_username = 'splunk-system-user'
        else:
            resp = self.service.get('authentication/users/%s' % search_username)

            resp_json = xmltodict.parse(resp.body.read())

            if type(resp_json['feed']['entry']) is dict:
                iterate_users = [resp_json['feed']['entry']]
            else:
                iterate_users = resp_json['feed']['entry']

            for user in iterate_users:
                if 'title' in user and user['title'] == search_username:
                    if 'content' in user and 's:dict' in user['content'] and 's:key' in user['content']['s:dict']:
                        for param in user['content']['s:dict']['s:key']:
                            if '@name' in param and '#text' in param:
                                if param['@name'] == 'email':
                                    api_username = param['#text']

        if not self.credential:
            event = {
                'status': 'Error',
                'message': 'No API token found. Please complete setup before using the | mesh command.'
            }

            return event

        # TODO: Validate the endpoint/query exists

        if not self.host:
            event = {
                'status': 'Error',
                'message': 'No valid environment configured. Please complete setup before using the | mesh command.'
            }

            return event

        splunk_env = self.service.get('server/info')

        resp_json = xmltodict.parse(splunk_env.body.read())

        product_type = None

        if 'feed' in resp_json and 'entry' in resp_json['feed'] and 'content' in resp_json['feed']['entry']:
            inner_content = resp_json['feed']['entry']['content']

            if 's:dict' in inner_content and 's:key' in inner_content['s:dict']:
                for param in inner_content['s:dict']['s:key']:
                    if '@name' in param and '#text' in param:
                        if param['@name'] == 'product_type':
                            product_type = param['#text']

                # Why, oh why, would you do this, Splunk?!
                for param in inner_content['s:dict']['s:key']:
                    if '@name' in param and '#text' in param:
                        if param['@name'] == 'instance_type':
                            product_type = param['#text']

        if not product_type:
            product_type='unknown'

        request_url='https://%s/api/1.0/customer/%s' % (self.host, self.query)

        if self.argument:
            request_url = '%s/%s' % (request_url, self.argument)

        if self.attr1:
            request_url = '%s/%s' % (request_url, self.attr1)

        request_headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % str(self.credential),
            'X-Remote-User': str(api_username),
            'X-Splunk-Type': str(product_type),
            'User-Agent': str(self.ua),

        }

        if self.cmd.view_id:
            request_headers['X-View-Id'] = str(self.cmd.view_id)
        else:
            request_headers['X-View-Id'] = 'None'

        if self.cmd.view_session:
            # request_headers['X-View-Session'] = self.cmd.view_session
            request_headers['X-View-Session'] = str(self.cmd.view_session)
        else:
            request_headers['X-View-Session'] = str(uuid.uuid4())

        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            context.load_cert_chain(certfile=self.certificate_file, keyfile=self.certificate_keyfile) #, password=certificate_secret)
        except FileNotFoundError:
            self.cmd.error_exit("error", "No certificate files found.")

        # connection = http.client.HTTPSConnection(self.host, port=443, context=context)
        connection = http.client.HTTPSConnection('api.cloud.nthdegree.io', port=443, context=context)

        if payload:
            connection.request(method=self.method, url=request_url, headers=request_headers, body=json.dumps(payload).encode())
        else:
            connection.request(method=self.method, url=request_url, headers=request_headers)
        response = connection.getresponse()

        return response
