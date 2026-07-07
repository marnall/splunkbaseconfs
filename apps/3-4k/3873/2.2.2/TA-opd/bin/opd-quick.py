import sys
from subprocess import Popen, PIPE
import os

try:
    del os.environ["LD_LIBRARY_PATH"]
except KeyError:
    pass
path = os.path.join(os.environ["SPLUNK_HOME"], "etc", "apps", "TA-opd", "bin", "opd.py")
args = ['python', path, "--quick"] + sys.argv[1:]
p = Popen(args, stdin=sys.stdin)
p.communicate()
