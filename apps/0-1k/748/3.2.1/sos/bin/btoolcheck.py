import splunk.Intersplunk as si
from common import get_sos_server
import subprocess, re, time, socket

_time=time.time()
sos_server=get_sos_server()

####################################
# main function
####################################
if __name__ == '__main__':

    try:
        pseudohandle = subprocess.Popen(["btool", "check"], shell=False, stdout=subprocess.PIPE)
        stdout = pseudohandle.communicate()
        
        results = []
        lines = stdout[0].split("\n")
        
        for line in lines:
            typoMatch = re.match(r"^Possible typo in stanza (\[[^\]]*\]) in ([^,]*), line (\d+): ([\S]*)\s*=\s*([^\v]*)", line)
            if typoMatch:
                results.append({"_raw": line, "_time": _time,
                                "sos_server": sos_server,
                                "stanza": typoMatch.group(1),
                                "fpath": typoMatch.group(2),
                                "line": typoMatch.group(3),
                                "key": typoMatch.group(4),
                                "value": typoMatch.group(5)})

        si.outputResults(results)

    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        si.generateErrorResults("Error '%s'. %s" % (e, stack))
