"""
Module MESRequest to authenticate the Splunk plug-in and collect threat events
from the Lookout RISK API.
"""
import json
import sys
import logging
import requests


# TODO: https://lookoutsecurity.jira.com/browse/EMM-8426
# Replace this with the lookout_mra_client/mra_client
class MESRequest:
    """
    Class MESRequest to authenticate the Splunk plug-in and collect threat events
    from the Lookout RISK API.
    """

    def __init__(self, api_domain, api_key, http_proxy, https_proxy, kv_handler):
        # static fields
        self.api_domain = api_domain
        self.api_key = api_key  # API key for Lookout Mobile Risk
        self.http_proxy = http_proxy
        self.https_proxy = https_proxy

        # populate dynamic variables from the kvstore_handler
        self.kvstore_handler = kv_handler

        # populate kvstore_handler's local variables
        self.kvstore_handler.get_this_ent()

        self.access_token = self.kvstore_handler.access_token
        self.refresh_token = self.kvstore_handler.refresh_token
        self.stream_position = self.kvstore_handler.stream_position
        self.stale_token_errors = ["REVOKED_REFRESH_TOKEN", "EXPIRED_TOKEN"]

    def refresh_header(self):
        """Format request headers"""
        return {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
            "cache-control": "no-cache",
        }

    def header(self, token):
        """Format request headers"""
        return {
            "accept": "application/json",
            "authorization": "Bearer {}".format(token),
            "content-type": "application/x-www-form-urlencoded",
            "cache-control": "no-cache",
        }

    def build_proxy_dict(self):
        """
        Returns a dictionary of http and/or https proxy configurations to
        be used by the requests module while connection to Lookout OAuth &
        Mobile Risk API endpoints.
        """
        proxyDict = {}
        logging.info("Building proxy configuration...")
        if self.http_proxy:
            proxyDict["http"] = self.http_proxy
        if self.https_proxy:
            proxyDict["https"] = self.https_proxy

        logging.info("Proxy Connections: {}".format(proxyDict))
        return proxyDict

    def refresh_oauth(self):
        """
        Refresh access token using the refresh token
        - Stores the new access token in the kvstore and in this object
        - If the refresh token has expired, requests a new refresh and access token
          and stores them in the kvstore and in this object
        """
        try:
            response = requests.post(
                self.api_domain + "/oauth/token",
                data="refresh_token={}&grant_type=refresh_token".format(
                    self.refresh_token
                ),
                proxies=self.build_proxy_dict(),
                headers=self.refresh_header(),
            )
            response_content = json.loads(response.text)
            if "access_token" in response_content:
                self.access_token = response_content["access_token"]
                self.kvstore_handler.store_in_kvstore("access_token", self.access_token)
                self.kvstore_handler.store_in_kvstore("is_valid", True)
            else:
                # if the refresh failed, request brand new API credentials
                response = requests.post(
                    self.api_domain + "/oauth/token",
                    data="grant_type=client_credentials",
                    proxies=self.build_proxy_dict(),
                    headers=self.header(self.api_key),
                )
                response_content = json.loads(response.text)
                if "access_token" in response_content:
                    self.access_token = response_content["access_token"]
                    self.refresh_token = response_content["refresh_token"]
                    self.kvstore_handler.store_in_kvstore(
                        "access_token", self.access_token
                    )
                    self.kvstore_handler.store_in_kvstore(
                        "refresh_token", self.refresh_token
                    )
                    self.kvstore_handler.store_in_kvstore("is_valid", True)
                else:
                    logging.error(
                        "Your Lookout application key has expired. "
                        + "Please get a new key and set up this Splunk app again.\n"
                        + "Go to https://mtp.lookout.com and generate a new key by "
                        + "navigating to System => Application Keys."
                    )
                    logging.error("Exiting...")
                    sys.exit(1)
        except requests.exceptions.ProxyError as e:
            logging.error(
                "Cannot connect to proxy. Remote end closed connection without response"
            )
        except requests.exceptions.RequestException as e:
            logging.error(e)

    def get_oauth(self):
        """
        Retrieve OAuth tokens from Lookout API
        - Returns the access_token and the refresh_token
        - If the access token is already stored, returns the
          variables stored locally
        """
        token_json = {}
        if self.access_token:
            logging.info("The access token has been found locally")
            return self.access_token, self.refresh_token

        logging.info("Could not find an access token, getting one now")

        try:
            response = requests.post(
                self.api_domain + "/oauth/token",
                data="grant_type=client_credentials",
                proxies=self.build_proxy_dict(),
                headers=self.header(self.api_key),
            )
            try:
                token_json = json.loads(response.text)
            except (AttributeError, ValueError) as e:
                logging.info("Exception when requesting new access token: " + str(e))
                logging.info("Refreshing access token...")
                self.refresh_oauth()

            if "access_token" in token_json and "error" not in token_json:
                logging.info("Storing creds in kvstore")
                self.access_token = token_json["access_token"]
                self.refresh_token = token_json["refresh_token"]
                self.kvstore_handler.store_in_kvstore(
                    "access_token", token_json["access_token"]
                )
                self.kvstore_handler.store_in_kvstore(
                    "refresh_token", token_json["refresh_token"]
                )
                self.kvstore_handler.store_in_kvstore("is_valid", True)
                logging.info("Got authenticated")
                return self.access_token, self.refresh_token
            else:
                if token_json["error"] and token_json["error"] == "invalid_client":
                    # Set flag to avoid unwanted retries in case of invalid key/client
                    self.kvstore_handler.store_in_kvstore("is_valid", False)
                logging.info("Error in oauth")
                logging.info(str(token_json))
                return False

        except requests.exceptions.ProxyError as e:
            logging.error(
                "Cannot connect to proxy. Remote end closed connection without response"
            )
        except requests.exceptions.RequestException as e:
            logging.error(e)

    def get_events(self):
        """
        Method to collect events from Metis API
        - Gets access token and stream position from KVStore
        - Requests events (retries if error HTTP code)
        - Collect events lists from Metis API, returns full list of events
        """
        if not self.access_token:
            self.get_oauth()

        events = []
        retry_count = 0
        more_events = True

        if self.access_token:
            # Added cycle count to avoid long data polling
            cycle_count = 0
            while more_events and retry_count < 10 and cycle_count < 10:
                logging.info(
                    "Fetching Events from Position {}".format(self.stream_position)
                )
                try:
                    response = requests.get(
                        self.api_domain + "/events?eventType=DEVICE,THREAT,AUDIT",
                        headers=self.header(self.access_token),
                        proxies=self.build_proxy_dict(),
                        params={"streamPosition": self.stream_position},
                    )
                    if (
                        response.status_code == 400
                        and response.json()["errorCode"] in self.stale_token_errors
                    ):
                        self.refresh_oauth()
                        continue
                    elif response.status_code != requests.codes.ok:
                        logging.info(
                            "Received error code {}, trying again to get events".format(
                                response.status_code
                            )
                        )
                        retry_count = retry_count + 1
                        continue
                except requests.exceptions.ProxyError as e:
                    logging.error(
                        "Cannot connect to proxy. Remote end closed connection without response"
                    )
                except requests.exceptions.RequestException as e:
                    logging.error(e)

                if response:
                    cycle_count = cycle_count + 1
                    events = events + response.json()["events"]
                    self.stream_position = response.json()["streamPosition"]

                    # update stream position in KV store
                    self.kvstore_handler.store_in_kvstore(
                        "streamPosition", self.stream_position
                    )

                    more_events = response.json()["moreEvents"]
                    logging.info("Fetched Event Count {}".format(len(events)))
                    logging.info("More Events to Fetch : {}".format(more_events))

            if retry_count >= 10:
                logging.error(
                    "Too many failed attempts to retrieve events, shutting down."
                )
                sys.exit(2)

        return events
