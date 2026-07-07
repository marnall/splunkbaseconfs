# encoding = utf-8

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import (Configuration, Option, dispatch,
                                      validators)

from ipqualityscoreclient import IPQualityScoreClient
from utils import BaseIPQualityScoreCommand, setup_logging


@Configuration()
class PhoneValidationCommand(BaseIPQualityScoreCommand):
    """
    Command class for checking the Phone validation IPQualityScore API.
    This command processes streaming records, retrieves credentials,
    and makes multithreaded API requests.
    """

    field = Option(require=False, default=None)
    phone_field = Option(require=False, default=None)
    strictness = Option(require=False, default=None, validate=validators.Integer())
    country = Option(require=False, default=None)
    enhanced_line_check = Option(require=False, default=None)
    enhanced_name_check = Option(require=False, default=None)

    def stream(self, records):
        logger = setup_logging()

        if self.field is None and self.phone_field is None:
            raise Exception(
                "Either field or phone_field argument is required to phone validation command."
            )
        elif self.field is not None and self.phone_field is not None:
            logger.error(
                'Phone field name should be passed using either "field" or "phone_field" argument, but not both. '
                "field has value "
                + self.field
                + " and phone_field has value "
                + self.phone_field
            )
            raise Exception(
                'Phone field name should be passed using either "field" or "phone_field" argument, but not both.'
            )
        else:
            if self.field is None and self.phone_field is not None:
                self.field = self.phone_field

        correct_records, _ = self.process_records(records, logger)

        if len(correct_records) > 0:
            usercreds = self.get_credentials()
            if usercreds is not None:
                client = IPQualityScoreClient(usercreds.get("password"), logger)

                phones = [record.get(self.field) for record in correct_records]
                results_dict = client.phone_validation_multithreaded(
                    phones,
                    country=self.country,
                    strictness=self.strictness,
                    enhanced_line_check=self.enhanced_line_check,
                    enhanced_name_check=self.enhanced_name_check,
                )

                yield from self.handle_results(correct_records, results_dict, client)
            else:
                raise Exception("No credentials have been found")
        else:
            logger.warning(f"No records in this stream with {self.field} field.")


if __name__ == "__main__":
    dispatch(PhoneValidationCommand, sys.argv, sys.stdin, sys.stdout, __name__)
