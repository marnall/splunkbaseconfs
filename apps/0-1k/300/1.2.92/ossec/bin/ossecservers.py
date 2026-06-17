#!/opt/splunk/bin/python
############################################################
#
# List all servers configured for remote management
#
# This may be a different list than that contained in the
# lookup table within the application, as it references
# configuration options directly.
#
# Needed to drive lookup tables and especially dropdown
# boxes for agent management screens.
#
############################################################
import sys
import splunk.Intersplunk as si
from pyOSSEC import *


try:
    results = []
    cfg = parse_config()
    for server in cfg:
        row = {
            'ossec_server':  server
        }

        if 'MANAGE_AGENTS' in cfg[server]:
            row['managed'] = 1
        else:
            row['managed'] = 0


        results.append(row)

except:
    import traceback
    stack = traceback.format_exc()
    results = si.generateErrorResults("Error : Traceback: " + str(stack))

si.outputResults(results)
