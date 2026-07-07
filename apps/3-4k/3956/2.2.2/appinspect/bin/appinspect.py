"""
appinspect.py
Handles uploading / sending file as well as building appinspect report
"""
import email
import os
import sys
import json
import base64
import shutil
import logging
import requests
import splunk
import mimetypes
import tarfile
import splunk.entity as entity

from pathlib import Path

def make_error_message(message, session_key, file_name):
    """Creates Error Message"""
    logging.error(message)
    splunk.rest.simpleRequest('/services/messages/new',
                              postargs={'name': 'Appinspect', 'value': '%s - %s' %(file_name, message),
                                        'severity': 'error'},
                              method='POST',
                              sessionKey=session_key)


class Login(splunk.rest.BaseRestHandler):
    """Handles login to Splunk"""

    def authenticate_user(self, request_payload):
        """Authenticates against Splunk's REST API endpoint"""
        payload = json.loads(request_payload)

        try:
            r = requests.get('https://api.splunk.com/2.0/rest/login/splunk',
                             auth=(payload['username'], payload['password']))
        except requests.exceptions.SSLError as e:
            self.response.setHeader('content-type', 'application/json')
            self.response.write(json.dumps({'msg': str(e)}))
            return

        if r.status_code == 200 or r.status_code == 401:
            self.response.setHeader('content-type', r.headers['content-type'])
            self.response.write(json.dumps(r.json()))
        else:
            self.response.setHeader('content-type', 'application/json')
            self.response.write(
                json.dumps({'msg': 'Error receiving data from API. Please try again later.',
                            'status_code': r.status_code}))

    def handle_POST(self):
        """Main Class Function"""
        payload = self.request['payload']
        self.authenticate_user(payload)

    handle_GET = handle_POST


class Upload(splunk.rest.BaseRestHandler):
    """Handles Upload File"""

    tmp_path = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'appinspect', 'local', '_tmp')

    def check_if_tmp_exists(self):
        """Checks if _tmp folder exists, if not, creates it"""
        try:
            if not os.path.exists(self.tmp_path):
                os.makedirs(self.tmp_path)
        except OSError as e:
            message = "Encountered an error while trying to create _tmp: %s" % (str(e))
            make_error_message(message, self.sessionKey, 'appinspect.py')
            sys.exit(0)

    def empty_out_tmp(self):
        """Empties out tmp folder if any files exist in it"""
        # Empty out the _tmp folder if any other files exist
        for the_file in os.listdir(self.tmp_path):
            file_path = os.path.join(self.tmp_path, the_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except OSError as e:
                message = "Encountered an error while trying to empty out _tmp: %s" % (str(e))
                make_error_message(message, self.sessionKey, 'appinspect.py')
                sys.exit(0)

    def create_file(self, file_path, content):
        """Creates the file to be inspected by appinspect"""
        try:
            with open(file_path, "wb") as fh:
                fh.write(base64.b64decode(content))
        except OSError as e:
            self.response.write(json.dumps(e))

    def handle_POST(self):
        """Main Class function"""
        # Remove the uploaded app
        self.response.setHeader('content-type', 'application/json')
        payload = json.loads(self.request['payload'])
        content = payload['content']
        _, name = os.path.split(payload['name'])
        if name == '':
            name = "inspected_splunk_app"
        file_path = os.path.join(self.tmp_path, name)
        response_data = {'file_name': name, 'file_path': file_path}
        self.check_if_tmp_exists()
        self.empty_out_tmp()
        self.create_file(file_path, content)

        if tarfile.is_tarfile(file_path):
            self.response.write(json.dumps(response_data))
        else:
            self.empty_out_tmp()

    handle_GET = handle_POST


class AuthCheck(splunk.rest.BaseRestHandler):
    """Handles sending file to Appinspect API endpoint"""

    def check_token(self, token):
        """Validates app against the appinspect API"""

        base_url = "https://appinspect.splunk.com"
        validate_url = base_url + "/v1/app/validate"
        headers = {"Authorization": "bearer {}".format(token), "max-messages": "all"}

        validate_response = requests.request("POST", validate_url, data={}, headers=headers)
        validate_response_json = validate_response.json()
        response_code = 200
        if 'code' in validate_response_json and validate_response_json["code"] == 'Unauthorized':
            response_code = 403
        validate_response_json["status_code"] = response_code
        return validate_response_json

    def handle_POST(self):
        """Main Class function"""

        payload = json.loads(self.request['payload'])
        token = payload['token']

        response = self.check_token(token)

        self.response.write(json.dumps(response))

    handle_GET = handle_POST



class Inspect(splunk.rest.BaseRestHandler):
    """Handles sending file to Appinspect API endpoint"""

    def validate_app(self, file_name, token):
        """Validates app against the appinspect API"""
        tmp_dir = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'appinspect', 'local',
                               '_tmp')

        file_path = Path(os.path.join(tmp_dir, file_name))

        if str(file_path.parent.absolute()) != tmp_dir:
            self.response.setStatus(500)
            return "Path provided is not intended location for tmp directory!"

        base_url = "https://appinspect.splunk.com"
        validate_url = base_url + "/v1/app/validate"

        try:
            file_handler = open(file_path, "rb")
        except OSError:
            self.response.setStatus(400)
            response = {}
            response["status_code"] = 400
            response["message"] = "File not found. Upload another file."
            return response

        files = {'app_package': file_handler}
        tags_entity = entity.getEntity('/configs/conf-appinspect_settings', 'active',
                                            namespace='appinspect',
                                            owner='nobody',
                                            sessionKey=self.sessionKey)

        self.tags = tags_entity.get('tags')

        fields = {'included_tags': self.tags}

        headers = {"Authorization": "bearer {}".format(token), "max-messages": "all"}



        validate_response = requests.request("POST", validate_url, data=fields, files=files,
                                             headers=headers)
        file_handler.close()

        validate_response_json = validate_response.json()
        response_code = 200
        if 'code' in validate_response_json and validate_response_json["code"] == 'Unauthorized':
            response_code = 403
        validate_response_json["token"] = token
        validate_response_json["file_name"] = file_name
        validate_response_json["status_code"] = response_code

        return validate_response_json

    def handle_POST(self):
        """Main Class function"""

        payload = json.loads(self.request['payload'])
        file_name = payload['file_name']
        token = payload['token']

        response = self.validate_app(file_name, token)

        self.response.write(json.dumps(response))

    handle_GET = handle_POST


