import import_declare_test

import json
import logging
import urllib.parse

import splunk.admin as admin
import splunk.rest as rest
from splunktaucclib.rest_handler import util as rest_handler_util

import util


APP_NAME = "Splunk_TA_Dynatrace"
ACCOUNT_CONF = "splunk_ta_dynatrace_account"
SETTINGS_CONF = "splunk_ta_dynatrace_settings"
PROXY_STANZA = "proxy"
CERTIFICATES_STANZA = "certificates"
LOGGER = logging.getLogger(__name__)


class ConfigHandler(admin.MConfigHandler):
    def setup(self):
        self.supportedArgs.addReqArg("dynatrace_account")

    def _make_api_call(self, url, session_key):
        try:
            _, payload = rest.simpleRequest(
                url,
                sessionKey=session_key,
                method="GET",
                getargs={"output_mode": "json"},
                raiseAllErrors=True,
            )
        except Exception as exc:
            LOGGER.error("Failed Splunk REST request to %s: %s", url, exc)
            raise

        return json.loads(payload.decode("utf-8"))

    def _get_properties_stanza(self, session_key, conf_name, stanza_name):
        stanza_path = urllib.parse.quote(stanza_name, safe="")
        url = (
            f"/servicesNS/nobody/{APP_NAME}/properties/{conf_name}/{stanza_path}"
        )
        payload = self._make_api_call(url, session_key)
        entries = payload.get("entry", [])
        stanza = {}
        for entry in entries:
            field_name = entry.get("name")
            if field_name is not None:
                stanza[field_name] = entry.get("content")
        return stanza

    def _get_encrypted_stanza(self, session_key, conf_name, stanza_name):
        realm = f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-{conf_name}"
        credential_name = urllib.parse.quote_plus(
            f"{realm}:{stanza_name}``splunk_cred_sep``1:"
        )
        url = (
            f"/servicesNS/nobody/{APP_NAME}/storage/passwords/{credential_name}"
        )

        try:
            payload = self._make_api_call(url, session_key)
        except Exception:
            return {}

        entries = payload.get("entry", [])
        if not entries:
            return {}

        clear_password = entries[0].get("content", {}).get("clear_password")
        if not clear_password:
            return {}

        return json.loads(clear_password)

    def _get_account(self, session_key, stanza_name):
        account = self._get_properties_stanza(session_key, ACCOUNT_CONF, stanza_name)
        account.update(
            self._get_encrypted_stanza(session_key, ACCOUNT_CONF, stanza_name)
        )
        return account

    def _get_proxy_settings(self, session_key):
        proxy_settings = {}
        try:
            proxy_settings = self._get_properties_stanza(
                session_key,
                SETTINGS_CONF,
                PROXY_STANZA,
            )
        except Exception:
            return {}

        proxy_settings.update(
            self._get_encrypted_stanza(session_key, SETTINGS_CONF, PROXY_STANZA)
        )
        return proxy_settings

    def _get_certificate_settings(self, session_key):
        try:
            return self._get_properties_stanza(
                session_key,
                SETTINGS_CONF,
                CERTIFICATES_STANZA,
            )
        except Exception:
            return {}

    def handleList(self, conf_info):
        if not self.callerArgs or not self.callerArgs.get("dynatrace_account"):
            raise ValueError("Missing Dynatrace account.")

        stanza_name = self.callerArgs["dynatrace_account"][0]
        session_key = self.getSessionKey()

        account = self._get_account(session_key, stanza_name)
        tenant = util.parse_url(account.get("username", ""))
        api_token = account.get("password")
        if not tenant or not api_token:
            raise ValueError(f"Account '{stanza_name}' is missing tenant or API token.")

        proxy_settings = self._get_proxy_settings(session_key)
        certificate_settings = self._get_certificate_settings(session_key)
        proxy_uri = rest_handler_util.get_proxy_uri(proxy_settings)
        verify = util.get_ssl_certificate_verification(
            user_certificate=certificate_settings.get("user_certificate")
        )

        entity_types = util.list_dynatrace_entity_types(
            tenant,
            api_token,
            proxy_uri=proxy_uri,
            verify=verify,
        )
        for entity_type in entity_types:
            conf_info[entity_type].append("entity", entity_type)


if __name__ == "__main__":
    admin.init(ConfigHandler, admin.CONTEXT_NONE)
