import os
import re
import io
import json

import splunk.entity as entity
import splunk.admin as admin

import risksense_util as util
from splunktaucclib.rest_handler.endpoint.validator import Validator


class GetSessionKey(admin.MConfigHandler):
    """
    Class to get session key
    """

    def __init__(self):
        self.session_key = self.getSessionKey()


def create_requests_proxy_dict():
    """
    Creates proxy dictionary used in requests module

    :return: Proxy dict
    """
    proxies = {}
    proxy_settings, proxy_enabled = get_proxy_config()

    # Create Proxy URL
    proxy_uri = util.create_uri(proxy_enabled, proxy_settings)
    if proxy_uri:
        proxies = {
            'http': proxy_uri,
            'https': proxy_uri
        }

    return proxies


def get_proxy_config():
    '''
    Gives information of proxy if proxy is enabled
    :return: dictionary having proxy information
    '''
    # Get proxy configurations
    proxy_configuration = util.read_conf_file(
        GetSessionKey().session_key, util.RISKSENSE_SETTINGS_CONF, stanza="proxy")

    entities = entity.getEntities(['admin', 'passwords'], namespace=util.APP,
                                  owner='nobody', sessionKey=GetSessionKey().session_key, search=util.APP, count=-1)
    return util.get_proxy_settings(proxy_configuration, entities)


class FilterValidator(Validator):
    """This class extends base class of Validator."""

    def validate(self, value, data):
        """We define Custom validation here for verifying filters given by user."""
        try:

            regex = r"^([a-zA-Z0-9_-]+=[^;]+:[a-zA-Z]+;)*([a-zA-Z0-9_-]+=[^;]+:[a-zA-Z]+)+$"
            if not re.match(regex, value):
                self.put_msg(
                    "Filters should be in the form of field1=value1:OPERATOR1;field2=value2:OPERATOR2...")
                return False

            session_key = GetSessionKey().session_key
            entities = entity.getEntities(['admin', 'passwords'], namespace=util.APP,
                                          owner='nobody', sessionKey=session_key, search=util.APP, count=-1)
            
            # Fetch account information
            account_name = data.get("risksense_account")
            account_stanza = util.get_account_data(session_key, entities, account_name)
            platform_url = account_stanza.get("platform_url")
            client_ids = account_stanza.get("client_id").strip().split(",")
            token = account_stanza.get('token')

            filters = data.get("filters")
            finding_type = data.get("finding_type")
            # Get only the first URL to validate
            url = util.make_risksense_url(platform_url, finding_type, client_ids)[0]
            proxies = create_requests_proxy_dict()
            session = util.requests_retry_session()
            headers = {
                "content-type": "application/json",
                "x-api-key": token
            }
            payload = {
                "page": 0,
                "size": 1,
                "filters": util.prepare_filters(helper=None, filters=filters)
            }
            response = session.post(url, headers=headers, data=json.dumps(
                payload), verify=util.VERIFY_SSL, proxies=proxies, timeout=util.REQUESTS_TIMEOUT)

            # Create a copy of response to return errors from API
            res = response
            response = response.json()
            msg = ''

            # Check if API returned errors
            if len(response.get("errors", [])):
                msg = response.get("errors")[0]["defaultMessage"]
            elif response.get("error"):
                msg = response.get("message")
            if msg:
                raise Exception(msg)

            res.raise_for_status()

        except Exception as e:
            msg = "Error while validating filters -> '{}'. Please Validate your fields and operators.".format(
                e)
            self.put_msg(msg)
            return False
        return True
