__author__ = 'Levonne Key <levonnekey@gmail.com>'
__license__ = 'Apache License, Version 2.0'

import os, sys
SPLUNK_HOME_PATH = os.environ.get("SPLUNK_HOME")
ROUTR_BIN_PATH = os.path.join(SPLUNK_HOME_PATH, 'etc', 'apps', 'routr', 'bin')

sys.path.append(ROUTR_BIN_PATH)
import routr
routr.TumblrSplunkAlerts().post_tumblr(sys.argv[1], sys.argv[2], sys.argv[3], 
    sys.argv[4], sys.argv[5], sys.argv[6])
