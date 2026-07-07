# - Process GUID Details
#     - `Documentation <https://developer.carbonblack.com/reference/carbon-black-cloud/platform/latest/platform-search-api-processes/#calls-for-events>`_
#     - Credential Type: Custom
#     - Global Configuration
#         - API Config: Supports multi-tenancy.
#             - To use multi-tenancy, include the ``org_key`` field with the corresponding value.
#         - Select the API Configs to use with this alert action.
#         - Only 1 API Config per Organization Key should be configured for each alert action.
#     - Search Configuration
#         - GUID Field: the field name that contains process GUID of the object in question.
import sys
import os
import json
import logging
import csv
import time
from VMWUtilities import KennyLoggins
from vmware_cbc_alert_actions import VmwareCBCAlertAction
from datetime import datetime
import multiprocessing.dummy as mp
from pathlib import Path
from vmware_paths import __app_name__

_alert_name = Path(__file__).stem
MAX_THREADS = 1
kl = KennyLoggins()
logger = kl.get_logger(app_name=__app_name__, file_name=_alert_name, log_level=logging.INFO)


class VmwareProcessGUIDDetails(VmwareCBCAlertAction):
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

    def get_single_process_guid(self, org_key, process_guid, cb):
        try:
            process_request_time = datetime.utcnow().isoformat()
            urlobject = "/api/investigate/v2/orgs/{}/processes/detail_jobs".format(org_key)
            urlbody = {"process_guids": [process_guid], "limited": True}
            self._log.info("action=submit process request, org_key: {}, process_guid: {}".format(org_key, process_guid))
            # self._log.debug("action=set url_body: {}, url: {}, type url body: {}".format(json.dumps(urlbody), urlobject, type(urlbody)))

            process_job_response = cb.post_object(urlobject, json.loads(json.dumps(urlbody)))
            process_job_data = process_job_response.json()
            self._log.debug(
                "process_job_data: {}, type process_job_data: {}".format(process_job_data,
                                                                         type(process_job_data)))

            self._log.info(
                "action=submitted process request, org_key: {}, process_guid: {}, job id returned: {}".format(
                    org_key, process_guid, process_job_data["job_id"]))

            self._log.info(
                "action=get status of process detail search, org_key: {}, process_guid: {}, job id: {}".format(
                    org_key, process_guid, process_job_data["job_id"]))

            contacted_count = 0
            completed_count = -1

            urlobject_status = "/api/investigate/v2/orgs/{}/processes/detail_jobs/{}".format(
                org_key, process_job_data["job_id"])

            submitted_job = datetime.now()
            self._log.debug("action=started get job status at: {}".format(submitted_job))

            process_job_status = cb.get_object(urlobject_status)
            base_sleep = 2
            time.sleep(base_sleep)

            while contacted_count != completed_count:
                current_job_time = datetime.now()
                job_time_diff = current_job_time - submitted_job
                job_time_diff_minutes = job_time_diff.total_seconds() / 60
                self._log.debug("action=sleeping before querying for status, time waited={}".format(job_time_diff_minutes))
                if job_time_diff_minutes >= 3:
                    # Time out after 3 minutes but download the results that have been processed in the 3 minutes
                    self._log.warning("action=Time out search after more than 3 minutes, job id={}, contacted count={}, completed count={}".format(process_job_data["job_id"], process_job_status["contacted"], process_job_status["completed"]))
                    break
                else:
                    process_job_status = cb.get_object(urlobject_status)
                    contacted_count = process_job_status["contacted"]
                    completed_count = process_job_status["completed"]
                base_sleep = base_sleep * 2
                time.sleep(base_sleep)

            result_contacted_count = 0
            result_completed_count = -1

            self._log.info(
                "action=get results of process detail search, process_guid={}, job id={}".format(
                    process_guid, process_job_data["job_id"]))
            urlobject_results = "/api/investigate/v2/orgs/{}/processes/detail_jobs/{}/results".format(
                org_key, process_job_data["job_id"])
            process_job_results = cb.get_object(urlobject_results)

            process_job_results["job_id"] = process_job_data["job_id"]
            process_job_results["requested_process_guid"] = process_guid
            process_job_results["process_query_requested_time"] = process_request_time
            self.addevent(json.dumps(process_job_results),
                          sourcetype="vmware:alert_action:{}".format(_alert_name))
        except Exception as te:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            self._log.error(
                "function=main action=fatal_error exception_line={} exception_file={}  message={}".format(
                    exc_tb.tb_lineno,
                    fname, te))

    def get_process_guids(self, org_key, config_process_guids, cb):
        try:
            p2 = mp.Pool(MAX_THREADS)
            matrix2 = [(org_key, x, cb) for x in config_process_guids]
            self._log.debug("process_guid_matrix: {}".format(matrix2))
            p2.starmap(self.get_single_process_guid, matrix2)
            p2.close()
            p2.join()
        except Exception as te:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            self._log.error(
                "function=main action=fatal_error exception_line={} exception_file={}  message={}".format(
                    exc_tb.tb_lineno,
                    fname, te))

    def main(self):
        try:
            self._log.debug("action=start")
            with self._load_results("rt") as fh:
                self._log.debug("file_handler={}".format(fh))
                p = mp.Pool(10)

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
                        self._log.debug("action=getting query fields from configuration result={}".format(num))
                        config_process_guids = result.get(self._configuration.get("process_guid_field"), None)
                        self._log.debug("action=check configuration variables")

                        if config_process_guids is None:
                            msg = "action=validating configuration values, msg=no process_guid specified, will not continue"
                            self._log.warn(msg)
                            self._log.debug("{}".format(json.dumps(self._configuration)))
                            self.addevent(msg, "vmware:alert_action{}:error".format(_alert_name))
                            return

                        pass_cb = None
                        if result.get("org_key", None) is not None and self._use_multi_tenant:
                            pass_cb = self.multi_tenant_apis[result.get("org_key")]["cb"]
                        else:
                            pass_cb = self.cb
                            result["org_key"] = self.tenant["org_key"]

                        self.get_process_guids(result.get("org_key", None), config_process_guids.split(","), pass_cb)
                        self._log.info("action=done getting process details, process guids: {}".format(config_process_guids))

                    except Exception as lre:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        self._log.error(
                            "function=main action=fatal_error exception_line={} exception_file={}  message={}".format(
                                exc_tb.tb_lineno,
                                fname, lre))

                matrix = [(num, result) for num, result in enumerate(csv.DictReader(fh))]
                self._log.debug("matrix: {}".format(matrix))
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
        modaction = VmwareProcessGUIDDetails(sys.stdin.read(), action_name=_alert_name)
        modaction.main()
        sc, evttype = modaction.get_evtidx("vmware_cbc_action_index")
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