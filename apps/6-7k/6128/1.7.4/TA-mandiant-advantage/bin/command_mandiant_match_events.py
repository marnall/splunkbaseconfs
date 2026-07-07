import import_declare_test

import json
import os
import sys

from common.log import get_logger
import socket
import splunk.clilib.cli_common
from common.indicator_helper import matched_event
from splunklib import client
from splunklib.searchcommands import (dispatch, StreamingCommand, Configuration,
                                      Option)

logger = get_logger(__file__)


@Configuration()
class MandiantMatchEvents(StreamingCommand):
  """Manage the processing of the Mandiant Matched Events feature"""

  # Declare params for the command as a searchcommand Option
  data_model = Option(
    doc='''**Syntax:** **data_model=***<value>*
    **Description:** the Splunk CIM data model used in the search''',
    require=True
  )
  fields = Option(
    doc='''**Syntax:** **fields=***<value>,<value>*
    **Description:** the field names to use for event matching''',
    require=True
  )

  def resolve_host(self, hostname):
    """Resolve hostname to IPv4/IPv6 address."""
    try:
      # This returns a list of (family, type, proto, canonname, sockaddr) tuples
      infos = socket.getaddrinfo(hostname, None)

      # Filter for IPv4 and IPv6 addresses
      ipv4_addresses = [info for info in infos if info[0] == socket.AF_INET]
      ipv6_addresses = [info for info in infos if info[0] == socket.AF_INET6]

      # Prefer IPv4, but fallback to IPv6 if necessary
      if ipv4_addresses:
          address = ipv4_addresses[0][4][0]
      elif ipv6_addresses:
          address = ipv6_addresses[0][4][0]
      else:
          return None  # No suitable address found
      return address
    except socket.gaierror:
      return None


  def create_service(self, session_key):
    """Create Service to communicate with splunk."""
    mgmt_uri = splunk.clilib.cli_common.getMgmtUri()
    hostname = mgmt_uri.split("//")[-1].split(":")[0]  # Extract hostname from URI
    mgmt_port = mgmt_uri.split(":")[-1]

    # Resolve hostname to IPv4 address
    ip_address = self.resolve_host(hostname)
    if not ip_address:
        raise Exception("Failed to resolve Splunk management URI to an IP address.")

    service = client.connect(host=ip_address, port=mgmt_port, token=session_key, app="TA-mandiant-advantage")
    return service

  def stream(self, records):
    """Entry point for the command, inherited from the StreamingCommand class.

    Receives events (records) from the results of a Splunk search, attepts to
    match values of provided fields with indicators in the
    mandiant_master_lookup

    Args:
      records: OrderedDict of search results from Splunk

    Yields:
      record: a dict of one of the processed search results
    """
    logger.info(f"{self.data_model} | Starting Mandiant Matched Events "
                f"Command for Data Model: {self.data_model}. "
                f"Matching on fields: {self.fields}")

    # Get Splunk session key from the inherited StreamingCommand class
    session_key = self.service.token
    logger.info(f"{self.data_model} | Splunk session key collected")

    # Initiate a Splunk service object
    service = self.create_service(session_key)

    # Setup custom collection managers
    master_lookup: client.KVStoreCollection = service.kvstore[
        "mandiant_master_lookup"]
    logger.info(f"{self.data_model} | Master lookup collection initialized")
    matched_events: client.KVStoreCollection = service.kvstore[
        "mandiant_matched_events"]
    logger.info(f"{self.data_model} | Matched Events collection initialized")

    # Get the fields to attempt to match on from the Option
    fields: list = self.fields.split(",")

    # Process search results one by one
    logger.info(f"{self.data_model} | Processing search results")
    for record in records:
      for field in fields:
        field_value: str = record.get(field)

        # Added to support Endpoint Service CIM Data Model
        if field in ["service_hash", "service_dll_hash"]:
          record['file_hash'] = field_value

        params = {"limit": 100, "skip": 0}
        query = json.dumps({'_key': field_value})
        results = master_lookup.data.query(query=query, **params)

        for result in results:
          if field_value == result.get('_key'):
            logger.info(f"{self.data_model} | Match found. Value: {field_value} "
                        f"in field {field}. Adding row to mandiant_matched_events")
            event = matched_event(record, result, field)
            matched_events.data.insert(json.dumps(event))
            logger.info(f"{self.data_model} | Matched event added to collection")

      yield record


dispatch(MandiantMatchEvents, sys.argv, sys.stdin, sys.stdout, __name__)
