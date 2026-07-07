import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ipinfo_bootstrap  # noqa: F401  -- pin vendored splunklib before any other import to defeat Splunk Enterprise Security sys.path collisions

from ipinfo.logging import get_logger
from ipinfo_RestAPI import make_rest_request
from splunklib.searchcommands import Configuration, GeneratingCommand, dispatch


@Configuration()
class IpinfoMeCommand(GeneratingCommand):
    # Custm command ipinfome to get utilization details from ipinfo/me endpoint
    def get_current_utilization(self):
        logger = get_logger("ipinfo_me")
        try:
            current_utilization = {"day": 0, "month": 0, "limit": 0, "remaining": 0}
            current_utilization_response = make_rest_request(self, None)
            current_utilization_response_json = json.loads(current_utilization_response)
            if current_utilization_response_json.get("requests"):
                current_utilization["day"] = current_utilization_response_json.get("requests").get("day")
                current_utilization["month"] = current_utilization_response_json.get("requests").get("month")
                current_utilization["limit"] = current_utilization_response_json.get("requests").get("limit")
                current_utilization["remaining"] = current_utilization_response_json.get("requests").get("remaining")
            else:
                logger.error("Error while fetching Current Utilization")
                pass
            return current_utilization
        except Exception as e:
            logger.error(e)
            logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
            return {"day": 0, "month": 0, "limit": 0, "remaining": 0}

    def generate(self):
        current_utilization = self.get_current_utilization()
        yield current_utilization


if __name__ == "__main__":
    dispatch(IpinfoMeCommand, sys.argv, sys.stdin, sys.stdout, __name__)
