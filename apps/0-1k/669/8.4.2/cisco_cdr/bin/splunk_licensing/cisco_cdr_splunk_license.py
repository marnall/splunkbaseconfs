# Copyright (C) 2010-2025 Sideview LLC.  All Rights Reserved.
"""
 This implements a scripttype=persist endpoint that runs in Splunk, whose
 function is to return information about the currently installed Splunk license,
 as well as about a few of the currently logged in user's capabilities.

 If your use of this app is through the Sideview Trial Internal Use License
 Agreement, or through the Sideview Term Internal Use License Agreement or
 through the Sideview Perpetual Internal Use License Agreement, then as per
 the relevant agreement any modification of this file or modified copies
 made of this file constitutes a violation of that agreement.
"""

import os
import sys
import json
import traceback
import base64
import logging
import string
import splunk
import splunk.entity as en

if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

from splunk.persistconn.application import PersistentServerConnectionApplication

APP = "cisco_cdr"


SPLUNK_HOME = os.environ["SPLUNK_HOME"]



def setup_logging(log_level):
    """ the app uses its own log file. """
    LOG_FILE_PATH = os.path.join(SPLUNK_HOME, "var", "log", "splunk", APP + ".log")
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"

    our_logger = logging.getLogger(APP)
    our_logger.propagate = False
    our_logger.setLevel(log_level)

    handler = logging.handlers.RotatingFileHandler(LOG_FILE_PATH, mode="a")
    handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    our_logger.addHandler(handler)
    return our_logger


logger = setup_logging(logging.INFO)



def build_response(status, message, output_mode="xml", payload=None):
    """ worker method to send back the given response to the client """
    response = {}
    response["status"] = status

    if 200 <= status < 400:
        if not payload:
            payload = {}
            payload["success"] = True
            if message:
                payload["messages"] = [{"text":message}]
        # nope.  you really really, cannot ever set this, or the rest command dies.
        #response["headers"] = {"Content-Type": "application/json"}
    else:
        payload = {}
        payload["success"] = False
        if message:
            payload["messages"] = [{"text":message}]
    response["payload"] = payload

    #I hate this...but
    # a) I don't want to actually implement the silly atom feed response type.
    # b) if we just ignore the output_mode=xml case (that the rest command submits),
    #    AND we just dont return any Content-Type header at all to the poor rest command
    #    then... it seems to give up, just present the json string, and gives no errors.
    #    if otoh we give them a Content Type header,  EVEN IF ITS "xml",
    #    then the rest command fails completely.
    if output_mode != "xml":
        content_type = "application/json"
        response["headers"] = {"Content-Type": content_type}

    #logger.error("response params are")
    #logger.error(json.dumps(response, indent=4, sort_keys=True))

    return response


def get_post_args(form_arr):
    """further parsing of the inscrutable json-formatted string
    that was passed as the sole arg to handle.  Because reasons."""
    out = {}
    for arr2 in form_arr:
        out[arr2[0]] = arr2[1]
    return out

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


def pick_a_winner(licenses):
    """ this paranoia seems to be unnecessary, but I was haunted by a memory of seeing this
    endpoint return more than one license....  like Enterprise, Trial, Free.
    It was probably a different endpoint and I can't reproduce the behavior but again... haunted."""
    for license in licenses:
        if license=="Enterprise":
            return license

    for license in licenses:
        if license=="Trial":
            return license

    for license in licenses:
        if license=="Free":
            return license
    return "UNKNOWN"

def get_simple_entity(session_key, uri):
    args = {
        "output_mode":"json"
    }
    _response, content = splunk.rest.simpleRequest(uri,
                       sessionKey=session_key,
                       getargs=args,
                       method='GET',
                       raiseAllErrors=True)
    content = json.loads(content)
    return content.get("entry")[0].get("content")

def get_license_keys(session_key):
    uri = "/services/server/info"
    args = {
        "output_mode": "json"
    }
    _response, content = splunk.rest.simpleRequest(uri,
                   sessionKey=session_key,
                   getargs=args,
                   method='GET',
                   raiseAllErrors=True)

    content = json.loads(content)
    licenses = []
    for record in content.get("entry"):
        licenses.append(record.get("content").get("activeLicenseGroup"))

    current_license = pick_a_winner(licenses)

    return {
        "license_type": current_license
    }

def get_cumulative_role_values(session_key):
    """ go get all the roles, and for each row get all the quota keys and merge them with highest
    number winning for each.  returns the cumulative dict."""
    auth_dict = get_simple_entity(session_key, "/services/authentication/current-context")
    output = {"capabilities": auth_dict.get("capabilities")}
    roles = auth_dict.get("roles", [])
    output["roles"] = ",".join(roles)
    restricted_roles = []
    for role in roles:
        try:
            role_dict = get_simple_entity(session_key, "/services/authorization/roles/%s" % role)
        except splunk.AuthorizationFailed:
            restricted_roles.append(role)
            logger.warning("This user is in the %s role but when we tried to GET that role's settings Splunk returned 403. o_O. Skipping.", role)
            continue
        except splunk.ResourceNotFound:
            restricted_roles.append(role)
            logger.warning("This user is in the %s role but when we tried to GET that role's settings Splunk returned 404. lolwut. o_O. Skipping.", role)
            continue

        for key, value in role_dict.items():
            if key.endswith("Quota"):
                if key not in output:
                    output[key] = value
                if int(value)>0:
                    output[key] = max(output[key], int(value))

    if len(restricted_roles) > 0:
        output["roles_whose_keys_we_are_unable_to_see"] = ",".join(restricted_roles)

    return output



def handle_get(session_key, output_mode, qs_dict):
    """ time to serve the donuts """

    try:
        # just a trick to let us restart the persistent process in between
        # code changes (during development).
        if "kill" in qs_dict:
            logger.warning("explicitly killing the scripttype=persist process.")
            sys.exit()

        payload = get_license_keys(session_key)

        # free splunk will throw http 402 if you ask it about roles and capabilities.
        if payload.get("license_type") != "Free":
            payload.update(get_cumulative_role_values(session_key))
        return build_response(200, "ok", output_mode, payload)

    except Exception:
        logger.error(traceback.format_exc())
        return build_response(500, traceback.format_exc(), output_mode)




class CiscoCdrSplunkLicenseInfoHandler(PersistentServerConnectionApplication):
    """
    PersistentServerConnectionApplication is undocumented.  There are some vague
    references to this entire part of Splunk's functionality in restmap.conf.spec
    and that's it.   If it weren't for James Ervin's conf2016 talk, nobody outside
    of Splunk would have a clue how to make one of these handlers run.
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
            #logger.error("input params are")
            #logger.error(json.dumps(params, indent=4, sort_keys=True))
            user_session_key = params["session"]["authtoken"]
            user = params["session"]["user"]
            method = params["method"]
            output_mode = params.get("output_mode", "json")

            if method == "GET":
                qs_dict = get_query_args(params)
                return handle_get(user_session_key, output_mode, qs_dict)

            return build_response(405, "Method not allowed (%s)" % method, output_mode)

        except Exception:
            logger.error(traceback.format_exc())
            return build_response(500, traceback.format_exc(), "json")
