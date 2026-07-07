#!/usr/bin/env python
#
# Copyright 2024 ClickHouse, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import base64
import datetime
import http.client
import json
import os
import ssl
import sys
import urllib.parse
import logging

# NOTE: all third party dependencies must exist within `<mod-input>/bin/lib` for this modular input to run!
# That is why `lib` folder should be added to Python path
# and all third party modules should be imported right after that.

lib_path = os.path.join(os.path.dirname(__file__), 'lib')
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

from splunklib.modularinput import Argument, Event, Scheme, Script
import splunklib.client as client

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Constants
HOSTNAME = "api.clickhouse.cloud"
BASE_URL = f"https://{HOSTNAME}/v1/organizations"
MASK = "<encrypted>"

class ClickHouseCloudAuditLogsScript(Script):
    def get_scheme(self):
        # Splunk will display "ClickHouse Cloud Audit Logs" to users for this input
        scheme = Scheme("ClickHouse Cloud Audit Logs")
        scheme.description = "Streams audit logs from ClickHouse Cloud (management events only, e.g., service creation)."

        # We need to validate that the supplied organization ID and API token are correct.
        scheme.use_external_validation = True

        # Multiple instances of this modular input can be used to monitor several cloud organizations.
        scheme.use_single_instance = False

        scheme.add_argument(Argument(
            name="organization",
            title="Organization ID",
            data_type=Argument.data_type_string,
            description="ID of the ClickHouse Cloud organization to fetch the audit logs for.",
            required_on_create=True
        ))

        scheme.add_argument(Argument(
            name="api_key_id",
            title="API key ID",
            data_type=Argument.data_type_string,
            description="ID of a valid ClickHouse Cloud API key with required permissions.",
            required_on_create=True
        ))

        scheme.add_argument(Argument(
            name="api_key_secret",
            title="API key secret",
            data_type=Argument.data_type_string,
            description="API key secret for the specified API key ID.",
            required_on_create=True,
            required_on_edit=False
        ))


        return scheme

    def validate_input(self, validation_definition):
        organization = validation_definition.parameters["organization"]
        api_key_id = validation_definition.parameters["api_key_id"]
        api_key_secret = validation_definition.parameters["api_key_secret"]

        session_key = validation_definition.metadata['session_key']
        args = {'token':session_key}
        service = client.connect(**args)

        if api_key_secret == MASK:
            for storage_password in service.storage_passwords:
                if storage_password.username == api_key_id:
                    api_key_secret = storage_password.content.clear_password
        try:
            # To verify, we just check with the current time, we do not care about the data
            from_date = datetime.datetime.utcnow()

            # Will raise an exception if something is not right
            _get_activities(organization, api_key_id, api_key_secret, from_date)
        except Exception as e:
            raise ValueError(f"Validation failed: {str(e)}")

    def encrypt_password(self, api_key_id, api_key_secret):

        try:
            for storage_password in self.service.storage_passwords:
                if storage_password.username == api_key_id:
                    self.service.storage_passwords.delete(username=storage_password.username)
                    break

            self.service.storage_passwords.create(api_key_secret, api_key_id)

        except Exception as e:
            raise Exception("An error occurred updating credentials. Please ensure your user account has admin_all_objects and/or list_storage_passwords capabilities. Details: %s" % str(e))

    def mask_password(self, organization, api_key_id, input_name):
        try:

            kind, name = input_name.split("://")
            item = self.service.inputs.__getitem__((name, kind))

            kwargs = {
                "organization": organization,
                "api_key_id": api_key_id,
                "api_key_secret": MASK
            }
            item.update(**kwargs).refresh()

        except Exception as e:
            raise Exception("Error updating inputs.conf: %s" % str(e))

    def get_password(self, api_key_id):
        for storage_password in self.service.storage_passwords:
            if storage_password.username == api_key_id:
                return storage_password.content.clear_password

    def stream_events(self, inputs, event_writer):
        for input_name, input_item in list(inputs.inputs.items()):
            organization = input_item["organization"]
            api_key_id = input_item["api_key_id"]
            api_key_secret = input_item["api_key_secret"]

            checkpoint_dir = inputs.metadata["checkpoint_dir"]
            checkpoint_file_path = os.path.join(checkpoint_dir, f"{organization}.txt")
            checkpoint_data = _read_checkpoint(checkpoint_file_path)

            try:
                if api_key_secret != MASK:
                    self.encrypt_password(api_key_id, api_key_secret)
                    self.mask_password(organization,api_key_id, input_name)
                activities = _get_activities(organization, api_key_id, self.get_password(api_key_id))
                new_checkpoint_data = ""

                for activity in activities["result"]:
                    if activity["id"] not in checkpoint_data:
                        _stream_event(event_writer, input_name, organization, activity)
                        new_checkpoint_data += f"{activity['id']}\n"

                _write_checkpoint(checkpoint_file_path, new_checkpoint_data)

            except Exception as e:
                logging.error(f"Error streaming events for {organization}: {str(e)}")

def _stream_event(event_writer, input_name, organization, activity):
    event = Event(
        stanza=input_name,
        data=json.dumps(activity),
        source=f"{BASE_URL}/{organization}/activities",
        time=datetime.datetime.strptime(activity["createdAt"], '%Y-%m-%dT%H:%M:%S%z').strftime('%s.000')
    )
    event_writer.write_event(event)

def _get_activities(organization, api_key_id, api_key_secret, from_date=None):
    if from_date:
        query_params = {"from_date": from_date.strftime('%Y-%m-%dT%H:%M:%S.000')}
    else:
        now = datetime.datetime.now(datetime.timezone.utc)
        query_params = {
            "from_date": (now - datetime.timedelta(days=365)).strftime('%Y-%m-%dT%H:%M:%S.000'),
            "to_date": now.strftime('%Y-%m-%dT%H:%M:%S.000'),
        }

    query_string = urllib.parse.urlencode(query_params)
    url = f"{BASE_URL}/{organization}/activities?{query_string}"

    # Create the base64 encoded credentials for Basic Auth
    credentials = f"{api_key_id}:{api_key_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/json",
        'User-Agent': 'splunk-clickhouse-cloud-audit-logs',
    }

    connection = None
    try:
        connection = http.client.HTTPSConnection(HOSTNAME)
        connection.request("GET", url, headers=headers)
        response = connection.getresponse()

        if not (200 <= response.status < 300):
            raise RuntimeError(f"HTTP {response.status}: {response.reason}")

        return json.loads(response.read().decode())

    except (http.client.HTTPException, ssl.SSLError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Error fetching activities: {str(e)}")

    finally:
        if connection:
            try:
                connection.close()
            except Exception as e:
                print(f"Error closing connection: {str(e)}", file=sys.stderr)

def _read_checkpoint(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return f.read().splitlines()
    return []

def _write_checkpoint(file_path, data):
    with open(file_path, "a") as f:
        f.write(data)

if __name__ == "__main__":
    sys.exit(ClickHouseCloudAuditLogsScript().run(sys.argv))
