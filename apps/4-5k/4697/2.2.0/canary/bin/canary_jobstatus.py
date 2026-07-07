# -*- coding: utf-8 -*-
import json
import logging
import os
import requests
import sys
import traceback

if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

APP = "canary"
SPLUNK_HOME = os.environ.get("SPLUNK_HOME")

if SPLUNK_HOME:
    import splunk
    from splunk.persistconn.application import PersistentServerConnectionApplication
    try:
        import canary_util
    except ImportError:
        sys.path.insert(1,os.path.join(SPLUNK_HOME, "etc", "apps", APP, "bin"))
        import canary_util
else:
    # base class offers zero help with actually handling the request, so when
    # in flask we don't need it.
    class PersistentServerConnectionApplication:
        pass


import sideview_canary as sv
import canary_request

logger = sv.setup_logging(logging.DEBUG)

class BadRequest(Exception):
    def __init__(self, message):
        self.status = 400
        self.message = message
    def __str__(self):
        return repr("status %s - %s" % (self.status, self.message))

def get_query_args(params, key="query"):
    """ just processing the inscrutable struct into more useful args"""
    out = {}
    if key not in params:
        return out
    query_array = params[key]
    for getarg, value in query_array:
        # simple non-repeat case
        if not getarg in out:
            out[getarg] = value
        # handle repeats
        else:
            oldval = out[getarg]
            # could already be a list
            if isinstance(oldval, list):
                oldval.append(value)
            # or we could be creating the list
            else:
                out[getarg] = [oldval, value]
    return out



class JobStatusHandler(PersistentServerConnectionApplication):
    """
    Return commonly used elements from the Job Status endpoint ../api/serach/jobs without
    flooding the browser with many megabytes of json it isn't interested in.

    Contract is to mirror the jobs endpoint, which means:

    Part 1
    - if a search ID (sid) is provided, return info for that.
    - else if no search ID 9sid) is provided, return info for whatever the jobs endpoint returns by default.

    Part 2:
    - if a keylist (kl) is provided, return those keys & values from the
      entry[0].content dict/object that are reuqested in the returned json.
      in other words, if kl=a,b, return { a : value_of_a, b : value_of_b }
    - if a keylist is omitted, return the typically useful fields from the job:
      isDone, isFailed, isFinalized, isPaused, isZombie

    """

    def __init__(self, command_line, command_arg):
        """ idk what they created the extra 2 args for, but the base class doesn't accept them. """
        PersistentServerConnectionApplication.__init__(self)


    def handle(self, in_string):
        """ time to make the hamburgers """

        # default set of keys to return
        keylist = ["dispatchState","doneProgress","earliestTime","eventAvailableCount","eventCount","isDone","isFailed","isFinalized","isPaused","isPreviewEnabled","isSaved","isSavedSearch","isZombie","latestTime","resultCount","resultPreviewCount","runDuration","scanCount"]

        #housekeeping.
        params = json.loads(in_string)
        qs_dict = get_query_args(params)
        request = canary_request.SplunkRequest(params)

        # if a sid was requested it will be expressed here.. canary_jobstatus/sid
        path_info = params.get("path_info")

        if "kl" in qs_dict:
            keylist = qs_dict["kl"].split(",")


        # aha.  we don't actually get to see output_mode in the raw qs_dict, because it is magic
        # and gets sneakily removed from there maybe because enforcement is actually handled by
        # the restmap.conf machinery.
        # and it is present at the root of the inscrutable wob in_string, blessed be her wobbiness.
        #if qs_dict.get("output_mode", "json") != "json":
        #    raise BadRequest("only output_mode=json is supported")

        # when calling underlying jobs endpoint, pass along all the args we don't know about
        filtered_getargs = qs_dict.copy()
        if "kl" in filtered_getargs:
            del filtered_getargs["kl"]
        #however, output_mode isn't there because it is a magic restmap.conf key, so.. put it back.
        filtered_getargs["output_mode"] = "json"

        # sid is always gonna be necessary.
        # likewise messages.  accidentally filtering out error messages would be bad.
        for key in ["sid","messages"]:
            if not key in keylist:
                keylist.append(key)


        # talk to jobs endpoint
        jobs_url = "/services/search/jobs"
        if path_info:
            jobs_url += "/" + path_info
        jobs_url = request.build_splunkd_mgmt_url(jobs_url)

        try:
            # previously we used a modified session object that jrod wrote,  that had the
            # semi-impossible mission of identifying and working with the splunk default cert
            # but still verifying every OTHER cert that came to it. just to make appinspect happy.
            # they changed appinspect to not require this, so I (ncm) went and killed it all.
            with requests.Session() as session:

                headers = { 'Authorization' : f'Splunk {request.session_key}',
                            'Accept' : '*/*',
                }
                response = session.get(jobs_url,  headers=headers, params=filtered_getargs, verify=False)

                if response.status_code != 200:
                    return {
                        "status" : response.status_code,
                        "payload": response.text,
                    }

                # for simplicity, we're going to prune job_json_data in place.
                job_json_data = response.json()

                def pruned_jobcontent_dict(job_data, keylist):
                    return { k : job_data[k] for k in job_data.keys() if k in keylist }

                for entry in job_json_data["entry"]:
                    new_content = pruned_jobcontent_dict(entry["content"], keylist)
                    entry["content"] = new_content

                return {
                    "headers": {"Content-Type": "application/json"},
                    "payload": json.dumps(job_json_data),
                }

        except Exception as e:
            return {
                "status" : 500,
                "payload": traceback.format_exc(),
            }
