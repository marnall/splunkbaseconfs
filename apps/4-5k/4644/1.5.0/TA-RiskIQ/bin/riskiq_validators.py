import requests
import json
import os
import base64
import pytz
from datetime import datetime
import traceback

from riskiq_logger_manager import setup_logging
import riskiq_common_utility as utils
import riskiq_constants as constants

from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from splunk.clilib import cli_common as cli

_LOGGER = setup_logging("ta_riskiq_setup")
APP_NAME = __file__.split(os.sep)[-3]


class ValidateLastUpdatedTime(Validator):
    """Validator class to check if last updated time is a future time."""

    def validate(self, value, data):
        """Validate method to perform action."""
        # Current time in PST timezone
        pst = pytz.timezone('America/Los_Angeles')
        current_time = datetime.now(tz=pst)

        # Initializing these variables to None. Update only if values are provided.
        last_updated_time = data.get('last_updated_time')

        try:
            # Check if entered start time and end time is in future:
            # If true, raise exception
            if last_updated_time:
                lut = datetime.strptime(
                    last_updated_time, "%Y-%m-%dT%H:%M:%S.%f")
                lut = pst.localize(lut)
                if lut > current_time:
                    self.put_msg("Future date is not allowed.")
                    return False
                else:
                    return True
        except ValueError:  # To handle scenario where invalid date is provided.
            msg = "Invalid date. Please enter valid date in YYYY-MM-DDTHH:MM:SS.sss format."
            _LOGGER.error(msg)
            self.put_msg(msg)
            return False
        except Exception as e:
            msg = "Unknown error occurred while validating inputs: {}".format(
                e)
            _LOGGER.error(msg)
            self.put_msg(msg)
            return False
        return True


class SessionKeyProvider(ConfigMigrationHandler):
    """Provides Splunk session key to custom validator."""

    def __init__(self):
        """Save session key in class instance."""
        self.session_key = self.getSessionKey()


class ValidateRiskIQEndpoints(Validator):
    """Validator for RiskIQ API credentials and endpoints."""

    def validate(self, value, data):
        """
        Check if the given value is valid.

        :param value: value to validate.
        :param data: whole payload in request.
        :return True or False
        """
        _LOGGER.info("Initiating configuration validation.")

        # Get Splunk Session Key
        splunk_session_key = SessionKeyProvider().session_key

        # Get proxy settings information
        try:
            proxies = utils.get_proxy_uri(splunk_session_key)
        except Exception as e:
            msg = "Unknown error occurred while reading proxy details: {}".format(
                e)
            _LOGGER.error(msg)
            self.put_msg(msg)
            return False

        api_key = data.get("api_key")
        api_secret = data.get("api_secret")
        client_token = (api_key + ":" + api_secret).encode()
        base64_client_token = base64.b64encode(client_token)

        endpoints = data.get('endpoint_select').split('~')
        events_request = {
            'endpoint': 'Events Endpoint',
            'selected': True if 'events' in endpoints else False,
            'url': 'https://ws.riskiq.net/v1/event/search?&scroll&results=1',
            'filters': {'filters': [{'filters': [{'field': 'createdAt',
                                                  'type': 'GTE',
                                                  'value': ''}]}]}}

        gi_assets_request = {
            'endpoint': 'Assets Global Inventory Endpoint',
            'selected': True if 'gi_assets' in endpoints else False,
            'url': 'https://api.riskiq.net/v1/globalinventory/search?mark=*&size=1',
            'filters': {'filters': {'condition': 'AND',
                                    'value': [{'operator': 'EQ',
                                               'name': 'state',
                                               'value': 'CONFIRMED'}]}}}

        for req in [events_request, gi_assets_request]:
            msg = None
            if req['selected']:
                try:
                    headers = {"Authorization": "Basic " + base64_client_token.decode(),
                               "Content-Type": "application/json"}
                    _LOGGER.debug("API Call filters for {} is {}".format(
                        str(req['endpoint']), str(req['filters'])))
                    response = requests.post(url=req['url'],
                                             headers=headers,
                                             data=json.dumps(req['filters']),
                                             verify=constants.SSL_VERIFY,
                                             proxies=proxies)
                    msg = "Authentication successful"
                    response.raise_for_status()
                    _LOGGER.info("Configuration validated successfully.")
                    return True
                except requests.exceptions.ProxyError:
                    msg = "Authentication failed. Please check the provided proxy configuration."
                    _LOGGER.error(traceback.format_exc())
                    self.put_msg(msg)
                    return False
                except Exception:
                    if "resp" in locals() and response.status_code == 401:
                        msg = "Authentication failed for {}. Please check the credentials".format(
                            req['endpoint'])
                    elif "resp" in locals() and response.status_code == 400:
                        msg = 'Provided filters for Tags, Organizations and Brands are wrong. Error Message: {}'.format(
                            msg.get('error', ""))
                    else:
                        msg = "Unable to request RiskIQ instance. "\
                            "Please validate the provided credentials."
                    _LOGGER.error(traceback.format_exc())
                    self.put_msg(msg)
                    return False


