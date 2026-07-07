"""
Written by Aplura, LLC
Copyright (C) 2016-2022 Aplura, ,LLC

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

This python script is the primary code for the ATA Portal ZTAP Alert Action within Splunk.
"""

import os
import sys
import json
import csv
import logging
import requests
import time
import version
import socket
import uuid
import warnings
from Utilities import KennyLoggins, Utilities
from criticalstart_client import CSAlertAction
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

import multiprocessing.dummy as mp

# Alert actions require an addition to the path, in order to prevent librarly conflicts during Splunk Precedence import.
_APP_NAME = "ztap_app"
_alert_name = "ataportal"
sys.path.insert(0, make_splunkhome_path(["etc", "apps", _APP_NAME, "lib"]))

# Gotta know when to fold 'em. This controls a specific location for logging within Splunk.
# Defaults to /opt/splunk/var/log/splunk/ztap_app/<file_name>
kl = KennyLoggins()
logger = kl.get_logger(
    app_name=_APP_NAME, file_name=_alert_name, log_level=logging.INFO
)


# Overrode the Retry class, to attempt to make the Alert Action calls more reliable during an outage.
class CallbackRetry(Retry):
    def __init__(self, *args, **kwargs):
        self._callback = kwargs.pop("callback", None)
        super(CallbackRetry, self).__init__(*args, **kwargs)

    def new(self, **kw):
        # pass along the subclass additional information when creating
        # a new instance.
        kw["callback"] = self._callback
        return super(CallbackRetry, self).new(**kw)

    def increment(self, method, url, *args, **kwargs):
        if self._callback:
            try:
                self._callback(url)
            except Exception:
                logger.debug("action=callback_retry_exception ignore=true")
        return super(CallbackRetry, self).increment(method, url, *args, **kwargs)


