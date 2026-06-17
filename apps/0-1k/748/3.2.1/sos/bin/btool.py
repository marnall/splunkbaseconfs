import splunk.Intersplunk as si
from common import get_sos_server, run_btool
import subprocess
import time

_time=time.time()
sos_server=get_sos_server()

####################################
# main function
####################################
if __name__ == '__main__':
    try:
        keywords,options = si.getKeywordsAndOptions()
        if len(keywords) == 0:
            si.generateErrorResults('Requires a conf file name.')
            exit(0)
        conffile = ' '.join(keywords)

        # Handle extra args:  e.g. 'app=learned' becomes --app=learned
        btool_options = []
        for (opt,arg) in options.items():
            btool_options.append("--%s=%s" % (opt, arg))
        btool_args = btool_options + [ conffile, "list-debug" ]
        results = []
        for (app, stanza, lines) in run_btool(*btool_args):
            results.append({"_raw" : "\n".join(lines),
                            "_time" : _time,
                            "stanza": stanza,
                            "app" : app,
                            "sos_server" : sos_server,
                            "source" : "btool",
                            "sourcetype" : "btool",
                            "linecount" : len(lines)})
        si.outputResults(results)

    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        si.generateErrorResults("Error '%s'. %s" % (e, stack))


