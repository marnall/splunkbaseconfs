#!/usr/bin/env python
# coding=utf-8

from collections import OrderedDict
import json
import logging
import os
import sys
from typing import Dict, Generator, List

# Needed to import embedded python libraries
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from censys.search import CensysHosts
from censys.common.exceptions import (
    CensysNotFoundException,
    CensysRateLimitExceededException,
)

from splunklib import client
from splunklib.binding import AuthenticationError
from splunklib.searchcommands import (
    dispatch,
    EventingCommand,
    Configuration,
)


class CensysSearchException(Exception):
    """Base Exception for the Censys search command."""


@Configuration()
class CensysSearchCommand(EventingCommand):
    """Implements the transform function for enriching events"""

    def __init__(self):
        super().__init__()
        self.cache = {}

        # Set up logging
        handler = logging.FileHandler("../var/log/censys_search.log", mode="a")
        self.search_logger = logging.getLogger("censys_search")
        self.search_logger.addHandler(handler)
        self.search_logger.setLevel(logging.WARNING)

    def transform(
        self, records: Generator[OrderedDict, None, None]
    ) -> Generator[OrderedDict, None, None]:
        """Enriches events with Censys Data and yields them back to the Splunk pipeline

        Args:
            records (Generator[OrderedDict, None, None]): A generator yielding Splunk OrderedDict search events.

        Yields:
            record (OrderedDict): An OrderedDict defining a Splunk search event.
        """

        # Get command fields and Censys API instance
        try:
            command_fields = self._get_command_fields(self.fieldnames)
            censys_api = self._get_censys_api()
        except CensysSearchException:
            self.search_logger.error(
                "An error occurred while creating the Censys Search API instance."
            )
            self.search_logger.error("Yielding all unmodified events back to Splunk.")

            for record in records:
                yield record
            return

        # Enrich events and yield them back to Splunk
        for record in records:
            ip_address = record.get(command_fields["ip"])

            # If a valid IP address is not found, yield the record and move on
            if not ip_address:
                self.search_logger.error(
                    f"Could not find a valid IP address at field: {str(command_fields['ip'])}."
                )
                self.search_logger.error(f"Yielding unmodified event back to Splunk.")

                yield record
                continue

            try:
                # Check the cache for previously grabbed censys data
                if ip_address in self.cache:
                    host_data = self.cache[ip_address]
                else:
                    host_data = censys_api.view(ip_address)
                    self.cache[ip_address] = host_data

                # If the record is json, add to the json _raw string for readability
                try:
                    json_record = json.loads(record["_raw"])
                    json_record["censys_data"] = self.parse_censys_output(
                        host_data, command_fields["content"]
                    )
                    record["_raw"] = json.dumps(json_record, indent=2)
                # If the record is not json skip adding it to _raw
                except json.decoder.JSONDecodeError:
                    pass

                # Add Censys data fields to record
                censys_data = self.parse_censys_output(
                    host_data, command_fields["content"]
                )
                # This will need to be parameterized if we add support for certs
                record_type = "host"

                for key, value in censys_data.items():
                    record[f"censys_{record_type}_{key}"] = json.dumps(value, indent=2)
            except CensysNotFoundException:
                self.search_logger.warning(
                    f"No Censys search data found for event with IP: {str(ip_address)}. Skipping it."
                )
            except CensysRateLimitExceededException:
                self.search_logger.error(
                    "Censys search API rate limit has been exceeded. Please slow down and try again later."
                )
            except Exception as e:
                self.search_logger.error(e)

            yield record

    def _get_api_credentials(self) -> Dict:
        """
        Fetches the Censys API credentials from Splunk storage.

        Returns:
            dict: A dictionary containing Censys API credentials if found.
        """

        credentials = {}
        args = {
            "token": self._metadata.searchinfo.session_key,
            "app": "censys_search",
            "owner": "nobody",
        }

        # Connect to Splunk storage
        try:
            service = client.connect(**args)

            # Get Censys API ID and API Secret
            for entry in service.storage_passwords:
                if entry.username == "public_key":
                    credentials["api_id"] = entry.clear_password
                elif entry.username == "private_key":
                    credentials["api_secret"] = entry.clear_password
        except AuthenticationError as e:
            self.search_logger.error(e)

        return credentials

    def _get_command_fields(self, fieldnames: List[str]) -> Dict:
        """
        Parses and validates censyssearch command parameters if provided.

        Args:
            fieldnames (list): The parameters passed to the censyssearch command.

        Returns:
            dict: A dictionary containing the censyssearch command field names and values.
        """

        if len(fieldnames) != 2 or fieldnames[1] not in {"summary", "verbose"}:
            self.search_logger.error(
                "Please supply the name of the field containing the IP address to query "
                "and specify either 'summary' or 'verbose' enrichment.\n"
                "For example: * | censyssearch ip_address_field summary"
            )
            raise CensysSearchException
        return {"ip": fieldnames[0], "content": fieldnames[1]}

    def _get_censys_api(self) -> CensysHosts:
        """
        Returns a credentialed Censys Search API instance.

        Returns:
            CensysHosts: An instance of the Censys Search API.
        """

        # Set up Censys API
        credentials = self._get_api_credentials()

        if not (credentials.get("api_id") and credentials.get("api_secret")):
            self.search_logger.error("Could not retrieve Censys API ID and API Secret")
            raise CensysSearchException

        return CensysHosts(
            api_id=credentials["api_id"], api_secret=credentials["api_secret"]
        )

    def parse_censys_output(self, host_data: Dict, content: str) -> Dict:
        """
        Parses Censys host data and packages it into a dictionary.

        Args:
            host_data (dict): Censys search API data results.
            content (str): A string specifying a 'summary' or 'verbose' response.

        Returns:
            dict: A dictionary containing the parse Censys Search API data.
        """
        success_msg = "Censys enrichment successful!"
        failure_msg = "We haven't found any publicly accessible services on this host or the host is on our blocklist."

        if content == "verbose":
            if (
                host_data.get("location")
                or host_data.get("services")
                or host_data.get("autonomous_system")
            ):
                host_data["status"] = success_msg
            else:
                host_data["status"] = failure_msg
            return host_data

        censys_data = {}
        service_list = []

        if host_data.get("services"):
            for service in host_data.get("services"):
                service_list.append(
                    {
                        "protocol": service.get("extended_service_name"),
                        "port": service.get("port"),
                        "title": self._get_title(service),
                        "tls_names": self._get_tls_names(service),
                    }
                )

        censys_data["services"] = service_list
        censys_data["operating_system"] = self._get_os(host_data)
        censys_data["location"] = self._get_location(host_data)
        censys_data["autonomous_system"] = self._get_autonomous_system(host_data)

        # Set censys enriched status field
        if any(censys_data.values()):
            censys_data["status"] = success_msg
        else:
            censys_data["status"] = failure_msg

        return censys_data

    @staticmethod
    def _get_title(service_data: Dict) -> str:
        """
        Parses and returns the service's title.

        Args:
            service_data (dict): The data associated with a Censys Search API service.

        Returns:
            str: The service's title if found.
        """

        title = ""

        try:
            for tag in service_data["http"]["response"]["html_tags"]:
                if "<title>" in tag:
                    title = tag[7:-8]
        except KeyError:
            return title

        return title

    @staticmethod
    def _get_tls_names(service_data: Dict) -> List[str]:
        """
        Parses and returns a list of the service's tls names.

        Args:
            service_data (dict): The data associated with a Censys Search API service.

        Returns:
            list(str): A list of the service's tls names if found.
        """

        tls_names = []

        try:
            for tls_name in service_data["tls"]["certificates"]["leaf_data"]["names"]:
                tls_names.append(tls_name)
        except KeyError:
            return tls_names

        return tls_names

    @staticmethod
    def _get_os(service_data: Dict) -> Dict:
        """
        Parses and returns the service's operating system info.

        Args:
            service_data (dict): The data associated with a Censys Search API service.

        Returns:
            dict: A dictionary containing the service's operating system info if found.
        """

        op_sys = {}

        if service_data.get("operating_system"):
            op_sys = {
                "vendor": service_data["operating_system"].get("vendor"),
                "product": service_data["operating_system"].get("product"),
                "version": service_data["operating_system"].get("version"),
            }

            # Prevent all "null" values from showing in os results
            if not any(op_sys.values()):
                return {}
        return op_sys

    @staticmethod
    def _get_location(service_data: Dict) -> Dict:
        """
        Parses and returns the service's location info.

        Args:
            service_data (dict): The data associated with a Censys Search API service.

        Returns:
            dict: A dictionary containing the service's location info if found.
        """

        location = {}

        if service_data.get("location"):
            location = {
                "country": service_data["location"].get("country"),
                "province": service_data["location"].get("province"),
                "city": service_data["location"].get("city"),
            }
        return location

    @staticmethod
    def _get_autonomous_system(service_data: Dict) -> Dict:
        """
        Parses and returns the service's autonomous system info.

        Args:
            service_data (dict): The data associated with a Censys Search API service.

        Returns:
            dict: A dictionary containing the service's autonomous system system info if found.
        """

        auto_sys = {}

        if service_data.get("autonomous_system"):
            auto_sys = {
                "asn": service_data["autonomous_system"].get("asn"),
                "name": service_data["autonomous_system"].get("name"),
            }
        return auto_sys


dispatch(CensysSearchCommand, sys.argv, sys.stdin, sys.stdout, __name__)
