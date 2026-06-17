# Copyright (C) 2023-2025 Sideview LLC.  All Rights Reserved.
"""
 This implements a scripttype=persist endpoint that runs in Splunk.
 It's purpose is to wrap up a series of creates and edits and acl-changes
 so that effectively one POST can edit/create a pair of origFoo destFoo transforms
 change their acl's to app-level sharing, and add them to the current active
 transforms in props.
 And if anything fails to... message the user at least.

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
import re

import splunk
from splunk import rest
#from splunk.clilib.cli_common import getWebConfKeyValue
#MGMT_PORT = str(getWebConfKeyValue("mgmtHostPort").rsplit(':', 1)[1])


if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

from splunk.persistconn.application import PersistentServerConnectionApplication

APP = "cisco_cdr"
TRANSFORM_PREFIX = "cisco-cdr"
AUTHORIZATION_FAILED_MESSAGE = "Your splunk user account does not have all the capabilities needed to perform this action"
SPLUNK_HOME = os.environ["SPLUNK_HOME"]
LOG_CONTENT_LENGTHS = True

sys.path.insert(1, os.path.join(os.environ['SPLUNK_HOME'], "etc", "apps", APP, "bin"))
from cisco_cdr_request import Request



def setup_logging(log_level):
    """ we use our own cisco_cdr.log file, although regrettably this is still
    left to be handled by the _internal data input"""

    LOGGING_FILE_NAME = APP + ".log"
    BASE_LOG_PATH = os.path.join("var", "log", "splunk")
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"

    our_logger = logging.getLogger(APP)
    our_logger.propagate = False
    if not our_logger.handlers:

        our_logger.setLevel(log_level)
        log_file_path = os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME)
        splunk_log_handler = logging.handlers.RotatingFileHandler(log_file_path, mode="a")
        splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
        our_logger.addHandler(splunk_log_handler)
    return our_logger

logger = setup_logging(logging.INFO)

"""
things borrowed from sideview_canary.py
cause we're not ready to just import from canary
"""

def get_rest_api_response(uri, session_key):
    """ simple wrapper around simpleRequest to return just the json response """
    getargs = {"output_mode":"json"}
    response, content = rest.simpleRequest(uri, sessionKey=session_key, method="GET",
                                            raiseAllErrors=True, getargs=getargs)
    if LOG_CONTENT_LENGTHS:
        logger.info("REST call to uri " + uri + " returned content-length of " + response.get("content-length"))
    return json.loads(content)

def get_single_rest_api_entry(uri, session_key):
    """ simplified way to just get the contents of the first stanza, parsed as json.
        95% of the time this is all we want."""

    content = get_rest_api_response(uri, session_key)
    return content["entry"][0]["content"]


def get_query_args(params):
    """ even more parsing of the inscrutable json-formatted string
        that was passed as the sole arg to handle.  Because reasons."""
    out = {}
    if "query" not in params:
        return out
    query_arr = params["query"]
    for pair in query_arr:
        out[pair[0]] = pair[1]
    return out

def is_valid_regex(pattern):
    """ like the title said"""
    try:
        re.compile(pattern)
        return True
    except re.error:
        return False

def handle_get(request):
    """ We don't really use GET, but this is where we hide the backdoor to restart the persistent endpoint """

    # just a trick to let us restart the persistent process in between
    # code changes (during development).
    if "kill" in request.qs_dict:
        logger.warning("explicitly killing the scripttype=persist process.")
        sys.exit()

    return build_json_response(400, "unimplemented")


def validate_name(name):
    """ check that the name is a non-empty string and is only alphanumeric chars"""

    if not name:
        return "No device type name was specified."
    if not name.isalnum():
        return "Device type names may only consist of letters and numbers."
    return False

def validate_name_and_regex(name, regex):
    """ check that name and regex passed for script tags or invalid regex syntax"""

    name_error = validate_name(name)
    if name_error:
        return name_error

    if not regex:
        return "no regex was specified."

    # We don't know of any place where splunk search result strings are rendered unescaped but
    # this is easy enough to prevent.
    if re.search(r"<script.*?>.*?</script>", regex, re.IGNORECASE | re.DOTALL):
        return "Regular expression is not valid."
    if not is_valid_regex(regex):
        return "Regular expression is not valid."
    return False



