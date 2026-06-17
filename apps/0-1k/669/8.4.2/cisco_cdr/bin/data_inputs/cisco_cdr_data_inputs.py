# Copyright (C) 2010-2025 Sideview LLC.  All Rights Reserved.
"""
 This implements a scripttype=persist endpoint that runs in Splunk, whose
 function is to check for existing data inputs and create them etc.

 If your use of this app is through the Sideview Trial Internal Use License
 Agreement, or through the Sideview Term Internal Use License Agreement or
 through the Sideview Perpetual Internal Use License Agreement, then as per
 the relevant agreement any modification of this file or modified copies
 made of this file constitutes a violation of that agreement.
"""

import os
import io
import re
import sys
import email
import json
import urllib.parse
import traceback
import logging
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

def fix_separators(path):
    """ os.path.isfile and os.listdir will happily accept the wrong slashes for
    the platform, but splunk wont.   We explicitly repair them if the
    customer typed them in wrong (which they do)"""

    last_char = path[-1:]
    if last_char == "/" or last_char == "\\":
        path = path[:-1]

    first_two_chars = path[:2]
    if first_two_chars == "//" or first_two_chars == "\\\\":
        return path

    sep = os.path.sep
    if sep == "\\":
        path = path.replace("/", sep)
    elif sep == "/":
        path = path.replace("\\", sep)
    return path

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



def build_response(status, message, license_str=None):
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
    content_type = "application/json"
    response["headers"] = {"Content-Type": content_type}


    return response


def get_tuple_as_dict(n_by_2_array):
    """ just convert the N x 2 array into a dict. One might ask why it wasn't
    in that format already..."""
    out = {}
    for pair in n_by_2_array:
        assert len(pair) == 2
        out[pair[0]] = pair[1]
    return out

def get_query_args(params):
    """even more parsing of the inscrutable json-formatted string
    that was passed as the sole arg to handle.  Because reasons."""
    if "query" not in params:
        return {}
    #logger.error(params.get("query"))
    return get_tuple_as_dict(params.get("query", []))


def get_multipart_form_args(params):
    """further parsing of the inscrutable json-formatted string
    that was passed as the sole arg to handle.  Because reasons."""

    header_dict = get_tuple_as_dict(params.get("headers", []))
    payload = params.get("payload", "")
    content_type = header_dict.get("Content-Type", "")

    if content_type.startswith("multipart/form-data"):
        raw = ("Content-Type: " + content_type + "\r\n\r\n").encode("utf-8") + payload.encode("utf-8")
        msg = email.message_from_bytes(raw)
        parts = msg.get_payload()
        if not isinstance(parts, list):
            return {}
        out = {}
        for part in parts:
            disposition = part.get("Content-Disposition", "")
            name_match = re.search(r'name="([^"]*)"', disposition)
            if not name_match:
                continue
            name = name_match.group(1)
            data = part.get_payload(decode=True) or b""
            if re.search(r"filename=", disposition):
                out[name] = data  # bytes for file uploads
            else:
                out[name] = data.decode("utf-8")
        return out

    parsed = urllib.parse.parse_qs(payload, keep_blank_values=True)
    return {k: v[0] for k, v in parsed.items()}





def get_matching_data_inputs(path, session_key):


    def paths_match(path1, path2):
        """ o_O  I can only assume I looked for something in os.* and found nothing. """
        if os.name == "nt":
            path1 = str(path1).lower()
            path2 = str(path2).lower()
        return path1 == path2

    matching = []
    inputs = en.getEntities("/data/inputs/monitor", count=0, namespace="cisco_cdr", owner="nobody", sessionKey=session_key)
    absPath = os.path.abspath(path)
    for i in inputs:
        p = inputs[i].name
        parent = os.path.abspath(os.path.dirname(p))

        if paths_match(os.path.abspath(p), absPath) or paths_match(parent, absPath):
            row = {}
            row["name"] = inputs[i].name
            row["index"] = inputs[i].get("index")
            row["sourcetype"] = inputs[i].get("sourcetype")
            if "move_policy" in inputs[i]:
                row["type"] = "batch"
            else:
                row["type"] = "monitor"

            try:
                row["disabled"] = splunk.util.normalizeBoolean(inputs[i].disabled)
            except:
                row["disabled"] = "false"
            matching.append(row)
    return matching


