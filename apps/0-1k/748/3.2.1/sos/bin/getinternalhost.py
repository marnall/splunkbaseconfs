import splunk.Intersplunk as si
from common import get_btool_internal_host, get_os_hostname
import time

_time = time.time()

if __name__ == '__main__':
    try:
        btoolHostname = get_btool_internal_host()
        if btoolHostname:
            # Note:  _raw no longer contains the btool output line
            results = [ {"_raw" : btoolHostname, "_time" : _time, "btoolHostname": btoolHostname} ]
        else:
            pythonHostname = get_os_hostname()
            results = [ {"_raw" : pythonHostname, "_time" : _time, "pythonHostname": pythonHostname} ]
        si.outputResults(results)

    except Exception, e:
        import traceback
        stack = traceback.format_exc()
        si.generateErrorResults("Error '%s'. %s" % (e, stack))
