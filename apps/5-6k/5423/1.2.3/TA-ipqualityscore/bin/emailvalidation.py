# encoding = utf-8

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import (Configuration, Option, dispatch,
                                      validators)

from ipqualityscoreclient import IPQualityScoreClient
from utils import BaseIPQualityScoreCommand, setup_logging


@Configuration()
class EmailValidationCommand(BaseIPQualityScoreCommand):
    """
    Command class for checking the Email Validation IPQualityScore API.
    This command processes streaming records, retrieves credentials,
    and makes multithreaded API requests.
    """

    field = Option(require=True, default=None, validate=validators.Fieldname())
    fast = Option(require=False, default=None, validate=validators.Boolean())
    timeout = Option(require=False, default=None, validate=validators.Integer())
    suggest_domain = Option(require=False, default=None, validate=validators.Boolean())
    strictness = Option(require=False, default=None, validate=validators.Integer())
    abuse_strictness = Option(
        require=False, default=None, validate=validators.Integer()
    )

    def stream(self, records):
        logger = setup_logging()

        correct_records, _ = self.process_records(records, logger)

        if len(correct_records) > 0:
            usercreds = self.get_credentials()
            if usercreds is not None:
                client = IPQualityScoreClient(usercreds.get("password"), logger)

                emails = [record.get(self.field) for record in correct_records]
                results_dict = client.email_validation_multithreaded(
                    emails,
                    fast=self.fast,
                    timeout=self.timeout,
                    suggest_domain=self.suggest_domain,
                    strictness=self.strictness,
                    abuse_strictness=self.abuse_strictness,
                )

                yield from self.handle_results(correct_records, results_dict, client)
            else:
                raise Exception("No credentials have been found")
        else:
            logger.warning(f"No records in this stream with {self.field} field.")


if __name__ == "__main__":
    dispatch(EmailValidationCommand, sys.argv, sys.stdin, sys.stdout, __name__)