# This is the main class that gets called to execute the Alert Action.
class CSZTAP(CSAlertAction):
    def __init__(self, settings, action_name):
        try:
            #
            # CSAlertAction is a class in the criticalstart_client.py module. criticalstart_client.py contains
            # classes that are base and can be used in multiple things like custom commands, alert actions,
            # modular inputs
            #
            CSAlertAction.__init__(
                self,
                settings=settings,
                action_name=_alert_name,
                filename=_alert_name,
                stanza="global_{}_configuration".format(_alert_name),
            )
            # how many retries should we attempt?
            retries = 4
            # timeout in seconds
            self._http_timeout = 5
            # counter for retry count
            self.retry_count = 0
            self._last_request_time = time.time()

            # Setting up a logging hook so we can programatically within splunk see the call attempts to verify that retries are indeed happening
            def logging_hook(response, *args, **kwargs):
                # log debug on retry events.
                now = time.time()
                logger.debug(
                    f"action=requests_logging_hook retry={self.retry_count} time={now} response={response} args={args} kwargs={kwargs} time_since_last={(now - self._last_request_time):.5f}s last={self._last_request_time}"
                )
                self.retry_count += 1
                self._last_request_time = time.time()

            self.retry_strategy = CallbackRetry(
                total=retries,
                read=retries,
                connect=retries,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["POST"],
                backoff_factor=2,
                callback=logging_hook,
            )
            adapter = HTTPAdapter(max_retries=self.retry_strategy)
            self.http = requests.Session()
            self.http.mount("https://", adapter)
            self.http.hooks["response"] = [logging_hook]
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = (
                'error_message="{}" '
                'error_type="{}" '
                'error_arguments="{}" '
                'error_filename="{}" '
                'error_line_number="{}" '
                'alert_name="{}" '.format(
                    str(e),
                    type(e),
                    "{}".format(e),
                    fname,
                    exc_tb.tb_lineno,
                    _alert_name,
                )
            )
            logger.fatal(error_msg)

    @staticmethod
    def extract(result):
        return {
            key: value for (key, value) in result.items() if not key.startswith("__")
        }

    def main(self):
        try:
            self._log.debug("action=start_main next=load_result_set_from_splunk_tgz")
            with self._load_results("rt") as fh:
                self._log.debug("action=loaded_result_set file_handler={}".format(fh))
                #
                # Allow for multiprocessing threads. Use 10 worker processes
                # Using a parallel processing dummy threads pool to accelerate the speed of events coming from the Search Head.
                #
                thread_count = 10
                self._log.debug(f"action=setting_mp_pool thread_count={thread_count}")
                p = mp.Pool(thread_count)

                def do_threaded_result(num, result):
                    try:
                        self._log.debug(
                            "action=process_result_thread result_num={}".format(num)
                        )
                        # CIM Actions - rid - result ID
                        result.setdefault("rid", str(num))
                        #
                        # Retrieve alert action parameters from result being processed
                        #
                        self._log.debug(
                            'action=process_result_thread result_num={} next="{}"'.format(
                                num, "setting HTTP headers"
                            )
                        )
                        headers = {
                            "Content-Type": "application/json",
                            "User-Agent": f"Splunk-ztap_app/{version.__version__}",
                        }
                        self._log.debug(
                            'action=process_result_thread result_num={} next="{}"'.format(
                                num, "setting body to post to ZTAP"
                            )
                        )

                        body = {
                            "search_query": self.ztap_search_job["search"],
                            "sid": self.sid,
                            "session_key": self.session_key,
                            "@version": "1",
                            "hostname": self.server_host,
                            "search_name": self.search_name,
                            "server_uri": self.server_uri,
                            "results_file": self.results_file,
                            "result_id": result["rid"],
                            "owner": self.owner,
                            "app": self.search_app,
                            "server_host": self.server_host,
                            "search_uri": self.search_uri,
                            "auth_token": self.token,
                            "search_earliest": datetime.fromisoformat(
                                self.ztap_search_job["earliestTime"]
                            ).strftime("%s"),
                            "search_latest": datetime.fromisoformat(
                                self.ztap_search_job["latestTime"]
                            ).strftime("%s"),
                            **self.extract(result),
                        }

                        configuration = self._configuration
                        if configuration.get("title"):
                            body["ata_incident_title_override"] = configuration["title"]
                        if configuration.get("group_by"):
                            body["ata_event_nuance_override"] = configuration[
                                "group_by"
                            ]
                        if configuration.get("event_type"):
                            body["event_type"] = configuration["event_type"]
                        if configuration.get("priority"):
                            body["event_priority"] = configuration["priority"]
                        if configuration.get("category"):
                            body["event_category"] = configuration["category"]

                        base_url = self.url

                        #
                        # Determine if a proxy server has been configured and associated with the alert action configuration
                        # Send to ZTAP appliance
                        #
                        # self._log.debug("body: {}".format(body))
                        self._log.debug(
                            'action=process_result_thread result_num={} next="{}"'.format(
                                num, "setting proxy configurations if required"
                            )
                        )
                        if self.proxy is not None:
                            self._log.debug(
                                'action=process_result_thread result_num={} next="{}"'.format(
                                    num, "send request through proxy"
                                )
                            )

                        Utilities.verify_https(base_url)
                        response = self.http.post(
                            url=base_url,
                            data=json.dumps(body),
                            headers=headers,
                            proxies=self.proxy,
                            timeout=self._http_timeout,
                        )
                        self._log.debug(
                            'action=process_result_thread result_num={} done="{}" body="{}"'.format(
                                num, "send_event_to_ztap", body
                            )
                        )
                        self._log.debug("POST event to ZTAP, body: {}".format(body))
                        self._log.debug(
                            "response status code: {}".format(response.status_code)
                        )

                        #
                        # Create status event that will be sent to Splunk for tracking
                        #
                        send_ztap_results = {
                            "psa_id": self.org_key,
                            "action": "success",
                            "description": "Created by alert action: {}".format(
                                _alert_name
                            ),
                            "sent_timestamp": datetime.utcnow().isoformat(),
                            "response_code": response.status_code,
                            "result_sent": result,
                        }

                        #
                        # Send status event to Splunk. The event will be stored in the index that is configured as the base
                        # index on the application configuration page
                        #
                        self.addevent(
                            json.dumps(send_ztap_results),
                            sourcetype="critical_start:alert_action:{}".format(
                                _alert_name
                            ),
                        )
                        self._log.debug(
                            'action=process_result_thread result_num={} done="{}" body="{}"'.format(
                                num, "send_event_response_to_splunk", send_ztap_results
                            )
                        )
                        if not response.ok:
                            self._log.error(
                                "function=main action=not_ok_response status={}".format(
                                    response.status_code
                                )
                            )
                            response.raise_for_status()

                    except Exception as lre:
                        self.log_exception(lre)

                #
                # Create matrix of events that will be used for multiprocessing
                #
                self._log.debug(
                    f'action=creating_mp_matrix reason="parallel processing"'
                )
                matrix = [
                    (num, result) for num, result in enumerate(csv.DictReader(fh))
                ]
                self._log.debug(
                    'action=creating_starmap reason="parallel processing of results matrix"'
                )
                p.starmap(do_threaded_result, matrix)
                self._log.debug('action=closing_threads reason="wait for it"')
                p.close()
                self._log.debug('action=thread_join reason="finish_sending_out"')
                p.join()

        except Exception as me:
            self._catch_error(me, action_name=self._action_name)

    def send_test_event(self):
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"Splunk-ztap_app/{version.__version__}",
        }
        self._log.debug("action=send_test_event")
        host = socket.gethostname()
        # Send a message with specific values.  These values are what the Portal API
        # searches for to verify that the test message was received.
        body = {
            "ata_incident_title_override": "CS Splunk App Test Event",
            "auth_token": self.token,
            "message": "This is a test event triggered by the CS Splunk App.",
            "hostname": host,
            "server_host": host,
            "sid": str(uuid.uuid4()),
        }

        base_url = self.url

        self._log.debug("POST test event to ZTAP, body: {}".format(body))

        Utilities.verify_https(base_url)

        return self.http.post(
            url=base_url,
            data=json.dumps(body),
            headers=headers,
            proxies=self.proxy,
            timeout=self._http_timeout,
        )

    def log_exception(self, ex):
        _, _, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error_msg_exception = 'function={} action={} exception_line={} exception_file={} message="{}" sent_timestamp={}'.format(
            "main",
            "failure",
            exc_tb.tb_lineno,
            fname,
            ex,
            datetime.utcnow().isoformat(),
        )
        self.addevent(
            f'{error_msg_exception} description="Alert Action Error"',
            sourcetype="critical_start:alert_action:{}:error".format(_alert_name),
        )
        self._log.error(error_msg_exception)


