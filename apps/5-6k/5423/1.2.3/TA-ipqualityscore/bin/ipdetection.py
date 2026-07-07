# encoding = utf-8

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import (Configuration, Option, dispatch,
                                      validators)

from ipqualityscoreclient import IPQualityScoreClient
from utils import BaseIPQualityScoreCommand, setup_logging


@Configuration()
class IPDetectionCommand(BaseIPQualityScoreCommand):
    """
    Command class for checking the Proxy Detection IPQualityScore API.
    This command processes streaming records, retrieves credentials,
    and makes multithreaded API requests.
    """

    field = Option(require=False, default=None)
    ip_field = Option(require=False, default=None)

    user_agent = Option(require=False, default=None)
    user_language = Option(require=False, default=None)

    allow_public_access_points = Option(
        require=False, default=None, validate=validators.Boolean()
    )
    mobile = Option(require=False, default=None, validate=validators.Boolean())
    fast = Option(require=False, default=None, validate=validators.Boolean())
    strictness = Option(require=False, default=None, validate=validators.Integer())
    transaction_strictness = Option(
        require=False, default=None, validate=validators.Integer()
    )
    lighter_penalties = Option(
        require=False, default=None, validate=validators.Boolean()
    )

    def stream(self, records):
        logger = setup_logging()
        if self.field is None and self.ip_field is None:
            raise Exception(
                "Either field or ip_field argument is required to ipdetection command."
            )
        elif self.field is not None and self.ip_field is not None:
            logger.error(
                'IP field name should be passed using either "field" or "ip_field" argument, but not both. '
                "field has value "
                + self.field
                + " and ip_field has value "
                + self.ip_field
            )
            raise Exception(
                'IP field name should be passed using either "field" or "ip_field" argument, but not both.'
            )
        else:
            if self.field is None and self.ip_field is not None:
                self.field = self.ip_field

        correct_records, _ = self.process_records(records, logger)

        if len(correct_records) > 0:

            ipqs_db_file_path_v4, ipqs_db_file_path_v6 = None, None
            try:
                app_config = self.service.confs['app']
                ipqs_db_file_path_v4 = app_config['ipqsdbfile'].content.get('path_v4')
                ipqs_db_file_path_v6 = app_config['ipqsdbfile'].content.get('path_v6')
            except  Exception as e:
                logger.error(f"Failed to retrieve IPQS database file path: {e}")

            usercreds = self.get_credentials()
            if usercreds is not None:
                client = IPQualityScoreClient(usercreds.get("password"), logger)

                ips = [record.get(self.field) for record in correct_records]
                results_dict = client.ip_detection_multithreaded(
                    ips,
                    allow_public_access_points=self.allow_public_access_points,
                    mobile=self.mobile,
                    fast=self.fast,
                    strictness=self.strictness,
                    lighter_penalties=self.lighter_penalties,
                    user_agent=self.user_agent,
                    user_language=self.user_language,
                    transaction_strictness=self.transaction_strictness,
                    ipv4_db_file=ipqs_db_file_path_v4,
                    ipv6_db_file=ipqs_db_file_path_v6,
                )
                yield from self.handle_results(correct_records, results_dict, client)
            else:
                raise Exception("No credentials have been found")
        else:
            logger.warning(f"No records in this stream with {self.field} field.")


if __name__ == "__main__":
    dispatch(IPDetectionCommand, sys.argv, sys.stdin, sys.stdout, __name__)
