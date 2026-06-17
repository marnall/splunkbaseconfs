# Copyright (C) 2010-2025 Sideview LLC.  All Rights Reserved.
"""
 This implements a scripttype=persist endpoint that runs in Splunk, whose
 function is to decode any license strings in sideview_license.conf for
 this app, and present the decoded license information to the client.

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

ENDPOINT_BASE = "/configs"
ENTITY_NAME = "conf-sideview_license"
CONF_FILE = "sideview_license.conf"
APP = "cisco_cdr"


"""
NOTE - We came across some evidence that a "user user" in Cloud has these capabilities.

accelerate_search
change_own_password
dispatch_rest_to_indexers
edit_search_schedule_window
export_results_is_visible
get_metadata
get_typeahead
input_file
list_inputs
list_metrics_catalog
output_file
pattern_detect
request_remote_tok
rest_apps_view
rest_properties_get
rest_properties_set
rtsearch
run_script_dnparse
schedule_rtsearch
search
"""
# the capabilities that we check for before we allow the user to update the app license.
# NOTE that the user just needs any one of these capabilities, and not all of them together.
SUFFICIENT_CAPABILITIES_FOR_LICENSE_UPDATE = ["license_edit", "edit_sourcetypes", "admin_all_objects"]

MISSING_EQUALS_SIGNS_TOLERATED = 2
SPLUNK_HOME = os.environ["SPLUNK_HOME"]

NOT_AUTHORIZED_TO_POST_LICENSES_ERROR = """It looks like your Splunk Enterprise
user account does not have the correct capabilities to be able to post licenses.
(Currently you need either the "license_edit" or "edit_sourcetypes" to edit Sideview
licenses).  Reach out to your local Splunk admin(s) for help, and contact Sideview support
if you would like more detail."""


def setup_logging(log_level):
    """ the app uses its own log file. """
    LOG_FILE_PATH = os.path.join(SPLUNK_HOME, "var", "log", "splunk", APP + ".log")
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"

    our_logger = logging.getLogger(APP)
    our_logger.propagate = False
    if not our_logger.handlers:
        our_logger.setLevel(log_level)
        handler = logging.handlers.RotatingFileHandler(LOG_FILE_PATH, mode="a")
        handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
        our_logger.addHandler(handler)
    return our_logger


logger = setup_logging(logging.INFO)


def decode(license_str):
    """ <photo of the Inanimate Carbon Rod> """
    out = list(license_str)
    q = 3
    for i, val in enumerate(license_str):
        if i % q == 0:
            if i >= len(license_str) - (q+2):
                out[i] = val
            else:
                temp = val
                j = 0
                while j < q-1:
                    out[i+j] = license_str[i+j+1]
                    j += 1
                out[i+q-1] = temp
    return "".join(out)


def get_json_license(license_str):
    """ given the license string on disk, or POST'ed by the user,  return the license json"""
    for delta in range(10):
        modified_license_str = license_str
        if delta > 0:
            modified_license_str = make_it_look_differenter(license_str, delta)
        try:
            will_it_blend = base64.b64decode(decode(modified_license_str))
            json.loads(will_it_blend)
            return will_it_blend
        except:
            pass
    raise ValueError("License invalid - (base64).")


def make_it_look_differenter(text, places):
    """ this looks insane and possibly it is.
       But at the time of this writing, our license-strings for any given customer are unusual in
       that the first chars and the last chars are the same each year.   So the admins quickly
       compare the start of the string, or maybe the end, or maybe both.
       The only different parts are in the middle, so they dont see the differences. They  conclude
       the new license they have is the same as the old expired one already in the system, and
       then MUCH CONFUSION .
       So at some point in the future we will randomly shift the chars using the year mod 10.
       (also insane) and issue them that way.   This will make every char in the strings look very
       different each year.  Admins will no longer falsely conclude that we screwed something up.
       """
    def substitute(char):
        """it just rotates uppercase chars around, and same with lowercase and same with digits.
        Anything else it leaves alone."""
        if char in string.ascii_lowercase:
            char_num = ord(char) - 97
            char = chr((char_num + places) % 26 + 97)
        elif char in string.ascii_uppercase:
            char_num = ord(char) - 65
            char = chr((char_num + places) % 26 + 65)
        elif char in string.digits:
            char_num = ord(char) - 48
            char = chr((char_num + places) % 10 + 48)
        return char
    return ''.join(substitute(char) for char in text)



