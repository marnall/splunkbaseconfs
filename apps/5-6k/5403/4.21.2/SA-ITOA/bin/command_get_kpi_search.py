# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys

# Core Splunk Imports
import splunk.rest

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path
from itsi.searches.get_kpi_search import KPISearchRetriever
from ITOA.setup_logging import getLogger4SearchCmd

logger, settings, read_results = getLogger4SearchCmd(return_all=True)


def parseArgs():
    '''
    Parse the arguments out, we're expecting only one argument - entity
    '''
    i = 1
    kvargs = {}
    fields = []
    incomplete_kv = None
    while i < len(sys.argv):
        arg = sys.argv[i]
        i += 1
        if arg == "is_debug":
            continue
        else:
            # We are using the fields here to match against the result set
            assignment_op = arg.find("=")
            '''
                We have a kwarg here:  It can take the following forms
                key=value
                key = value
                key= value
                key =value
                ERROR Conditions
                = (no other parameters)
                key=
                =value
                QUESTIONABLE Conditions
                key == value
            '''
            if assignment_op == -1:
                if incomplete_kv is not None:
                    # We had an incomplete kv and now an assignment op
                    if incomplete_kv[:-1] not in kvargs:
                        kvargs[incomplete_kv[:-1]] = [arg]
                    elif arg not in kvargs[incomplete_kv[:-1]]:
                        kvargs[incomplete_kv[:-1]].append(arg)
                    incomplete_kv = None
                    continue
                # No assignment character, add it to the fields list and continue
                fields.append(arg)
                continue
            if assignment_op == 0:
                # We began the string with an equals sign
                if len(fields) == 0:
                    # This will abort our run
                    splunk.Intersplunk.parseError("Incomplete key-value pair found. Must specify a key.")
                if arg.rfind("=") != 0:
                    splunk.Intersplunk.parseError("Double equal signs found. Must fix your query.")
                key = fields.pop()
                if len(arg) == 1:
                    # We have something like key = value, save this as an incomplete kv
                    incomplete_kv = key + arg
                    continue
                else:
                    # We have something like this key =value
                    if key not in kvargs:
                        kvargs[key] = [arg[1:]]
                    elif arg[1:] not in kvargs[key]:
                        kvargs[key].append(arg[1:])
                continue
            if assignment_op == len(arg) - 1:
                # The only equals sign was at the very end of the string
                incomplete_kv = arg
                continue
            # The first assignment op was somewhere in the middle of the string.  Check for dupes
            if assignment_op != arg.rfind("="):
                splunk.Intersplunk.parseError("Double equal signs found. Must fix your query.")
            # Only one assignment operator
            pargs = arg.split("=")
            if pargs[0] in kvargs:
                kvargs[pargs[0]].append(pargs[1])
            else:
                kvargs[pargs[0]] = [pargs[1]]
    if incomplete_kv is not None:
        splunk.Intersplunk.parseError("Incomplete key-value pair found. Must fix your query.")

    return {'kvargs': kvargs}


args = parseArgs()

is_debug = False
kvArgsObj = args['kvargs']
if 'is_debug' in kvArgsObj:
    val = kvArgsObj['is_debug']
    if len(val) > 0 and val[0] == 'True':
        is_debug = True

results = []
sr = None
try:
    sr = KPISearchRetriever(read_results, settings, args, is_debug)
    logger.error("args into command [get_kpi_search] - %s, is_debug = %s", args, is_debug)
    results = sr.execute()
except Exception as e:
    if sr is not None:
        sr.logger.exception(e)
    results = splunk.Intersplunk.generateErrorResults(e)
finally:
    # Output results
    sr.logger.debug(results)
    splunk.Intersplunk.outputResults(results)
