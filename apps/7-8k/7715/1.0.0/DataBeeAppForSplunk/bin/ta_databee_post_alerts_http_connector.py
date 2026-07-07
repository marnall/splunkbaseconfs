"""DataBee post HTTP Conntector Alert Action file."""
import import_declare_test  # isort: skip # noqa: F401
import sys
import time
import json
import traceback
import urllib.parse
from alert_actions_base import ModularAlertBase
from databee_helpers.conf_helper import get_credentials
from databee_helpers.rest_helper import RestHelper
from databee_helpers.constants import ENDPOINT_SEARCH_JOBS
import splunk.rest as rest
from solnlib.utils import is_true


class AlertActionPostDataHTTPConnector(ModularAlertBase):
    """Alert Action."""

    def __init__(self, ta_name, alert_name):
        """Initialise Alert Action."""
        super(AlertActionPostDataHTTPConnector, self).__init__(ta_name, alert_name)

    def validate_params(self):
        """Validate Params."""
        if not self.get_param("global_account"):
            self.log_error("DataBee Account is a mandatory parameter, but its value is None.")
            return False
        return True

    def check_notable_creation_status(self):
        flag = True
        for x in range(1, 6):
            if flag:
                self.log_debug(
                    f'checking the signature "Modular action script duration" with attempt: {x}'
                )
                src_modaction = f'search tag=modaction sid="{self.sid}" | fields *'
                self.log_debug(
                    'Search query to be performed for checking the signature '
                    f' "Modular action script duration": {src_modaction}'
                )
                args = {
                    "search": src_modaction,
                    "output_mode": "json",
                    "earliest_time": "-10m"
                }

                # get triggered alerts
                _, content = rest.simpleRequest(
                    ENDPOINT_SEARCH_JOBS,
                    sessionKey=self.session_key,
                    postargs=args,
                    method="POST",
                    raiseAllErrors=True,
                )
                content = content.splitlines()
                for res in content:
                    res = json.loads(res)
                    signature = res.get("result", {}).get("signature", "")
                    if signature == 'Modular action script duration':
                        flag = False
                time.sleep(10)

    def process_event(self, *args, **kwargs):
        """Process events."""
        status = 0
        start_time = time.time()
        try:
            if not self.validate_params():
                return 3
            self.global_account = self.get_param('global_account')
            self.log_info("Alert action ta_databee_post_alerts_http_connector started.")
            self.log_debug((
                f'action=parameter_received global_account={self.global_account}'))

            sid_label_dict = {
                self.sid: [self.search_name, int(time.time())]
            }
            databee_config = {
                "session_key": self.session_key
            }
            account_info = get_credentials(
                session_key=self.session_key,
                account_name=self.global_account
            )
            databee_config.update(account_info)
            databee_rest_helper = RestHelper(databee_config, self._logger)

            # check notable alert action is enabled or not
            status, content = rest.simpleRequest(
                f"/servicesNS/nobody/-/saved/searches/{urllib.parse.quote(self.search_name)}",
                sessionKey=self.session_key,
                getargs={"output_mode": "json"},
                method="GET",
                raiseAllErrors=True,
            )

            conf_info = json.loads(content)['entry'][0]['content']

            if is_true(conf_info.get('action.notable', False)):
                self.log_info('Posting the events with the notable action schema.')
                self.check_notable_creation_status()
                databee_rest_helper.post_notable_events_to_databee(sid_label_dict)

            else:
                databee_rest_helper.post_alerts_events_to_databee(sid_label_dict)

            total_time_taken = time.time() - start_time
            self.log_info("Alert Action completed and total time taken: {}".format(total_time_taken))
            return 0
        except (AttributeError, TypeError) as ae:
            self.log_error(
                "Error: {}. Double check spelling and also verify that a compatible version of "
                "Splunk_SA_CIM is installed.".format(str(ae))
            )
            return 4
        except Exception as e:
            msg = "Unexpected error: {}."
            if str(e):
                self.log_error(msg.format(str(e)))
            else:
                self.log_error(msg.format(traceback.format_exc()))
            return 5
        return status


if __name__ == "__main__":
    exitcode = AlertActionPostDataHTTPConnector(
        "DataBeeAppForSplunk", "ta_databee_post_alerts_http_connector"
    ).run(sys.argv)
    sys.exit(exitcode)
