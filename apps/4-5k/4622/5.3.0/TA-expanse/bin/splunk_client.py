import re
import time

from splunklib import client as client

from solnlib.splunkenv import get_splunkd_uri

from splunklib.results import JSONResultsReader


class SplunkClient:
    def __init__(self, username, password, splunk_uri=None):
        host, port, owner, app_name = self.parseAppNameFromUrl(self.get_splunk_base_url(splunk_uri))
        self.__splunk_service = client.connect(host=host, port=port, username=username, password=password)
        self.__splunk_service.namespace['owner'] = 'nobody'

    def list(self, owner, app):
        return self.__splunk_service.kvstore.list(owner=owner, app=app)

    def create(self, collection, owner, app):
        self.__splunk_service.kvstore.create(collection, owner=owner, app=app)

    def get_collection(self, collection):
        return self.__splunk_service.kvstore[collection]

    def delete(self, collection, query):
        return self.__splunk_service.kvstore[collection].data.delete(query)

    def query(self, query):
        return self.__splunk_service.jobs.create(query=query)

    @staticmethod
    def get_splunk_base_url(uri):
        if not uri:
            uri = "{}/servicesNS/nobody/TA-expanse/storage/collections".format(get_splunkd_uri())
        return uri

    @staticmethod
    def parseAppNameFromUrl(url):
        pattern = r"https://([^/:]+):?(\d*)/servicesNS/([^/]+)/([^/]+)/.*"

        # Use the re.search() function to extract the Splunk details from the URL using the pattern
        match = re.search(pattern, url)

        if not match:
            raise Exception("invalid url")
        splunk_host = match.group(1)
        port = match.group(2)  # default port is 8089 if not included in the URL
        owner = match.group(3)
        app_name = "TA-expanse"

        return splunk_host, port, owner, app_name

    @staticmethod
    def get_job_results_counts(job):
        return job['resultCount']

    @staticmethod
    def get_query_results_reader(helper, job, input_name, **kwargs):
        """
        Helper method to read results from splunk when the job status is done

        Args:
            helper (smi.Script): A helper object that controls logging and state.
            job (splunklib.Job): Job object that represents the query job in splunk.
            input_name (str): The name of the input for the integration.
        Returns:
            splunklib.results.JSONResultsReader: Splunk object to help read query results.
        """
        job_results = job.results(output_mode='json', **kwargs)
        helper.log_info(f"Job results retrieved for {input_name}")
        return JSONResultsReader(job_results)

    @staticmethod
    def wait_for_query_job_to_complete(helper, job, input_name):
        """
        Waiting for job query to finish processing. This allows us to get the results and resultCount for the job.
        """
        while not job.is_done():
            time.sleep(2)
            stats = job.refresh()
            helper.log_debug(f"Waiting for {input_name} splunk query results {stats['dispatchState']}")
        helper.log_debug(f"Job finished: {input_name}")
        return
