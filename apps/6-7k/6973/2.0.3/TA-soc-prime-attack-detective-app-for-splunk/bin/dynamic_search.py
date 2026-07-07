import ta_soc_prime_attack_detective_app_for_splunk_declare
import time
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import splunklib.client as client
import splunklib.results as results



@Configuration()
class StreamingCSC(StreamingCommand):
    thread_count = Option(
        require=True,
        doc="Number of threads for parallel execution",
        default=4,
        validate=validators.Integer(minimum=1) 
    )

    def stream(self, records):
        service = self.service

        records_list = list(records)
        thread_count = self.thread_count

        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            future_to_record = {
                executor.submit(self.process_record, service, record): record
                for record in records_list
            }

            for future in as_completed(future_to_record):
                record = future_to_record[future]
                try:
                    updated_record = future.result()
                    yield updated_record
                except Exception as e:
                    self.logger.error(f"Error processing record: {record}, Error: {e}")
                    record["error"] = str(e)
                    yield record

    def process_record(self, service, record):

        index = record.get("Index")
        sourcetype = record.get("Sourcetype")
        field_name = record.get("field_name")
        earliest =  record.get("earliest")
        latest = record.get("latest")

        search_query = (
            f"search index={index} earliest=\"{earliest}\" latest=\"{latest}\" sourcetype=\"{sourcetype}\" "
            f"| eval {field_name} = coalesce({field_name},\"missing\") "
            f"| stats values({field_name}) as event_code by index, sourcetype"
        )

        self.logger.info(f"Executing search: {search_query}")
        results = self.run_search(service, search_query)
        record["results"] = json.dumps(results)

        return record

    def run_search(self, service, query, output_mode="json"):
        """
        Execute the given Splunk query and return the results.
        """
        job = service.jobs.create(query)
        self.logger.info(f"Search job created: {job.sid}")

        while not job.is_done():
            time.sleep(1)

        kwargs_normalsearch = {"exec_mode": "normal", "count": 0}
        results_reader = results.ResultsReader(job.results(**kwargs_normalsearch))

        return [result for result in results_reader if isinstance(result, dict)]


dispatch(StreamingCSC, sys.argv, sys.stdin, sys.stdout, __name__)