"""Data collection logic and implementation."""
import json
import time
from pt_client import PTClient
from passivetotal_utils import COMMON_SOURCETYPE, remove_keys


class ModInputPTClient(PTClient):
    """PassiveTotal Client specific for Modular Input."""

    @staticmethod
    def add_query_parameter(response, params):
        """Add query parameter in response.

        :param response: Response received from API (After general processing)
        :param params: Params passed in API calls.

        :return data: List of dicts
        """
        data = []
        query = params.get("query")

        if not query:
            return response

        for result in response:
            result["query"] = query
            data.append(result)
        return data

    @staticmethod
    def rename_source_key(response):
        """Rename 'source' named key to avoid conflict with Splunk's built-in key 'source'."""
        data = []
        for event in response:
            if 'source' not in event:
                continue
            event["passivetotal_source"] = event.get("source")
            event.pop("source", None)
            data.append(event)
        return data

    def _process_tab(self, tab, response, params):
        """Call process_<tab> and customize_<tab>, if exists."""
        # General Processing
        func = 'process_{}'.format(tab)
        if hasattr(self, func):
            response = getattr(self, func)(response, params)

        # Customized Processing
        func = 'customize_{}'.format(tab)
        if hasattr(self, func):
            response = getattr(self, func)(response, params)

        # Common must Processing
        response = self.add_query_parameter(response, params)

        return response

    def customize_subdomains(self, response, params):
        """Customize subdomains."""
        return [remove_keys(response, ['queryValue', 'success'])]

    def customize_osint(self, response, params):
        """Customize osint."""
        return self.rename_source_key(response)

    def customize_hashes(self, response, params):
        """Customize hashes."""
        return self.rename_source_key(response)

    def customize_passivedns(self, response, params):
        """Customize passivedns."""
        return self.rename_source_key(response)

    def customize_tags(self, response, params):
        """Customize tags."""
        return [response]


class PassiveTotalCollect(object):
    """PassiveTotalCollect class handling data collection."""

    def __init__(self, helper, ew, indicator, dataset):
        """
        Initialise object.

        :param helper: BaseModInput Obj
        :param ew: EventWriter Obj
        :param indicator: ip or domain
        :param dataset: Dataset to collect data of
        """
        self.input_name = helper.get_input_stanza_names()
        self.helper = helper
        self.event_writer = ew
        self.dataset = dataset
        self.sourcetype = "{}:{}".format(COMMON_SOURCETYPE, dataset)
        self.index = helper.get_arg("index")
        self.query = {"query": indicator}
        self.indicator = indicator
        self.session_key = self.helper.context_meta['session_key']

        self.helper.log_debug(
            "Creating client object for dataset={} indicator={}".format(self.dataset, self.indicator))
        self.pt_client = ModInputPTClient(session_key=self.session_key)

    def get_articles(self):
        """Get latest articles."""
        checkpoint_key = '{}_{}'.format(self.input_name, self.dataset)
        checkpoint = self.helper.get_check_point(checkpoint_key)
        self.helper.log_info('Get Checkpoint: {}={}'.format(checkpoint_key, checkpoint))
        last_ingested_article_guid = checkpoint.get('guid') if checkpoint else None
        latest_article_guid = last_ingested_article_guid
        collection_completed = False
        params = {'page': 0}

        try:
            while not collection_completed:
                self.helper.log_info('Fetching {}: {}'.format(self.dataset, params))
                articles = self.pt_client.get_tab(self.dataset, params)
                if len(articles) == 0:
                    break

                if params['page'] == 0:
                    latest_article_guid = articles[0].get('guid')

                for article in articles:
                    article_guid = article.get('guid')
                    if article_guid == last_ingested_article_guid:
                        collection_completed = True
                        break

                    yield article
                params['page'] += 1

        finally:
            if last_ingested_article_guid != latest_article_guid:
                checkpoint = {'guid': latest_article_guid}
                self.helper.save_check_point(checkpoint_key, checkpoint)
                self.helper.log_info('Save Checkpoint:  {}={}'.format(checkpoint_key, checkpoint))

    def start_data_collection(self):
        """Collect data."""
        start_time = time.time()
        self.helper.log_debug("Starting data collection for dataset={} indicator={}".format(
            self.dataset, self.indicator))
        try:
            events = []
            if self.dataset == 'articles':
                events = self.get_articles()
            else:
                events = self.pt_client.get_tab(
                    self.dataset, self.query)

            count = 0
            for event in events:
                splunk_event = self.helper.new_event(
                    source=self.helper.get_input_type(),
                    index=self.index, sourcetype=self.sourcetype,
                    data=json.dumps(event, ensure_ascii=False, sort_keys=True)
                )
                self.event_writer.write_event(splunk_event)
                count += 1

            self.helper.log_info("Total events indexed for dataset={} indicator={} is {}".format(
                self.dataset, self.indicator, count))

            end_time = time.time()
            self.helper.log_debug("Data collection successful for dataset={} indicator={}".format(
                self.dataset, self.indicator))
            self.helper.log_debug("Time taken to collect data for dataset={} indicator={} is {} seconds".format(
                self.dataset, self.indicator, end_time - start_time))

        except Exception as e:
            self.helper.log_error("Error while collecting data for input {} dataset={} indicator={} Error -> {}".format(
                self.input_name, self.dataset, self.indicator, e))
