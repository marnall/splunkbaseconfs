#!/usr/bin/env python3
#
# File: command_elasticquery.py - Version 1.3.3
# Copyright ( c ) Datapunctum AG 2026-2-11
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import sys
import signal
import uuid
import time
import queue
from datetime import datetime
from multiprocessing import Process, Queue, active_children, set_start_method


### Ensuring our child processes are killed and cleaned up properly when we get a SIGTERM
### Note that has to be before the imports below, otherwise it won't work (ugly Splunk stuff)
def handle_sigterm(sig, frame):
    for p in active_children():
        p.terminate()
        p.join()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_sigterm)
    set_start_method("spawn")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import splunklib.client as client
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators

from _env import CONFIG

from elasticspl_template.factory_logger import Logger
from elasticspl_template.factory_dataset import DatasetFactory
from elasticspl.consts import SearchMode
from elasticspl.service_elastic_instance import ElasticInstanceService
from elasticspl.service_elastic_query import ElasticQueryService
from elasticspl.helper_elastic_query_runner import run_query_lucene, run_query_dsl, run_query_esql
from elasticspl.helper_elastic_query_parser import ElasticQueryParserHelper


@Configuration()
class elasticQuery(GeneratingCommand):
    max_results = Option(require=False, default=0)
    instance = Option(require=True)
    search_name = Option(require=True)
    timestamp_used = Option(require=False)
    timestamp_field = Option(require=False)
    replacements = Option(require=False)
    scroll_size = Option(require=False, default=1000, validate=validators.Integer(0, 10000))

    # Internal
    start_time = None
    runner_duration = 0

    def generate(self):
        """
        Runs the query and yields the results
        """

        self.uuid = str(uuid.uuid4())
        logger = Logger(logname="command", uuid=self.uuid)
        self.start_time = time.time()

        try:
            self._validate_args()

            session_key = self._metadata.searchinfo.session_key
            user = self._metadata.searchinfo.username

            earliest = int(self._metadata.searchinfo.earliest_time)
            latest = int(self._metadata.searchinfo.latest_time)

            logger.info(
                {
                    "action": "query",
                    "search_name": self.search_name,
                    "earliest": earliest,
                    "latest": latest,
                    "max_results": self.max_results,
                    "instance": self.instance,
                    "timestamp_field": self.timestamp_field,
                    "timestamp_used": self.timestamp_used,
                    "replacements": self.replacements,
                    "scroll_size": self.scroll_size,
                    "user": user,
                    "app": self._metadata.searchinfo.app,
                }
            )

            dataset_factory = DatasetFactory(uuid=self.uuid, client=client, session_key=session_key)
            dataset_user = dataset_factory.get_dataset_service("users")
            current_user = dataset_user.get_by_id(user)
            current_user["name"] = user
            current_user_roles = []

            dataset_roles = dataset_factory.get_dataset_service("roles")
            roles = current_user["roles"]
            for role in roles:
                current_user_roles.append(role)
                role_object = dataset_roles.get_by_id(role)
                if "imported_roles" in role_object:
                    for imported_role in role_object["imported_roles"]:
                        if imported_role not in current_user_roles:
                            current_user_roles.append(imported_role)

            # Check if the user is allowed to run the command
            if not (set(CONFIG["ELASTIC_COMMAND_SAVED_ROLES"] + CONFIG["ADMIN_ROLES"]) & set(current_user_roles)):
                logger.error('action="__init__",result="unauthorized"')
                raise Exception('Unauthorized - You are not allowed to run the "elasticquery" command')

            # Get the instance
            elastic_instance_service: ElasticInstanceService = ElasticInstanceService(uuid=self.uuid, client=client, session_key=session_key, privileged_key=session_key, user=user)
            elastic_instance: list[dict] = elastic_instance_service.get_instance(self.instance)

            if elastic_instance is None:
                logger.error(f'action="instance_check",status="failure",user="{ user }",reason="instance_not_found",instance="{ self.instance }"')
                raise Exception("Instance not found")

            # Get the query query
            elastic_query_service = ElasticQueryService(uuid=self.uuid, client=client, session_key=session_key, privileged_key=session_key, user=user)
            query = elastic_query_service.get_query(self.search_name)

            if query is None:
                logger.error(f'action="saved_query_check",status="failure",user="{ user }",reason="query_not_found"')
                raise Exception("Saved search not found")

            if query.mode not in [SearchMode.DSL, SearchMode.LUCENE, SearchMode.ESQL]:
                logger.info(f'action="query_check",status="failure",user="{ user }",reason="invalid_mode",mode="{query.mode}"')
                raise Exception("Query is not in valid mode")

            self.query_mode = query.mode

            # Parse query
            user_input = {
                "timestamp_field": self.timestamp_field,
                "timestamp_used": self.timestamp_used,
                "replacements": self.replacements,
            }
            default_input = {
                "timestamp_field": query.default_timestamp_field,
                "timestamp_used": query.default_timestamp_used,
                "replacements": query.default_replacements,
            }
            self.timestamp_field = user_input["timestamp_field"] if user_input["timestamp_field"] else default_input["timestamp_field"]

            query_parser = ElasticQueryParserHelper(self.uuid, query.mode)
            query_string, indexes = query_parser.parse_query(query.query, earliest, latest, user_input, default_input)
            query_runner_info = {
                "uuid": self.uuid,
                "instance": elastic_instance,
                "query": query_string,
                "indexes": indexes,
                "scroll_size": self.scroll_size,
                "timestamp_field": self.timestamp_field,
            }

            for result in self.run(logger, query, query_runner_info):
                yield result

        except Exception as e:
            logger.exception({"error": str(e)})
            self.write_error(str(e))

    def run(self, logger, query, query_runner_info):
        """
        Runs the query on unix systems using multiprocessing and queues
        """
        try:
            event_queue = Queue(maxsize=500)
            message_queue = Queue()

            if query.mode == SearchMode.LUCENE:
                producers = [
                    Process(
                        target=run_query_lucene,
                        args=(
                            int(self.max_results),
                            event_queue,
                            message_queue,
                            query_runner_info,
                        ),
                    )
                ]
            elif query.mode == SearchMode.DSL:
                producers = [
                    Process(
                        target=run_query_dsl,
                        args=(
                            int(self.max_results),
                            event_queue,
                            message_queue,
                            query_runner_info,
                        ),
                    )
                ]
            elif query.mode == SearchMode.ESQL:
                logger.info("Running ESQL")

                producers = [
                    Process(
                        target=run_query_esql,
                        args=(
                            event_queue,
                            message_queue,
                            query_runner_info,
                        ),
                    )
                ]
            else:
                raise Exception("Unknown mode specified")

            for p in producers:
                p.daemon = True
                p.start()

            self.logs_without_fields = 0

            # Consuming event queue
            while True:
                try:
                    for r in self.format_result(event_queue.get(block=False)):
                        yield r
                except queue.Empty:
                    if all(not p.is_alive() for p in producers):
                        break

            # Consuming message queue
            summary_dict = None
            while True:
                try:
                    message = message_queue.get(block=False)
                    if "type" in message and message["type"] == "elastic_info":
                        message = message["message"]
                        summary_dict = message
                        self.runner_duration = message["total_time"]
                        self.write_info(
                            f"Got { message['results'] } with { message['requests'] } requests, took { message['total_elastic_time'] }s waiting for Elasticsearch, { message['total_parse_time'] }s parsing and { message['total_put_time'] }s queueing"
                        )
                    elif "type" in message and message["type"] == "warning":
                        self.write_warning(message["message"])
                    elif "type" in message and message["type"] == "error":
                        self.write_error(message["message"])
                    elif "type" in message and message["type"] == "info":
                        self.write_info(message["message"])
                    else:
                        self.write_debug(message["message"])
                except queue.Empty:
                    break

            self.write_info(f"Done - took { round( time.time() - self.start_time, 2 )}s! Runner took {self.runner_duration}s")

            if self.logs_without_fields > 0:
                self.write_warning(f"{ self.logs_without_fields } logs didn't have a timestamp field, please check your query")

            if summary_dict is not None:
                logger.info(
                    {
                        "status": "success",
                        "result": "done",
                        "result_count": summary_dict["results"],
                        "request_count": summary_dict["requests"],
                        "total_time": round(time.time() - self.start_time, 2),
                        "total_elastic_time": summary_dict["total_elastic_time"],
                        "total_parse_time": summary_dict["total_parse_time"],
                        "total_put_time": summary_dict["total_put_time"],
                        "total_runner_time": self.runner_duration,
                    }
                )

        except Exception as e:
            logger.exception(str(e))
            self.write_error(str(e))

        finally:
            for p in active_children():
                p.terminate()
                p.join()

    def format_result(self, res):
        """
        Formats the result to Splunk format
        """
        if self.query_mode in [SearchMode.LUCENE, SearchMode.DSL]:
            if isinstance(res, list):
                for result in res:
                    if not "fields" in result:
                        self.logs_without_fields += 1
                        continue

                    timestamp = result["fields"][self.timestamp_field][0]

                    yield self.gen_record(
                        **{
                            "index": result["_index"],
                            "source": "adhoc",
                            "sourcetype": "elastic_json",
                            "_time": f"{ timestamp[ 0:10 ] }.{ timestamp[ 10:13 ] }",
                            "_raw": result["_source"],
                        }
                    )
            else:
                if not "fields" in res:
                    self.logs_without_fields += 1
                    return

                timestamp = res["fields"][self.timestamp_field][0]
                yield self.gen_record(
                    **{
                        "index": res["_index"],
                        "source": "adhoc",
                        "sourcetype": "elastic_json",
                        "_time": f"{ timestamp[ 0:10 ] }.{ timestamp[ 10:13 ] }",
                        "_raw": res["_source"],
                    }
                )
        elif self.query_mode == SearchMode.ESQL:
            for result in res:
                timestamp = result.get(self.timestamp_field, -1)
                if isinstance(timestamp, str):
                    dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
                    timestamp = int(dt.timestamp())

                if "_raw" in result:
                    raw = result["_raw"]
                    del result["_raw"]
                    yield self.gen_record(
                        **{
                            "index": result.get("_index", "unknown"),
                            "source": "adhoc",
                            "sourcetype": "elastic_json",
                            "_time": timestamp,
                            "_raw": raw,
                            **result,
                        }
                    )
                else:
                    yield self.gen_record(
                        **{
                            "index": result.get("_index", "unknown"),
                            "source": "adhoc",
                            "sourcetype": "elastic_json",
                            "_time": timestamp,
                            "_raw": result,
                        }
                    )

    def _validate_args(self):
        """
        validate arguments
        """
        # Check if timestamp_used is given, if yes check if True or False
        if self.timestamp_used is None:
            self.timestamp_used = None
        elif self.timestamp_used in ["True", "true", "1", "t", "T"]:
            self.timestamp_used = True
        else:
            self.timestamp_used = False

        if self.scroll_size is None:
            self.scroll_size = 1000


dispatch(elasticQuery, sys.argv, sys.stdin, sys.stdout, __name__)
