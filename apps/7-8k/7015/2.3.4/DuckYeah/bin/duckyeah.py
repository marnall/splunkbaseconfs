import http.client
import base64
import io
import json
import os
import platform
import re
import shutil
import ssl
import sys
import tarfile
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import requests
import xmltodict

from requests_toolbelt.multipart.encoder import MultipartEncoder
from splunklib.results import \
    Message, ResultsReader

class duckYeahAPI:
    argument = False
    debug = False

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

        storage_passwords = service.storage_passwords

        credential_name = "duckyeah:%s:" % cmd._metadata.searchinfo.username
        self.credential = False

        for storage_password in storage_passwords.list():
            if storage_password.name == credential_name:
                self.credential = storage_password['clear_password']

        self.service = service
        self.cmd = cmd

        # Load the settings
        jobs = self.service.jobs

        kwargs_blockingsearch = {"exec_mode": "blocking"}
        searchquery_blocking = "| savedsearch duckYeahMungedSettings | fields id value"

        job = jobs.create(searchquery_blocking, **kwargs_blockingsearch)

        while not job.is_done():
            sleep(.2)

        results = ResultsReader(job.results())

        for result in results:
            if isinstance(result, dict):
                self.settings[result['id']] = result['value']

        if self.settings['duckyeah_active_env'] in self.settings:
            self.host = self.settings[self.settings['duckyeah_active_env']]
        else:
            self.host = False

        if self.debug:
            self.host = '127.0.0.1'

        appinfo = service.apps["DuckYeah"]

        ua_string = "DuckYeah/%s (%s)" % (appinfo['state']['content']['version'], platform.platform())

        self.ua = ua_string

    def queryAPI(self, payload=False):
        api_username = self.get_username()

        # if not self.credential:
        #     event = {
        #         'status': 'Error',
        #        'message': 'No API token found. Please complete setup before using the | wizard🪄 command.'
        #     }

        #     return event

        # TODO: Validate the endpoint/query exists

        if not self.host:
            event = {
                'status': 'Error',
                'message': 'No valid environment configured. Please complete setup before using the | wizard🪄 command.'
            }

            return event

        request_url='https://%s/api/1.0/duckyeah/%s' % (self.host, self.query)

        if self.argument:
            request_url = '%s/%s' % (request_url, self.argument)

        if self.attr1:
            request_url = '%s/%s' % (request_url, self.attr1)

        request_headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % self.credential,
            'X-Remote-User': api_username,
            'User-Agent': self.ua,
            'Connection': 'close'
        }

        if self.cmd.session:
            request_headers['X-Session-Id'] = self.cmd.session
        else:
            request_headers['X-Session-Id'] = str(uuid.uuid4())

        if self.debug:
            context = ssl._create_unverified_context()
        else:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS)

        if self.debug:
            connection = http.client.HTTPSConnection(self.host, port=3000, context=context)
        else:
            connection = http.client.HTTPSConnection(self.host, port=443, context=context)

        if payload:
            connection.request(method=self.method, url=request_url, headers=request_headers, body=json.dumps(payload).encode())
        else:
            connection.request(method="GET", url=request_url, headers=request_headers)

        response = connection.getresponse()

        return response

    def process_upload(self, event):
        complex_query = self.query.split("/")

        api_username = self.get_username()

        self.build_upload_file(event)

        files = ('app_package', (self.upload_filename, self.upload_file.getvalue(), 'rb'))
        fields = [files]

        payload = MultipartEncoder(fields=fields)

        request_headers = {
            'Authorization': 'Bearer %s' % self.credential,
            'Cache-Control': 'no-cache',
            'X-Remote-User': api_username,
            'Content-Type': payload.content_type,
            'User-Agent': self.ua,
            'Connection': 'close',
            'Accept': 'application/json, application/gzip, application/octet-stream'
        }

        if self.cmd.session:
            request_headers['X-Session-Id'] = self.cmd.session
        else:
            request_headers['X-Session-Id'] = str(uuid.uuid4())

        if self.debug:
            request_url='https://%s:3000/api/1.0/duckyeah/%s' % (self.host, self.query)
        else:
            request_url='https://%s/api/1.0/duckyeah/%s' % (self.host, self.query)

        if self.argument:
            request_url = '%s/%s' % (request_url, self.argument)

        if self.attr1:
            request_url = '%s/%s' % (request_url, self.attr1)

        if self.debug:
            response = requests.post(request_url, data=payload, headers=request_headers, verify=False)
        else:
            response = requests.request('POST', request_url, data=payload, headers=request_headers)

        content_type = response.headers['content-type']

        if content_type != 'application/json':
            event['cwd'] = os.getcwd()

            d = response.headers['content-disposition']
            fname = re.findall("filename=\"(.+)\"", d)[0]

            content = response.content

            open(os.path.join('packages', '%s' % fname), 'wb').write(response.content)

            if event['preserve_local'] == "0":
                if os.path.exists(os.path.join(os.path.sep, os.environ['SPLUNK_HOME'], 'etc', 'apps', event['app'], 'local')):
                    shutil.rmtree(os.path.join(os.path.sep, os.environ['SPLUNK_HOME'], 'etc', 'apps', event['app'], 'local'))

                if os.path.exists(os.path.join(os.path.sep, os.environ['SPLUNK_HOME'], 'etc', 'apps', event['app'], 'metadata', 'local.meta')):
                    os.remove(os.path.join(os.path.sep, os.environ['SPLUNK_HOME'], 'etc', 'apps', event['app'], 'metadata', 'local.meta'))

            params = {
                "configured": 1,
                "filename": True,
                "name": os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'DuckYeah', 'bin', 'packages', '%s' % fname),
                "update": True
            }

            self.service.post('apps/local', **params)

            event['uploaded'] = True
            event['upload_resp'] = {}
            event['package_file'] = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'DuckYeah', 'bin', 'packages', '%s' % fname)
        else:
            event['json'] = True
            self.response = response.json()

    def build_upload_file(self, event):
        ignore_manifest = [
            ".DS_Store",
            ".git",
            ".gitignore",
            "package.py",
            "app_pack",
            "AppPack_Local.json",
            "backup.sh",
            "reset.sh",
            "default_backup",
            "local_backup",
            "metadata_backup",
            "node_modules",
            "src",
            "package.json",
            "package-lock.json",
            "webpack.config.js",
            "__pycache__",
            "dist",
            "tmp"
        ]

        arc_name = "%s.tgz" % event['session_id']

        app_home = os.path.join(os.path.sep, os.environ['SPLUNK_HOME'], 'etc', 'apps', event['app'])

        event['arc_name'] = arc_name

        fh = io.BytesIO()

        og_dir = os.getcwd()
        os.chdir(app_home)

        with tarfile.open(fileobj=fh, mode='w:gz', encoding='utf-8') as f:
            for root, dirs, files in os.walk('.'):
                for file in files:
                    ignore_segment = False
                    parent_path = root.split(os.path.sep)
        
                    for segment in parent_path:
                       if segment in ignore_manifest:
                           ignore_segment = True

                    if 'default.old' in root:
                        continue

                    if file[-3:] == "swp":
                        continue

                    # There may eventually be a valid use case for this; we'll see.
                    if file[-3:] == "tgz":
                        continue

 
                    if file in ignore_manifest or ignore_segment:
                        # Don't log these global ignores.
                        continue
            
                    #if file in self.config['ignore_files']:
                    #    self.warn('Ignoring %s due to local override.' % file)
                    #    continue
                    
                    addfile = os.path.join(root, file)

                    locallead = '.%s' % os.path.sep

                    if addfile[0:2] == locallead:
                        addfile = addfile[2:]
                
                    #self.debug('Adding [%s] to archive.' % addfile)
                    f.add(addfile, arcname=os.path.join(
                        os.path.sep,
                        event['app'],
                        addfile
                    ))

        self.upload_file = fh
        self.upload_filename = arc_name

        os.chdir(og_dir)


    def get_username(self):
        search_username = self.cmd._metadata.searchinfo.username

        api_username = None

        if search_username == 'splunk-system-user':
            api_username = 'splunk-system-user'
        else:
            resp = self.service.get('authentication/users')

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

        return api_username
