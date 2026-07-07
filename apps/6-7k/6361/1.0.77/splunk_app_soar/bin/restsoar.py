# Copyright (C) 2023-2024 Splunk Inc. All Rights Reserved.

import os
import sys
import time
from soar import fetch_soar_config, fetch_soar_pass, SOARClient
from soar_utils import setup_logging

from soar_imports import APP_NAME, REDIRECT_DETECTED_MSG

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', APP_NAME, 'bin', 'ta_splunk_app_soar', 'aob_py3'))

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
import json

@Configuration()
class RestSOARCommand(GeneratingCommand):   
    log = setup_logging("soar_rest_calls.log", "restsoar_command")
 
    endpoint = Option(require=True)
    soar_server = Option(require=True)

    config_id = None
    soar_config = None
    soar_pass = None

    def generate(self):
        session_key = self._metadata.searchinfo.session_key

        self.config_id, self.soar_config, error_msg = fetch_soar_config(self.soar_server)

        if error_msg:
            self.log.error("Error: Failed to fetch SOAR server configuration. " + error_msg)
            yield self.gen_record(_time=time.time(), _raw={'failed': True, 'message': error_msg})
            return
        
        base_server = self.soar_config["server"]

        soar_token = fetch_soar_pass(session_key, self.config_id)

        soar_client = SOARClient(base_server, soar_token)

        res = soar_client.make_request(self.endpoint)

        if res.is_redirect:
            msg = f"Failed to fetch results. {REDIRECT_DETECTED_MSG}"
            self.log.error(msg)
            yield self.gen_record(_time=time.time(), _raw={'failed': True, 'message': msg})
            return

        res_json = res.json()
        self.log.info("REST response: " + json.dumps(res_json))

        if "count" in res_json and "num_pages" in res_json:
            for entry in res_json["data"]:
                yield self.gen_record(_time=time.time(), _raw=entry)
        elif type(res_json) == list:
            for el in res_json:
                yield self.gen_record(_time=time.time(), _raw=el)
        else:
            yield self.gen_record(_time=time.time(), _raw=res_json)

dispatch(RestSOARCommand, sys.argv, sys.stdin, sys.stdout, __name__)
