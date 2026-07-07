#!/usr/bin/python
# -*- coding: utf-8 -*-
# -----------------------------------------
# Phantom App Connector python file
# -----------------------------------------

# Python 3 Compatibility imports
from __future__ import print_function, unicode_literals

import json
import time

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector


class RetVal(tuple):

    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class CadoResponseConnector(BaseConnector):

    def __init__(self):
        super(CadoResponseConnector, self).__init__()

        self._state = None
        self._base_url = None
        # self._refresh_token = None
        self._access_token = None
        self._default_project = None
        self._default_bucket = None
        self._default_region = None

    def _process_empty_response(self, response, action_result):
        ''' Process empty response from rest call
        '''
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(
                phantom.APP_ERROR, "Empty response and no information in the header"
            ), None
        )

    def _process_html_response(self, response, action_result):
        ''' Process an HTML response, do this no matter what the api talks.
        There is a high chance of a PROXY in between phantom and the rest of
        world, in case of errors, PROXY's return HTML, this function parses
        the error and adds it to the action_result.
        '''

        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split('\n')
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = '\n'.join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = "Status Code: {0}. Data from server:\n{1}\n".format(status_code, error_text)

        message = message.replace(u'{', '{{').replace(u'}', '}}')
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        ''' Process json response from the rest call
        '''

        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR, "Unable to parse JSON response. Error: {0}".format(str(e))
                ), None
            )

        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        message = "Error from server. Status Code: {0} Data from server: {1}".format(
            r.status_code,
            r.text.replace(u'{', '{{').replace(u'}', '}}')
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        ''' Handle response from the rest call
        '''

        # Store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, 'add_debug_data'):
            action_result.add_debug_data({'r_status_code': r.status_code})
            action_result.add_debug_data({'r_text': r.text})
            action_result.add_debug_data({'r_headers': r.headers})

        # Process a json response
        if 'json' in r.headers.get('Content-Type', ''):
            return self._process_json_response(r, action_result)

        # Process an HTML response, do this no matter what the api talks.
        if 'html' in r.headers.get('Content-Type', ''):
            return self._process_html_response(r, action_result)

        # If it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_response(r, action_result)

        # Handle everything else
        message = "Can't process response from server. Status Code: {0} Data from server: {1}".format(
            r.status_code,
            r.text.replace('{', '{{').replace('}', '}}')
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, method="get", **kwargs):
        ''' Make rest call to Cado Response
        '''

        config = self.get_config()
        resp_json = None

        if 'headers' not in kwargs:
            kwargs['headers'] = {'Authorization': f'Bearer {self._access_token}'}

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, "Invalid method: {0}".format(method)),
                resp_json
            )

        # Create a URL to connect to
        url = self._base_url + endpoint

        try:
            r = request_func(
                url,
                verify=config.get('verify_server_cert', False),
                **kwargs
            )
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR, "Error Connecting to server. Details: {0}".format(str(e))
                ), resp_json
            )

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):
        ''' Test connectivity to Cado Response asset
        '''

        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress("Connecting to endpoint")

        ret_val, response = self._make_rest_call(
            '/notifications', action_result, params=None
        )

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed.")
            return action_result.get_status()

        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_pipelines(self, param):
        ''' Get all pipelines in specified project
        '''

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))
        project_id = param['project_id']

        ret_val, response = self._make_rest_call(
            f'/tasks/pipelines?project_id={project_id}',
            action_result,
            params=None,
            method="get"
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        pipeline_info = response
        action_result.add_data(pipeline_info)
        self.save_progress(f"Returned pipeline info is: {pipeline_info}")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_pipeline(self, param):
        ''' Get pipeline details from specified pipeline ID
        '''

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))
        pipeline_id = param['pipeline_id']

        # make rest call
        ret_val, response = self._make_rest_call(
            f'/tasks/pipelines?pipeline_id={pipeline_id}',
            action_result,
            params=None,
            method="get"
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        pipeline_info = response
        action_result.add_data(pipeline_info)
        self.save_progress(f"Returned pipeline info is: {pipeline_info}")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_loop_pipeline(self, param, max_timeout=86400):
        ''' Loop over pipeline until terminated
        '''

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))

        pipeline_terminated = False
        pipeline_timeout = 0

        while not pipeline_terminated or pipeline_timeout >= max_timeout:
            response = self._get_pipeline(param, action_result)[1]

            action_result.add_data(response)

            self.save_progress(f"Returned pipeline info is: {response}")
            self.save_progress(f"Pipeline terminated: {response['terminated']}")

            pipeline_terminated = response['terminated']

            if not pipeline_terminated:
                pipeline_terminated += 60
                time.sleep(60)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_pipeline(self, param, action_result):
        ''' Get pipeline details from specified pipeline ID
        '''

        pipeline_id = param['pipeline_id']

        response = self._make_rest_call(
            f'/tasks/pipelines?pipeline_id={pipeline_id}',
            action_result,
            params=None,
            method="get"
        )

        return response

    def _handle_list_projects(self, param):
        ''' Get list of all projects
        '''

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))

        ret_val, response = self._make_rest_call(
            '/projects/',
            action_result,
            params=None
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        project_info = [{'id': project['id'], 'case_name': project['caseName']} for project in response]
        action_result.add_data(project_info)
        self.save_progress(f"Returned project info is: {project_info}")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_create_project(self, param):
        ''' Create a new project with specified project name
        '''

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))
        project = param['project_name']
        self.save_progress(project)

        data = {"caseName": project}

        ret_val, response = self._make_rest_call(
            '/projects',
            action_result,
            params=None,
            method="post",
            json=data
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        project_info = {'id': response['id'], 'msg': response['msg']}
        action_result.add_data(project_info)
        self.save_progress(f"RESPONSE DATA IS: {response}")
        self.save_progress(f"RETURNED PROJECT INFO IS: {project_info}")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_ec2(self, param):
        ''' Get a list of available instances in a region and role
        '''

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))

        # make rest call
        ret_val, response = self._make_rest_call(
            f'/projects/{param["project_id"]}/imports/ec2',
            action_result,
            params=None
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        aws_info = []
        for aws in response['instances']:
            aws_info.append({'placement': aws['_placement'], 'state': aws['_state'], 'id': aws['id'], 'instance_name': aws['instance_name'], 'ip_addr': aws['ip_address'],
            'instance_type': aws['instance_type'], 'region': aws['region']['name']})
        action_result.add_data(aws_info)
        self.save_progress(f"RETURNED AWS INFO DETAILS: {aws_info}")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_bucket(self, param):
        ''' Retrieve s3 buckets
        if bucket query parameter is provided, return all files in the given bucket
        and if not provided, return list of all buckets in the aws environemt
        '''
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        self.save_progress("Getting action result")
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress("Get action result")

        project_id = param['project_id']

        # Make rest call
        ret_val, response = self._make_rest_call(
            f'/projects/{project_id}/imports/s3',
            action_result,
            params=None
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        bucket_info = [{'bucket_name': buckets} for buckets in response['buckets']]
        action_result.add_data(bucket_info)
        self.save_progress(f"RETURNED AWS INFO DETAILS: {bucket_info}")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_capture_ec2(self, param):
        ''' Create EC2 Acquiring task
        Create a new task to acquriing new AWS EC2 Instance as a new
        evidence in the platform based on the given parameters
        '''

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        self.save_progress("Getting action result")
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress("Get action result")

        project_id = param['project_id']
        instance_id = param['instance_id']
        region = param['region']

        data = {
            'instance_id': instance_id,
            'region': region,
            'include_disks': 'True',
            'include_logs': 'True',
            'include_screenshot': 'True',
            'compress': 'True',
            'include_hash': 'False'
        }

        # make rest call
        ret_val, response = self._make_rest_call(
            f'/projects/{str(project_id)}/imports/ec2',
            action_result,
            params=None,
            method="post",
            json=data
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        acquire_info = response
        action_result.add_data(acquire_info)
        self.save_progress(f"RETURNED ACQUIRE INFO IS: {acquire_info}")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_capture_bucket(self, param):
        ''' Create S3 bucket acquire task
        Create a new task to acquiring new evidence from S3 bucket.
        can acquire the entire s3 bucket or a specefic file
        '''

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        action_result = self.add_action_result(ActionResult(dict(param)))

        project_id = param['project_id']
        bucket = param['bucket']

        data = {'bucket': f'{bucket}', 'as_single_items': 'yes'}

        # make rest call
        ret_val, response = self._make_rest_call(
            f'/projects/{str(project_id)}/imports/s3',
            action_result,
            params=None,
            method="post",
            json=data
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        acquire_info = [{'pipelines': pipeline} for pipeline in response['pipelines']]
        action_result.add_data(acquire_info)
        self.save_progress(f"RETURNED ACQUIRE INFO IS: {acquire_info}")

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ''' Call relevant handler for specified action
        '''

        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == 'test_connectivity':
            ret_val = self._handle_test_connectivity(param)

        elif action_id == 'list_projects':
            ret_val = self._handle_list_projects(param)

        elif action_id == 'create_project':
            ret_val = self._handle_create_project(param)

        elif action_id == 'list_instances':
            ret_val = self._handle_list_ec2(param)

        elif action_id == 'list_buckets':
            ret_val = self._handle_list_bucket(param)

        elif action_id == 'list_pipelines':
            ret_val = self._handle_list_pipelines(param)

        elif action_id == 'get_pipeline':
            ret_val = self._handle_get_pipeline(param)

        elif action_id == 'loop_pipeline':
            ret_val = self._handle_loop_pipeline(param)

        elif action_id == 'capture_instance':
            ret_val = self._handle_capture_ec2(param)

        elif action_id == 'capture_bucket':
            ret_val = self._handle_capture_bucket(param)

        elif action_id == 'fresh_token':
            ret_val = self._handle_get_fresh_token(param)

        return ret_val

    def initialize(self):
        ''' Load the state in initialize, use it to store data
        that needs to be accessed across actions.
        '''

        self._state = self.load_state()

        config = self.get_config()

        self._base_url = config.get('base_url')
        self._access_token = config.get('access_token')
        self._default_project = config.get('default_project')
        self._default_bucket = config.get('default_bucket')
        self._default_region = config.get('default_region')

        return phantom.APP_SUCCESS

    def finalize(self):
        ''' Save the state, this data is saved across actions and app upgrades
        '''

        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument('input_test_json', help='Input Test JSON file')
    argparser.add_argument('-u', '--username', help='username', required=False)
    argparser.add_argument('-p', '--password', help='password', required=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password

    if username is not None and password is None:

        # User specified a username but not a password, so ask
        import getpass
        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = CadoResponseConnector._get_phantom_base_url() + '/login'

            print("Accessing the Login page")
            r = requests.get(login_url, verify=False)
            csrftoken = r.cookies['csrftoken']

            data = dict()
            data['username'] = username
            data['password'] = password
            data['csrfmiddlewaretoken'] = csrftoken

            headers = dict()
            headers['Cookie'] = 'csrftoken=' + csrftoken
            headers['Referer'] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=False, data=data, headers=headers)
            session_id = r2.cookies['sessionid']
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = CadoResponseConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json['user_session_token'] = session_id
            connector._set_csrf_info(csrftoken, headers['Referer'])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    exit(0)


if __name__ == '__main__':
    main()