def get_current_custom_index(session_key):
    """ Looks in the `custom_index` macro to see where the app *thinks* the data is. """
    p = en.getEntity("/admin/macros", "custom_index", namespace="cisco_cdr", owner="-", sessionKey=session_key)
    search_term = p["definition"]
    if search_term.strip() == "*":
        return "main"
    match = re.match(r'[\"\s\(]*?index\s*?=[\"\s\(]*?([^\"]+)[\"\s\)]*?$', search_term)
    if match:
        return match.group(1)


def get_indexes(session_key):
    index_entities = en.getEntities("/admin/indexes", count=0, namespace="cisco_cdr", owner="-", sessionKey=session_key)
    index_names = []
    for idx in index_entities:
        name = index_entities[idx].name
        if not name.startswith("_"):
            index_names.append(name)
    return index_names


def get_file_types(path):
    """ Look into the actual files in the specified directory. gives back a simple directory
    of what's there """
    file_types = {"cdr":0, "cmr":0, "other":0}
    files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    for f in files:
        if f.startswith("cdr_"):
            file_types["cdr"] += 1
        elif f.startswith("cmr_"):
            file_types["cmr"] += 1
        else:
            file_types["other"] += 1
    return file_types


def get_file_types_description_message(path, types):
    pluralized = "files" if int(types["cdr"])>1 else "file"
    indexMessage = [
        "That path (%s) contains %d CDR %s" % (path, types["cdr"], pluralized)
    ]

    if types["cmr"] > 0:
        pluralized = "files" if int(types["cmr"])>1 else "file"
        indexMessage.append(" and %s CMR %s" % (types["cmr"], pluralized))

    if types["other"] > 0:
        pluralized = "files" if int(types["other"])>1 else "file"
        indexMessage.append(" (There are also %s other %s which we will ignore)" % (types["other"], pluralized))
    indexMessage.append(". ")

    return "".join(indexMessage)





def getErrorResponse(**kwargs):
    r = {}
    r["success"] = False
    for key in ("message", "data_inputs"):
        if key in kwargs:
            r[key] = kwargs[key]
    if "message" in kwargs:
        logger.error(kwargs["message"])
    if "e" in kwargs:
        e = kwargs["e"]
        logger.error(str(e))
    return json.dumps(r)


