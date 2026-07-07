# Copyright (C) 2022-2023 Sideview LLC.  All Rights Reserved.

import logging
import os
import sys

import splunk

try:
    #python2
    from urllib import urlencode
except ImportError:
    #python3
    from urllib.parse import urlencode

APP = "sideview_ui"
SPLUNK_HOME = os.environ["SPLUNK_HOME"]


LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, "etc", "log.cfg")
LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, "etc", "log-local.cfg")
LOGGING_STANZA_NAME = "python"
LOGGING_FILE_NAME = APP + ".log"
BASE_LOG_PATH = os.path.join("var", "log", "splunk")
LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
def setup_logging(log_level):
    """ we use our own canary.log file, although regrettably this is still
    left to be handled by the _internal data input"""
    if not SPLUNK_HOME:
        logger = logging.getLogger(APP)
        logger.setLevel(log_level)
        return logger
    LOG_FILE_PATH = os.path.join(SPLUNK_HOME, "var", "log", "splunk", APP + ".log")
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"

    our_logger = logging.getLogger(APP)
    if not our_logger.handlers:

        our_logger.propagate = False
        our_logger.setLevel(log_level)
        handler = logging.handlers.RotatingFileHandler(LOG_FILE_PATH, mode="a")
        handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
        our_logger.addHandler(handler)
    return our_logger

logger = setup_logging(logging.DEBUG)



def get_query_args(params, key="query"):
    """ just processing the inscrutable struct into more useful args"""
    out = {}
    if key not in params:
        return out
    query_array = params[key]
    for pair in query_array:
        out[pair[0]] = pair[1]
    return out


def get_path_segments(params):
    if "path_info" not in params:
        logger.error("no path_info found in json")
        return None, None, None
    path_tuple = params["path_info"].split('/')
    app = None
    view = None
    action = None
    if len(path_tuple) > 0:
        app = path_tuple[0]
    if len(path_tuple) > 1:
        view = path_tuple[1]
    if len(path_tuple) > 2:
        action = path_tuple[2]
    if not path_tuple or len(path_tuple) > 3:
        raise AssertionError("this path makes no sense %s" % params["path_info"])

    return app, view, action


class Request(object):
    def __init__(self, params=None, test_mode=False):
        if not params and test_mode:
            return

        self.app, self.view, self.action = get_path_segments(params)
        self.lang = params.get("lang", "en-US")

        protocol = "http"
        if params.get("connection").get("ssl", True):
            protocol = "https"
        self.protocol = protocol

        session_dict = params.get("session")
        self.session_key = session_dict.get("authtoken")
        self.user_name = session_dict.get("user")
        self.headers = {}
        for header in params["headers"]:
            self.headers[header[0]] = header[1]

        #self.csrf_token = get_csrf_token_from_cookie(self.headers)

        self.locale = params.get("lang", "en-US")
        if self.locale.find("/") != -1:
            logger.error("locale has a slash in it. locale=%s", self.locale)
            self.locale = self.locale.replace("/", "")

        self.method = params.get("method")

        self.qs_dict = get_query_args(params)
        self.post_dict = get_query_args(params, "form")

        # just a trick to let us restart the persistent process during development
        if self.method == "GET" and "kill" in self.qs_dict:
            logger.warning("killing this scripttype=persist process.")
            sys.exit()

    def __str__(self):
        try:
            args = (self.app, self.view, self.user_name, self.locale, self.method)
            out = []
            out.append("app=%s view=%s user_name=%s locale=%s method=%s" % args)
            for header in self.headers:
                out.append("%s header = %s" %(header, self.headers[header]))
            return "\n".join(out)
        except Exception as e:
            return "unexpected exception casting to string - %s" % e

    def get_redirect_location(self, view_type):
        """
        TODO - yep.  we still need a canary_compatible=<boolean> somewhere.  If we extend app.conf
        there still seems to be no way to actually get that key out via REST.
        :facepalm:.  but maybe fresh coffee will find a way."""
        sideview_apps = ["canary", "cisco_cdr", "SA_cisco_cdr_axl", "shoretel", "covid19_sideview"]
        supported_view_types = ["Advanced XML", "Sideview XML", "Canary yaml"]
        qs_dict = self.qs_dict.copy()

        if self.app in sideview_apps and view_type in supported_view_types:
            uri_template = "%s://%s/%s/splunkd/__raw/sv_view/%s/%s"
        else:
            uri_template = "%s://%s/%s/app/%s/%s"
            if "search.name" in qs_dict:
                if self.view in ["search", "report"]:
                    # the arg doesn't stand for argument.  it stands for AAAAARGGGGGGG WHOSE STUPID
                    # IDEA WAS IT TO REQUIRE THE ENTIRE EAI URL BUT JUST FOR THE REPORT PAGE. Ahem.
                    saved_search_arg = qs_dict["search.name"]
                    if self.view == "report":
                        saved_search_arg = "/servicesNS/%s/%s/saved/searches/%s" % (self.user_name, self.app, saved_search_arg)
                    qs_dict["s"] = saved_search_arg
                    del qs_dict["search.name"]



        request_host = self.headers.get("Host", "localhost")
        url = uri_template  % (self.protocol, request_host, self.lang, self.app, self.view)
        if not qs_dict:
            return url
        return "%s?%s" % (url, urlencode(qs_dict))
