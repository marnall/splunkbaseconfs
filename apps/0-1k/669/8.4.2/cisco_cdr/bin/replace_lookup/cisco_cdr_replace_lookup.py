# Copyright (C) 2010-2025 Sideview LLC.  All Rights Reserved.
"""
 This implements a scripttype=persist endpoint that runs in Splunk
"""

import os
import sys
import json
import traceback
import logging
import email
import urllib.parse
import csv
import random
import re
import io
import tempfile


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

#class CustomFieldStorage(cgi.FieldStorage):
#    def make_file(self, binary=None):
#        return tempfile.TemporaryFile("wb+")

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


def build_response(status, message):
    """ worker method to send back the given response to the client """
    response = {}
    response["status"] = status

    payload = {}
    payload["success"] = 200 <= status < 400

    if message:
        payload["messages"] = [{"text":message}]
    response["payload"] = payload

    # nope.  you really really, cannot ever set this, or the rest command dies.
    #response["headers"] = {"Content-Type": "application/json"}

    content_type = "application/json"
    response["headers"] = {"Content-Type": content_type}

    #logger.error("response params are")
    #logger.error(json.dumps(response, indent=4, sort_keys=True))

    return response

def get_tuple_as_dict(n_by_2_array):
    """ just convert the N x 2 array into a dict. One might ask why it wasn't
    in that format already..."""
    out = {}
    for pair in n_by_2_array:
        assert len(pair) == 2
        out[pair[0]] = pair[1]
    return out

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
            val = data if re.search(r"filename=", disposition) else data.decode("utf-8")
            if name == "lookupFile":
                if isinstance(val, str):
                    raise ValueError("lookupFile provided is not a file but a simple string")
                val = io.StringIO(val.decode("utf-8"))
            out[name] = val
        return out

    parsed = urllib.parse.parse_qs(payload, keep_blank_values=True)
    return {k: v[0] for k, v in parsed.items()}


def get_query_args(params):
    """even more parsing of the inscrutable json-formatted string
    that was passed as the sole arg to handle.  Because reasons."""
    if "query" not in params:
        return {}
    #logger.error(params.get("query"))
    return get_tuple_as_dict(params.get("query", []))


def is_shc(session_key):
    """ returns True if this instance is in a Search Head Cluster."""
    uri = "/services/shcluster/captain/info"
    try:
        _response, _content = splunk.rest.simpleRequest(uri, sessionKey=session_key, method='GET',
                                  raiseAllErrors=True)
        #logger.error(_content)
        #logger.error(_response)
        return True

    # We make a strange assumption, that a 403 returned, means that the
    # feature we're trying to access is actually there.
    # from some testing, it seems if the node is NOT in a SHC, then you
    # get a 503 not a 403
    except splunk.AuthorizationFailed as e:
        logger.info("shcluster endpoint raised AuthorizationFailed with status %s", e.statusCode)
        if e.statusCode == 403:
            return True
        #All other statuses are unexpected. re-raise.
        raise

    except splunk.RESTException as e:
        logger.info("shcluster endpoint raised RESTException with status %s", e.statusCode)
        if e.statusCode == 503:
            return False
        #All other statuses are unexpected. re-raise.
        raise

def handle_get(qs_dict):
    """ time to serve the donuts """
    try:
        # just a trick to let us restart the persistent process in between
        # code changes (during development).
        if "kill" in qs_dict:
            logger.warning("explicitly killing the scripttype=persist process.")
            sys.exit()
    except Exception:
        logger.error(traceback.format_exc())
        return build_response(500, traceback.format_exc())
    return build_response(200, "Hello human. Nothing is really returned from this handler for GET. perhaps you meant POST?")

def modify_acl(session_key, user):
    """ time to make the donuts world-readable (world-eatable?) """
    uri = "/servicesNS/nobody/%s/configs/conf-sideview_license/%s/acl"  % (APP, APP)
    post_args = {"perms.write": "admin", "perms.read":  "*", "sharing": "app", "owner": user}
    splunk.rest.simpleRequest(uri,
                              sessionKey=session_key,
                              postargs=post_args,
                              method='POST',
                              raiseAllErrors=True)

def get_existing_file_info(session_key, namespace, user, lookup_name):
    """ ask Splunk what it thinks about all this"""
    url = 'data/lookup-table-files'


    if not lookup_name.endswith(".csv"):
        lookup_name = lookup_name + ".csv"
    existingEntity = en.getEntity(url, lookup_name, namespace=APP, owner=user, sessionKey=session_key)
    return existingEntity["eai:data"], existingEntity["eai:acl"]

