import json
import os
import sys
import time
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import (Configuration, GeneratingCommand, Option,
                                      dispatch)

from ipqualityscoreclient import IPQualityScoreClient
from utils import setup_logging
from validation import Validation


@Configuration()
class DynamicSearch(GeneratingCommand):
    """
    Command class for checking the IPQualityScore API.
    This command processes generating records, retrieves credentials,
    and makes IPQualityScore API requests.
    """

    field = Option(require=True, default=None)
    value = Option(require=True, default=None)

    def generate(self):
        logger = setup_logging()
    
        if "ipqualityscore" in self.field:
            self.field = self.field.split("ipqualityscore_")[1]
        try:
            if not self.field or not self.value:
                if "Login" in self.field:
                    pass
                else:
                    yield self.gen_record(
                        _time=time.time(), error="Please provide a valid field and value."
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
            if "Dark Web Leak" in self.field or "dark_web_leak" in self.field:
                if "username" in self.field.lower():
                    results_dict = ipqualityscoreclient.dark_web_leak_multithreaded(
                        [self.value], "username"
                    )
                elif "password" in self.field.lower():
                    results_dict = ipqualityscoreclient.dark_web_leak_multithreaded(
                        [self.value], "password"
                    )
                elif "email" in self.field.lower():
                    validate_email_field = Validation.validating_ioc(
                        self.field, self.value
                    )
                    if validate_email_field is not None:
                        results_dict = ipqualityscoreclient.dark_web_leak_multithreaded(
                            [self.value], "email"
                        )
                    else:
                        yield self.gen_record(
                            _time=time.time(), error="Please provide valid Email value."
                        )
                        return
                else:
                    yield self.gen_record(
                        _time=time.time(),
                        error="Field not found. Possible Dark Web Leak Fields are Email, Password, Username.",
                    )
                    return
            elif "Login" in self.field:
                record = {"_time": time.time(), "field": "Login", "value": "IPQS Account Login"}
                url = f"https://www.ipqualityscore.com/api/json/loginhistory/{usercreds.get('password')}/"
                response = requests.get(url, params={"plugin_source": "splunk"}, timeout=10)
                response.raise_for_status()
                data = response.json()
                if data.get("message") == "Success":
                    login_logs = data.get("login_logs")
                    if login_logs:
                        data.pop("login_logs")
                        for obj in login_logs:
                            record.update(data)
                            record.update(obj)
                            record["status"] = "api call success"
                            yield self.gen_record(_raw=json.dumps(record), **record)
                    else:
                        record.update(data)
                        record["status"] = "api call success"
                else:
                    record["message"] = data.get("message")
                    record["status"] = "api call failed"
                    yield self.gen_record(_raw=json.dumps(record), **record)
            else:
                validated_ioc_name = Validation.validating_ioc(self.field, self.value)
                if validated_ioc_name is not None:
                    if self.field == "IP Address" or "ip" in self.field:
                        results_dict = ipqualityscoreclient.ip_detection_multithreaded(
                            [self.value], ipv4_db_file=ipqs_db_file_path_v4, ipv6_db_file=ipqs_db_file_path_v6
                        )
                    elif self.field == "Email Address" or "email" in self.field:
                        results_dict = (
                            ipqualityscoreclient.email_validation_multithreaded(
                                [self.value]
                            )
                            if "@" in self.value
                            else ipqualityscoreclient.url_checker_multithreaded(
                                [self.value]
                            )
                        )
                    elif self.field == "Phone" or "phone" in self.field:
                        results_dict = (
                            ipqualityscoreclient.phone_validation_multithreaded(
                                [self.value]
                            )
                        )
                    elif "url" in self.field.lower() or "domain" in self.field.lower():
                        results_dict = ipqualityscoreclient.url_checker_multithreaded(
                            [self.value]
                        )
                    else:
                        yield {
                            "error": "Field not found. Possible Fields are IP, Email, Domain, URL, Phone."
                        }
                        return
                else:
                    yield {"error": "Please provide valid indicator value."}
                    return

            record = {"_time": time.time(), "field": self.field, "value": self.value}
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
                if record.get("ipqualityscore_from_db_file"):
                    record[
                        ipqualityscoreclient.get_prefix() + "_status"
                    ] = "data fetched from db file"
                else:
                    record[
                        ipqualityscoreclient.get_prefix() + "_status"
                    ] = "api call success"
            else:
                record[
                    ipqualityscoreclient.get_prefix() + "_status"
                ] = "api call failed"
            yield self.gen_record(_raw=json.dumps(record), **record)

        except Exception as err:
            logger.error(f"error occurred: {err}")
            yield {"error": err}


if __name__ == "__main__":
    dispatch(DynamicSearch, sys.argv, sys.stdin, sys.stdout, __name__)
