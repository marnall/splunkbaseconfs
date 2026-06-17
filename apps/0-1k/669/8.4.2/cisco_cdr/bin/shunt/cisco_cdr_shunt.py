# Copyright (C) 2010-2025 Sideview LLC.  All Rights Reserved.
"""
 This implements a scripttype=persist endpoint that runs in Splunk, whose
 function is to redirect the user to a working URL to render a given view
 from a Sideview app, depending on whether this is Splunk 8 or an older version
 and depending on whether Canary app is installed or not.
 On Splunk 8 where Canary is not installed, it redirects to a view called
 sorry_canary_not_installed, which would generally be a simplexml view but can
 be whatever you like.

 If your use of this app is through the Sideview Free Internal Use License
 Agreement or through the Sideview Trial Internal Use License Agreement,
 or through the Sideview Term Internal Use License Agreement or through the
 Sideview Perpetual Internal Use License Agreement, then as per the relevant
 agreement any modification of this file or modified copies made of this
 file constitutes a violation of that agreement.

 Thus if you want to create an app with Canary views, you need to make one of
 these which... the legal stuff above just said you couldn't do so CONTACT US.
 We just haven't gotten around to this part yet.  Contact us though.
"""

import os
import sys
import json
import traceback
import logging
import urllib

import splunk
import splunk.entity as en

if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

from splunk.persistconn.application import PersistentServerConnectionApplication
import splunk.rest as rest

APP = "cisco_cdr"
SPLUNK_HOME = os.environ["SPLUNK_HOME"]

sys.path.insert(1, os.path.join(os.environ['SPLUNK_HOME'], "etc", "apps", APP, "bin"))
from cisco_cdr_request import Request


def setup_logging(log_level):
    """ the app uses its own log file. """
    log_file_path = os.path.join(SPLUNK_HOME, "var", "log", "splunk", APP + ".log")
    logging_format = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"

    our_logger = logging.getLogger(APP)
    our_logger.propagate = False
    if not our_logger.handlers:
        our_logger.setLevel(log_level)
        handler = logging.handlers.RotatingFileHandler(log_file_path, mode="a")
        handler.setFormatter(logging.Formatter(logging_format))
        our_logger.addHandler(handler)
    return our_logger


logger = setup_logging(logging.INFO)

"""
things borrowed from sideview_canary.py
cause we're not ready to just import from canary
"""

def memoize_non_empty_values(func):
    """these two memoize decorators are a little silly and strangely simple
    and each only used by ONE FUNCTION.   but.. they work."""
    cache = dict()

    def memoized_func(*args):
        if args in cache:
            return cache[args]
        result = func(*args)
        if result:
            cache[args] = result
        return result

    return memoized_func

def get_rest_api_response(uri, session_key):
    """ simple wrapper around simpleRequest to return just the json response """
    getargs = {"output_mode":"json"}
    _response, content = rest.simpleRequest(uri, sessionKey=session_key, method="GET",
                                            raiseAllErrors=True, getargs=getargs)
    return json.loads(content)

def get_single_rest_api_entry(uri, session_key):
    """ simplified way to just get the contents of the first stanza, parsed as json.
        95% of the time this is all we want."""

    content = get_rest_api_response(uri, session_key)
    return content["entry"][0]["content"]

@memoize_non_empty_values
def get_splunk_server_config(session_key):
    """ returns splunk version, build number, httpport and root_endpoint in a simple dict"""
    server_uri = "/server/info/server-info"
    server_entry = get_single_rest_api_entry(server_uri, session_key)

    web_conf_uri = "/services/configs/conf-web/settings"
    web_conf_entry = get_single_rest_api_entry(web_conf_uri, session_key)

    return {
        "SPLUNK_VERSION": server_entry.get("version", "0"),
        "SPLUNK_BUILD_NUMBER": server_entry.get("build", "0"),
        # these ones... really do have to exist. If somehow they're not there
        # then throwing KeyError is perfectly fine.
        "SPLUNKWEB_PORT_NUMBER": web_conf_entry.get("httpport"),
        "ROOT_ENDPOINT": web_conf_entry.get("root_endpoint")
    }

def get_query_args(params):
    """even more parsing of the inscrutable json-formatted string
    that was passed as the sole arg to handle.  Because reasons."""
    out = {}
    if "query" not in params:
        return out
    query_arr = params["query"]
    for pair in query_arr:
        out[pair[0]] = pair[1]
    return out

