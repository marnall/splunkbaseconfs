"""Custom command to pull indicators from Passivetotal."""
import ta_riskiq_passivetotal_declare
import sys
import splunk.Intersplunk
import traceback
import six
import json
import time
from collections import defaultdict
from passivetotal_utils import setup_logging, MAX_WORKER_THREADS, DATASETS
from threadpool import ThreadPool
from pt_client import PTClient


class PullIndicators(object):
    """Fetch data for indicators present in Splunk."""

    def __init__(self, input_events, settings, options):
        """Initialize the Indicators Object."""
        self.session_key = settings.get("sessionKey")
        self.logger = setup_logging(session_key=self.session_key)
        self.input_events = input_events
        self.options = options
        self.logger.debug('Parameters received: {}'.format(self.options))
        self.indicators = set()
        self.fields_mapping = defaultdict(set)
        self.results = self.input_events

        try:
            # Fetch indicators from main search
            self.prepare_indicators()
            self.pt_client = PTClient(session_key=self.session_key)
        except Exception as ex:
            self.logger.error(
                "Exception: {} -- Traceback: {}".format(ex, traceback.format_exc()))
            splunk.Intersplunk.generateErrorResults(str(ex))
            sys.exit(0)

    def prepare_indicators(self):
        """Prepare list of indicators and datasets to fetch from Passivetotal API."""
        # Validation of Input Parameters
        self.fields = self.options.get("field")
        if not (isinstance(self.fields, six.string_types) and self.fields.strip()):
            raise Exception("Please provide required parameter 'field'.")

        self.datasets = self.options.get("type")
        if not (isinstance(self.datasets, six.string_types) and self.datasets.strip()):
            raise Exception("Please provide required parameter 'type'.")

        # Filter empty, None and duplicate values to reduce API calls
        self.fields = list(
            set(filter(None, list(self.fields.split(",")))))
        self.datasets = list(
            set(filter(None, list(self.datasets.split(",")))))

        for dataset in self.datasets:
            if dataset not in DATASETS:
                raise Exception(
                    "Type must be one of the following : '{}'.".format(", ".join(DATASETS)))
        for event in self.input_events:
            for field in self.fields:
                if event.get(field):
                    value = event.get(field)
                    if isinstance(value, six.string_types) and value.strip():
                        value = value.split()
                    if isinstance(value, list):
                        self.indicators.update(value)
                        for each_value in value:
                            self.fields_mapping[each_value].add(field)
        # Filter empty, None and duplicate values to reduce API calls
        self.indicators = list(filter(None, self.indicators))

    def collect_events(self):
        """Collect events from API and outputs to Splunk."""
        self.logger.info("Command statistics --> Input Events={}, Indicators={}, Datasets={}".format(
            len(self.input_events), len(self.indicators), len(self.datasets)))

        # Initialize Threadpool
        pool = ThreadPool(MAX_WORKER_THREADS, logger=self.logger)
        for indicator in self.indicators:
            for dataset in self.datasets:
                pool.add_task(self.fetch_data, indicator, dataset)

        # Wait till all Threads are done
        pool.wait_completion()
        self.logger.info("Total output events={}".format(len(self.results)))
        splunk.Intersplunk.outputResults(self.results)

    def fetch_data(self, indicator, dataset):
        """
        Perform API call for a particular indicator and dataset.

        :param indicator: ip / domain
        :param dataset: Type of data to fetch
        """
        try:
            api_params = {
                "query": indicator
            }
            events = self.pt_client.get_tab(dataset, api_params)
            self.logger.info("Received {} events for indicator={} dataset={}".format(
                len(events), indicator, dataset))

            # Process events
            if isinstance(events, list):
                for event in events:
                    if isinstance(event, dict):
                        self.results.append(
                            self.prepare_splunk_event(event, indicator))
            elif isinstance(events, dict):
                self.results.append(self.prepare_splunk_event(events, indicator))

        except Exception as ex:
            self.logger.error(
                "Error occured while fetching data for indicator={} dataset={} Exception: {} ".format(
                    indicator, dataset, ex))
            return

    def prepare_splunk_event(self, event, indicator):
        """
        Return a python dict from json event.

        :param event: JSON Event
        :param indicator: ip / hostname
        :return: Dictionary
        """
        # Add new fields from Splunk data to API data for co-relation
        for field in list(self.fields_mapping[indicator]):
            event[field] = indicator
        splunk_event = {
            "_raw": json.dumps(event),
            "_time": time.time()
        }
        splunk_event.update(event)
        return splunk_event


def main():
    """Command execution starts here."""
    start_time = time.time()
    input_events, _, settings = splunk.Intersplunk.getOrganizedResults()
    _, options = splunk.Intersplunk.getKeywordsAndOptions()
    rpt_indicators = PullIndicators(input_events, settings, options)
    try:
        rpt_indicators.collect_events()
    except Exception as ex:
        rpt_indicators.logger.error(
            "Exception: {} -- Traceback: {}".format(ex, traceback.format_exc()))
        splunk.Intersplunk.generateErrorResults(str(ex))
        return
    end_time = time.time()
    rpt_indicators.logger.info("Time taken to fetch all events is {} seconds.".format(int(end_time - start_time)))
    rpt_indicators.logger.info(
        "Completed execution of rptpullindicators command ")


if __name__ == "__main__":
    main()
