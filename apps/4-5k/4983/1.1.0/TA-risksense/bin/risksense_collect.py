import json
import time
import sys

from risksense_connect import RisksenseConnect
import risksense_util as util


class RisksenseCollect(object):
    '''
    Class for handling data collection for Risksense
    '''

    def __init__(self, helper, ew):
        '''
        Initialize RisksenseCollect object with input params

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        '''

        self.name = helper.get_input_stanza_names()
        self.helper = helper
        self.event_writer = ew
        self.index = helper.get_arg('index')
        self.account = helper.get_arg('risksense_account')
        self.finding_type = helper.get_arg('finding_type')

        self.sourcetype = "risksense:hosts" if self.finding_type == "hosts" else "risksense:apps"
        self.client_sourcetype = "risksense:clients"
        # Create a connection object
        self._create_connection_object()

    def _create_connection_object(self):
        '''
        Creates RisksenseConnect object which stores the API requests metadata.
        '''
        self.helper.log_debug(
            "Creating connection object prior to data collection")
        self.connection = RisksenseConnect(
            self.helper, self.account, self.finding_type)

    def collect_risksense_events(self):
        # Collect client data
        start_time = time.time()

        self.helper.log_debug("Collecting clients data")
        self.invoke_api_and_ingest_events("clients", "GET")
        self.helper.log_debug("Finished collecting clients data")

        self.helper.log_debug("Collecting {} data".format(self.finding_type))
        self.invoke_api_and_ingest_events(self.finding_type)
        self.helper.log_debug(
            "Finished collecting {} data".format(self.finding_type))

        end_time = time.time()
        self.helper.log_debug(
            "Time taken to collect all data is {} seconds.".format(end_time - start_time))

    def invoke_api_and_ingest_events(self, data_type, method="POST"):
        '''
        Risksense data collection logic.

        Step 1: Make an initial API request and fetch the totalElements (events).
        Step 2: While all events are not collected:
                Paginate through the resposnes and index events
        '''
        connection = self.connection
        urls = connection.client_url if data_type == "clients" else connection.urls
        payload = connection.payload
        client_ids = connection.client_ids
        params = dict()
        # For every client id collect data
        for url in urls:
            # Page counter
            page = 0
            # Indexed events counter
            total_indexed = 0
            # Processed events counter
            total_processed_events = 0
            # Total events counter
            total_events = 0
            # Events per page counter
            events_per_page = 0

            while not total_events or total_processed_events < total_events:
                # Iterate through all pages until all events are collected
                params["page"] = payload["page"] = page
                events_per_page = 0

                try:
                    if data_type == "clients":
                        response = connection.session.request(method=method, url=url, headers=connection.headers, params=params,
                                                              verify=util.VERIFY_SSL, proxies=connection.proxies,
                                                              timeout=util.REQUESTS_TIMEOUT)
                    else:
                        response = connection.session.request(method=method, url=url, headers=connection.headers,
                                                              data=json.dumps(payload), verify=util.VERIFY_SSL,
                                                              proxies=connection.proxies, timeout=util.REQUESTS_TIMEOUT)

                    # Create a copy of response to raise status error after converted to json
                    res = response
                    response = response.json()

                    # If error returned by API, log that error else raise_for_status
                    if len(response.get("errors", [])):
                        self.helper.log_error(
                            "Error occured while collecting data for url {} {}".format(url,
                                                                                       response.get("errors")))
                    # Don't break here as data is also returned along with errors

                    res.raise_for_status()

                    if not total_events:
                        total_events = response["page"]["totalElements"]
                        self.helper.log_info(
                            "Total {} events available in platform {} ".format(data_type, total_events))

                    if not total_events:
                        break

                    if not response.get("_embedded", {}).get(data_type):
                        break

                    for event in response["_embedded"][data_type]:
                        total_processed_events += 1
                        splunk_event = None
                        if data_type == "clients":
                            if str(event["id"]) in client_ids:
                                client_event = util.prepare_client_event(event)
                                splunk_event = self.helper.new_event(source=self.helper.get_input_type(),
                                                                     index=self.index, sourcetype=self.client_sourcetype, data=json.dumps(client_event))

                        else:
                            splunk_event = self.helper.new_event(source=self.helper.get_input_type(),
                                                                 index=self.index, sourcetype=self.sourcetype, data=json.dumps(event))

                        if splunk_event:
                            self.event_writer.write_event(splunk_event)
                            total_indexed += 1
                            events_per_page += 1
                    page += 1
                    self.helper.log_info(
                        "{} events indexed from page {}".format(events_per_page, page))

                except Exception as e:
                    self.helper.log_error(
                        "Error occured while collecting data for url {} {}".format(url, e))
                    break

            self.helper.log_info(
                "Total {} events indexed for input {} are {}".format(data_type, self.name, total_indexed))