def handle_create(request) :
    """ on POST to the main URL, create the two transforms and the one props key to implement one of our
      custom device types """

    name = request.post_dict.get("name", None)
    regex = request.post_dict.get("regex", None)
    error = validate_name_and_regex(name, regex)
    if error:
        logger.error("error on create: %s", error)
        return build_json_response(400, error)



    logger.info("creating custom device_type %s", name)

    try:
        create_transform(request.user_name, name, "orig", regex, request.session_key)
        create_transform(request.user_name, name, "dest", regex, request.session_key)
        create_report_key(request.user_name, name, request.session_key)
    except splunk.BadRequest as e:
        return build_json_response(400, e.get_message_text())
    except splunk.AuthorizationFailed:
        return build_json_response(403, AUTHORIZATION_FAILED_MESSAGE)

    logger.info("custom device_type created. name=%", name)
    return build_json_response(200, "success")

def handle_edit(request, name):
    """ on a PUT to the main endpoint + "/{name}",  update the regexes in the two transforms of that device type."""
    error = validate_name_and_regex(name, request.post_dict.get("regex", None))
    if error:
        logger.error("error on edit: %s", error)
        return build_json_response(400, error)

    logger.info("editing custom device_type %s", name)
    regex = request.post_dict["regex"]
    success, message = transforms_exist(request.user_name, name, request.session_key)
    logger.info(message)


    if not success:
        return build_json_response(404, message)
    try:
        edit_transform(name, "orig", regex, request.session_key)
        edit_transform(name, "dest", regex, request.session_key)
    except splunk.BadRequest as e:
        return build_json_response(400, e.get_message_text())
    except splunk.AuthorizationFailed:
        return build_json_response(403, AUTHORIZATION_FAILED_MESSAGE)

    logger.info("custom device_type successfully edited. name=%s", name)
    return build_json_response(200, "success")

def handle_delete(request):
    """ delete the 2 transforms and the props.conf entry for the device_type passed in 'name'
        Note: this probably should be changed to pass the name as a segment, like we do  during edit. """

    name = request.post_dict.get("name", None)
    error = validate_name(name)
    if error:
        logger.error("error on delete: %s", error)
        return build_json_response(400, error)

    logger.info("deleting custom device_type %s", name)
    try:
        successes = 0
        for direction in ["orig", "dest"]:
            try:
                delete_transform(request.user_name, name, direction, request.session_key)
                successes += 1
            except splunk.ResourceNotFound:
                pass
        try:
            remove_name_from_report_key(request.user_name, name, request.session_key)
            successes += 1
        except splunk.ResourceNotFound:
            pass
    except splunk.AuthorizationFailed:
        return build_json_response(403, AUTHORIZATION_FAILED_MESSAGE)
    except splunk.BadRequest:
        msg = "Unable to delete - possibly the device type is owned by a different user and your account lacks admin-all-objects."
        return build_json_response(400, msg)

    message = "unexpected failure"
    if successes==0:
        message = "we found nothing to delete that matched that name."
        return build_json_response(400, message)
    if successes>0:
        if successes==4:
            message = "custom device type %s deleted" % name
        elif successes<4:
            message = "we found some things to delete that matched that name, but not a full set."
    logger.info("custom device_type deleted. name=%s", name)
    return build_json_response(200, message)

def build_json_response(status, message):
    """ convenience, to simplify returning the endpoint's json responses."""
    payload = {
        "message": message
    }
    return build_response(status, json.dumps(payload))

def build_response(status, payload=None, content_type="application/json", location=None):
    """ core method to return things to the client. """
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

def transforms_exist(user, name, session_key):
    """ check whether both transforms exist """
    found = []
    for direction in ["orig", "dest"]:
        try:
            uri = "/servicesNS/%s/%s/data/transforms/extractions/%s-%s%s" % (user, APP, TRANSFORM_PREFIX, direction, name)
            _resp = get_rest_api_response(uri, session_key)
            found.append(direction)
        except splunk.ResourceNotFound:
            pass
    directions_found = ",".join(found)
    if directions_found == "orig,dest":
        return True, "both the orig and dest transform exist"
    if directions_found == "orig":
        return False, "only the orig transform exists"
    if directions_found == "dest":
        return False, "only the dest transform exists"
    return False, "neither transform exists"

def contains_capturing_group(regex):
    """ checks whether the regex contains () to define capturing group """
    return re.search(r"\([^)]+\)", regex)