def validate_license(license_str):
    """
    as advertised. raises exceptions if the license is malformed.
    Note that it doesn't care if the license is EXPIRED.
    """
    if license_str.strip() == "":
        raise ValueError("No license entered")
    if license_str.strip() == "to kill":
        raise ValueError("I'm afraid your license to kill has been revoked")

    license_str = get_json_license(license_str)
    try:
        license_dict = json.loads(license_str)
    except Exception:
        raise ValueError("License invalid- (decoded string is not json)")
    if "le" not in license_dict or "se" not in license_dict:
        raise ValueError("License invalid - license string lacks core fields")
    if license_dict["pr"] != APP:
        raise ValueError("License invalid - This license is for a different app (it is for the %s app)" % license_dict["pr"])
    if "v" in license_dict:
        raise ValueError("License invalid - This version of the app only works with version 1 "\
                "of Sideview's licensing schema - This license is version %s." % license_dict["v"])


def build_response(status, message, output_mode="xml", license_str=None):
    """ worker method to send back the given response to the client """
    response = {}
    response["status"] = status

    if 200 <= status < 400:
        if license_str:
            payload = license_str
        else:
            payload = {}
            payload["success"] = True
            if message:
                payload["messages"] = [{"text":message}]
        # nope.  you really really, cannot ever set this, or the endpoint dies.
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

def is_free(session_key):
    uri = "/services/cisco_cdr_splunk_license"
    _response, content = splunk.rest.simpleRequest(uri, sessionKey=session_key, method='GET',
                                  raiseAllErrors=True)
    content = json.loads(content)
    return content["license_type"] == "Free"


def handle_get(session_key, output_mode, qs_dict):
    """ time to serve the donuts """
    try:
        # just a trick to let us restart the persistent process in between
        # code changes (during development).
        if "kill" in qs_dict:
            logger.warning("explicitly killing the scripttype=persist process.")
            sys.exit()

        stanza = en.getEntity(ENDPOINT_BASE,
                              ENTITY_NAME,
                              namespace=APP,
                              owner="nobody",
                              sessionKey=session_key)

        if (not stanza or stanza["license"] is None or
                stanza["license"] == ""):
            return build_response(404, "no license found", output_mode)

    except Exception:
        logger.error(traceback.format_exc())
        return build_response(500, traceback.format_exc(), output_mode)

    try:
        license_str = stanza["license"]
        validate_license(license_str)
    except ValueError as e:
        logger.error(traceback.format_exc())
        return build_response(500, traceback.format_exc(), output_mode)
    else:
        license_str = get_json_license(license_str)

        license_str = license_str.decode("ascii")
        return build_response(200, False, output_mode, license_str)


def is_user_authorized_to_edit_app_licenses(session_key):
    """ time to see if this person is allowed to come in here where we make the donuts"""

    if is_free(session_key):
        return True

    uri = "/services/authentication/current-context"
    args = {"output_mode": "json"}
    _response, content = splunk.rest.simpleRequest(uri,
                                                   sessionKey=session_key,
                                                   getargs=args,
                                                   method='GET',
                                                   raiseAllErrors=True)
    content = json.loads(content)

    # if this is going to blow up, it's actually better to NOT catch the exception
    # cause then the user will send us the verbatim stack trace out of the UI.
    for capability in content.get("entry")[0].get("content").get("capabilities", {}):
        if capability in SUFFICIENT_CAPABILITIES_FOR_LICENSE_UPDATE:
            return True
    return False


def modify_acl(session_key, user):
    """ time to make the donuts world-readable (world-eatable?) """
    uri = "/servicesNS/nobody/%s/configs/conf-sideview_license/%s/acl"  % (APP, APP)
    post_args = {"perms.write": "admin", "perms.read":  "*", "sharing": "app", "owner": user}
    splunk.rest.simpleRequest(uri,
                              sessionKey=session_key,
                              postargs=post_args,
                              method='POST',
                              raiseAllErrors=True)

