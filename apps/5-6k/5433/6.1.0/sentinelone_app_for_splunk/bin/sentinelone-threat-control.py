"""
sentinelone-threat-control.py ;; 
Written by ksmith for Aplura, LLC
Copyright (C) 2016-2024 Aplura, LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import sys
import os
import json
import logging
import csv
import re
from Utilities import KennyLoggins
from s1_alert_action import S1AlertAction
from s1_app_properties import __app_name__
import multiprocessing.dummy as mp
from datetime import datetime
import s1_paths

_alert_name = "sentinelone-threat-control"
kl = KennyLoggins()
logger = kl.get_logger(
    app_name=__app_name__, file_name=_alert_name, log_level=logging.INFO
)


class S1ThreatControl(S1AlertAction):
    def __init__(self, settings, action_name):
        try:
            S1AlertAction.__init__(
                self,
                settings=settings,
                action_name=_alert_name
            )
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

    def main(self):
        try:
            self._log.debug("action=start")
            s1_clients = {}
            self.setup_s1_client()
            s1_clients = self.clients_by_url()
            with self._load_results("rt") as fh:
                self._log.debug("file_handler={}".format(fh))
                p = mp.Pool(10)

                def us(r, k):
                    if k in r:
                        r["orig_{}".format(k)] = r.get(k, "")
                        del r[k]

                def do_threaded_result(num, result):
                    try:
                        self._log.debug(
                            "processing result number result={}".format(num)
                        )
                        result.setdefault("rid", str(num))
                        #  Update results for orig_ keys
                        [
                            us(result, key)
                            for key in ["sourcetype", "source", "host", "index"]
                        ]
                        delete_result_keys = [
                            key for key in result if re.match(r"_[a-z_]+", key)
                        ]
                        for key in delete_result_keys:
                            del result[key]
                        self._log.info(
                            "action=applying_threat_control_action, result={}".format(
                                num
                            )
                        )
                        incident_status = self._configuration.get(
                            "incident_status", None
                        )
                        verdict = self._configuration.get("verdict", None)
                        site_ids = result.get(
                            self._configuration.get("site_id", None), None
                        )
                        threat_ids = result.get(
                            self._configuration.get("threat_id", None), None
                        )
                        default_auth_hosts = {
                            x: self.utils.get_api_config(x)
                            for x in self.get_config("auth_hosts", "").split(",")
                        }
                        self._log.debug(
                            "default_auth_hosts: {}, type: {}".format(
                                default_auth_hosts, type(default_auth_hosts)
                            )
                        )
                        for key, value in default_auth_hosts.items():
                            mgmt_host = result.get(
                                self._configuration.get("mgmt_host", value["url"]),
                                value["url"],
                            )
                            # self._log.info("mgmt_host: {}".format(mgmt_host))
                            for mgmt_url in s1_clients.items():
                                if mgmt_host in mgmt_url[0]:
                                    tmp_site_ids = []
                                    tmp_threat_ids = []
                                    self._log.debug("mgmt_host: {}".format(mgmt_host))

                                    if site_ids is None:
                                        msg = (
                                            "action=validating_configuration_values, "
                                            "msg='no site ids specified, will not continue'"
                                        )
                                        self._log.warning(msg)
                                        self._log.debug(
                                            "{}".format(json.dumps(self._configuration))
                                        )
                                        self.addevent(
                                            msg,
                                            f"sentinelone:alert_action{_alert_name}:error",
                                        )
                                        continue_processing = False
                                    else:
                                        continue_processing = True
                                        tmp_site_ids = site_ids.split(",")

                                    if threat_ids is None:
                                        msg = (
                                            "action=validating_configuration_values "
                                            "msg=no threat ids specified, will not continue"
                                        )
                                        self._log.warning(msg)
                                        self._log.debug(
                                            "{}".format(json.dumps(self._configuration))
                                        )
                                        self.addevent(
                                            msg,
                                            f"sentinelone:alert_action{_alert_name}:error",
                                        )
                                        continue_processing = False
                                    else:
                                        continue_processing = True
                                        tmp_threat_ids = threat_ids.split(",")

                                    if incident_status is None:
                                        msg = (
                                            "action=validating_configuration_values"
                                            "msg=no incident status specified, will not continue"
                                        )
                                        self._log.warning(msg)
                                        self._log.debug(
                                            "{}".format(json.dumps(self._configuration))
                                        )
                                        self.addevent(
                                            msg,
                                            f"sentinelone:alert_action{_alert_name}:error",
                                        )
                                        continue_processing = False
                                    else:
                                        continue_processing = True

                                    if incident_status == "resolved" and (
                                        verdict is None or verdict == "undefined"
                                    ):
                                        msg = (
                                            "action=validating_configuration_values, "
                                            "msg=incident status cannot be set to resovled without "
                                            "an analyst verdict, will not continue"
                                        )
                                        self._log.warning(msg)
                                        self._log.debug(
                                            "{}".format(json.dumps(self._configuration))
                                        )
                                        self.addevent(
                                            msg,
                                            "sentinelone:alert_action{}:error".format(
                                                _alert_name
                                            ),
                                        )
                                        continue_processing = False
                                    else:
                                        continue_processing = True

                                    if continue_processing:
                                        self._log.info(
                                            "action=processing threat control actions"
                                            "site_ids: {}, threat_ids: {}, incident_status: {}, "
                                            "verdict: {}, mgmt_host: {}".format(
                                                tmp_site_ids,
                                                tmp_threat_ids,
                                                incident_status,
                                                verdict,
                                                mgmt_host,
                                            )
                                        )
                                        try:
                                            resp = s1_clients[
                                                mgmt_host
                                            ].threats.update_threat_incident(
                                                incident_status=incident_status,
                                                analyst_verdict=verdict,
                                                ids=threat_ids,
                                                siteIds=site_ids,
                                            )
                                            self._log.debug(
                                                "resp_status_code: {}, resp after calling action: {}".format(
                                                    resp.status_code, resp
                                                )
                                            )
                                            results = resp.json
                                            self._log.debug(
                                                "results after calling action: {}".format(
                                                    results
                                                )
                                            )
                                        except Exception as rerr:
                                            msg = (
                                                "action=processing site_ids: {}, threat_ids: {},"
                                                "incident_status: {}, analyst_verdict: {}, msg={}".format(
                                                    site_ids,
                                                    threat_ids,
                                                    incident_status,
                                                    verdict,
                                                    rerr,
                                                )
                                            )
                                            self._log.warning(msg)
                                            self._log.debug(
                                                "{}".format(
                                                    json.dumps(self._configuration)
                                                )
                                            )
                                            self.addevent(
                                                msg,
                                                "sentinelone:alert_action:{}:error".format(
                                                    _alert_name
                                                ),
                                            )
                                            return

                                        threat_control_event = {}
                                        threat_control_event[
                                            "description"
                                        ] = "Created by alert action: {}".format(
                                            _alert_name
                                        )
                                        threat_control_event[
                                            "management_host"
                                        ] = mgmt_host
                                        threat_control_event["siteId"] = site_ids
                                        threat_control_event["threatId"] = threat_ids
                                        threat_control_event[
                                            "incident_status"
                                        ] = incident_status
                                        threat_control_event[
                                            "analyst_verdict"
                                        ] = verdict
                                        threat_control_event["result"] = results
                                        threat_control_event[
                                            "updated_timestamp"
                                        ] = datetime.utcnow().isoformat()
                                        self.addevent(
                                            json.dumps(threat_control_event),
                                            sourcetype="sentinelone:alert_action:{}".format(
                                                _alert_name
                                            ),
                                        )
                                else:
                                    self._log.error(
                                        "action=process threat control, "
                                        "msg=mgmt_host not found in instantiated clients:"
                                        " mgmt_host: {}, mgmt_url: {}".format(
                                            mgmt_host, mgmt_url[0]
                                        )
                                    )

                    except Exception as lre:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        self._log.error(
                            "function=main action=fatal_error exception_line={} exception_file={}  message={}".format(
                                exc_tb.tb_lineno, fname, lre
                            )
                        )

                matrix = [
                    (num, result) for num, result in enumerate(csv.DictReader(fh))
                ]
                p.starmap(do_threaded_result, matrix)
                p.close()
                p.join()

        except Exception as me:
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
                    str(me),
                    type(me),
                    "{}".format(me),
                    fname,
                    exc_tb.tb_lineno,
                    self._action_name,
                )
            )
            self._log.error(error_msg)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        logger.fatal("FATAL Unsupported execution mode (expected --execute flag)")
        sys.exit(1)
    try:
        logger.info("instantiating {}".format(_alert_name))
        modaction = S1ThreatControl(sys.stdin.read(), action_name=_alert_name)
        modaction.main()
        sc, evttype = modaction.get_evtidx("sentinelone_base_index")
        logger.info(
            'action=found_eventtype class=alert_action_index alert_action_index="{}"'.format(
                evttype
            )
        )
        modaction.writeevents(
            index=evttype,
            fext="sentinelone_alert_action_st",
            sourcetype="sentinelone:alert_action:{}".format(_alert_name),
            source="sentinelone:alert_action:{}:{}".format(
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
