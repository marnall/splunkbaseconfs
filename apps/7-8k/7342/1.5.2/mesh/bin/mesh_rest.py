#!/usr/bin/env python

import os

os.chdir(os.path.join(os.environ['SPLUNK_HOME'], "etc", "apps", "mesh", "bin"))

import base64
import io
import json
import math
import requests
import ssl
import sys
import time

# from splunk.persistconn.application import PersistentServerConnectionApplication
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from splunk.persistconn.application import PersistentServerConnectionApplication

import certifi
import splunklib.client as client
import splunklib.results as results

import meshapi

class meshAPIRest(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    def handle(self, in_string):
        """
        Called for a simple synchronous request.
        @param in_string: request data passed in
        @rtype: string or dict
        @return: String to return in response.  If a dict was passed in,
                 it will automatically be JSON encoded before being returned.
        """

        config = json.loads(in_string)

        query = config["path_info"]

        context = ssl.create_default_context()
        context.load_verify_locations("../lib/certifi/cacert.pem")

        service = client.connect(token=config["session"]["authtoken"], app="mesh", context=context)

        # service = client.connect(token=config["system_authtoken"], app="mesh")

        searchinfo = { "username": config["session"]["user"] }

        metadata = { "searchinfo": SimpleNamespace(**searchinfo) }

        self._metadata = SimpleNamespace(**metadata)
        self.view_id = "splunk_rest_search"
        self.view_session = "none"

        pathparts = query.split("/")

        if pathparts[0] == 'health':
            api = meshapi.meshAPI(service, query, self)

            response = api.queryAPI()

            resp = json.loads(response.read())

            jobs = service.jobs
            search = '''%s%s
                        `mesh_prep(%s,%s)`
                        | enmesh™
                            view_id=%s
                            view_session=%s
            ''' % (
                'search ' if resp[0]["search"][0] != "|" else '',
                resp[0]["search"],
                self.view_id,
                self.view_session,
                self.view_id,
                self.view_session
            )

            kwargs_health = {
                "exec_mode": "blocking",
                "adhoc_search_level": "verbose"
            }

            if 'earliest' in resp[0]:
                kwargs_health['earliest_time'] = resp[0]['earliest']

            if 'latest' in resp[0]:
                kwargs_health['latest_time'] = resp[0]['latest']

            job = jobs.create(search, **kwargs_health)

            payload = { "entry": [] }
            content_wrapper = { "content": {} }

            for result in results.JSONResultsReader(job.results(output_mode='json')):
                content_wrapper = { "content": {} }

                if type(result) is dict:
                    for key, value in result.items():
                        content_wrapper["content"][key] = value

                    payload["entry"].append(content_wrapper)
                # else:
                #     content_wrapper["content"]['severity_level'] = "0"

                # payload["entry"].append(content_wrapper)

        if pathparts[0] == 'releases':
            if pathparts[1] == 'update':

                setup = {
                    'splunk_version': '8.2.5'
                }

                api = meshapi.meshAPI(service, query, self)

                response = api.queryAPI(setup)

                resp = json.loads(response.read())

                jobs = service.jobs

                search = '| makeresults | eval arc_name="%s"' % resp[0]['arc_name']

                # TODO: Debug
                with open( os.path.join('tmp', resp[0]['arc_name']), 'wb') as f:
                    b = base64.b64decode( resp[0]['fh'].encode('ascii') )      
                    f.write(b)

                params = {
                    "configured": 1,
                    "filename": True,
                    "name": os.path.join(os.getcwd(), 'tmp', resp[0]['arc_name']),
                    "update": True
                }
        
                service.post('apps/local', **params)

                kwargs_update = {
                    "exec_mode": "blocking",
                    "adhoc_search_level": "verbose"
                }

                job = jobs.create(search, **kwargs_update)

                payload = { "entry": [] }

                for result in results.JSONResultsReader(job.results(output_mode='json')):
                    content_wrapper = { "content": {} }

                    if type(result) is dict:
                        for key, value in result.items():
                            content_wrapper["content"][key] = value

                        payload["entry"].append(content_wrapper)

                os.remove(os.path.join('tmp', resp[0]['arc_name']))


        if pathparts[0] == 'scheduler':
            payload = { "entry": [] }

            api = meshapi.meshAPI(service, query, self)

            response = api.queryAPI()

            resp = json.loads(response.read())

            jobs = service.jobs

            # TODO: Verify that multiple tasks are split out on multi-task outcomes

            for schedule in resp:
                outcome_result = {
                    "implemented": 0,
                    "validated": 0,
                    "status": 0,
                    "implemented_time": math.floor(time.time())
                }

                payload['entry'].append(self.make_content_entry({
                    '_time': time.time(),
                    'task': 'discovery',
                    'action': 'start'
                }))

                if schedule['discovery_type'] == "spl":
                    job = jobs.create(schedule['discovery_logic'], exec_mode="blocking", adhoc_search_level="verbose")

                    implement_tasks = []

                    # TODO: Apply per-task, per-outcome variables here

                    for result in results.JSONResultsReader(job.results(output_mode='json')):
                        implement_task = schedule['implement_logic']

                        for key, value in result.items():
                            var_replace = "{{%s}}" % key

                            implement_task = implement_task.replace(var_replace, value)

                        implement_tasks.append(implement_task)

                # TODO: Code for discovery_type == "rest"

                payload['entry'].append(self.make_content_entry({
                    '_time': time.time(),
                    'task': 'discovery',
                    'action': 'end'
                }))

                itask = 0

                for task in implement_tasks:
                    itask = itask + 1

                    payload['entry'].append(self.make_content_entry({
                        '_time': time.time(),
                        'task': 'implement',
                        'sequence': itask,
                        'action': 'start'
                    }))

                    # TODO: Code for implement_type = "spl"

                    if schedule['implement_type'] == "rest":
                        request_headers = {
                            'Authorization': 'Bearer %s' % config["session"]["authtoken"]
                        }

                        response = requests.request(schedule['implement_method'], task, headers=request_headers, verify=api.cafile)

                    payload['entry'].append(self.make_content_entry({
                        '_time': time.time(),
                        'task': 'implement',
                        'sequence': itask,
                        'action': 'end'
                    }))


                # payload["entry"].append(content_wrapper)
                if itask > 0:
                    outcome_result['implemented'] = 1


                payload['entry'].append(self.make_content_entry({
                    '_time': time.time(),
                    'task': 'validate',
                    'action': 'start'
                }))

                # TODO: Code for validate_type = rest

                if schedule['validate_type'] == 'spl':
                    if "{{checkup_id}}" in schedule['validate_logic']:
                        validate_logic = schedule['validate_logic'].replace("{{checkup_id}}", schedule['checkup_id'])
                    else:
                        validate_logic = schedule['validate_logic']

                    job = jobs.create(validate_logic, exec_mode="blocking", adhoc_search_level="verbose")

                    for result in results.JSONResultsReader(job.results(output_mode='json')):
                        if 'severity_level' in result:
                            if result['severity_level'] == "0" or result['severity_level'] == 1:
                                outcome_result['status'] = 1

                # TODO: Check the validity of the validate logic to make this assertion. Not the RESULT, just
                # THAT the validation occurred.

                outcome_result['validated'] = 1

                payload['entry'].append(self.make_content_entry({
                    '_time': time.time(),
                    'task': 'validate',
                    'action': 'end'
                }))

                payload['entry'].append(self.make_content_entry({
                    '_time': time.time(),
                    'task': 'update',
                    'action': 'start'
                }))

                search = '''| savedsearch meshUpdateOutcome
                    implemented="%s"
                    validated="%s"
                    status="%s"
                    implemented_time="%s"
                    schedule_id="%s"
                    view_id=%s
                    view_session=%s
                ''' % (
                    outcome_result['implemented'],
                    outcome_result['validated'],
                    outcome_result['status'],
                    outcome_result['implemented_time'],
                    schedule['schedule_id'],
                    self.view_id,
                    self.view_session
                )

                job = jobs.create(search, exec_mode="blocking", adhoc_search_level="verbose")

                payload['entry'].append(self.make_content_entry({
                    '_time': time.time(),
                    'task': 'update',
                    'action': 'end'
                }))

        if pathparts[0] == 'watchdog':
            api = meshapi.meshAPI(service, query, self)

            response = api.queryAPI()

            resp = json.loads(response.read())

            jobs = service.jobs
            search = '''%s
                        | eval
                            mesh_check="data_watchdog_%s"
                        | lookup watchdog_ignore _key as key OUTPUT ignored AS ignore_alerts
                        | join type=outer [
                            | rest splunk_server=local /services/configs/conf-server/shclustering
                            | fields shcluster_label
                            | rename
                                shcluster_label AS watchdog_shcluster_label
                            ]
                        | join type=outer [
                            | rest splunk_server=local /services/server/info
                            | fields guid
                            | rename
                                guid AS watchdog_guid
                        ]
                        | eval
                            watchdog_environment=coalesce(watchdog_shcluster_label, watchdog_guid, "unknown")
                        | fields - watchdog_guid, watchdog_shcluster_label
                        | enmesh™
                            view_id=%s
                            view_session=%s
                        %s
            ''' % (
                resp[0]["spl"],
                pathparts[-1],
                self.view_id,
                self.view_session,
                "%s" % '''
                    | rename
                            key AS _key
                        | eval
                            updated=now()
                        | outputlookup append=t watchdog_alert_freq
                ''' if pathparts[-1] == 'discovery' else ""
            )

            job = jobs.create(search, exec_mode="blocking", adhoc_search_level="verbose", preview=False)

            payload = { "entry": [] }
            content_wrapper = { "content": {} }

            for result in results.JSONResultsReader(job.results(output_mode='json')):
                if type(result) is not dict:
                    continue

                content_wrapper = { "content": {} }

                # raise Exception(result)

                for key, value in result.items():
                    content_wrapper["content"][key] = value

                payload["entry"].append(content_wrapper)

        if pathparts[0] == 'aco_instruction':
            now = int(time.time())

            api = meshapi.meshAPI(service, query, self)
            response = api.queryAPI()
            resp = json.loads(response.read())

            payload = { "entry": [] }
            content_wrapper = { "content" : {} }

            if 'instruction' in resp and resp['instruction'] == 'install_content':
                params = json.loads(resp['parameters'])
                result = 'unknown'
                installed_app = True

                try:
                    installed_result = service.get('apps/local/%s' % params['app'])
                except:
                    installed_app = False
                    pass

                if not installed_app:
                    if not 'splunkbase' in params:
                        splunkapp = {
                            "configured": 1,
                            "filename": True,
                            "name": params['name'],
                            "update": True
                        }

                        service.post('apps/local', **splunkapp)
                    else:
                        headers = {
                            'Authorization': resp['token']
                        }

                        version_url = 'https://splunkbase.splunk.com/api/v1/app/%s/release/' % params['splunkbase']

                        response = requests.get(version_url, headers=headers)

                        if response.status_code == 200:
                            vresp = response.json()
                            version = vresp[0]['name']

                        splunkapp = {
                            "auth": resp['token'],
                            "configured": 1,
                            "filename": True,
                            "name": 'https://splunkbase.splunk.com/app/%s/release/%s/download/' % ( params['splunkbase'], version),
                            "update": True
                        }

                    try:
                        service.post('apps/local', **splunkapp)
                        result = 'success'
                    except:
                        result = 'fail'
                        pass
                else:
                    result = 'exists'

            if 'instruction' in resp and resp['instruction'] == 'create_index':
                params = json.loads(resp['parameters'])
                result = 'unknown'
                existing_index = True

            
                try:
                    index_result = service.get('data/indexes/%s' % params['name'])
                except:
                    existing_index = False
                    pass

                if not existing_index:
                    create_index = {
                        "name": params['name']
                    }

                    if 'datatype' in params:
                        create_index['datatype'] = params['datatype']
                    else:
                        create_index['datatype'] = 'event'

                    try:
                        service.post('data/indexes', **create_index)
                        result = 'success'
                    except:
                        result = 'fail'
                        pass
                else:
                    result = 'exists'

            if resp and '_key' in resp:
                api.method = 'POST'
                query = "%s/%s" % (
                    query,
                    resp['_key']
                )

                api.query = query

                data = {
                    "result": result
                }

                response = api.queryAPI(payload=data)

                resp = json.loads(response.read())

                content_wrapper['content'] = resp
   
                payload['entry'].append(content_wrapper)

        return {
            "payload": payload,
            "status": 200,
            "headers": {
                "Content-Type": "application/json"
            }
        }

    def make_content_entry(self, content):
        content_wrapper = { "content": {} }

        for key, value in content.items():
            content_wrapper['content'][key] = value

        return content_wrapper

    def handleStream(self, handle, in_string):
        """
        For future use
        """
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")

    def done(self):
        """
        Virtual method which can be optionally overridden to receive a
        callback after the request completes.
        """
        pass
