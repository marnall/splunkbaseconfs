# Copyright (C) 2023-2024 Splunk Inc. All Rights Reserved.

import os
import sys
import time

from soar_imports import APP_NAME

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', APP_NAME, 'lib'))

LINUX_LIB_PATH = os.path.join(splunkhome, 'etc', 'apps', APP_NAME, 'lib', 'linux')
MAC_LIB_PATH = os.path.join(splunkhome, 'etc', 'apps', APP_NAME, 'lib', 'mac')

if sys.platform == "linux" or sys.platform == "linux2":
    sys.path.append(LINUX_LIB_PATH)
elif sys.platform == "darwin":
    sys.path.append(MAC_LIB_PATH)

sys.path.append(os.path.join(splunkhome, 'etc', 'apps', APP_NAME, 'bin', 'ta_splunk_app_soar', 'aob_py3'))

from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option, validators
from soar import fetch_soar_config, fetch_soar_pass, SOARClient
from soar_utils import setup_logging

import asyncio

@Configuration()
class RestSOARStreamCommand(EventingCommand):
    log = setup_logging("soar_rest_calls.log", "restsoarstream_command")
    endpoint = Option(require=True, validate=validators.Fieldname())
    soar_server = Option(require=True)

    def transform(self, records):
        session_key = self._metadata.searchinfo.session_key

        self.config_id, self.soar_config, error_msg = fetch_soar_config(self.soar_server)
        
        if error_msg:
            self.log.error("Error: Failed to fetch SOAR server configuration. " + error_msg)
            yield self.gen_record(_time=time.time(), _raw={'failed': True, 'message': error_msg})
            return
        
        base_server = self.soar_config["server"]

        soar_token = fetch_soar_pass(session_key, self.config_id)

        soar_client = SOARClient(base_server, soar_token)
        
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(soar_client.make_request_async(records, self.endpoint))

        for result in results:
            yield result

dispatch(RestSOARStreamCommand, sys.argv, sys.stdin, sys.stdout, __name__)
