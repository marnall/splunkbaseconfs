import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import (Configuration, GeneratingCommand, Option,
                                      dispatch, validators)

from ipqualityscoreclient import IPQualityScoreClient
from utils import setup_logging
from validation import Validation


@Configuration()
class IPQS(GeneratingCommand):
    value = Option(require=True, default=None)
    strictness = Option(require=False, default=None, validate=validators.Integer())
    timeout = Option(require=False, default=None, validate=validators.Integer())
    fast = Option(require=False, default=None, validate=validators.Boolean())

    def generate(self):
        try:
            logger = setup_logging()
            if not self.value:
                yield self.gen_record(
                    _time=time.time(), error="Please provide a value."
                )
                return
            storage_passwords = self.service.storage_passwords
            usercreds = None
            for credential in storage_passwords:
                if credential.content.get("realm") != "ipqualityscore_realm":
                    continue
                usercreds = {
                    "username": credential.content.get("username"),
                    "password": credential.content.get("clear_password"),
                }
            if usercreds is not None:
                ipqualityscoreclient = IPQualityScoreClient(
                    usercreds.get("password"), logger
                )
            else:
                yield self.gen_record(
                    _time=time.time(), error="No credentials have been found."
                )
                return
            validated_ioc_name = Validation.validating_ioc("domain_and_url", self.value)
            if not validated_ioc_name:
                yield self.gen_record(
                    _time=time.time(), error="Please provide valid indicator."
                )
                return
            results_dict = {}
            results_dict = ipqualityscoreclient.url_checker_multithreaded(
                [self.value],
                strictness=self.strictness,
                fast=self.fast,
                timeout=self.timeout,
            )
            record = {"_time": time.time(), "value": self.value}
            detection_result = results_dict.get(self.value)
            if detection_result is not None:
                if not detection_result.get("success"):
                    yield self.gen_record(
                        _time=time.time(), error=detection_result.get("message")
                    )
                    return
                for key, val in detection_result.items():
                    new_key = ipqualityscoreclient.get_prefix() + "_" + key
                    record[new_key] = val
                record[ipqualityscoreclient.get_prefix() + "_status"] = "api call success"
                # record.update(detection_result)
                # record["_status"] = "api call success"
            else:
                record["_status"] = "api call failed"
            yield self.gen_record(_raw=json.dumps(record), **record)

        except Exception as err:
            yield {"_raw": err, "_time": time.time()}
            logger.exception(err)


if __name__ == "__main__":
    dispatch(IPQS, sys.argv, sys.stdin, sys.stdout, __name__)