def create_transform(user, name, direction, regex, session_key):
    """ create an individual transform stanza, for either orig or dest """
    assert(direction in ["orig","dest"])

    # in some slightly older versions of splunk there was a very longstanding
    # bug where if you ever had an enabled transform that didn't actually USE
    # any capturing group references in its FORMAT key,   you still have to put one
    # in the regex or Splunk Search would die -- zero results for all searches, all users,
    # across all sourcetypes and all apps.  This seems to be fixed in 9.X but we
    # have a long memory.
    if not contains_capturing_group(regex):
        raise splunk.BadRequest("%s does not contain a capturing group" % regex)


    uri = "/servicesNS/%s/%s/data/transforms/extractions/%s-%s%s" % (user, APP, TRANSFORM_PREFIX, direction, name)
    postargs = {
        "REGEX": regex,
        "FORMAT": "%s_device_type::%s" % (direction, name),
        "SOURCE_KEY": "%sDeviceName" % (direction),
        "name": "%s-%s%s" % (TRANSFORM_PREFIX, direction, name)
    }
    response, _content = rest.simpleRequest(uri, sessionKey=session_key, method="POST",
                                            raiseAllErrors=True, postargs=postargs)
    if LOG_CONTENT_LENGTHS:
        logger.info("REST call to create transform returned content-length of %s",  response.get("content-length"))
    _share_transform(user, name, direction, session_key)

def edit_transform(name, direction, regex, session_key):
    """ edit an individual transform stanza, for either orig or dest """
    assert(direction in ["orig","dest"])

    if not contains_capturing_group(regex):
        raise splunk.BadRequest("%s does not contain a capturing group" % regex)

    uri = "/servicesNS/nobody/%s/data/transforms/extractions/%s-%s%s" % (APP, TRANSFORM_PREFIX, direction, name)
    postargs = {
        "REGEX": regex,
        "FORMAT": "%s_device_type::%s" % (direction, name),
        "SOURCE_KEY": "%sDeviceName" % (direction)
    }
    _response, _content = rest.simpleRequest(uri, sessionKey=session_key, method="POST",
                                            raiseAllErrors=True, postargs=postargs)


def _share_transform(user, name, direction, session_key):
    """ share an individual transform stanza, at the "app" level for either orig or dest """
    assert(direction in ["orig","dest"])
    uri = "/servicesNS/%s/%s/data/transforms/extractions/%s-%s%s/acl" % (user, APP, TRANSFORM_PREFIX, direction, name)
    postargs = {
        "sharing": "app",
        "owner": user
    }
    response, _content = rest.simpleRequest(uri, sessionKey=session_key, method="POST",
                                            raiseAllErrors=True, postargs=postargs)
    if LOG_CONTENT_LENGTHS:
        logger.info("share transform REST call returned content-length of %s", response.get("content-length"))

def delete_transform(user, name, direction, session_key):
    """ delete a given transform, either orig or dest """
    assert(direction in ["orig","dest"])

    uri = "/servicesNS/%s/%s/data/transforms/extractions/%s-%s%s" % (user, APP, TRANSFORM_PREFIX, direction, name)
    response, _content = rest.simpleRequest(uri, sessionKey=session_key, method="DELETE",
                                            raiseAllErrors=True, postargs={})
    if LOG_CONTENT_LENGTHS:
        logger.info("delete transform REST call returned content-length of %s", response.get("content-length"))


def create_report_key(user, name, session_key):
    """ add the orig and test transform names corresponding to the given name, to the props.conf entry.
        creates that entry in props if it does not already exist. """
    logger.info("create_report_key")
    key = "REPORT-custom-device-types"
    uri = "/servicesNS/nobody/cisco_cdr/data/props/extractions/cucm_cdr %3A REPORT-custom-device-types"

    rules = []
    rules.append("%s-orig%s" % (TRANSFORM_PREFIX, name))
    rules.append("%s-dest%s" % (TRANSFORM_PREFIX, name))

    try:
        content = get_single_rest_api_entry(uri, session_key)

        new_rules = rules
        rules = content["value"].split(",")
        rules += new_rules

    except splunk.ResourceNotFound:
        logger.info("no REPORT-custom-device-types key existed so we are creating one")
        postargs = {
            "stanza": "cucm_cdr",
            "type": "REPORT",
            "name": "custom-device-types",
            "value": ",".join(rules)
        }
        create_uri = "/servicesNS/%s/cisco_cdr/data/props/extractions" % user
        response, content = rest.simpleRequest(create_uri, sessionKey=session_key, method="POST",
                                               raiseAllErrors=True, postargs=postargs)
        if LOG_CONTENT_LENGTHS:
            logger.info("REST call to create a new REPORT-custom-device-types key in props returned content-length of %s", response.get("content-length"))
        _share_report_key(user, session_key)
        return
    # IT DID exist though, so we are just appending to it
    logger.info("a REPORT-custom-device-types key existed so we are appending to it. New rules are %s", ",".join(rules))
    postargs = {
        "value": ",".join(rules)
    }
    response, _content = rest.simpleRequest(uri, sessionKey=session_key, method="POST",
                                           raiseAllErrors=True, postargs=postargs)
    if LOG_CONTENT_LENGTHS:
        logger.info("REST call to edit existing REPORT-custom-device-types key in props returned content-length of %s", response.get("content-length"))

