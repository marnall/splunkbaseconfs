import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import (Configuration, GeneratingCommand,
                                      dispatch)

from utils import setup_logging
import requests


@Configuration()
class IPQS(GeneratingCommand):
    def generate(self):
        try:
            logger = setup_logging()
            storage_passwords = self.service.storage_passwords
            usercreds = None
            for credential in storage_passwords:
                if credential.content.get("realm") != "ipqualityscore_realm":
                    continue
                usercreds = {
                    "username": credential.content.get("username"),
                    "password": credential.content.get("clear_password"),
                }
            record = {"_time": time.time()}
            if usercreds is not None:
                url = f"https://www.ipqualityscore.com/api/json/loginhistory/{usercreds.get('password')}/"
                response = requests.get(url, params={"plugin_source": "splunk"}, timeout=10)
                response.raise_for_status()
                data = response.json()
                if data.get("message") == "Success":
                    record.update(data)
                    record["_status"] = "api call success"
                else:
                    record["message"] = data.get("message")
                    record["_status"] = "api call failed"
                yield self.gen_record(_raw=json.dumps(record), **record)
            else:
                yield self.gen_record(
                    _time=time.time(), error="No credentials have been found."
                )
                return
        except Exception as err:
            yield {"_raw": err, "_time": time.time()}
            logger.exception(err)


if __name__ == "__main__":
    dispatch(IPQS, sys.argv, sys.stdin, sys.stdout, __name__)
