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

_alert_name = "googleworkspace-pubsub"
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
            self.setup_gw("pubsub")
            with self._load_results("rt") as fh:
                self._log.debug("file_handler={}".format(fh))
                p = mp.Pool(10)

                def us(r, k):
                    r["orig_{}".format(k)] = r.get(k, "")
                    if k in r:
                        del r[k]

                futures = dict()

                def get_callback(fss, data):
                    def callback(fss):
                        try:
                            fss.result()
                            futures.pop(data)
                        except Exception as e:  # noqa
                            self._catch_error(e)

                    return callback

                def do_threaded_result(num, result):
                    try:
                        self._log.info("processing result number result={}".format(num))
                        result.setdefault('rid', str(num))
                        delete_result_keys = [key for key in result if re.match(r"_[a-z_]+", key)]
                        for key in delete_result_keys:
                            del result[key]
                        data = None
                        try:
                            data = json.dumps(result)
                        except:
                            self._log.info("action=pubsub failure to convert to json string data={}".format(result))
                            data = "{}".format(result)
                        futures.update({data: None})
                        # When you publish a message, the client returns a future.
                        future = self.client.publish(self.path, data.encode("utf-8"))
                        futures[data] = future
                        # Publish failures shall be handled in the callback function.
                        future.add_done_callback(get_callback(future, data))
                        #  Update results for orig_ keys
                        [us(result, key) for key in ["sourcetype", "source", "host", "index"]]
                        self.addevent(json.dumps(result),
                                      sourcetype="googleworkspace:alert_action:{}".format(_alert_name))
                    except Exception as lre:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        self._log.error(
                            "function=main action=fatal_error exception_line={} exception_file={}  message={}".format(
                                exc_tb.tb_lineno,
                                fname, lre))

                matrix = [(num, result) for num, result in enumerate(csv.DictReader(fh))]
                self.client = self.pubsub.PublisherClient(credentials=self.non_delegated_credential)
                self.path = self.client.topic_path(self.get_config("project_id"), self.get_config("topic_id"))

                self._log.info("action=pubsub_publish setup_client path={}".format(self.path))
                # Wrap subscriber in a 'with' block to automatically call close() when done.
                p.starmap(do_threaded_result, matrix)
                p.close()
                p.join()
                import time
                while futures:
                    time.sleep(5)

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