class MyDict(dict):
    """Self-referential dict"""

    def __getitem__(self, item):
        """Get Item"""
        return dict.__getitem__(self, item) % self


class CheckStatus(splunk.rest.BaseRestHandler):
    """Checks status, builds and emails report"""
    report_complete = False
    report_file_name = ""
    report_file_path = ""
    reports_path = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'appinspect', 'local',
                                'reports')

    @staticmethod
    def check_status(urls, status_headers):
        """Checks report status from Appinspect API"""
        status_response = requests.get(urls['status_url'], headers=status_headers)
        status_response.raise_for_status()
        if status_response.status_code != 200:
            return status_response
        status_response_json = status_response.json()
        return status_response_json

    def delete_report(self):
        """Deletes reports in reports folder"""
        if os.path.exists(self.reports_path):
            for the_file in os.listdir(self.reports_path):
                file_path = os.path.join(self.reports_path, the_file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except OSError as e:
                    message = "Encountered an error while trying to empty out file from reports folder: %s" % (
                        str(e))
                    make_error_message(message, self.sessionKey, 'appinspect.py')
                    sys.exit(0)

    def handle_POST(self):
        """Checks report status from Appinspect API"""

        # Delete any reports that currently exist in the report folder
        self.delete_report()

        payload = json.loads(self.request['payload'])

        if 'links' in payload:
            urls = MyDict({
                'base_url': "https://appinspect.splunk.com/",
                'status_url': '%(base_url)s' + payload['links'][0]['href'],
                'report_url': '%(base_url)s' + payload['links'][1]['href']
            })
            fields = {
                'token': payload['token'],
                'file_name': payload['file_name']
            }
            status_headers = {"Authorization": "bearer {}".format(fields['token']),
                            "max-messages": "all"}
            report_headers = {"Authorization": "bearer {}".format(fields['token']),
                            "max-messages": "all",
                            "Content-Type": "text/html"}

            while not self.report_complete:
                status_response_json = self.check_status(urls, status_headers)
                if status_response_json['status'] == 'SUCCESS':
                    self.report_complete = True
                    break
                if status_response_json['status'] == 'PROCESSING':
                    self.report_processing = True
                    self.response.setStatus(202)
                    self.response.setHeader('content-type', 'application/json')
                    self.response.write(json.dumps({
                        "message" : "waiting",
                        "status_code" : 202
                    }))
                    break
                if status_response_json['status'] == 'ERROR':
                    self.response.setStatus(500)
                    self.response.setHeader('content-type', 'application/json')
                    self.response.write("Error generating Appinspect report.")
                    break
        else:
            response = json.loads(self.request['payload'])
            self.response.setHeader('content-type', 'application/json')
            self.response.setStatus(400)
            self.response.write(json.dumps({
                'message' : response['message'],
                'status_code' : 400
            }))

        if self.report_complete:
            self.report_file_name = fields['file_name'][0:fields['file_name'].find('.')] + '.html'

            try:
                if not os.path.exists(self.reports_path):
                    os.makedirs(self.reports_path)
            except OSError as e:
                self.response.setStatus(500)
                self.response.write("Cannot create reports path {}".format(e))

            self.report_file_path = os.path.join(self.reports_path, self.report_file_name)

            report_file_path = Path(self.report_file_path)

            if str(report_file_path.parent.absolute()) != self.reports_path:
                self.response.setStatus(500)
                return "Report can not be generated outside of intended path!"

            report_response = requests.request("GET", urls['report_url'], headers=report_headers)

            try:
                with open(self.report_file_path, 'w') as results_file:
                    results_file.write(str(report_response.content))
                results_file.close()
            except OSError as e:
                self.response.setStatus(500)
                self.response.write("Cannot generate report for this app! {}".format(e))

            report_data = {
                'file_name': self.report_file_name,
                'file_content': base64.b64encode(bytes(str(report_response.text).encode('utf-8'))),
                'status_code': 200
            }

            report_data['file_content'] = report_data['file_content'].decode('utf-8')
            self.response.setStatus(200)
            self.response.write(json.dumps(report_data))

    handle_GET = handle_POST
