import json
from splunklib.modularinput import Event
import splunklib.results as results
import logger.log as log
import math
import re
from datetime import datetime
from time import sleep


class BaseFetcher:
    """
    Base class to fetch data from an API and write it as Splunk events.
    """

    entity = None
    sourcetype = None
    pagination_limit = None
    source = "nutanixpc:pcdiscovery"
    logger = log.Logs().get_logger("PCDiscovery")

    def __init__(self, api_processor, ew, input_name, service, pc_ip=None):
        self.api_processor = api_processor
        self.ew = ew
        self.input_name = input_name
        self.service = service
        self.pc_ip = pc_ip

    def get_exists_in_db_result(self, job):
        while not job.is_done():
            sleep(.2)
        rr = results.JSONResultsReader(job.results(output_mode='json'))
        for result in rr:
            if isinstance(result, results.Message):
                self.logger.info(f'{result.type}: {result.message}')
            elif isinstance(result, dict):
                self.logger.info(f'found: {result["count"]} same row in db in this period')
                if int(result["count"]) > 0:
                    return True
        return False

    def performance_statistics(self, metrics, extra_fields, json_list):
        output = []
        for json_data in json_list:
            metric_data = {metric: {} for metric in metrics}
            all_timestamps = set()

            for metric in metrics:
                for entry in json_data.get(metric, []):
                    try:
                        ts_obj = datetime.strptime(entry['timestamp'], "%Y-%m-%dT%H:%M:%SZ")
                    except ValueError:
                        ts_obj = datetime.strptime(entry['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ")
                    metric_data[metric][ts_obj] = entry['value']
                    all_timestamps.add(ts_obj)

            if not all_timestamps:
                continue

            all_timestamps = sorted(all_timestamps)

            for ts in all_timestamps:
                record = {'timestamp': ts.strftime("%Y-%m-%dT%H:%M:%SZ")}
                
                for field in extra_fields:
                    record[field] = json_data.get(field, '')

                for metric in metrics:
                    record[metric] = metric_data[metric].get(ts, 0)

                output.append(record)

        return output

    def _fetch_pages(self, url, param=None, pagination_limit=None, entity=None):
        """
        Generator that yields datasets page by page.
        Handles both paginated and non-paginated cases.
        """
        entity = entity or self.entity
        pagination_limit = pagination_limit or self.pagination_limit

        if pagination_limit:
            url = f"{url}?$page=0&$limit={pagination_limit}"

        dataset = self.api_processor.make_api_call(url, param=param)
        if not dataset:
            return

        yield dataset

        if pagination_limit:
            total_results = dataset["metadata"]["totalAvailableResults"]
            total_pages = math.ceil(total_results / pagination_limit)
            self.logger.info(
                f"{entity} - Total found: {total_results}, Total pages: {total_pages}."
            )

            for page in range(1, total_pages):
                paginated_url = (
                    self.api_processor.get_url(entity)
                    + f"?$page={page}&$limit={pagination_limit}"
                )
                self.logger.info(f"Fetching page {page} with URL: {paginated_url}")
                dataset = self.api_processor.make_api_call(paginated_url, param=param)
                if dataset:
                    yield dataset
                else:
                    self.logger.error(f"Failed to fetch data for page {page}.")
                    return
    
    def get_value_by_name(self, params, name):
        for item in params:
            if item.get("paramName") == name:
                param_value = item.get("paramValue", {})
                if "stringValue" in param_value:
                    return param_value["stringValue"]
                elif "intValue" in param_value:
                    return param_value["intValue"]
                else:
                    return "{" + name + "}"
        return "{" + name + "}"

    def populate_message(self, message, params):
        placeholders = re.findall(r"{(.*?)}", message)
        for ph in placeholders:
            value = self.get_value_by_name(params, ph)
            message = message.replace("{" + ph + "}", str(value))
        return message

    def manipulate_data(self, item):
        """
        Manipulate the data before writing.
        Override this in subclasses if needed.
        """
        return json.dumps(item)

    def data_exists_in_db(self, data):
        return False

    def create_splunk_event(self, url, data):
        manupulated_data = self.manipulate_data(data)
        data_in_db = self.data_exists_in_db(manupulated_data)
        if not data_in_db:
            event = Event(
                stanza=self.input_name,
                source=self.source,
                host=url,
                data=manupulated_data,
                sourcetype=self.sourcetype,
            )
            try:
                self.ew.write_event(event)
                return None, True
            except Exception as e:
                return e, False
        else:
            self.logger.info('skipping, data already in db')
            return None, False

    def validate_dataset(self, dataset):
        return dataset.get("data")

    def collect_event_data(self, ext_id=None, cl_ext_id=None, param=None, entity=None, pagination_limit=None):
        """
        Collect data from API and return normalized list of events.
        Supports optional entity and pagination overrides.
        """
        entity = entity or self.entity
        if not entity or not self.sourcetype:
            error_msg = "Subclasses must define 'entity' and 'sourcetype'."
            self.logger.error(error_msg)
            return [], None

        url = self.api_processor.get_url(entity, ext_id=ext_id, cl_ext_id=cl_ext_id)
        self.logger.info(f"url: {url}, param: {param}")

        all_events = []
        for dataset in self._fetch_pages(url, param=param, pagination_limit=pagination_limit, entity=entity):
            self.logger.info(f"Parsing data for Splunk {entity} ingestion.")
            event_data = self.validate_dataset(dataset)
            if not event_data:
                self.logger.warning(f"No 'data' returned for {entity}")
                continue

            if isinstance(event_data, dict):
                event_data = [event_data]

            all_events.extend(event_data)

        if not all_events:
            self.logger.warning("No data returned after API request")

        return all_events, url

    def get_events(self, events):
        return events

    def write_events(self, events, url, entity=None):
        """
        Write collected events into Splunk.
        """
        entity = entity or self.entity
        count = 0
        for item in self.get_events(events):
            event_error, uploaded = self.create_splunk_event(url, item)
            if event_error:
                self.logger.error(
                    f"Failed to write event for {entity}: {event_error}",
                    exc_info=True,
                )
            elif uploaded:
                count += 1
        self.logger.info(f"Wrote {count} events for {entity}")
        return count

    def fetch_and_write_event(self, ext_id=None, cl_ext_id=None, param=None, entity=None, pagination_limit=None):
        """
        Combined step: collect + write.
        """
        events, url = self.collect_event_data(
            ext_id=ext_id,
            cl_ext_id=cl_ext_id,
            param=param,
            entity=entity,
            pagination_limit=pagination_limit,
        )
        if events:
            return self.write_events(events, url, entity=entity)
        return 0
