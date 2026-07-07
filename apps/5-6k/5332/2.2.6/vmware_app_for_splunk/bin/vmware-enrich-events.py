# - Enrich CB Analytics Events
#     - `Documentation <https://developer.carbonblack.com/reference/carbon-black-cloud/platform/latest/platform-search-api-enriched-events/#start-an-enriched-events-search-v2>`_
#     - Very specific configuration required for proper operation.
#     - Credential Type: Custom
#     - Global Configuration
#         - None
#     - Search Configuration
#         - API Config: Supports single instance and multi-tenancy
#             - To use Authenticated Support, the ``org_key`` field *MUST* be included in the results
#         - Required fields: ``sourcetype``, ``host``, ``org_key``, ``alert_id``, ``source``
#         - ``alert_id`` *MUST* be a ``;:;:`` separated string, with de-dupped Alert IDs for query to the endpoint via alert action.
import sys
import os
import json
import logging
import csv
import uuid
from VMWUtilities import KennyLoggins, Utilities
from vmware_cbc_alert_actions import VmwareCBCAlertAction
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import multiprocessing.dummy as mp
from pathlib import Path
import vmware_paths
from cbc_sdk.endpoint_standard import EnrichedEvent

_alert_name = Path(__file__).stem
__app_name__ = vmware_paths.__app_name__
kl = KennyLoggins()
logger = kl.get_logger(app_name=__app_name__, file_name=_alert_name, log_level=logging.INFO)


class EnrichedEventJson(EnrichedEvent):
    def __init__(self, cb, model_unique_id=None, initial_data=None, force_init=False, full_doc=True):
        """
        Initialize the EnrichedEventJSON object.

        Args:
            cb (CBCloudAPI): A reference to the CBCloudAPI object.
            model_unique_id (Any): The unique ID for this particular instance of the model object.
            initial_data (dict): The data to use when initializing the model object.
            force_init (bool): True to force object initialization.
            full_doc (bool): True to mark the object as fully initialized.
        """
        self._details_timeout = 0
        self._info = None
        super(EnrichedEventJson, self).__init__(cb, model_unique_id=model_unique_id, initial_data=initial_data,
                                            force_init=force_init, full_doc=full_doc)

    def json(self):
        return self._info

class VmwareEnrichEvents(VmwareCBCAlertAction):
    def __init__(self, settings, action_name):
        try:
            VmwareCBCAlertAction.__init__(self, settings=settings, action_name=_alert_name,
                                          filename=_alert_name,
                                          stanza="global_{}_configuration".format(_alert_name))
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

    def main(self):
        try:
            self._log.debug("action=start")
            with self._load_results("rt") as fh:
                self._log.debug("file_handler={}".format(fh))
                p = mp.Pool(10)
                tracking_key = "{}".format(uuid.uuid4())
                def do_threaded_result(num, result):
                    try:
                        self._log.debug("processing result number result={}".format(num))
                        result.setdefault('rid', str(num))
                        for key in ["host", "sourcetype", "source", "index", "sid"]:
                            if key in result:
                                result["orig_{}".format(key)] = result[key]
                                del result[key]
                        delete_result_keys = [key for key in result if '_mv' in key]
                        for key in delete_result_keys:
                            del result[key]
                        self._log.debug("getting alert id field result={}".format(num))
                        alert_id = result.get(self._configuration.get("alert_id_field", None), None)
                        self._log.debug("checking fields result={} alert_id={}".format(num, alert_id))
                        if alert_id is None:
                            msg = "action=cannot_complete_action alert_id={} alert_id_field={} ".format(
                                alert_id, self._configuration.get("alert_id_field", None))
                            self._log.warn(msg)
                            self._log.debug("{}".format(json.dumps(self._configuration)))
                            self.addevent(msg, "vmware:alert_action:{}:error".format(_alert_name))
                            return
                        api = None
                        try:
                            self._log.debug("action=starting_enrich_events_call")
                            if result.get("org_key", None) is not None and self._use_multi_tenant:
                                org_key = result.get("org_key")
                                self._log.debug("action=multi_tenant_api_usage org_key={}".format(org_key))
                                api = self.multi_tenant_apis[org_key]["cb"]
                            else:
                                api = self.cb
                            if api is None:
                                result["alert_action_exception"] = "api_not_found"
                                result["tracking_key"] = tracking_key
                                self.addevent(json.dumps(dict(result)),
                                              sourcetype="vmware:alert_action:{}".format(_alert_name))
                                return
                            passed_alerts = alert_id.split(";:;:")
                            self._log.debug("tracking_key={} alerts={}".format(tracking_key, passed_alerts))
                            alerts = " OR ".join(["alert_id:{}".format(x) for x in passed_alerts])
                            # legacy_alerts = " OR ".join(["legacy_alert_id:{}".format(x) for x in passed_alerts])
                            #total_alert_filter = "{} OR {}".format(alerts, legacy_alerts)
                            total_alert_filter = "{}".format(alerts)
                            self._log.debug("tracking_key={} alerts_filter=\"{}\"".format(tracking_key, total_alert_filter))
                            # results = list(api.select(EnrichedEventJson).where(total_alert_filter))
                            enriched_events_query = api.select(EnrichedEventJson).where(total_alert_filter)
                            enriched_events_query._default_args['fields'] = ["*", "process_cmdline"]
                            results = list(enriched_events_query)

                            def proc_evt(evt, idx):
                                self._log.debug("tracking_key={} result_index={}".format(tracking_key, idx))
                                ev = evt.json()
                                ev["tracking_key"] = tracking_key
                                return json.dumps(ev)
                            [self.addevent(proc_evt(r, i),
                                           sourcetype="vmware:cbc:events:detail") for (i, r) in enumerate(results)]
                            if len(results) > 0:
                                self._log.debug("tracking_key={} total_results={} type={}".format(tracking_key, len(results), type(results[0].json())))
                            else:
                                self._log.debug("tracking_key={} total_results={}".format(tracking_key, len(results)))
                        except Exception as te:
                            exc_type, exc_obj, exc_tb = sys.exc_info()
                            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                            self._log.error(
                                "function=main action=fatal_error exception_line={} exception_file={}  message={}".format(
                                    exc_tb.tb_lineno,
                                    fname, te))
                    except Exception as lre:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        self._log.error(
                            "function=main action=fatal_error exception_line={} exception_file={}  message={}".format(
                                exc_tb.tb_lineno,
                                fname, lre))

                matrix = [(num, result) for num, result in enumerate(csv.DictReader(fh))]
                p.starmap(do_threaded_result, matrix)
                p.close()
                p.join()

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
        modaction = VmwareEnrichEvents(sys.stdin.read(), action_name=_alert_name)
        modaction.main()
        sc, evttype = modaction.get_evtidx("vmware_cbc_base_index")
        logger.info("action=found_eventtype class=alert_action_index alert_action_index=\"{}\"".format(evttype))
        modaction.writeevents(index=evttype,
                              fext='vmware_cbc_alert_action_st',
                              sourcetype="vmware:alert_action:{}".format(_alert_name),
                              source="vmware:alert_action:{}:{}".format(_alert_name,
                                                                        modaction.payload[
                                                                            "search_name"].replace(" ",
                                                                                                   "_")))
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
