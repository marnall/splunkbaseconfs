#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import requests
import time
import json
from constants import LaceworkAPIConfConstants, StoragePasswordConfConstants
from helpers import getStanzaValue
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
from splunklib.binding import HTTPError

LW_API_FILENAME = LaceworkAPIConfConstants.LW_API_FILENAME
LW_API_STANZA = LaceworkAPIConfConstants.LW_API_STANZA
LW_API_FIELD_DOMAIN = LaceworkAPIConfConstants.LW_API_FIELD_DOMAIN

SP_API_TOKEN_STANZA = StoragePasswordConfConstants.SP_API_TOKEN_STANZA


@Configuration()
class LaceworkAPICommand(GeneratingCommand):
    """Custom search command that calls lacework endpoints
    An example to use this command in Splunk:
    | lacework target="/api/....."

    Args:
        GeneratingCommand (class): Generating Command generates events based on command arguments.
         It receives no input and must be the first command on a pipeline.

    Raises:
        KeyError: Raised when API domain cannot be found from lacework-api.conf
        Exception: Raised when API token cannot be found from passwords.conf
        json.decoder.JSONDecodeError: Raised when response cannot be decoded into valid JSON

    Yields:
        dict: Json object containing the current time and raw data from the event
    """

    target = Option(require=True)

    def get_API_domain(self):
        """Get API domain from lacework-api.conf

        Raises:
            KeyError: Raised when API domain cannot be found from lacework-api.conf

        Returns:
            str: API domain path. E.g. https://exampleDomain.lacework.net
        """
        domain = getStanzaValue(self.service.confs, LW_API_FILENAME, LW_API_STANZA, LW_API_FIELD_DOMAIN)

        return "https://" + str(domain)

    def get_API_token(self):
        """Get API token from passwords.conf through Splunk endpoints

        Args:
            credentials (list): A list of storage password credentials

        Raises:
            Exception: Raised when API token cannot be found from passwords.conf

        Returns:
            str: API token
        """
        credentials = self.service.storage_passwords.list()
        for item in credentials:
            if item.realm == SP_API_TOKEN_STANZA and item.username == SP_API_TOKEN_STANZA:
                return item.clear_password
        raise Exception(
            "API token not found. Please review your setup conf settings again.")

    def generate(self):
        """Main function that gets called upon running this search command in a Splunk search.
        Generates events based on the target endpoint.

        Raises:
            json.decoder.JSONDecodeError: Rasied when response cannot be decoded into valid JSON

        Yields:
            dict: Json object containing the current time and raw data from the event
        """
        api_domain = self.get_API_domain()
        API_token = self.get_API_token()
        auth_header = {"Authorization": "Bearer " + API_token}
        response = requests.get(
            url=api_domain+str(self.target), headers=auth_header)
        response.raise_for_status()
        try:
            res_json = response.json()
        except json.decoder.JSONDecodeError as e:
            yield {"_time": time.time(), "_raw": response.text}
            raise e
        if "data" in res_json:
            for event in res_json["data"]:
                yield {"_time": time.time(), "_raw": event}
        else:
            yield {"_time": time.time(), "_raw": res_json}


if __name__ == "__main__":
    dispatch(LaceworkAPICommand, sys.argv, sys.stdin, sys.stdout, __name__)
