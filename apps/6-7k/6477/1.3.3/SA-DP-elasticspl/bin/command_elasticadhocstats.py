#!/usr/bin/env python3
#
# File: command_elasticadhocstats.py - Version 1.3.3
# Copyright ( c ) Datapunctum AG 2026-2-11
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import splunklib.client as client
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option

from _env import CONFIG

from elasticspl_template.factory_logger import Logger
from elasticspl_template.factory_dataset import DatasetFactory

from elasticspl.service_elastic_instance import ElasticInstanceService
from elasticspl.helper_elastic_query_runner import run_query_stats, run_query_esql_stats
from elasticspl.helper_elastic_query_parser import ElasticQueryParserHelper
from elasticspl.consts import SearchMode


@Configuration(type="reporting")
class elasticAdhocStats(GeneratingCommand):
    instance = Option(require=True)
    query = Option(require=True)
    timestamp_field = Option(require=False)
    timestamp_used = Option(require=False)
    replacements = Option(require=False)
    mode = Option(require=False)

    def generate(self):
        """
        Runs the query and yields the results
        """
        self.uuid = str(uuid.uuid4())
        logger = Logger(logname="command", uuid=self.uuid)

        try:
            self._validate_args()

            session_key = self._metadata.searchinfo.session_key
            user = self._metadata.searchinfo.username

            earliest = int(self._metadata.searchinfo.earliest_time)
            latest = int(self._metadata.searchinfo.latest_time)
            self.query = self.query.replace("'", '"')

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
            if not (set(CONFIG["ELASTIC_COMMAND_ADHOC_ROLES"] + CONFIG["ADMIN_ROLES"]) & set(current_user_roles)):
                logger.error('action="__init__",result="unauthorized"')
                raise Exception('Unauthorized - You are not allowed to run the "elasticadhocstats" command')

            # Get the instance
            elastic_instance_service: ElasticInstanceService = ElasticInstanceService(uuid=self.uuid, client=client, session_key=session_key, privileged_key=session_key, user=user)
            elastic_instance: list[dict] = elastic_instance_service.get_instance(self.instance)

            if elastic_instance is None:
                logger.error(f'action="instance_check",status="failure",user="{ user }",reason="instance_not_found",instance="{ self.instance }"')
                raise Exception("Instance not found")

            # Parse query
            user_input = {
                "timestamp_field": self.timestamp_field,
                "timestamp_used": self.timestamp_used,
                "replacements": self.replacements,
            }
            default_input = {
                "timestamp_field": "",
                "timestamp_used": "",
                "replacements": "",
            }

            query_parser = ElasticQueryParserHelper(self.uuid, self.mode)
            query, indexes = query_parser.parse_query(self.query, earliest, latest, user_input, default_input)
            query_runner_info = {
                "uuid": self.uuid,
                "instance": elastic_instance,
                "query": query,
                "indexes": indexes,
                "timestamp_field": self.timestamp_field,
            }

            # Get results
            if self.mode == SearchMode.DSL_STATS:
                for chunck in run_query_stats(query_runner_info):
                    # As chunck can be a list of dicts or a dict
                    if isinstance(chunck, list):
                        for result in chunck:
                            yield self.gen_record(**result)
                    else:
                        yield self.gen_record(**chunck)
            elif self.mode == SearchMode.ESQL:
                for chunck in run_query_esql_stats(query_runner_info):
                    # As chunck can be a list of dicts or a dict
                    if isinstance(chunck, list):
                        for result in chunck:
                            yield self.gen_record(**result)
                    else:
                        yield self.gen_record(**chunck)

        except Exception as e:
            logger.exception({"error": str(e)})
            self.write_error(str(e))

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
        if self.mode is None:
            self.mode = SearchMode.DSL_STATS
        if self.mode not in [SearchMode.DSL_STATS, SearchMode.ESQL]:
            raise Exception("Invalid mode - mode must be either 'stats' or 'esql'")


dispatch(elasticAdhocStats, sys.argv, sys.stdin, sys.stdout, __name__)
