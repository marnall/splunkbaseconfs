import ta_agari_declare
import json
import agari_utils
import requests
import six
import socks
import calendar
import time
from os import path
from dateutil.parser import parse as date_parse
from requests.exceptions import RequestException
from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunk import rest
from datetime import datetime, timedelta
USER_AGENT = "AgariSplunk BP_PD_PR_Integration/v3.3.0"

class IntervalValidator(Validator):
    def validate(self,value,data):
        interval = data.get("interval","")
        interval = int(interval)
        if interval <= 0:
            self.put_msg("Interval must be a positive integer.")
            return False     
        if interval < 120:
            self.put_msg("Interval must be greater than or equal to 120 seconds.")
            return False
        return True

class DefaultTimeValidator(Validator):
    def validate(self,value,data):
        start_date = data.get("start_date","")
        if not start_date.strip():
            today = datetime.now()
            days = timedelta(days = 14)
            start_date = today - days
            data['start_date'] = start_date
        else:
            start_date = start_date.strip()
            dt_timestamp=date_parse(start_date)
            timestamp_obj = calendar.timegm(dt_timestamp.timetuple())
            now = time.time()
            diff = (now-timestamp_obj)/(60*60*24)
            if int(diff) >= 60:
                self.put_msg("Date Time must be less than 60 days")
                return False
        return True

class SetDefaultTime(Validator):
    def validate(self,value,data):
        start_date = data.get("start_date","")
        if not start_date.strip():
            today = datetime.now()
            days = timedelta(days = 14)
            start_date = today - days
            data['start_date'] = start_date
        return True

class AccountValidator(Validator):
    """To Validate Token of Agari Account."""

    def validate(self, value, data):
        """Validate Agari token given by user."""
        client_id = data.get("client_id")
        client_secret = data.get("client_secret")
        hostname = agari_utils.AGARI_HOSTNAME
        try:
            if (not client_id) or (isinstance(client_id, six.string_types) and len(client_id.strip()) <= 0):
                self.put_msg("Client ID is required.")
                return False
            if (not client_secret) or (isinstance(client_secret, six.string_types) and len(client_secret.strip()) <= 0):
                self.put_msg("Client Secret is required.")
                return False
            proxies = agari_utils.create_requests_proxy_dict()
            session = agari_utils.requests_retry_session()
            headers = {
                "content-type": "application/json",
                "content-type": "application/x-www-form-urlencoded",
                "User-Agent": str(USER_AGENT)
            }
            payload = "client_id={}&client_secret={}".format(client_id, client_secret)
            url = agari_utils.make_agari_url(platform_url=hostname, endpoint=agari_utils.OAUTH_ENDPOINT)
            response = session.post(
                url,
                headers=headers,
                data = payload,
                verify=agari_utils.get_verify_flag(),
                proxies=proxies,
                timeout=agari_utils.REQUESTS_TIMEOUT,
            )
            # Create a copy of response to return errors from API
            res = response
            try:
                response = response.json()
            except Exception as e:
                self.put_msg('{} {}. Cause -> '.format(
                'Could not connect to provided Agari Account.',
                'Please recheck Agari credentials or Proxy settings.',
                str(e)))
                return False

            # Check if API returned errors
            if response.get("error", "").strip() == "invalid_client":
                self.put_msg(
                    "Invalid Client ID or Client Secret. Please enter valid Agari Client ID and Client Secret."
                )
                return False

            res.raise_for_status()

        except (requests.exceptions.ProxyError, socks.ProxyError):
            self.put_msg("Invalid Proxy credentials. Please recheck your Proxy settings.")
            return False

        except Exception as e:
            self.put_msg('{} {}. Cause -> {}'.format(
                'Error occured while validating parameters.',
                'Please recheck Agari credentials or Proxy settings.',
                str(e)
            ))
            return False

        return True
