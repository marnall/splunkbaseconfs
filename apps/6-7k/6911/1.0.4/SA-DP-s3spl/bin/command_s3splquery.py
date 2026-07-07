#!/usr/bin/env python3.7
#
# File: command_s3splquery.py - Version 1.0.4
# Copyright ( c ) Datapunctum AG 2024-11-22
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import sys
import traceback
import uuid
import time
import signal

import queue
from multiprocessing import Process, JoinableQueue, active_children, set_start_method


### Ensuring our child processes are killed and cleaned up properly when we get a SIGTERM
### Note that has to be before the imports below, otherwise it won't work (ugly Splunk stuff)
def handle_sigterm(_sig, _frame):
    for p in active_children():
        p.terminate()
        p.join()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_sigterm)
    set_start_method("spawn")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import splunklib.client as client
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option

from _env import CONFIG

from s3spl_template.factory_logger import Logger
from s3spl_template.service_proxy import ProxyService
from s3spl_template.factory_dataset import DatasetFactory

from s3spl.service_bucket import BucketService
from s3spl.service_query import QueryService
from s3spl.helper_query_runner import run_query
from s3spl.helper_query_parser import QueryParserHelper


@Configuration()
class s3SPLQuery(GeneratingCommand):
    max_results = Option(require=False, default=0)
    bucket = Option(require=True)
    query_name = Option(require=True)
    replacements = Option(require=False)

    threads = Option(require=False, default=1)

    # Internal
    logger = None
    start_time = None

    def generate(self):
        """
        Runs the query and yields the results
        """

        self.uuid = str(uuid.uuid4())
        self.logger = Logger(logname="command", uuid=self.uuid)
        self.start_time = time.time()

        try:
            session_key = self._metadata.searchinfo.session_key
            user = self._metadata.searchinfo.username
            app = self._metadata.searchinfo.app

            earliest = int(self._metadata.searchinfo.earliest_time)
            latest = int(self._metadata.searchinfo.latest_time)

            dataset_factory = DatasetFactory(uuid=self.uuid, client=client, session_key=session_key)
            dataset_user = dataset_factory.get_dataset_service("users")
            current_user = dataset_user.get_by_id(user)
            current_user["name"] = user
            current_user_roles = []

            dataset_roles = dataset_factory.get_dataset_service("roles")
            roles = current_user["roles"]
            for role in roles:
                current_user_roles.extend(dataset_roles.get_imported_roles_by_id(role))

            current_user_roles = list(set(current_user["roles"] + current_user_roles))

            # Check if the user is allowed to run the command
            if not (set(CONFIG["S3SPL_COMMAND_SAVED_ROLES"] + CONFIG["ADMIN_ROLES"]) & set(current_user_roles)):
                self.logger.error('action="__init__",result="unauthorized"')
                raise Exception('Unauthorized - You are not allowed to run the "s3splquery" command')

            # Get the bucket
            bucket_service: BucketService = BucketService(uuid=self.uuid, client=client, session_key=session_key, user=user, app=app)
            bucket: list[dict] = bucket_service.get_bucket(self.bucket)

            if bucket is None:
                self.logger.error(f'action="bucket_check",status="failure",user="{ user }",reason="bucket_not_found",bucket="{ self.bucket }"')
                raise Exception("Bucket not found")

            # Get the query
            query_service = QueryService(uuid=self.uuid, client=client, session_key=session_key, user=user, app=app)
            query = query_service.get_query(self.query_name)

            if query is None:
                self.logger.error(f'action="saved_query_check",status="failure",user="{ user }",reason="query_not_found"')
                raise Exception("Saved search not found")

            # Get proxy config
            proxy_service: ProxyService = ProxyService(uuid=self.uuid, client=client, session_key=session_key, user=user)
            proxy_config = proxy_service.get_request_info()

            # Parse query
            user_input = {
                "timestamp_field": None,
                "timestamp_used": None,
                "timestamp_format": None,
                "replacements": self.replacements,
                "fields": None,
                "field_delimiter": None,
                "record_delimiter": None,
            }
            default_input = {
                "timestamp_field": query.timestamp_field,
                "timestamp_used": query.timestamp_used,
                "timestamp_format": query.timestamp_format,
                "replacements": query.replacements,
                "fields": query.fields,
                "field_delimiter": query.field_delimiter,
                "record_delimiter": query.record_delimiter,
            }
            meta_fields = {
                "index_field": query.index_field,
                "source_field": query.source_field,
                "sourcetype_field": query.sourcetype_field,
                "host_field": query.host_field,
                "time_field": query.timestamp_field,
                "raw_field": query.raw_field if not bucket.bucket_ia else "event",
            }

            query_parser = QueryParserHelper(self.uuid)
            parsed_query, merged_inputs = query_parser.parse_query(
                query=query.query,
                earliest=earliest,
                latest=latest,
                user_input=user_input,
                default_input=default_input,
                timezone=bucket.timezone,
                limit=bucket.max_events_per_file,
                bucket_ia=bucket.bucket_ia,
            )
            query_runner_info = {
                "uuid": self.uuid,
                "bucket": bucket,
                "earliest": earliest,
                "latest": latest,
                "query": parsed_query,
                "merged_inputs": merged_inputs,
                "meta_fields": meta_fields,
                "query_threads": int(self.threads),
                "proxy_config": proxy_config,
            }

            # Run the query
            for result in self.run_query(query_runner_info):
                yield result

        except Exception as e:
            self.logger.error(traceback.format_exc())
            self.write_error(str(e))

    def run_query(self, query_runner_info):
        """
        Runs the query on unix systems using multiprocessing and queues
        """
        try:
            event_queue = JoinableQueue(maxsize=2000)
            message_queue = JoinableQueue()

            producers = [
                Process(
                    target=run_query,
                    args=(
                        self.uuid,
                        int(self.max_results),
                        event_queue,
                        message_queue,
                        query_runner_info,
                    ),
                )
            ]

            for p in producers:
                p.daemon = True
                p.start()

            self.logs_without_fields = 0

            # Consuming event queue
            while True:
                try:
                    event = event_queue.get(block=False)
                    if isinstance(event, list):
                        for row in event:
                            yield row
                    else:
                        yield event
                except queue.Empty:
                    if all(not p.is_alive() for p in producers):
                        break

            # Consuming message queue
            while True:
                try:
                    message = message_queue.get(block=False)
                    if "type" in message and message["type"] == "warning":
                        self.write_warning(message["message"])
                    elif "type" in message and message["type"] == "error":
                        self.write_error(message["message"])
                    elif "type" in message and message["type"] == "info":
                        self.write_info(message["message"])
                    else:
                        self.write_debug(message["message"])
                except queue.Empty:
                    break

            self.write_info(f"Done - took { round( time.time() - self.start_time, 2 )}s!")

            if self.logs_without_fields > 0:
                self.write_warning(f"{ self.logs_without_fields } logs didn't have a timestamp field, please check your query")

        except Exception as e:
            self.logger.error(traceback.format_exc())
            for p in active_children():
                p.terminate()
                p.join()
            self.write_error(str(e))
            raise e


dispatch(s3SPLQuery, sys.argv, sys.stdin, sys.stdout, __name__)
