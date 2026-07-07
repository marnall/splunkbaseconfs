# encoding = utf-8

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import (Configuration, Option, dispatch,
                                      validators)

from ipqualityscoreclient import IPQualityScoreClient
from utils import BaseIPQualityScoreCommand, setup_logging


@Configuration()
class DarkWebLeakCommand(BaseIPQualityScoreCommand):
    """
    Command class for checking the Dark Web Leak IPQualityScore API.
    This command processes streaming records, retrieves credentials,
    and makes multithreaded API requests.
    """

    field = Option(require=True, default=None, validate=validators.Fieldname())
    field_type = Option(require=True, default=None)

    def stream(self, records):
        logger = setup_logging()

        correct_records, _ = self.process_records(records, logger)

        if len(correct_records) > 0:
            usercreds = self.get_credentials()
            if usercreds is not None:
                client = IPQualityScoreClient(usercreds.get("password"), logger)

                inputs = [record.get(self.field) for record in correct_records]
                results_dict = client.dark_web_leak_multithreaded(
                    inputs, input_type=self.field_type
                )

                yield from self.handle_results(correct_records, results_dict, client)
            else:
                raise Exception("No credentials have been found")
        else:
            logger.warning(f"No records in this stream with {self.field} field.")


if __name__ == "__main__":
    dispatch(DarkWebLeakCommand, sys.argv, sys.stdin, sys.stdout, __name__)