def handle_post(session_key, user, output_mode, post_args):
    """ time to secretly replace the donuts """
    new_license_str = post_args["license"].strip()

    # Splunk - I learned it from watching you - "OPTIMISTIC_ABOUT_FILE_LOCKING"
    if "wildlyOptimisticAboutLicenseString" not in post_args:

        # a bit odd.  Because meatbag often doesn't copy the trailing
        # equals signs when they paste in the license, we just try
        # tacking on one or two equals signs if parsing fails.
        for i in range(MISSING_EQUALS_SIGNS_TOLERATED+1):
            try:
                validate_license(new_license_str)
            except ValueError as exc:
                if i == 0:
                    first_traceback = traceback.format_exc()
                if i == MISSING_EQUALS_SIGNS_TOLERATED:
                    # omitting the equals sign is such a common copy+paste mistake
                    # that we just try and tolerate it...
                    if first_traceback:
                        logger.error(first_traceback)
                    error_str = "the license string you submitted appears to be invalid. "\
                        "Check for any typos and try again. Details - decoding the license "\
                        "failed with -- %s \n %s" % (str(exc), post_args["license"].strip())
                    return build_response(400, error_str, output_mode)
                new_license_str += "="

    stanza = en.getEntity(ENDPOINT_BASE, ENTITY_NAME, namespace=APP, owner="nobody",
                          sessionKey=session_key)
    if not stanza:
        stanza = en.Entity(ENDPOINT_BASE, ENTITY_NAME, namespace=APP, owner="nobody")
        stanza["name"] = APP

    stanza["license"] = new_license_str
    try:
        en.setEntity(stanza, sessionKey=session_key)
    except splunk.RESTException as exc:

        if exc.statusCode == 405:
            logger.warning('User "%s" lacks authorization to update the license for app="%s"', user, APP)

            # splunk is just wrong here to return 405.  The server does
            # support the method, the user is just not authorized to use it.
            return build_response(403, NOT_AUTHORIZED_TO_POST_LICENSES_ERROR)

        message = exc.msg

        #this class seems a bit broken. Sometimes it feels like having structured
        # messages. Sometimes it doesn't.
        try:
            message = message[0]["text"]
        except TypeError:
            logger.error(traceback.format_exc())

        logger.error('Unexpected error occurred user="%s" app="%s" license_str="%s"', user, APP, new_license_str)
        logger.error("posting to %s/%s, we received an error %s %s",
                     ENDPOINT_BASE, ENTITY_NAME, exc.statusCode, message)
        logger.error(message)
        logger.error(traceback.format_exc())

        return build_response(exc.statusCode, message)

    modify_acl(session_key, user)

    logger.info('new license string received and has been saved to the %s stanza in %s user="%s" app="%s" license_str="%s"', APP, CONF_FILE, user, APP, new_license_str)
    return build_response(200, "Successfully saved your new license string", output_mode)

class CiscoCdrLicenseInfoHandler(PersistentServerConnectionApplication):
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

            if method == "POST":
                post_args = get_post_args(params["form"])


                if is_user_authorized_to_edit_app_licenses(user_session_key):
                    if params.get("system_authtoken", False):
                        system_session_key = params.get("system_authtoken")
                        return handle_post(system_session_key, user, output_mode, post_args)
                    else:
                        logger.info("passSystemAuth appears to have been set to False in local restmap.conf configuration. This means the license handler will use the user's session key to apply the license, which in turn means it will only work if that user has the \"admin-all-objects\" capability.")
                        return handle_post(user_session_key, user, output_mode, post_args)
                logger.error("%s is not authorized to edit app licenses.", user)
                return build_response(403, NOT_AUTHORIZED_TO_POST_LICENSES_ERROR)

            return build_response(405, "Method not allowed (%s)" % method, output_mode)

        except Exception:
            logger.error(traceback.format_exc())
            return build_response(500, traceback.format_exc(), "json")
