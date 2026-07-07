# Copyright (C) 2010-2025 Sideview LLC.  All Rights Reserved.
"""
If your use of this app is through the Sideview Trial License Agreement,
or through the Sideview Internal Use License Agreement, then as per the
relevant agreement any modification of this file or modified copies made
of this file constitutes a violation of that agreement.
"""

import os
import sys
import json
import traceback
import splunk

APP = "SA_cisco_cdr_axl"

# the capabilities that we check for before we allow the user to update AXL credentials.
# NOTE that the user just needs any one of these capabilities, and not all of them together.
# NOTE the first 4 are only on admin by default.  edit_sourcetypes is power though.
SUFFICIENT_CAPABILITIES_FOR_CREDENTIAL_UPDATE = ["admin_all_objects", "license_edit", "edit_local_apps", "edit_monitor", "indexes_edit", "edit_sourcetypes"]

# boo.  splunk forgot to put the bin directory for CURRENTAPP into sys.path.
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'], "etc", "apps", APP, "bin"))
import axl_shared as axl


if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

from splunk.persistconn.application import PersistentServerConnectionApplication

logger = axl.get_logger()


def build_response(status, message, output_mode="xml", payload=None):
    """ worker method to make headers and payloads and status etc."""
    response_dict = {}
    response_dict["status"] = status

    if 400 > status >= 200:
        if not payload:
            payload = {}
            payload["success"] = True
            if message:
                payload["messages"] = [{"text":message}]
        # nope.  you really really, cannot ever set this, or the rest command dies.
        #response_dict["headers"] = {"Content-Type": "application/json"}
    else:
        assert not payload
        payload = {}
        payload["success"] = False
        if message:
            payload["messages"] = [{"text":message}]
    response_dict["payload"] = payload

    #I hate this...but
    # a) I don't want to actually implement the silly atom feed response type.
    # b) if we just ignore the output_mode=xml case (that the rest command submits),
    #    AND we just dont return any Content-Type header at all to the poor rest command
    #    then... it seems to give up, just present the json string, and gives no errors.
    #    if otoh we give them a Content Type header,  EVEN IF ITS "xml",
    #    then the rest command fails completely.
    if output_mode != "xml":
        content_type = "application/json"
        response_dict["headers"] = {"Content-Type": content_type}

    #logger.error("response params are")
    #logger.error(json.dumps(response_dict, indent=4, sort_keys=True))

    return response_dict


def authorized_to_edit_credentials(session_key):
    """ time to see if this person is allowed to come in here where we make the donuts"""
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
        if capability in SUFFICIENT_CAPABILITIES_FOR_CREDENTIAL_UPDATE:
            return True
    return False

def get_post_args(form_arr):
    """ life is too short. turn stupid array into a dict. """
    out = {}
    for arr in form_arr:
        out[arr[0]] = arr[1]
    return out

def get_query_args(params):
    """ life is too short. turn stupid array into a dict. """
    out = {}
    if "query" not in params:
        return out
    query_arr = params["query"]
    for pair in query_arr:
        out[pair[0]] = pair[1]
    return out

class CiscoAxlAdminHandler(PersistentServerConnectionApplication):
    """ This is basically a wrapper for the core conf-ciscoaxl endpoint, but with the
    important addition that it also wraps the passwords.conf functionality.  in other words
    it writes the password field to the passwords.conf stanza as appropriate. """

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle_get(self, stanza_name, session_key, output_mode, qs_dict):
        """ Getting either a single credential, or a list of all of them. """

        # just a trick to let us restart the persistent process in between
        # code changes (during development).
        if "kill" in qs_dict:
            logger.warning("some development-only code is active and is about to kill this scripttype=persist process.")
            sys.exit()
        if stanza_name:
            logger.info("looking for stanza %s", stanza_name)
            try:
                connections = axl.get_connection(stanza_name, session_key)
            except splunk.ResourceNotFound:
                return build_response(404, "stanza %s not found" % stanza_name, output_mode)
        else:
            connections = axl.get_active_connections(session_key)
        return build_response(200, False, output_mode, connections)


    def handle_post(self, stanza_name, session_key, output_mode, post_args):
        """ note that we don't save the port information in thepassword store, just the hostname."""

        host = stanza_name.split(":")[0]
        user = stanza_name.split(":")[2]

        logger.info("saving new password information for host=%s user=%s", host, user)

        password = post_args["password"]

        try:
            axl.get_connection(stanza_name, session_key)
        except splunk.ResourceNotFound as e:
            if axl.create_connection(stanza_name, session_key):
                axl.set_password(host, user, APP, session_key, password)
                return build_response(200, "created new stanza", output_mode)

        if axl.update_connection(stanza_name, session_key):
            axl.set_password(host, user, APP, session_key, password)
            return build_response(200, False, output_mode)
        return build_response(500, "failed to update user", output_mode)



    def handle(self, in_string):
        """ this is the one relevant method in splunk's base class."""
        try:
            # Because passing a single argument that is an arbitrary JSON structure
            # with unknown conventions is apparently the new black.  =|
            params = json.loads(in_string)
            #logger.error("input params are")
            #logger.error(json.dumps(params, indent=4, sort_keys=True))
            session_key = params["session"]["authtoken"]
            method = params["method"]
            output_mode = params["output_mode"]

            try:
                stanza_name = params["path_info"].split('/', 1)[0]
            except KeyError as e:
                stanza_name = False

            if stanza_name and stanza_name.find("%20")!=-1:
                return build_response(400, "spaces are not allowed because such stanzas cannot be saved in the Splunk password store", output_mode)

            if method == "GET":
                qs_dict = get_query_args(params)
                return self.handle_get(stanza_name, session_key, output_mode, qs_dict)

            if method == "POST":
                post_args = get_post_args(params["form"])

                if authorized_to_edit_credentials(session_key):

                    if params.get("system_authtoken", False):
                        #logger.warning("we secretly replaced the office coffee with Mildred's Medically Inadvisable Caffeine Crystals")
                        session_key = params.get("system_authtoken")
                    else:
                        logger.info("passSystemAuth appears to have been set to False in local restmap.conf configuration. This means that when creating/editing/deleting any credentials from ciscoaxl.conf, the handler will use the user's session key to apply the license, which in turn means it will only work if that user has the \"admin-all-objects\" capability.")
                else :
                    return build_response(403, "Sorry - your Splunk user account does not have any of the capabilities that are set as the minimum to use this page.  One potentially quick fix is to ask your admins to make you a power user.", output_mode)

                if post_args.get("action", False) == "delete":
                    if axl.delete_connection(stanza_name, session_key):
                        return build_response(200, "credential deleted", output_mode)
                    return build_response(500, "unable to delete credential", output_mode)

                return self.handle_post(stanza_name, session_key, output_mode, post_args)

        except splunk.AuthorizationFailed as e:
            return build_response(403, traceback.format_exc(), output_mode)

        except Exception as e:
            logger.error(traceback.format_exc())
            return build_response(500, traceback.format_exc(), output_mode)
