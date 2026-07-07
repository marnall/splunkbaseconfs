__author__ = 'Levonne Key <levonnekey@gmail.com>'
__license__ = 'Apache License, Version 2.0'

import os, sys
SPLUNK_HOME_PATH = os.environ.get("SPLUNK_HOME")
ROUTR_BIN_PATH = os.path.join(SPLUNK_HOME_PATH, 'etc', 'apps', 'routr', 'bin')
os.environ['REQUESTS_CA_BUNDLE'] = os.path.join(ROUTR_BIN_PATH, 'cacert.pem')

sys.path.append(ROUTR_BIN_PATH)
import routr
routr.TweetSplunkAlerts().post_tweet(sys.argv[4], sys.argv[6])
