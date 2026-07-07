# - Enrich CB Analytics Events
#     - `Documentation
#     <https://developer.carbonblack.com/reference/carbon-black-cloud/platform/latest/platform-search-api-enriched-events/#start-an-enriched-events-search-v2>`_
#     - Very specific configuration required for proper operation.
#     - Credential Type: Custom
#     - Global Configuration
#         - None
#     - Search Configuration
#         - API Config: Supports single instance and multi-tenancy
#             - To use Authenticated Support, the ``org_key`` field *MUST* be included in the results
#         - Required fields: ``sourcetype``, ``host``, ``org_key``, ``alert_id``, ``source``
#           Only 1 org_key and 1 alert_id per row.
import sys
from pathlib import Path
import os
import json
import logging
import csv
import time
import uuid
from VMWUtilities import KennyLoggins
from vmware_cbc_alert_actions import VmwareCBCAlertAction
import vmware_paths
from vmware_cbc_classes import EnrichedEventObservationJson

__app_name__ = vmware_paths.__app_name__
_alert_name = Path(__file__).stem

kl = KennyLoggins()
logger = kl.get_logger(app_name=__app_name__, file_name=_alert_name, log_level=logging.INFO)


class VmwareEnrichEventsObs(VmwareCBCAlertAction):
    def __init__(self, settings, action_name):
        try:
            VmwareCBCAlertAction.__init__(self, settings=settings, action_name=_alert_name,
                                          filename=_alert_name,
                                          stanza="global_{}_configuration".format(_alert_name))
            self.tracking_key = "{}".format(uuid.uuid4())
            self._cmd = _alert_name
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = "error_message=\"{}\" " \
                        "error_type=\"{}\" " \
                        "error_arguments=\"{}\" " \
                        "error_filename=\"{}\" " \
                        "error_line_number=\"{}\" " \
                        "alert_name=\"{}\" " \
                .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, _alert_name)
            logger.fatal(error_msg)

    def _preamble(self, kwargs):
        dict_strs = [f'{k}="{kwargs[k]}"' for k in kwargs]
        return f'cmd="{self._cmd}" tracking_uuid="{self.tracking_key}" {" ".join(dict_strs)}'

    def main(self):
        try:
            self._log.debug(self._preamble({"action": "start"}))
            alert_sourcetype = f"vmware:alert_action:{_alert_name}"
            raw_alerts = []
            distinct_alert_ids = []
            process_alerts = []
            with self._load_results("rt") as fh:
                self._log.debug("file_handler={}".format(fh))
                raw_alerts = list(csv.DictReader(fh))
            for num, result in enumerate(raw_alerts):
                self._log.debug("processing result number result={}".format(num))
                self._log.debug(self._preamble({"action": "getting_alert_action_fields", "r_num": num}))
                alert_id_field = self._configuration.get("alert_id_field", None)
                org_key_field = self._configuration.get("org_key_field", None)
                alert_id = result.get(alert_id_field, None)
                org_key = result.get(org_key_field, None)
                self._log.debug(self._preamble(
                    {"action": "field_check", "alert_id_field": alert_id_field, "org_key": org_key,
                     "org_key_field": org_key_field, "alert_id": alert_id}))
                if alert_id is None:
                    msg = self._preamble(
                        {"action": "alert_id_null", "alert_id_field": alert_id_field, "org_key": org_key,
                         "org_key_field": org_key_field, "alert_id": alert_id})
                    self._log.warn(msg)
                    self.addevent(msg, f"{alert_sourcetype}:error")
                    continue
                dist_alert = {
                    'rid': str(num),
                    'org_key': org_key,
                    'alert_id': alert_id,
                    'alert_action_execution_id': self.tracking_key
                }
                for key in ["host", "sourcetype", "source", "index", "sid"]:
                    if key in result:
                        dist_alert[f"orig_{key}"] = result[key]
                self._log.debug(self._preamble({"action": "setup_distinct_alert", **dist_alert}))
                a_id = f'{org_key}:{alert_id}'
                if a_id not in distinct_alert_ids:
                    distinct_alert_ids.append(a_id)
                    process_alerts.append(dist_alert)
            self._log.info(self._preamble(
                {"action": "processing_events_check", "alerts_to_process": len(distinct_alert_ids)}))

            for alert in process_alerts:
                try:
                    cbapi = None
                    try:
                        if alert.get("org_key", None) is not None and self._use_multi_tenant:
                            org_key = alert.get("org_key")
                            cbapi = self.multi_tenant_apis[org_key]["cb"]
                        else:
                            cbapi = self.cb
                    except Exception as ae:
                        self._catch_error(ae, _alert_name)
                    if cbapi is None:
                        alert["alert_action_exception"] = "api_not_found"
                        self.addevent(json.dumps(dict(alert)),
                                      sourcetype=alert_sourcetype)
                        continue
                    # observation_query = cbapi.select(EnrichedEventObservationJson, alert_id=alert.get("alert_id"))
                    # obs_details = observation_query.get_bulk_details()
                    alert_id = alert.get("alert_id")
                    obs_details = EnrichedEventObservationJson.bulk_get_details(cbapi, alert_id=alert_id)
                    if obs_details is None:
                        obs_details = []
                    self._log.debug(self._preamble(
                        {"alert_id": alert_id, "action": "received_details", "details_length": len(obs_details)}))
                    alert["observations"] = []
                    for a_num, detail in enumerate(obs_details):
                        obs = EnrichedEventObservationJson.json(detail)
                        obs["alert_id"] = alert_id
                        obs["observation_seq_num"] = a_num
                        st = time.localtime()
                        tm = time.mktime(st)
                        obs["alert_action_timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(tm))
                        self._log.debug(self._preamble(
                            {"action": "field_updates_before_addevent",
                             "alert_id": alert_id,
                             "observation_seq_num": a_num,
                             "alert_action_timestamp": obs["alert_action_timestamp"]}))
                        self.addevent(json.dumps(obs), sourcetype=alert_sourcetype)
                        # alert["observations"].append(EnrichedEventObservationJson.json(detail))
                except Exception as fe:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    error_msg = " " \
                                "warn_message=\"{}\" " \
                                "warn_type=\"{}\" " \
                                "warn_arguments=\"{}\" " \
                                "warn_filename=\"{}\" " \
                                "warn_line_number=\"{}\" " \
                                "alert_name=\"{}\" " \
                        .format(str(fe), type(fe), "{}".format(fe), fname, exc_tb.tb_lineno, self._action_name)
                    self._log.warn(error_msg)
        except Exception as me:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = " " \
                        "error_message=\"{}\" " \
                        "error_type=\"{}\" " \
                        "error_arguments=\"{}\" " \
                        "error_filename=\"{}\" " \
                        "error_line_number=\"{}\" " \
                        "alert_name=\"{}\" " \
                .format(str(me), type(me), "{}".format(me), fname, exc_tb.tb_lineno, self._action_name)
            self._log.error(error_msg)


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        logger.fatal("FATAL Unsupported execution mode (expected --execute flag)")
        sys.exit(1)
    modaction = None
    try:
        logger.info("instantiating {}".format(_alert_name))
        payload = sys.stdin.read()
        modaction = VmwareEnrichEventsObs(payload, action_name=_alert_name)
        modaction.main()
        sc, evttype = modaction.get_evtidx("vmware_cbc_base_index")
        logger.info("action=found_eventtype class=alert_action_index alert_action_index=\"{}\"".format(evttype))
        modaction.writeevents(index=evttype,
                              fext='vmware_cbc_alert_action_enrich-alert-obs',
                              sourcetype="vmware:alert_action:{}".format(_alert_name),
                              source="vmware:alert_action:{}:{}".format(_alert_name,
                                                                        modaction.payload[
                                                                            "search_name"].replace(" ",
                                                                                                   "_")))
        time.sleep(5)
    except Exception as e:
        try:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = " " \
                        "error_message=\"{}\" " \
                        "error_type=\"{}\" " \
                        "error_arguments=\"{}\" " \
                        "error_filename=\"{}\" " \
                        "error_line_number=\"{}\" " \
                        "alert_name=\"{}\" " \
                .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, _alert_name)
            logger.error(error_msg)
        except Exception as e:
            logger.critical(e)
        sys.exit(3)
