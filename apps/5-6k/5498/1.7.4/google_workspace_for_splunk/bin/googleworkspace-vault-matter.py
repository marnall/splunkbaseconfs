# Alert action - PubSub
#
import sys
import os
import json
import logging
import csv
import re
from Utilities import KennyLoggins
from google_constants import app_name as _APP_NAME
from google_alert_action import GWAlertAction
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import multiprocessing.dummy as mp

from datetime import datetime

_alert_name = "googleworkspace-vault-matter"
sys.path.insert(0, make_splunkhome_path(["etc", "apps", _APP_NAME, "lib"]))

kl = KennyLoggins()
logger = kl.get_logger(app_name=_APP_NAME, file_name=_alert_name, log_level=logging.INFO)


class GWAlert(GWAlertAction):
    def __init__(self, settings, action_name):
        try:
            GWAlertAction.__init__(self, settings=settings, action_name=_alert_name,
                                   filename=_alert_name,
                                   stanza="global_{}_configuration".format(_alert_name))
            self.client = None
            self.path = None
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
            self.setup_vault()
            action = self._configuration.get("action", "none").lower()
            if action == "none":
                raise NotImplementedError("Action not implemented")
            # result.get(self._configuration.get("hash_field", None), None)
            with self._load_results("rt") as fh:
                self._log.debug("file_handler={}".format(fh))
                p = mp.Pool(10)

                def us(r, k):
                    r["orig_{}".format(k)] = r.get(k, "")
                    if k in r:
                        del r[k]

                def do_threaded_result(num, result, act):
                    try:
                        self._log.info("processing result number result={}".format(num))
                        result.setdefault('rid', str(num))
                        delete_result_keys = [key for key in result if re.match(r"_[a-z_]+", key)]
                        for key in delete_result_keys:
                            del result[key]
                        [us(result, key) for key in ["sourcetype", "source", "host", "index"]]
                        # DO THE ALERT ACTION HERE
                        local_action = act
                        if act == "inline":
                            local_action = result.get("action", "none")
                        if local_action not in ["create", "close", "reopen", "delete", "undelete", "get"]:
                            result["failure_message"] = "Not Implemented: {}".format(local_action)
                        else:
                            matter_id = result.get(self._configuration.get("matter_id_field"), "NAN")
                            if local_action == "create":
                                result["action_result"] = self.create_matter(result.get("name", "Unknown"),
                                                                             result.get("description", "Unknown"))
                            elif local_action == "close":
                                result["action_result"] = self.close_matter(matter_id)
                            elif local_action == "reopen":
                                result["action_result"] = self.reopen_matter(matter_id)
                            elif local_action == "delete":
                                result["action_result"] = self.delete_matter(matter_id)
                            elif local_action == "undelete":
                                result["action_result"] = self.undelete_matter(matter_id)
                            elif local_action == "get":
                                result["action_result"] = self.get_matter(matter_id)
                        self.addevent(json.dumps(result),
                                      sourcetype="googleworkspace:alert_action:{}".format(_alert_name))
                    except Exception as lre:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        self._log.error(
                            "function=main action=fatal_error exception_line={} exception_file={}  message={}".format(
                                exc_tb.tb_lineno,
                                fname, lre))

                matrix = [(num, result, action) for num, result in enumerate(csv.DictReader(fh))]
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
    try:
        logger.info("instantiating {}".format(_alert_name))
        modaction = GWAlert(sys.stdin.read(), action_name=_alert_name)
        modaction.main()
        sc, evttype = modaction.get_evtidx("google_workspace")
        logger.info("action=found_eventtype class=alert_action_index alert_action_index=\"{}\"".format(evttype))
        modaction.writeevents(index=evttype,
                              fext='googleworkspace_alert_action_st',
                              sourcetype="googleworkspace:alert_action:{}".format(_alert_name),
                              source="googleworkspace:alert_action:{}:{}".format(_alert_name,
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
