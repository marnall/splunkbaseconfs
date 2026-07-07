from __future__ import absolute_import
import os
import sys
import json
import requests
from datetime import datetime
from settings import APP_ID

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(
    os.path.join(splunkhome, "etc", "apps", APP_ID, "lib")
)
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)
from dt_api_wrapper import DtApiWrapper
from dt_logger import DTLogger
from domaintools.exceptions import (
    ServiceException,
    NotAuthorizedException,
    ServiceUnavailableException,
)
import dt_exception_messages


@Configuration()
class ImportIrisDetectMonitorsCommand(GeneratingCommand):
    """This custom search command makes a request to the Iris Detect Monitors API endpoint and outputs the results.

        Inherits from the GeneratingCommand custom search type. Override the `generate` method as the entrypoint to this script

        Example:
            | dtimportirisdetectmonitors
    """

    feature = Option(
        doc="""
                **Syntax:** **feature=***<feature>*
                **Description:** Feature in the app where this was called""",
        default="adhoc",
        require=False,
    )

    def get_token(self):
        """get session key used to decrpyt api credentials"""
        return self.metadata.searchinfo.session_key

    def get_user(self):
        """get current logged in user"""
        return self.metadata.searchinfo.username

    def generate(self):
        """This is the entry point to a GeneratingCommand subclass. You must override this method

            :return: generator rows to pass on to next command of SPL search after transform
        """
        self.dt_log = DTLogger(
            "iris_detect", os.path.basename(__file__), self.get_user(), self.feature
        )
        self.dt_log.info("starting import_iris_detect_monitors.py")

        api_wrapper = DtApiWrapper(self.service, self.dt_log)
        api = api_wrapper.create_dt_api()
        try:
            kwargs = {"offset": 0}
            response = api.iris_detect_monitors(**kwargs).response()
            results = response.get("monitors", [])
            count = len(results)
            while response.get("total_count", 0) != count:
                kwargs["offset"] += response.get("limit")
                response = api.iris_detect_monitors(**kwargs).response()
                count += len(response.get("monitors", []))
                results.extend(response.get("monitors"))

            for result in results:
                yield {
                    "monitor_id": result.get("id"),
                    "term": result.get("term"),
                    "state": result.get("state"),
                    "match_substring_variations": result.get("match_substring_variations"),
                    "nameserver_exclusions": result.get("nameserver_exclusions"),
                    "text_exclusions": result.get("text_exclusions"),
                    "created_date": datetime.fromisoformat(result.get("created_date")).timestamp(),
                    "updated_date": datetime.fromisoformat(result.get("updated_date")).timestamp(),
                    "status": result.get("status"),
                    "created_by": result.get("created_by"),
                    "_raw": json.dumps(result),
                }
            self.dt_log.info("api status up", {"status": "up"})
        except NotAuthorizedException as e:
            self.dt_log.error(e, {"status": "down"})
            raise Exception(dt_exception_messages.missing_iris_detect_access)
        except ServiceUnavailableException as e:
            self.dt_log.error(e, {"status": "down"})
            raise Exception(dt_exception_messages.service_not_available)
        except requests.exceptions.ProxyError as e:
            self.dt_log.error(e, {"status": "down"})
            raise Exception(dt_exception_messages.proxy_error)
        except requests.exceptions.SSLError as e:
            self.dt_log.error(e, {"status": "down"})
            raise Exception(dt_exception_messages.ssl_error.format(e))
        except Exception as e:
            self.dt_log.error(e, {"status": "down"})
            raise Exception(dt_exception_messages.generic.format(e))

        self.dt_log.info("completed import_iris_detect_monitors.py")


dispatch(ImportIrisDetectMonitorsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