def is_csv(lookup_file):
    try:
        _dialect = csv.Sniffer().sniff(lookup_file.read(1024))
        lookup_file.seek(0)
        return True
    except csv.Error:
        return False

def delete_file_if_exists(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)


def handle_post(session_key, user, post_args):
    """ time to secretly replace the donuts """

    for required_arg in ["lookupFile","lookupName"]:
        if not required_arg in post_args:
            return build_response(500, "makes no sense, but there's no %s arg in the post args" % required_arg)

    lookup_file = post_args.get("lookupFile")
    lookup_name = post_args.get("lookupName")
    #current_view = post_args.get("currentView")

    if not re.match(r"^[a-zA-Z0-9_-]+$", lookup_name):
        return build_response(400, "Lookup file name provided is not valid")


    existing_file_path, existing_file_acl = get_existing_file_info(session_key, APP, user, lookup_name)

    if sys.platform == "win32" and existing_file_acl and existing_file_acl.get("sharing") == "user":
        return build_response(401, "Due to some permissions problems with how Splunk writes to non-shared lookup files, we cannot reupload this lookup.  First use the 'Permissions' link in Manager to share this lookup with all users of the given app and then try again.")

    if not is_csv(lookup_file):
        return build_response(400, "That... really doesn't look like a csv file")


    temp_file_path, error = create_temp_lookup(lookup_file, lookup_name, existing_file_path)

    if not temp_file_path:
        return build_response(500, "Unable to write temp file to the relevant lookup directory: " + str(error))

    try:
        existing_header_row = get_header_row(existing_file_path)
    except Exception as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return build_response(500, "Something went wrong when we tried to get the header row of the existing lookup file: " + str(e))

    try:
        new_header_row = get_header_row(temp_file_path)
    except Exception as e:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        logger.error(e)
        logger.error(traceback.format_exc())
        return build_response(500, "Something went wrong when we tried to get the header row of the temporary file: " + str(e))

    existing_header_row.sort()
    new_header_row.sort()

    if ",".join(existing_header_row) != ",".join(new_header_row):
        logger.warning("old header row and new header row do not match old is %s and new is %s", existing_header_row, new_header_row)
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        return build_response(500, "The column names on the csv you are uploading do not match the column names on the existing lookup that is in place. You will have to delete and recreate the lookup in Manager.  (old columns are %s and new are %s)" % (existing_header_row, new_header_row))


    # if somehow there's an old file lingering from a failed previous attempt.
    delete_file_if_exists(existing_file_path+".bak")

    # move the old file out of the way and only delete it after.
    try:
        os.rename(existing_file_path, existing_file_path+".bak")
    except FileNotFoundError as e:
        logger.error(e)
        logger.error(traceback.format_exc())

    os.rename(temp_file_path, existing_file_path)

    delete_file_if_exists(temp_file_path)

    delete_file_if_exists(existing_file_path+".bak")
    message = "The %s lookup has been successfully updated" % lookup_name
    logger.info(message)


    file_name =  os.path.basename(existing_file_path)
    try:
        status, content = force_shc_replication_for_lookup(APP, file_name, session_key)
    except Exception as e:
        logger.error("Unexpected error received when we tried to force shc replication for this lookup file %s", file_name)
        logger.error(traceback.format_exc())


    return build_response(200, message)


def get_header_row(file_path):
    """ just grab the first row"""
    with open(file_path, "r") as f:
        reader = csv.reader(f)
        try:
            return reader.next()
        except AttributeError:
            return next(reader)
    return []


def create_temp_lookup(lookup_file, lookup_name, existing_file_path):
    """ write to a temp file first, and then after this returns, the
    calling code will do a rename to move the temp file over the real file"""
    temp_file_name = lookup_name + str(random.random())[1:]
    try:
        existing_lookup_dir, _existing_lookup_file = os.path.split(existing_file_path)
    except Exception as e:
        return False, "error determining existing lookup path " + str(e)

    try:
        line = lookup_file.readline()
        if not line:
            return False, "The file you have uploaded seems to be empty."

        temp_file_path = os.path.join(existing_lookup_dir, temp_file_name)

        dest_dir_normalized = os.path.dirname(os.path.normpath(temp_file_path))
        lookup_dir_normalized = os.path.normpath(existing_lookup_dir)
        if dest_dir_normalized != lookup_dir_normalized:
            return False, 'Something went wrong with the lookup names. Does your lookup name perhaps contain slashes, backslashes, or a "../"?'

        if os.path.exists(temp_file_path):
            return False, 'This should never occur but it did. Our randomly generated filename collided with an existing file. Try again.'

        with open(temp_file_path, "w") as f:
            f.write(line)
            for line in lookup_file:
                f.write(line)

        return temp_file_path, ""

    except Exception as e:
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        except:
            pass
        return False, "Unknown exception creating temp lookup file " + str(e) + ", " + traceback.format_exc()


