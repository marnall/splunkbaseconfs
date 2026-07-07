import sys
import os
import json
import time
import traceback
import urllib.parse

sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..')))
import import_declare_test  # noqa: E402 F401
import splunk.rest as rest  # noqa: E402
from solnlib.credentials import CredentialManager  # noqa: E402
from splunk.persistconn.application import PersistentServerConnectionApplication  # noqa: E402
from databee_helpers.logger_manager import setup_logging  # noqa: E402
from databee_helpers.conf_helper import get_credentials  # noqa: E402
from databee_helpers.rest_helper import RestHelper  # noqa: E402
from databee_helpers.constants import ENDPOINT_SEARCH_JOBS  # noqa: E402
from solnlib.utils import is_true  # noqa: E402

APP_NAME = import_declare_test.ta_name


class DatabeePostHistoricalAlertsHttpConnector(PersistentServerConnectionApplication):
    """Custom Encryption Handler."""

    def __init__(self, _command_line, _command_arg):
        """Initialize object with given parameters."""
        self.logger = setup_logging("ta_databee_post_historical_alerts_http_connector")
        self.payload = {}
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a synchronous from splunkd.
    def handle(self, in_string):
        """
        For using any custom command, Called for a simple synchronous request.

        @param in_string: request data passed in
        @rtype: string or dict
        @return: String to return in response.  If a dict was passed in,
                it will automatically be JSON encoded before being returned.
        """
        try:
            self.logger.info(
                "message=start_execution | DataBee Info: Started DataBee Post Historical"
                " Alerts HTTP Connector."
            )
            start_time = time.time()
            req_data = json.loads(in_string)
            self.admin_session_key = req_data.get('system_authtoken', None)
            form_data = dict(req_data.get("form"))

            self.account_name = form_data.get("account_name")
            self.triggered_alerts_sid = form_data.get("triggered_alerts_sid").split(",")

            self.logger.info(
                f'message=parameter_received account_name={self.account_name}'
                f' triggered_alerts_sid={self.triggered_alerts_sid}'
            )

            databee_config = {
                "session_key": self.admin_session_key
            }
            account_info = get_credentials(
                session_key=self.admin_session_key,
                account_name=self.account_name
            )
            databee_config.update(account_info)
            databee_rest_helper = RestHelper(databee_config, self.logger)

            alerts_sid_label_dict = dict()
            notable_sid_label_dict = dict()
            for item in self.triggered_alerts_sid:
                item = item.split('-----')
                sid = item[0]
                trigger_time_epoch = item[1]
                src = f'| rest /servicesNS/nobody/-/search/jobs/{sid}'
                self.logger.info(
                    'message=search_query | Search query to be performed for getting '
                    f'label of triggered alert: {src}'
                )
                args = {
                    "search": src,
                    "output_mode": "json"
                }
                # get label for triggered alerts
                _, content = rest.simpleRequest(
                    ENDPOINT_SEARCH_JOBS,
                    sessionKey=self.admin_session_key,
                    postargs=args,
                    method="POST",
                    raiseAllErrors=True,
                )
                content = content.splitlines()
                for res in content:
                    res = json.loads(res)
                    sid_label = res.get('result', {}).get('label', None)
                    if sid_label:
                        # check notable alert action is enabled or not
                        _, content = rest.simpleRequest(
                            f"/servicesNS/nobody/-/saved/searches/{urllib.parse.quote(sid_label)}",
                            sessionKey=self.admin_session_key,
                            getargs={"output_mode": "json"},
                            method="GET",
                            raiseAllErrors=True,
                        )

                        conf_info = json.loads(content)['entry'][0]['content']
                        if is_true(conf_info.get('action.notable', False)):
                            notable_sid_label_dict[sid] = [sid_label, trigger_time_epoch]
                        else:
                            alerts_sid_label_dict[sid] = [sid_label, trigger_time_epoch]
                    else:
                        self.logger.error(
                            f'message=label_not_found | Error occured while getting label of triggered alert: {sid}'
                        )
            if alerts_sid_label_dict:
                self.logger.debug(
                    f'message=created_alerts_sid_label_dict | alerts_sid_label_dict={alerts_sid_label_dict}'
                )
                databee_rest_helper.post_alerts_events_to_databee(alerts_sid_label_dict)
            if notable_sid_label_dict:
                self.logger.debug(
                    f'message=created_notable_sid_label_dict | notable_sid_label_dict={notable_sid_label_dict}'
                )
                databee_rest_helper.post_notable_events_to_databee(notable_sid_label_dict)

            self.logger.info(
                'message=end_execution | End of the DataBee Post Historical Alerts HTTP.'
                " Total time taken: elapsed_seconds={:.3f}".format(
                    time.time() - start_time
                )
            )
            self.payload['response'] = "Success"
            self.status = 200
            return {'payload': self.payload,
                    'status': self.status
                    }

        except Exception:
            error_msg = f"DataBee Error: Error occured while posting historical alerts - {traceback.format_exc()}"
            self.logger.error(
                f'message=error_occured | {error_msg}'
            )
            return {
                'payload': error_msg,
                'status': 500
            }

    def handleStream(self, handle, in_string):
        """For future use."""
        raise NotImplementedError("PersistentServerConnectionApplication.handleStream")

    def done(self):
        """Virtual method which can be optionally overridden to receive a callback after the request completes."""
        pass
