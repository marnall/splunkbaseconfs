#!/usr/bin/env python3
#
# File: command_elasticparse.py - Version 1.3.3
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

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option

from elasticspl_template.factory_logger import Logger

from elasticspl.helper_elastic_query_parser import ElasticQueryParserHelper


@Configuration()
class elasticParse(GeneratingCommand):
    query = Option(require=True)
    timestamp_field = Option(require=True)
    timestamp_used = Option(require=False)
    replacements = Option(require=False)

    mode = Option(require=False)

    def generate(self):
        """
        Parses the query and yields the query
        """

        self.uuid = str(uuid.uuid4())
        logger = Logger(logname="command", uuid=self.uuid)

        try:
            self._validate_args()

            earliest = int(self._metadata.searchinfo.earliest_time)
            latest = int(self._metadata.searchinfo.latest_time)
            self.query = self.query.replace("'", '"')

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
            query_dict, indexes = query_parser.parse_query(self.query, earliest, latest, user_input, default_input)

            yield {
                "_raw": {
                    "query": query_dict,
                    "indexes": indexes,
                },
            }

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
            self.mode = "ts"
        if self.mode not in ["lucene", "ts"]:
            raise Exception("Mode must be lucene or ts")


dispatch(elasticParse, sys.argv, sys.stdin, sys.stdout, __name__)
