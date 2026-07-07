# Copyright (C) 2022-2026 Sideview LLC.  All Rights Reserved.
"""
Provides a small request object that provides a more natural interface to the weird
and toxic giant-json-arg that Splunk put in restmap.conf endpoints.
Hand that giant json struct to the Request constructor and let it sort things out.
"""
import logging
import os
import sys
import canary_util.splunk_https_session

from urllib.parse import urlencode

APP = "canary"
SPLUNK_HOME = os.environ.get("SPLUNK_HOME")

if SPLUNK_HOME:
    import splunk
else:
    import flask




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


def get_path_segments(app_path):
    path_tuple = app_path.split('/')
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
        raise AssertionError("this path makes no sense %s" % app_path)

    return app, view, action


class BaseRequest(object):
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


    def get_cookie_value(self, cookie_name):
        #this string looks like  "foo=bar; baz=bat; token=12314312;"
        cookie_str = self.headers.get("Cookie", "")
        for cookie in cookie_str.split(" "):
            if cookie.startswith(cookie_name + "="):
                return cookie.rstrip(";").split("=")[1]
        return ""

    def get_redirect_location(self, view_type, root_endpoint=""):
        """
        always called when we've already decided to redirect.
        And only called in two cases
        1) uri ended at the app segment and upstream code has already
        determined a good landing page and set it in self.view   (o_o)
        2) or "view" is actually a core splunk page and we have to artfully send the user over to
        the splunk-convention uri now.
        """

        # much like in the shunt_endpoint of an app that uses Canary views,
        # we have to worry tha sometimes root_endpoint is "", and sometimes it
        # is "/".
        if root_endpoint == "/":
            root_endpoint = ""

        supported_view_types = ["Advanced XML", "Sideview XML", "Canary yaml"]
        qs_dict = self.qs_dict.copy()

        if view_type in supported_view_types:
            uri_template = "%s://%s%s/%s/splunkd/__raw/sv_view/%s/%s"
        else:
            uri_template = "%s://%s%s/%s/app/%s/%s"
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
        url = uri_template  % (self.protocol, request_host, root_endpoint, self.lang, self.app, self.view)
        if not qs_dict:
            return url
        return "%s?%s" % (url, urlencode(qs_dict))

    def build_splunkd_mgmt_url(self, url):
        """ Accepts a url such as /services/....
            returns a url such as https://localhost:8089:/services/...

            rest_uri -> 'https://127.0.0.1:8089'
            rest_handler_params -> { ..., 'server': { 'rest_uri' : 'https://127.0.0.1:8089', ... }, ...}
            The latter is the format of the junk that SplunkPersistentRestHandlers are fed
      """
        if url.startswith('http'):
            return url
        if not url.startswith('/'):
            url = '/' + url
        return self._mgmt_url() + url

    def get_session(self, appname=None):
        raise NotImplementedError


class SplunkRequest(BaseRequest):
    def __init__(self, params=None, test_mode=False):
        if not params and test_mode:
            return

        if "path_info" not in params:
            #logger.info("no path_info found in json")
            self.app, self.view, self.action = None, None, None
        else:
            self.app, self.view, self.action = get_path_segments(params['path_info'])
        self.lang = params.get("lang", "en-US")

        protocol = "http"
        if params.get("connection",{}).get("ssl", True):
            protocol = "https"
        self.protocol = protocol

        session_dict = params.get("session", False)
        if session_dict:
            self.session_key = session_dict.get("authtoken")
            self.user_name = session_dict.get("user")

        self.headers = {}
        for header in params.get("headers",[]):
            self.headers[header[0]] = header[1]

        #self.csrf_token = get_csrf_token_from_cookie(self.headers)

        self.locale = params.get("lang", "en-US")
        self.method = params.get("method")

        server_info = params.get('server', {})
        self.rest_uri = server_info.get('rest_uri')

        self.qs_dict = get_query_args(params)
        self.post_dict = get_query_args(params, "form")

        ui_theme = self.get_cookie_value("sideview_ui_theme") or self.qs_dict.get("sideview_ui_theme","light")
        if ui_theme in ["light", "dark", "default_system_theme"]:
            self.ui_theme = ui_theme
        else:
            self.ui_theme = "light"
            logger.error("invalid value for UI Theme - " + ui_theme)



        # just a trick to let us restart the persistent process during development
        if self.method == "GET" and "kill" in self.qs_dict:
            logger.warning("killing this scripttype=persist process.")
            sys.exit()



    def _mgmt_url(self):
        return self.rest_uri

    # on the splunk side we killed this for now.  Previous implementation was mostly around
    # cert verification which we no longer need to worry about ( here it's always to localhost:8089)
    #def get_session(self, appname=None):
    #    return canary_util.splunk_https_session.get_splunkd_https_session(self._mgmt_url(), appname or self.app)


class FlaskProxiedRequest(BaseRequest):
    def __init__(self, viewpath, test_mode=False, flask=None):
        if test_mode:
            return

        self.flask = flask

        self.app, self.view, self.action = get_path_segments(viewpath)
        self.lang = flask.request.environ.get("splunk.lang", "en-US")

        self.protocol = flask.request.scheme

        session_dict = flask.request.environ.get("splunk.session")
        if session_dict:
            self.session_key = session_dict.get("authtoken")
            self.user_name = session_dict.get("user")
        else:
            self.session_key = flask.session['sessionKey']
            self.user_name = flask.session['username']
        self.headers = flask.request.headers

        #self.csrf_token = get_csrf_token_from_cookie(self.headers)

        # why is self.locale duplicated from self.lang?
        self.locale = self.lang
        self.method = flask.request.method

        self.qs_dict =  flask.request.args
        self.post_dict = flask.request.form

        # just a trick to let us restart the persistent process during development
        if self.method == "GET" and "kill" in self.qs_dict:
            logger.warning("killing this scripttype=persist process.")
            sys.exit()

    def _mgmt_url(self):
        return self.flask.current_app.config['SPLUNKD_MGMTURL']

    def get_session(self):
        return canary_util.splunk_https_session.get_splunkd_https_session(self._mgmt_url())

if SPLUNK_HOME:
    Request = SplunkRequest
else:
    Request = FlaskProxiedRequest
