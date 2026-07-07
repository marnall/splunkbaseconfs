# Copyright (C) 2023-2024 Splunk Inc. All Rights Reserved.

import os
import sys
from sys import platform
from soar_utils import setup_logging
from urllib.parse import quote, unquote

APP = "splunk_app_soar"

CERT_FILE_LOCATION_DEFAULT = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', APP, 'default', 'cert_bundle.pem')
CERT_FILE_LOCATION_LOCAL = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', APP, 'local', 'cert_bundle.pem')

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', APP, 'lib'))

log = setup_logging("soar_rest_calls.log", "soar_client")

if platform == "linux" or platform == "linux2":
    sys.path.append(os.path.join(splunkhome, 'etc', 'apps', APP, 'lib', 'linux'))
elif platform == "darwin":
    sys.path.append(os.path.join(splunkhome, 'etc', 'apps', APP, 'lib', 'mac'))

import splunk.entity as entity
import json
import requests
import aiohttp
import asyncio

from splunk.clilib import cli_common as cli

def fetch_soar_config(soar_server):
    server_cfgs = cli.getConfStanzas('ta_splunk_app_soar_account') # returns all stanza of conf file

    for config_id in server_cfgs:
        if server_cfgs[config_id].get("custom_name") == soar_server:
            if not server_cfgs[config_id].get("server").lower().startswith('https://'):
                return None, None, "SOAR only supports https, please update your server config."
            return config_id, server_cfgs[config_id], ''
    err_msg = 'The provided value "{custom_name}" for the field "soar_server" is invalid. Check that a SOAR server with the given name is configured in Splunk App for SOAR.'.format(custom_name=soar_server)
    return None, None, err_msg

def fetch_soar_pass(session_key, config_id):
    soar_passwords_stanza= "__REST_CREDENTIAL__#splunk_app_soar#configs/conf-ta_splunk_app_soar_account:{id}``splunk_cred_sep``1:".format(id=config_id)
    passwords_entry = entity.getEntities(['storage', 'passwords'], namespace=APP, owner='nobody', sessionKey=session_key)[soar_passwords_stanza]["clear_password"]
    password = json.loads(passwords_entry).get("password")

    return password

class SOARClient():
    server_url = None
    auth_token = None
    verify = True
    allow_redirects = False

    def __init__(self, server_url, auth_token):
        self.server_url = server_url
        self.auth_token = auth_token
        self.fetch_verify_certs()

    def fetch_verify_certs(self):
        cfg = cli.getConfStanza('soar','verify_certs')
        value = cfg.get("value")
        if value == "true" and os.path.isfile(CERT_FILE_LOCATION_LOCAL):
            self.verify = CERT_FILE_LOCATION_LOCAL
        elif value == "true" and os.path.isfile(CERT_FILE_LOCATION_DEFAULT):
            self.verify = CERT_FILE_LOCATION_DEFAULT
        else:
            self.verify = False

    def make_request(self, endpoint, method="GET", **kwargs):
        
        url = self.server_url + "/rest/" + endpoint
        headers = {
            "Accept": "application/json",
            "ph-auth-token": self.auth_token
        }

        return requests.request(
            method=method,
            url=url,
            headers=headers,
            verify=self.verify,
            allow_redirects=self.allow_redirects,
            **kwargs
        )

    async def read_url(self, session, url, record):
        async with session.get(url) as resp:
            res_json = await resp.json()
            record["soar_response"] = res_json
            return record

    async def make_request_async(self, records, endpoint, method="GET", **kwargs):
        tasks = []

        headers = {
            "Accept": "application/json",
            "ph-auth-token": self.auth_token
        }

        async with aiohttp.ClientSession(headers=headers, connector=aiohttp.TCPConnector(ssl=False)) as session:
            for record in records:
                url = self.server_url + "/rest/" + record["endpoint"]
                tasks.append(asyncio.create_task(self.read_url(session, url, record)))
            return await asyncio.gather(*tasks)
