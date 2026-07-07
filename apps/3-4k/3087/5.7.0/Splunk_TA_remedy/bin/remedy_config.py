#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""

* isort ignores:
- isort: skip = Should not be sorted.
* flake8 ignores:
- noqa: F401 -> Def = module imported but unused
    Reason for ignoring = This is necessary as it contains adding a path to sys.path
"""

import splunk_ta_remedy_declare  # isort: skip # noqa: F401

import json

import remedy_consts as c
import solnlib.credentials as cred
import splunktaucclib.rest_handler.credentials as ucc_cred
from solnlib import conf_manager as conf
from splunktaucclib.rest_handler.endpoint import MultipleModel


class RemedyConfig:
    def __init__(self, splunk_uri, session_key):
        self.stanzas = {}
        self.splunk_uri = splunk_uri
        self.session_key = session_key
        self.app_name = c.APP_NAME
        cong_mgr = conf.ConfManager(
            self.session_key,
            app=self.app_name,
            realm="__REST_CREDENTIAL__#{}#configs/conf-splunk_ta_remedy_settings".format(
                self.app_name
            ),
        )
        remedy_conf = cong_mgr.get_conf(c.REMEDY_CONF, True)
        remedy_conf.reload()
        remedy_account = remedy_conf.get(c.REMEDY_ACCOUNT)

        password = remedy_account.get(c.PASSWORD)

        if password:
            cred_mgr = self.get_cred_mgr()
            password = cred_mgr.get_password(c.REMEDY_ACCOUNT)
            remedy_account[c.PASSWORD] = password
            password = json.loads(password)[c.PASSWORD]

        remedy_account[c.PASSWORD] = password
        self.stanzas[c.REMEDY_ACCOUNT] = remedy_account

        proxy = remedy_conf.get(c.PROXY_STANZA)

        proxy_password = proxy.get(c.PROXY_PASSWORD)

        if proxy_password:
            cred_mgr = self.get_cred_mgr()
            proxy_password = cred_mgr.get_password(c.PROXY_STANZA)
            proxy[c.PROXY_PASSWORD] = proxy_password
            proxy_password = json.loads(proxy_password)[c.PROXY_PASSWORD]

        proxy[c.PROXY_PASSWORD] = proxy_password
        self.stanzas[c.PROXY_STANZA] = proxy

        remedy_ws = remedy_conf.get(c.REMEDY_WS)

        self.stanzas[c.REMEDY_WS] = remedy_ws

        remedy_fields_conf = cong_mgr.get_conf(c.REMEDY_FIELDS_CONF, True)
        remedy_fields_conf.reload()
        create_incident_fields = remedy_fields_conf.get(c.CREATE_INCIDENT)
        update_incident_fields = remedy_fields_conf.get(c.UPDATE_INCIDENT)
        self.stanzas[c.CREATE_INCIDENT] = create_incident_fields
        self.stanzas[c.UPDATE_INCIDENT] = update_incident_fields

    def get_cred_mgr(self):
        endpoint = MultipleModel(c.REMEDY_CONF, models=[])
        self.realm = ucc_cred.RestCredentialsContext(endpoint, self.app_name).realm()
        cred_mgr = cred.CredentialManager(
            self.session_key, self.app_name, realm=self.realm
        )
        return cred_mgr

    def get_stanzas(self):
        return self.stanzas

    def update_stanza(self, conf_file, stanza_name, stanza):
        cong_mgr = conf.ConfManager(self.session_key, app=self.app_name).get_conf(
            conf_file, True
        )
        cong_mgr.update(stanza_name, stanza)
        cong_mgr.reload()