def _share_report_key(user, session_key):
    """ Share the "REPORT-custom-device-types" props.conf entry at the app level for all users """
    uri = "/servicesNS/" + user + "/cisco_cdr/data/props/extractions/cucm_cdr %3A REPORT-custom-device-types/acl"
    postargs = {
        "sharing": "app",
        "owner": user
    }
    response, _content = rest.simpleRequest(uri, sessionKey=session_key, method="POST",
                                            raiseAllErrors=True, postargs=postargs)
    if LOG_CONTENT_LENGTHS:
        logger.info("REST call to share existing REPORT-custom-device-types key in props returned content-length of %s", response.get("content-length"))


def delete_report_key(user, session_key):
    """ Delete the "REPORT-custom-device-types" props.conf entry outright"""

    for uri in [
        # user space
        "/servicesNS/" + user + "/cisco_cdr/data/props/extractions/cucm_cdr %3A REPORT-custom-device-types",
        # shared app space
        "/servicesNS/nobody/cisco_cdr/data/props/extractions/cucm_cdr %3A REPORT-custom-device-types"
    ] :

        try:
            response, _content = rest.simpleRequest(uri, sessionKey=session_key, method="DELETE", raiseAllErrors=True, postargs={})
            if LOG_CONTENT_LENGTHS:
                logger.info("REST call to delete existing REPORT-custom-device-types key in props returned content-length of %s",  response.get("content-length"))

            #resp = requests.delete("https://localhost:" + MGMT_PORT + uri, verify=False)
            #if resp.status_code==403:
            #    raise splunk.AuthorizationFailed


        except splunk.ResourceNotFound:
            pass


def remove_name_from_report_key(user, name, session_key):
    """ Carefully remove the orig and dest transforms matching the given 'name',  from the
        "REPORT-custom-device-types" props.conf entry.
        NOTE: this assumes it has already been shared to the app level  """

    uri = "/servicesNS/nobody/cisco_cdr/data/props/extractions/cucm_cdr %3A REPORT-custom-device-types"

    content = get_single_rest_api_entry(uri, session_key)
    names = content["value"].split(",")

    names_to_remove = []
    names_to_remove.append("%s-orig%s" % (TRANSFORM_PREFIX, name))
    names_to_remove.append("%s-dest%s" % (TRANSFORM_PREFIX, name))
    for n in names_to_remove:
        if n in names:
            names.remove(n)

    if len(names)==0:
        delete_report_key(user, session_key)
    else:
        postargs = {
            "value": ",".join(names)
        }
        response, content = rest.simpleRequest(uri, sessionKey=session_key, method="POST",
                                               raiseAllErrors=True, postargs=postargs)
        if LOG_CONTENT_LENGTHS:
            logger.info("REST call to edit existing REPORT-custom-device-types key in props (removing transforms) returned content-length of %s", response.get("content-length"))

class CiscoCdrCustomDeviceTypeHandler(PersistentServerConnectionApplication):
    """ This implements a scripttype=persist rest handler to receive input from the
        Cisco CDR app's "define custom device types" page.  Input is validated
        and then required calls are made to modify props and transforms config to
        implement the defined device type. """

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        """
        the main template method of PersistentServerConnectionApplication
        note that passing a single string arg that is an arbitrary JSON structure
        with unknown inscrutable conventions is apparently the new black.  =|
        """
        try:
            params = json.loads(in_string)
            request = Request(params)

            method = params["method"]

            if method == "GET":
                return handle_get(request)
            if method == "POST":
                if request.post_dict.get("action", False) == "delete":
                    return handle_delete(request)

                return handle_create(request)

            if method == "PUT":
                segments = []
                if "path_info" in params:
                    segments = params["path_info"].split('/')
                    if len(segments)==1:
                        return handle_edit(request, segments[0])
                    return build_json_response(400, "extra segments in path")
                return build_json_response(400, "no name specified")

            # leaving this here in case we ever put proper method=DELETE back....
            # Which we can do once we are long past supporting 9.1.X and earlier
            if method == "DELETE":
                return handle_delete(request)

            return build_json_response(405, "Method not allowed (%s)" % method)

        except splunk.BadRequest as e:
            logger.error(traceback.format_exc())
            return build_json_response(400, str(e))

        except Exception:
            logger.error(traceback.format_exc())
            return build_json_response(500, traceback.format_exc())
