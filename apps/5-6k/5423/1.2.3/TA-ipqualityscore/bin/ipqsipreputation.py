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

    def generate(self):
        try:
            logger = setup_logging()
            if not self.value:
                yield self.gen_record(
                    _time=time.time(), error="Please provide a value."
                )
                return
            
            ipqs_db_file_path_v4, ipqs_db_file_path_v6 = None, None
            try:
                app_config = self.service.confs['app']
                ipqs_db_file_path_v4 = app_config['ipqsdbfile'].content.get('path_v4')
                ipqs_db_file_path_v6 = app_config['ipqsdbfile'].content.get('path_v6')
            except  Exception as e:
                logger.error(f"Failed to retrieve IPQS database file path: {e}")


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
            validated_ioc_name = Validation.validating_ioc("ip", self.value)
            results_dict = {}
            if validated_ioc_name is not None:
                results_dict = ipqualityscoreclient.ip_detection_multithreaded(
                    [self.value],
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
            else:
                yield {
                    "_raw": "Please provide valid indicator value.",
                    "_time": time.time(),
                }
                return
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
                # record.update(detection_result)
                if record.get("ipqualityscore_from_db_file"):
                    record[
                        ipqualityscoreclient.get_prefix() + "_status"
                    ] = "data fetched from db file"
                else:
                    record[
                        ipqualityscoreclient.get_prefix() + "_status"
                    ] = "api call success"
                # record["_status"] = "api call success"
            else:
                record["_status"] = "api call failed"
            yield self.gen_record(_raw=json.dumps(record), **record)

        except Exception as err:
            yield {"_raw": err, "_time": time.time()}
            logger.exception(err)


if __name__ == "__main__":
    dispatch(IPQS, sys.argv, sys.stdin, sys.stdout, __name__)
