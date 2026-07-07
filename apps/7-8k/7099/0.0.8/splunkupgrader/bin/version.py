import os, glob
import re
from time import sleep

def version():
    path = os.path.join(os.getenv('SPLUNK_HOME'), 'etc', 'apps', 'splunkupgrader', 'bin')
    file = glob.glob("{}/*.tgz".format(path))[-1]
    splunk_version = re.search(r"splunk-([^\-]+)-", file)[1]
    splunk_version = str(splunk_version)
    return splunk_version