class CiscoCdrCreateLocalDataInputsHandler(PersistentServerConnectionApplication):
    """
    PersistentServerConnectionApplication is undocumented.  There are some vague
    references to this entire part of Splunk's functionality in restmap.conf.spec
    and that's it.   If it weren't for James Ervin's conf2016 talk, nobody outside
    of Splunk would have a clue how to make one of these handlers run.
    """

    def __init__(self, command_line, command_arg):
        """ a shiny new donkey for whoever brings me... wait scratch that."""
        PersistentServerConnectionApplication.__init__(self)

    def validate(self, post_args, session_key):
        # CLEAN THIS UP.
        # have one try / except for all these validations,  then have each raise an exception and the generic except can do a build_response
        if "path" not in post_args:
            raise ValueError("no path supplied")
        try:
            path = post_args.get("path")
            data_inputs = get_matching_data_inputs(path, session_key)

        except Exception as e:
            raise ValueError("Error encountered while looking for existing data inputs " + str(e))

        if data_inputs:
            raise ValueError("We are unable to proceed safely - We have found one or more data inputs already on this Splunk instance that match the files in this path.")

        if "index" in post_args:
            installed_indexes = get_indexes(session_key)

            if post_args.get("index") not in installed_indexes:
                raise ValueError("the index posted does not seem to exist")


        try:
            types = get_file_types(path)
        except OSError as e:
            # http://bugs.python.org/issue6609
            message = "Either this directory does not exist, or the user as which Splunk is running does not have read access here."
            logger.warning("hit an exception getting file types. Most likely - %s", message)
            raise ValueError(message)

        except Exception as e:
            raise ValueError("Unexpected error while checking the path for files. " + str(e))

        if types["cdr"] + types["cmr"] == 0:
            raise ValueError("That path (%s) does exist but it seems to contain no CDR or CMR files whose filenames begin with 'cdr_' or 'cmr_'." % path)


        files_description_message = get_file_types_description_message(path, types)
        return build_response(200, files_description_message)


    def create_data_inputs(self, path, index, session_key):


        logger.info("creating data inputs for files at " + path + " with index=" + index)

        def create_data_input(sourcetype, index, path, wildcard_match):
            entity_name = "batch://" + path + os.path.sep + wildcard_match
            postargs = {
                "name" : entity_name,
                "sourcetype" : sourcetype,
                "index" : index,
                "move_policy" : "sinkhole",
                "crcSalt" : "<SOURCE>"
            }
            getargs = {}
            # TODO - change this to
            # uri = "/services/cisco_cdr/configs/conf-inputs"
            uri = "/servicesNS/nobody/cisco_cdr/configs/conf-inputs"
            serverResponse, serverContent = splunk.rest.simpleRequest(uri, postargs=postargs, getargs=getargs, raiseAllErrors=True, sessionKey=session_key)
            logger.info("created a data input with name " + entity_name)
            if serverResponse.status == 201:
                try:
                    atomFeed = splunk.rest.format.parseFeedDocument(serverContent)
                except Exception as e:
                    logger.error(e)
                return True

        create_data_input("cucm_cdr", index, path, "cdr_*")

        create_data_input("cucm_cmr", index, path, "cmr_*")
        logger.info("success - we created both data inputs")

        return True, "We have successfully created the data inputs, however we need to restart the Splunk Server before they can start indexing."






    def handle(self, in_string):
        """
        the main template method of PersistentServerConnectionApplication
        note that passing a single string arg that is an arbitrary JSON structure
        with unknown inscrutable conventions is apparently the new black.  =|
        #thisisfine
        """
        try:
            params = json.loads(in_string)
            session_key = params["session"]["authtoken"]
            method = params["method"]
            output_mode = params.get("output_mode", "json")

            if method == "GET":
                qs_dict = get_query_args(params)
                if "kill" in qs_dict:
                    logger.warning("explicitly killing the scripttype=persist process.")
                    sys.exit()

                return build_response(400, "this handler doesn't really support GET")

            elif method == "POST":

                post_args = get_multipart_form_args(params)
                action = params['path_info']
                if action == "validate":
                    return self.validate(post_args, session_key)
                elif action == "create":
                    self.validate(post_args, session_key)

                    index = post_args.get("index", "")
                    path = post_args.get("path", "")

                    if not index:
                        raise ValueError("No index was provided.")

                    try:
                        self.create_data_inputs(path, index, session_key)
                        return build_response(200, "We have successfully created the config for the data inputs. Next you will need to restart the Splunk Server to activate them. If you are an admin, click 'Settings' then 'Server Controls' then 'Restart Splunk'")

                    except splunk.AuthorizationFailed as e:
                        return build_response(403, "Unfortunately your user account does not have the 'admin-all-objects' capability in Splunk, which means you cannot use the conf-inputs endpoint.   Proceed creating the data inputs manually as per our docs. Contact Sideview Support for help. We apologize for this inconvenience.")
                return build_response(400, "action not supported - " + action)


            return build_response(405, "Method not allowed (%s)" % method)

        except ValueError as e:
            return build_response(400, str(e))
        except Exception:
            logger.error(traceback.format_exc())
            return build_response(500, traceback.format_exc())
