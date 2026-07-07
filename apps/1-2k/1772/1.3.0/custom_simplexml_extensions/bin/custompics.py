#
#   Copyright 2014 by mathias herzog, <mathu at gmx dot ch>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import os
import csv
import sys
import splunk.Intersplunk
import string

# configure logging
import logging
from logging.handlers import RotatingFileHandler
def setup_logging():
   """ initialize the logging handler """
   logger = logging.getLogger('splunk.custom-examples')
   SPLUNK_HOME = os.environ['SPLUNK_HOME']

   LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
   LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
   LOGGING_STANZA_NAME = 'python'
   LOGGING_FILE_NAME = "custom-examples.log"
   BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
   LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
   splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a')
   splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
   logger.addHandler(splunk_log_handler)
   splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
   return logger

logger = setup_logging()

# get search results and settings
results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
# clear results as we don't need them
results = []

# initialize Splunk directory paths
splunk_home = splunk.Intersplunk.splunkHome()
app_name = settings.get('namespace')
logger.debug("namespace: %s" % app_name)
app_dir =  os.path.join(sys.path[0],"../..")
logger.debug("app_dir: %s" % app_dir)
app_path = "%s/%s" % (app_dir,app_name)
logger.debug("app_path: %s" % app_path)

i = 1
while i<len(sys.argv):
  image_path = "%s/appserver/static/%s" % (app_path, sys.argv[i])
  logger.debug("image_path: %s" % image_path)

  try:
    for dirname, dirnames, filenames in os.walk(image_path):
      for filename in filenames:
        fields = {}
        url = "/static/app/%s/%s/%s" % (app_name, sys.argv[i],filename)
        logger.debug("url: %s" % url)
        fields["url"] = url
        results.append(fields)
  except:
    e = sys.exc_info()
    logger.error("error wile reading directory: %s" % image_path)
    logger.error(e)
    splunk.Intersplunk.parseError("error while reading: %s" % image_path)

  i += 1

# finally return results to Splunk
splunk.Intersplunk.outputResults(results)