def is_canary_installed(session_key):

    uri = "/services/apps/local/%s" % "canary"

    getargs = {"output_mode":"json"}
    try:
        _response, _content = rest.simpleRequest(uri, sessionKey=session_key, method="GET",
                                                 raiseAllErrors=True, getargs=getargs)
    except splunk.ResourceNotFound as e:
        return False
    return True

def get_splunk_major_version(config):
    splunk_version = config.get("SPLUNK_VERSION")
    numbers = splunk_version.split(".")
    return int(numbers[0])



def get_view_location(request, root_endpoint, splunk_major_version, canary_is_installed):
    host = request.headers.get("Host")

    base_url = "%s://%s%s/%s" % (request.protocol, host, root_endpoint, request.locale)

    if splunk_major_version < 8:
        return "%s/app/%s/home_redirect" % (base_url, APP)
    if canary_is_installed:
        view = request.qs_dict.get("view", False)
        #pass on any other qs args verbatim.
        temp_dict = dict(request.qs_dict)
        del temp_dict["view"]
        qs = ""
        if temp_dict:
            qs = "?" + urllib.parse.urlencode(temp_dict)
    else:
        return "%s/app/%s/sorry_canary_not_installed" % (base_url, APP)
    return "%s/splunkd/__raw/sv_view/%s/%s%s" % (base_url, APP, view, qs)

def handle_get(request, config):
    """ time to serve the donuts """

    output_mode = "xml"

    # just a trick to let us restart the persistent process in between
    # code changes (during development).
    if "kill" in request.qs_dict:
        logger.warning("explicitly killing the scripttype=persist process.")
        sys.exit()

    try:
        view = request.qs_dict.get("view", False)
        root_endpoint = config.get("ROOT_ENDPOINT", "")


        # this is the easiest way to avoid sending people to URLs with double slashes.
        if root_endpoint == "/":
            root_endpoint = ""

        if not view:
            msg = "Bad Request - no view was provided in the querystring"
            return build_response(400, msg, output_mode)

        splunk_major_version = get_splunk_major_version(config)
        canary_is_installed = is_canary_installed(request.session_key)

        location = get_view_location(request, root_endpoint, splunk_major_version, canary_is_installed)

        return build_response(301, "Resource moved to %s" % location, output_mode, location)

    except Exception:
        logger.error(traceback.format_exc())
        return build_response(500, traceback.format_exc(), output_mode)


def build_response(status, payload=None, content_type=None, location=None):
    """ core  method to return things to the client. """
    response_dict = {}
    response_dict["status"] = status

    if payload:
        response_dict["payload"] = payload

    # pro-tip - setting a "Content-Length" header works fine on mgmt port and blows up on the
    # web port proxy somehow.
    headers = {}
    if content_type:
        headers["Content-Type"] = content_type

    if location:
        headers["Location"] = location

    if headers:
        response_dict["headers"] = headers
    return response_dict




class CiscoCdrShuntHandler(PersistentServerConnectionApplication):
    """
    Shunt because "Redirect" is too pretty a word for what it does.

    In a Sideview app's default.xml,  instead of direct references to view names like:
      <view name="my_view"/>
    there needs to be this instead:
      <a href="../../splunkd/__raw/sideview_ui_shunt?view=my_view">My View</a>

    The reason for this situation is twofold.
    1) Users often skip the docs and install an app without noticing that it requires that the
        Canary app also be installed.   This code detects that and redirects them to a static
        sorry page called "sorry_canary_not_installed"
    2) When the user is in the app,  but technically in a core splunk view like "search" or
        "report", the nav still needs to work properly.

    And Canary's "AppNav" module actually is aware of this convention and when it sees a shunt
    URL in the default.xml,  it actually puts a regular old link right to the Canary URI instead
    """

    def __init__(self, command_line, command_arg):
        """ a shiny new donkey for whoever brings me... wait scratch that."""
        PersistentServerConnectionApplication.__init__(self)



    def handle(self, in_string):
        """
        the main template method of PersistentServerConnectionApplication
        note that passing a single string arg that is an arbitrary JSON structure
        with unknown inscrutable conventions is apparently the new black.  =|
        #thisisfine
        """
        try:
            params = json.loads(in_string)

            request = Request(params)
            #logger.error("input params are")
            #logger.error(json.dumps(params, indent=4, sort_keys=True))

            method = params["method"]

            if method == "GET":
                config = get_splunk_server_config(request.session_key)
                return handle_get(request, config)

            return build_response(405, "Method not allowed (%s)" % method, "xml")

        except Exception:
            logger.error(traceback.format_exc())
            return build_response(500, traceback.format_exc(), "json")
