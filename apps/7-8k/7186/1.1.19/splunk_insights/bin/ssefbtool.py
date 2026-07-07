import splunk.Intersplunk as si
from common import get_sos_server, run_btool
import subprocess
import time
import sys
import os
import re

'''
# !!!!! DEBUG !!!!
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
dbg.enable_debugging(timeout=25)
#################
'''

#dbg.set_breakpoint()
_time=time.time()
sos_server=get_sos_server()

####################################
# main function
####################################
if __name__ == '__main__':
    try:
        
        keywords = []
        argvals = dict()

        if sys.version_info >= (3, 0):
            keywords = [x for x in sys.argv if not re.findall("^\w+=|btool.py$", x)]
            argvals = dict(u.split("=", 1) for u in [x for x in sys.argv if re.findall("^\w+=", x)])
        else :
            keywords = filter(lambda x: not re.findall("^\w+=|btool.py$", x), sys.argv)
            argvals = dict(u.split("=", 1) for u in filter(lambda x: re.findall("^\w+=", x), sys.argv))

        if len(keywords) == 0 and len(argvals) == 0:
            si.generateErrorResults('Requires a conf file name.')
            exit(0)
        
        if len(keywords) == 0 :
            keywords = argvals["conf"].replace('"','').split(",")
        
        results = []
        for conffile in keywords :

            # Handle extra args:  e.g. 'app=learned' becomes --app=learned
            btool_options = []
            #for (opt,arg) in options.items():
            #    btool_options.append("--%s=%s" % (opt, arg))
            btool_args = btool_options + [ conffile, "list-debug" ]
            for (app, stanza, lines) in run_btool(*btool_args):
                results.append({"_raw" : "\n".join(lines),
                                "_time" : _time,
                                "stanza": stanza,
                                "conf": conffile,
                                "app" : app,
                                "sos_server" : sos_server,
                                "source" : "btool",
                                "sourcetype" : "btool",
                                "linecount" : len(lines)})

        si.outputResults(results)

    except Exception as e:
        import traceback
        stack =  traceback.format_exc()
        si.generateErrorResults("Error '%s'. %s" % (e, stack))
