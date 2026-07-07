# encoding = utf-8

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import (Configuration, Option, dispatch,
                                      validators)

from ipqualityscoreclient import IPQualityScoreClient
from utils import BaseIPQualityScoreCommand, setup_logging


@Configuration()
class URLCheckerCommand(BaseIPQualityScoreCommand):
    """
    Command class for checking the Malicious URL Scanner IPQualityScore API.
    This command processes streaming records, retrieves credentials,
    and makes multithreaded API requests to assess the risk of URLs.
    """

    field = Option(require=True, default=None, validate=validators.Fieldname())
    strictness = Option(require=False, default=None, validate=validators.Integer())
    timeout = Option(require=False, default=None, validate=validators.Integer())
    fast = Option(require=False, default=None, validate=validators.Boolean())

    def stream(self, records):
        logger = setup_logging()

        correct_records, _ = self.process_records(records, logger)

        if len(correct_records) > 0:
            usercreds = self.get_credentials()
            if usercreds is not None:
                client = IPQualityScoreClient(usercreds.get("password"), logger)

                links = [record.get(self.field) for record in correct_records]
                results_dict = client.url_checker_multithreaded(
                    links,
                    strictness=self.strictness,
                    fast=self.fast,
                    timeout=self.timeout,
                )

                yield from self.handle_results(correct_records, results_dict, client)
            else:
                raise Exception("No credentials have been found")
        else:
            logger.warning(f"No records in this stream with {self.field} field.")


if __name__ == "__main__":
    dispatch(URLCheckerCommand, sys.argv, sys.stdin, sys.stdout, __name__)