class ValidateRiskIQGlobalInventoryInputs(Validator):
    """Validator for RiskIQ Global Inventory Assets inputs like tags/brands/organizations."""

    def validate(self, value, data):
        """
        Check if the given value is valid.

        :param value: value to validate.
        :param data: whole payload in request.
        :return True or False
        """
        _LOGGER.info("Initiating Global Inventory Assets tags/brands/organizations validation.")

        # Get Splunk Session Key
        splunk_session_key = SessionKeyProvider().session_key

        # Get proxy settings information
        try:
            proxies = utils.get_proxy_uri(splunk_session_key)
        except Exception as e:
            msg = "Unknown error occurred while reading proxy details: {}".format(
                e)
            _LOGGER.error(msg)
            self.put_msg(msg)
            return False

        # Get GI Assets modular input tags/brands/organization details
        account_name = data.get("global_account")
        tags_filter = data.get("tags")
        brands_filter = data.get("brands")
        org_filter = data.get("organizations")

        # Get Account details which is used to configure this input
        account_details = cli.getConfStanza(constants.ACCOUNT_CONF_NAME, account_name)
        api_key = account_details.get('api_key')
        api_secret = utils.get_account_clear_password(splunk_session_key, account_name)
        if not api_secret:
            msg = "Error occurred while reading the api secret value of the configured account from passwords.conf."
            _LOGGER.error(msg)
            self.put_msg(msg)
            return False

        client_token = (api_key + ":" + api_secret).encode()
        base64_client_token = base64.b64encode(client_token)

        gi_assets_request = {
            'endpoint': 'Assets Global Inventory Endpoint',
            'url': 'https://api.riskiq.net/v1/globalinventory/search?mark=*&size=1',
            'filters': {'filters': {'condition': 'AND',
                                    'value': [{'operator': 'EQ',
                                               'name': 'state',
                                               'value': 'CONFIRMED'}]}}}

        if tags_filter:
            tags_filter = tags_filter.split(",")
            gi_assets_request['filters']['filters']['value'].append(
                {'operator': 'IN', 'name': 'tag', 'value': tags_filter})
        if org_filter:
            org_filter = org_filter.split(",")
            gi_assets_request['filters']['filters']['value'].append(
                {'operator': 'IN', 'name': 'organization', 'value': org_filter})
        if brands_filter:
            brands_filter = brands_filter.split(",")
            gi_assets_request['filters']['filters']['value'].append(
                {'operator': 'IN', 'name': 'brand', 'value': brands_filter})

        output_msg = None
        try:
            headers = {"Authorization": "Basic " + base64_client_token.decode(),
                       "Content-Type": "application/json"}
            _LOGGER.debug("API Call filters for {} is {}".format(
                str(gi_assets_request['endpoint']), str(gi_assets_request['filters'])))
            response = requests.post(url=gi_assets_request['url'],
                                     headers=headers,
                                     data=json.dumps(gi_assets_request['filters']),
                                     verify=constants.SSL_VERIFY,
                                     proxies=proxies)
            output_msg = response.json()
            response.raise_for_status()
            _LOGGER.info("Global Inventory Assets input configuration validated successfully.")
            return True
        except requests.exceptions.ProxyError:
            msg = "Global Inventory Assets input configuration failed. Please check the provided proxy configuration."
            _LOGGER.error(traceback.format_exc())
            self.put_msg(msg)
            return False
        except Exception:
            if response.status_code == 401:
                msg = "Configuration failed for Global Inventory Assets. Please check the credentials"
            elif response.status_code == 400:
                msg = 'Provided filters for Tags, Organizations and Brands are wrong. Error Message: {}'.format(
                    output_msg.get('error', ""))
            else:
                msg = "Unable to request RiskIQ instance. "\
                    "Please validate the provided credentials."
            _LOGGER.error(traceback.format_exc())
            self.put_msg(msg)
            return False
