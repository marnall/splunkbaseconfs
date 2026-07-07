#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library
import os
import sys
import json
import time
import requests

# Logging
import logging
from logging.handlers import RotatingFileHandler

# Networking
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_trackmetestremoteaccounts.log" % splunkhome,
    mode="a",
    maxBytes=10000000,
    backupCount=1,
)
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(filename)s %(funcName)s %(lineno)d %(message)s"
)
logging.Formatter.converter = time.gmtime
filehandler.setFormatter(formatter)
log = logging.getLogger()  # root logger - Good to get it only once.
for hdlr in log.handlers[:]:  # remove the existing file handlers
    if isinstance(hdlr, logging.FileHandler):
        log.removeHandler(hdlr)
log.addHandler(filehandler)  # set the new handler
# set the log level to INFO, DEBUG as the default is ERROR
log.setLevel(logging.INFO)

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# import Splunk
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

# Import trackme libs
from trackme_libs import trackme_reqinfo


@Configuration(distributed=False)
class TrackMeTestRemoteAccounts(GeneratingCommand):

    accounts = Option(
        doc="""
        **Syntax:** **accounts=****
        **Description:** comma separated list of accounts to test, use * for all.""",
        require=False,
        default="*",
        validate=validators.Match("accounts", r"^.*$"),
    )

    def generate(self, **kwargs):
        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": f"Splunk {self._metadata.searchinfo.session_key}",
            "Content-Type": "application/json",
        }

        # get splunkd_uri
        splunkd_uri = self._metadata.searchinfo.splunkd_uri

        # get accounts
        requested_accounts = self.accounts.split(",")

        # run a get call against /services/trackme/v2/configuration/list_accounts
        url = f"{splunkd_uri}/services/trackme/v2/configuration/list_accounts"
        response = requests.get(url, headers=header, verify=False, timeout=600)
        response.raise_for_status()
        accounts = response.json().get("accounts", [])

        # remote local from the list accounts
        accounts.remove("local")

        # if accounts only contains local, yield a message as no remote accounts are configured
        if not accounts:
            yield {
                "_time": time.time(),
                "_raw": "No remote accounts are configured",
            }

        else:

            logging.info(f"list of available accounts: {accounts}")

            # for each account, do a post call against /services/trackme/v2/configuration/test_remote_account

            if self.accounts != "*":
                if not set(requested_accounts).issubset(set(accounts)):
                    error_message = f"requested account(s): {requested_accounts} not in the list of available accounts: {accounts}"
                    logging.error(error_message)
                    yield {
                        "_time": time.time(),
                        "_raw": {
                            "account": ",".join(requested_accounts),
                            "app_namespace": "search",
                            "host": "unknown",
                            "port": "unknown",
                            "status": "failure",
                            "message": f"requested account(s): {requested_accounts} not in the list of available accounts: {accounts}",
                            "accounts": accounts,
                            "requested_accounts": requested_accounts,
                        },
                        "account": ",".join(requested_accounts),
                        "app_namespace": "search",
                        "host": "unknown",
                        "port": "unknown",
                        "status": "failure",
                        "message": f"requested account(s): {requested_accounts} not in the list of available accounts: {accounts}",
                        "accounts": accounts,
                        "requested_accounts": requested_accounts,
                    }
                    return

            for account in accounts:
                if account == "local":
                    continue
                if "*" in requested_accounts or account in requested_accounts:
                    url = f"{splunkd_uri}/services/trackme/v2/configuration/test_remote_account"
                    response = requests.post(
                        url,
                        headers=header,
                        verify=False,
                        timeout=600,
                        data=json.dumps({"account": account}),
                    )

                    # Check if response is successful and contains JSON
                    try:
                        response.raise_for_status()
                        
                        # Check content type to ensure it's JSON
                        content_type = response.headers.get('content-type', '').lower()
                        if 'application/json' not in content_type:
                            error_message = f"Invalid response content type for account '{account}': {content_type}. Response: {response.text[:200]}"
                            logging.error(error_message)
                            
                            # Yield record with consistent structure matching successful case
                            yield {
                                "_time": time.time(),
                                "_raw": {
                                    "account": account,
                                    "app_namespace": "search",
                                    "host": "unknown",
                                    "port": "unknown",
                                    "status": "failure",
                                    "message": f"Invalid response content type for account '{account}': {content_type}",
                                    "content_type": content_type,
                                    "response_preview": response.text[:200]
                                },
                                "account": account,
                                "app_namespace": "search",
                                "host": "unknown",
                                "port": "unknown",
                                "status": "failure",
                                "message": f"Invalid response content type for account '{account}': {content_type}",
                                "content_type": content_type,
                                "response_preview": response.text[:200]
                            }
                            continue
                        
                        # Parse JSON response
                        json_response = response.json()
                        
                        # yield the json value
                        yield_record = {
                            "_time": time.time(),
                            "_raw": json_response,
                        }

                        # for key value in json_value, add to yield_record
                        for key, value in json_response.items():
                            yield_record[key] = value

                        # yield the yield_record
                        yield yield_record
                        
                    except requests.exceptions.HTTPError as e:
                        error_message = f"HTTP error for account '{account}': {e}. Response: {response.text[:200]}"
                        logging.error(error_message)
                        
                        # Parse response to extract account details if available
                        try:
                            response_json = response.json()
                            app_namespace = response_json.get('app_namespace', 'search')
                            host = response_json.get('host', 'unknown')
                            port = response_json.get('port', 'unknown')
                            
                            # If host is still unknown, try to extract from error message
                            if host == 'unknown' and 'message' in response_json:
                                import re
                                # Look for IP addresses in the error message
                                ip_match = re.search(r'https?://([0-9.]+):(\d+)', response_json['message'])
                                if ip_match:
                                    host = ip_match.group(1)
                                    port = ip_match.group(2)
                        except:
                            app_namespace = 'search'
                            host = 'unknown'
                            port = 'unknown'
                            
                            # Try to extract host from error message even if JSON parsing fails
                            try:
                                import re
                                ip_match = re.search(r'https?://([0-9.]+):(\d+)', response.text)
                                if ip_match:
                                    host = ip_match.group(1)
                                    port = ip_match.group(2)
                            except:
                                pass
                        
                        # Yield record with consistent structure matching successful case
                        yield {
                            "_time": time.time(),
                            "_raw": {
                                "account": account,
                                "app_namespace": app_namespace,
                                "host": host,
                                "port": port,
                                "status": "failure",
                                "message": f"HTTP error for account '{account}': {e}",
                                "http_status": response.status_code,
                                "response_preview": response.text[:200]
                            },
                            "account": account,
                            "app_namespace": app_namespace,
                            "host": host,
                            "port": port,
                            "status": "failure",
                            "message": f"HTTP error for account '{account}': {e}",
                            "http_status": response.status_code,
                            "response_preview": response.text[:200]
                        }
                    except json.JSONDecodeError as e:
                        error_message = f"Invalid JSON response for account '{account}': {e}. Response: {response.text[:200]}"
                        logging.error(error_message)
                        
                        # Try to extract host from response text
                        host = "unknown"
                        port = "unknown"
                        try:
                            import re
                            ip_match = re.search(r'https?://([0-9.]+):(\d+)', response.text)
                            if ip_match:
                                host = ip_match.group(1)
                                port = ip_match.group(2)
                        except:
                            pass
                        
                        # Yield record with consistent structure matching successful case
                        yield {
                            "_time": time.time(),
                            "_raw": {
                                "account": account,
                                "app_namespace": "search",
                                "host": host,
                                "port": port,
                                "status": "failure",
                                "message": f"Invalid JSON response for account '{account}': {e}",
                                "json_error": str(e),
                                "response_preview": response.text[:200]
                            },
                            "account": account,
                            "app_namespace": "search",
                            "host": host,
                            "port": port,
                            "status": "failure",
                            "message": f"Invalid JSON response for account '{account}': {e}",
                            "json_error": str(e),
                            "response_preview": response.text[:200]
                        }
                    except Exception as e:
                        error_message = f"Unexpected error for account '{account}': {e}"
                        logging.error(error_message)
                        
                        # Yield record with consistent structure matching successful case
                        yield {
                            "_time": time.time(),
                            "_raw": {
                                "account": account,
                                "app_namespace": "search",
                                "host": "unknown",
                                "port": "unknown",
                                "status": "failure",
                                "message": f"Unexpected error for account '{account}': {e}",
                                "exception_type": type(e).__name__
                            },
                            "account": account,
                            "app_namespace": "search",
                            "host": "unknown",
                            "port": "unknown",
                            "status": "failure",
                            "message": f"Unexpected error for account '{account}': {e}",
                            "exception_type": type(e).__name__
                        }

        # performance counter
        run_time = round(time.time() - start, 3)
        logging.info(f'trackmetestremoteaccounts has terminated, run_time="{run_time}"')


dispatch(TrackMeTestRemoteAccounts, sys.argv, sys.stdin, sys.stdout, __name__)
