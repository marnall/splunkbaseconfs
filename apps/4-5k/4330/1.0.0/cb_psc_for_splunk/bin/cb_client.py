import urllib
import json
import sys
import os
import math
import time
from random import shuffle
from datetime import datetime, date
from RESTClient import RESTClient
from Utilities import Utilities, KennyLoggins
import logging
import version

class cb_client(RESTClient):

    base_st = "carbonblack:psc"
    endpoints = {
        "notifications": {"url": "integrationServices/v3/notification", "sourcetype": "{}:notification".format(base_st)},
        "api": {"sourcetype": "{}:api".format(base_st)}
    }
    def __init__(self, app_name, configuration, modular_input):
        try:
            RESTClient.__init__(self, app_name=app_name, configuration=configuration)
            self.modular_input = modular_input
            self.utilities = Utilities(app_name=app_name, session_key=self.modular_input.get_config("session_key"))
            self.auth_header = {"X-Auth-Token": "{}".format(self._token)}
            self.user_agent_header = {"User-Agent": self._user_agent}
            self._session.headers.update(self.auth_header)
            self._session.headers.update(self.user_agent_header)
        except Exception as e:
            end_mod_input = self.current_milli_time()
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            jsondump = {"message": str((e)),
                        "exception_type": "%s" % type(e).__name__,
                        "filename": fname,
                        "exception_line": exc_tb.tb_lineno
                        }
            self._log.error("action=endpoint_error {} {}".format(e, self._build_string(jsondump)))

    def current_milli_time(self):
        return float(time.time())

    def _build_url(self, endpoint):
        self._log.debug("action=build_url endpoint={}".format(endpoint))
        return "https://{}/{}".format(self._hostname, self.endpoints.get(endpoint, {}).get("url"))

    def _build_string(self, o):
        return ' '.join(" {}=\"{}\" ".format(key, val) for (key, val) in o.iteritems())

    def error(self, s, e):
        self._log.error("action=log_error timer={} {}".format(self.current_milli_time(), s))
        if e is not None:
            raise e

    def _call(self, endpoint="", payload=None):
        try:
            fullUrl = "{}".format(self._build_url(endpoint))
            if payload is not None:
                fullUrl = "{}?{}".format(fullUrl, self._payload(**payload))
            self._log.debug("logic=rest full_url={}".format(fullUrl))
            return self._read(fullUrl, payload=None)
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            jsondump = {"message": str(e),
                        "exception_type": "{}".format(type(e).__name__),
                        "filename": fname,
                        "exception_line": exc_tb.tb_lineno
                        }
            self.mi_error(jsondump)
            self._log.error("action=endpoint_error {} {}".format(str(e), self._build_string(jsondump)))
            return {}

    def mi_error(self, j):
        oldst = self.modular_input.sourcetype()
        self.modular_input.sourcetype("{}:error".format(self._app_name))
        self.modular_input.print_event(json.dumps(j))
        self.modular_input.sourcetype(oldst)

    def get_notifications(self):
        try:
            self._log.info("action=start")
            results = self._call(endpoint="notifications")
            self._log.info("action=return_result length={}".format(len(results)))
            # Only uncomment if you dislike your disk space: self._log.debug("action=return_results results={}".format(results))
            self.modular_input.sourcetype(self.endpoints.get("notifications").get("sourcetype"))
            total_events = 0
            self._log.debug("action=set_sourcetype sourcetype={}".format(self.modular_input.sourcetype()))
            if "notifications" in results:
                total_events = len(results["notifications"])
                self.modular_input.print_multiple_events([x for x in results["notifications"]])
                results["notifications"] = "indexed"
            self.modular_input.sourcetype(self.endpoints.get("api").get("sourcetype"))
            self._log.debug("action=set_sourcetype sourcetype={}".format(self.modular_input.sourcetype()))
            self.modular_input.print_event(json.dumps({"total_events": total_events,
                                                       "response": results,
                                                       "endpoint": self.endpoints.get("notifications").get("url")}))
            return True
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            jsondump = {"message": str(e),
                        "exception_type": "%s" % type(e).__name__,
                        "exception_arguments": "%s" % e,
                        "filename": fname,
                        "exception_line_number": exc_tb.tb_lineno
                        }
            self.mi_error(jsondump)
            self._log.error("action=get_notifications_error {} {}".format(e, self._build_string(jsondump)))
            return False