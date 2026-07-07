# - Consume Alert History by ID
#     - `Documentation
#     <https://developer.carbonblack.com/reference/carbon-black-cloud/platform/latest/alerts-api/>`_
#     - Very specific configuration required for proper operation.
#     - Credential Type: Custom
#     - Global Configuration
#         - None
#     - Search Configuration
#         - API Config: Supports single instance and multi-tenancy
#             - To use Authenticated Support, the ``org_key`` field *MUST* be included in the results
#         - Required fields:  ``org_key``, ``alert_id``
#           Only 1 org_key and 1 alert_id per row.
import sys
import time
from pathlib import Path
import os
import json
import logging
import csv
from VMWUtilities import KennyLoggins
from vmware_cbc_alert_actions import VmwareCBCAlertAction
import vmware_paths
from cbc_sdk.platform import Alert

_alert_name = Path(__file__).stem
__app_name__ = vmware_paths.__app_name__
kl = KennyLoggins()
logger = kl.get_logger(
    app_name=__app_name__, file_name=_alert_name, log_level=logging.INFO
)


class VmwareAlertHistory(VmwareCBCAlertAction):
    def __init__(self, settings, action_name):
        try:
            VmwareCBCAlertAction.__init__(
                self,
                settings=settings,
                action_name=_alert_name,
                filename=_alert_name,
                stanza="global_{}_configuration".format(_alert_name),
            )
            self._cmd = _alert_name
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
            self._log.debug(self._preamble(action="start"))
            alert_sourcetype = f"vmware:alert_action:{_alert_name}"
            raw_alerts = []
            distinct_alert_ids = []
            process_alerts = []
            with self._load_results("rt") as fh:
                self._log.debug("file_handler={}".format(fh))
                raw_alerts = list(csv.DictReader(fh))

            alert_id_field = self._configuration.get("alert_id_field", None)
            org_key_field = self._configuration.get("org_key_field", None)
            for num, result in enumerate(raw_alerts):
                self._log.debug("processing result number result={}".format(num))
                self._log.debug(
                    self._preamble(action="getting_alert_action_fields", r_num=num, **result)
                )
                alert_id = result.get(alert_id_field, None)
                org_key = result.get(org_key_field, None)
                self._log.debug(
                    self._preamble(
                        action="field_check",
                        alert_id_field=alert_id_field,
                        org_key=org_key,
                        org_key_field=org_key_field,
                        alert_id=alert_id,
                    )
                )
                if alert_id is None:
                    msg = self._preamble(
                        action="alert_id_null",
                        alert_id_field=alert_id_field,
                        org_key=org_key,
                        org_key_field=org_key_field,
                        alert_id=alert_id,
                    )
                    self._log.warn(msg)
                    self.addevent(msg, f"{alert_sourcetype}:error")
                    continue
                dist_alert = {
                    "rid": str(num),
                    "org_key": org_key,
                    "alert_id": alert_id,
                    "alert_action_execution_id": self.tracking_key,
                }
                for key in ["host", "sourcetype", "source", "index", "sid"]:
                    if key in result:
                        dist_alert[f"orig_{key}"] = result[key]
                self._log.debug(
                    self._preamble(action="setup_distinct_alert", **dist_alert)
                )
                a_id = f"{org_key}:{alert_id}"
                if a_id not in distinct_alert_ids:
                    distinct_alert_ids.append(a_id)
                    process_alerts.append(dist_alert)
            self._log.info(
                self._preamble(
                    action="processing_events_check",
                    alerts_to_process=len(distinct_alert_ids),
                )
            )
            for alert in process_alerts:
                try:
                    cbapi = None
                    self._log.debug(self._preamble(action="processing_alert", **alert))
                    try:
                        if (
                            alert.get("org_key", None) is not None
                            and self._use_multi_tenant
                        ):
                            org_key = alert.get("org_key")
                            cbapi = self.multi_tenant_apis[org_key]["cb"]
                        else:
                            cbapi = self.cb
                    except Exception as ae:
                        self._catch_error(ae, _alert_name)
                    if cbapi is None:
                        alert["alert_action_exception"] = "api_not_found"
                        self.addevent(
                            json.dumps(dict(alert)), sourcetype=alert_sourcetype
                        )
                        continue
                    alert_id = alert[alert_id_field]
                    self._log.debug(
                        self._preamble(
                            action="gathering_alert_history", alert_id=alert_id
                        )
                    )
                    alert["alert_history"] = cbapi.select(Alert, alert_id).get_history()
                    self._log.debug(
                        self._preamble(
                            action="gathered_alert_history",
                            alert_id=alert_id,
                            num_results=len(alert["alert_history"]),
                        )
                    )
                    self._log.debug(
                        self._preamble(
                            action="gathering_threat_history", alert_id=alert_id
                        )
                    )
                    alert["threat_history"] = cbapi.select(Alert, alert_id).get_history(
                        threat=True
                    )
                    self._log.debug(
                        self._preamble(
                            action="gathered_threat_history",
                            alert_id=alert_id,
                            num_results=len(alert["threat_history"]),
                        )
                    )
                    self.addevent(json.dumps(alert), sourcetype=alert_sourcetype)
                except Exception as fe:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    error_msg = (
                        " "
                        'warn_message="{}" '
                        'warn_type="{}" '
                        'warn_arguments="{}" '
                        'warn_filename="{}" '
                        'warn_line_number="{}" '
                        'alert_name="{}" '.format(
                            str(fe),
                            type(fe),
                            "{}".format(fe),
                            fname,
                            exc_tb.tb_lineno,
                            self._action_name,
                        )
                    )
                    self._log.warning(error_msg)
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
    modaction = None
    try:
        logger.info("instantiating {}".format(_alert_name))
        modaction = VmwareAlertHistory(sys.stdin.read(), action_name=_alert_name)
        modaction.main()
        sc, evttype = modaction.get_evtidx("vmware_cbc_base_index")
        logger.info(
            'action=found_eventtype class=alert_action_index alert_action_index="{}"'.format(
                evttype
            )
        )
        modaction.writeevents(
            index=evttype,
            fext="vmware_cbc_alert_action_alert-history",
            sourcetype="vmware:alert_action:{}".format(_alert_name),
            source="vmware:alert_action:{}:{}".format(
                _alert_name, modaction.payload["search_name"].replace(" ", "_")
            ),
        )
        time.sleep(5)
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