def force_shc_replication_for_lookup(app, filename, session_key):
    """
    notify the Search Head Cluster that this particular lookup file needs to be replicated now.
    """

    uri = "/services/replication/configuration/lookup-update-notify"

    args = {
        "app": app,
        "filename": os.path.basename(filename),
        "user": "nobody",
    }

    response, content = splunk.rest.simpleRequest(uri, method="POST", postargs=args, sessionKey=session_key, raiseAllErrors=False)

    if response.status == 400:
        if "Could not find lookup_table_file" in content:
            logger.error("lookup replication not triggered because Splunk could not find the file. filename=%s, app=%s, status_code=%s, content=\"%s\"",
                         filename, app, response.status, content)

        elif "No local ConfRepo registered" in content:
            logger.info("lookup replication not triggered for %s, because this is not an SHC", filename)

        else:
            logger.error("lookup replication not triggered. filename=%s, app=%s, status_code=%s, content=\"%s\"",
                         filename, app, response.status, content)
    elif response.status == 200:
        logger.info("Splunk notified that a lookup file needs to be replicated (only relevant if this is an SHC). filename=%s, app=%s", filename, app)

    else :
        logger.error("Unexpected response to our lookup replication notification. filename=%s, app=%s, status_code=%s, content=\"%s\"",
                 filename, app, response.status, content)

    return (response.status, content)




class CiscoCdrReplaceLookupHandler(PersistentServerConnectionApplication):
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
            #logger.debug("input params are")
            #logger.debug(json.dumps(params, indent=4, sort_keys=True))
            session_key = params["session"]["authtoken"]
            user = params["session"]["user"]
            method = params["method"]


            qs_dict = get_query_args(params)

            if method == "GET":
                return handle_get(qs_dict)

            if method == "POST":
                # in 6.3.9 and before we worried about SHC here and prevented
                # people from posting changes to the SHC member. Our reasoning
                # was that the changes might be obliterated with the next push
                # from the deployer.
                # In 6.3.10 we put deployer_lookups_push_mode = always_preserve
                # into app.conf effectively preventing the deployer from EVER
                # overwriting the live lookups,  so now we allow this again.
                #shc_session_key = params.get("system_authtoken", session_key)
                #if is_shc(shc_session_key):
                #    return build_response(405, CANT_POST_ON_SHC_ERROR)

                post_args = get_multipart_form_args(params)
                return handle_post(session_key, user, post_args)

            return build_response(405, "Method not allowed (%s)" % method)
        except UnicodeDecodeError as e:
            logger.error(traceback.format_exc())


            # this is essentially bonus and rather than trying to make the logic perfect, if it hits any exception
            # it just gives up trying to tell the user the position and offending character.
            try:
                message = str(e)
                regex = re.compile(r"decode byte (?P<byte>0x\S+) in position (?P<position>\d+): invalid (start|continuation) byte")
                match = re.search(regex, message)

                keys = match.groupdict()
                position = keys.get("position", "unknown")
                logger.info("A non UTF8 character was encountered at position %s of a file uploaded. Returning error message to the user." % position)

                start=int(position)-10
                end=int(position)+10
                return build_response(400, "Error decoding file as UTF-8.  There is an escape sequence in the file. FIRST make sure that when you created this file, it was saved with UTF-8 encoding and not ascii encoding. If it was saved with UTF-8 encoding, then you can find the first escaped character(s) at position %s . look carefully at this section: %s \n\nContact Sideview Support if you need more help." % (position, in_string[start:end]))

            # ok whatever just bail out and tell them it's a problem with the file.
            except Exception as f:
                logger.info("The user uploaded a csv file with a non UTF8 character in it. Returning error message to the user.")
                return build_response(400, "Somewhere in this file there is at least one non-UTF8 character. Look carefully for strange 'smart quote' characters or 'smart apostrophes'. Contact Sideview Support if you need more help.")

        except Exception:
            logger.error(traceback.format_exc())
            return build_response(500, traceback.format_exc())