if __name__ == "__main__":
    # This is standard Alert Action code for Splunk. Don't modify this please.
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        msg = "FATAL Unsupported execution mode (expected --execute flag)"
        logger.error(msg)
        sys.exit(1)

    modaction = None
    try:
        logger.info("instantiating {}".format(_alert_name))
        #
        # Get events from Splunk (sent via STDIN)
        #
        modaction = CSZTAP(sys.stdin.read(), action_name=_alert_name)
        modaction.main()
        # send_to_ztap(loads(sys.stdin.read()))
        sc, evttype = modaction.get_evtidx("critical_start_aa_index")
        logger.info(
            'action=found_eventtype class=alert_action_index alert_action_index="{}"'.format(
                evttype
            )
        )
        #
        # Send event that will be used adaptive response framework so ES can pickup the result and display it
        #
        modaction.writeevents(
            index=evttype,
            fext="critical_start_alert_action_st",
            sourcetype="critical_start:alert_action:{}".format(_alert_name),
            source="critical_start:alert_action:{}:{}".format(
                _alert_name, modaction.payload["search_name"].replace(" ", "_")
            ),
        )

    except Exception as e:
        try:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = (
                " "
                'error_message="{}" '
                'error_type="{}" '
                'error_arguments="{}" '
                'error_filename="{}" '
                'error_line_number="{}" '
                'alert_name="{}" '.format(
                    str(e),
                    type(e),
                    "{}".format(e),
                    fname,
                    exc_tb.tb_lineno,
                    _alert_name,
                )
            )
            logger.error(error_msg)
        except Exception as e:
            logger.critical(e)
        sys.exit(3)
