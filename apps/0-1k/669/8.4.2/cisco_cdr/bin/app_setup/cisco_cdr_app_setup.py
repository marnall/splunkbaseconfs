# Copyright (C) 2013-2025 Sideview LLC.  All Rights Reserved.
"""
This is currently implemented as a "scripted input" and the air quotes are
because it is designed to never return any data, and thus never actually
input any indexed data to splunk.
Instead we rely in the interval=-1 functionality in inputs.conf to run
this script reliably on every splunk restart.

Thus on every restart this script can do FTR (first-time-run) things
and for customers and prospects who are updating to a newer version, we can
catch migration cases here and do some amount of health checking and logging.

"""

import sys
import os
import traceback
import logging

import app_setup_functions

APP = "cisco_cdr"
SPLUNK_HOME = os.environ["SPLUNK_HOME"]




logger = app_setup_functions.setup_logging(logging.INFO)


"""
# A possible direction we could take, instead of our current
#     `|inputlookup foo | magic | outputlookup foo` approach.
#  APPARENTLY this works with SHC.... but the tempfile approach just looks
# like it's gonna trigger various appinspect/vetting hammers so... i'm hesitant.
# shipping it here just so we can test it out someday later.

def save_lookup(self, filename, rows, fieldnames=None):
    stagingdir = os.path.join(os.environ["SPLUNK_HOME"], "var", "run", "splunk", "lookup_tmp")
    stagingpath = os.path.join(stagingdir, filename)

    try:
        os.makedirs(stagingdir)
    except Exception as e:
        logger.error("Exception while trying to make temp folder for temp lookup. Likely a permissions problem.")
        logger.error(traceback.format_exc(e))

    if fieldnames is None:
        fieldnames = rows[0].keys()

    with open(stagingpath, "w") as f:
        c = csv.DictWriter(f, fieldnames=fieldnames)
        c.writeheader()
        c.writerows(rows)

    path = splunk.entity.buildEndpoint(
        ["data", "lookup-table-files"],
        entityName=filename,
        namespace="myAppName,
        owner="nobody",
    )

    splunk.rest.simpleRequest(
        path,
        sessionKey=self.sessionKey,
        postargs={"eai:data": stagingpath},
        method="POST"
    )
"""


def main():
    session_key = False
    for line in sys.stdin:
        session_key = line

    if not session_key:
        logger.error("For some reason the %s_app_setup.py script did not receive a session_key on stdin. check whether passauth is set to true in inputs.conf.", APP)

    elif app_setup_functions.is_rest_api_responding(session_key):
        try:
            app_setup_functions.run_migration_and_ftr_checks(session_key)

        except Exception as e:
            logger.error("Unexpected exception %s\n", str(e), traceback.format_exc())

main()
