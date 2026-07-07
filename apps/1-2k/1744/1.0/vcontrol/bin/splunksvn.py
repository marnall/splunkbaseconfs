#!/appl/splunk/bin/python
"""
This scripts implements splunk svn functionality

@author: Mathias Herzog, <mathu at gmx dot ch>

@license:
Copyright 2014 by mathias herzog, <mathu at gmx dot ch>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import sys
import os
import commands
import optparse
import signal
import splunklib.client as client

import splunk
import splunk.Intersplunk
import splunk.entity
import splunk.auth as auth

import logging
from logging.handlers import RotatingFileHandler

from util import *

def setup_logging():
   """ initialize the logging handler """
   logger = logging.getLogger('splunk.svn')    
   SPLUNK_HOME = os.environ['SPLUNK_HOME']
          
   LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
   LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
   LOGGING_STANZA_NAME = 'python'
   LOGGING_FILE_NAME = "svn.log"
   BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
   LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
   splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a') 
   splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
   logger.addHandler(splunk_log_handler)
   splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
   return logger

logger = setup_logging()

def signalHandler(signum, frame):
  """Exits when called, used to handle all signals."""
  sys.exit(0)

def optional_arg(arg_default):
  """handle optional script input arguments"""
  def func(option,opt_str,value,parser):
    if parser.rargs and not parser.rargs[0].startswith('-'):
      val=parser.rargs[0]
      parser.rargs.pop(0)
    else:
      val=arg_default
    setattr(parser.values,option.dest,val)
  return func

def main():
  """main method"""

  # SIGNAL HANDLER
  signal.signal(signal.SIGINT, signalHandler)
  signal.signal(signal.SIGQUIT, signalHandler)
  signal.signal(signal.SIGTERM, signalHandler)

  parser = optparse.OptionParser(formatter=optparse.TitledHelpFormatter(), usage=globals()['__doc__'], version='0.1')
  parser.add_option('-l', '--local', action='store_true', help='work with svn local commands') 
  parser.add_option('-r', '--remote', action='store_true', help='work with svn remote commands') 
  parser.add_option('-g', '--get_revisions', action='store_true', help='get svn revisions') 
  parser.add_option('-n', '--revision_number', help='revision number if option -r is set') 
  parser.add_option('-d', '--dir', action='callback', callback=optional_arg("."), help='directory path (argument is optional)', dest='dir' )
  parser.add_option('-a', '--action', action='callback', callback=optional_arg('list'), help='svn action, either commit or add (argument is optional)', dest='action' )
  parser.add_option('-c', '--context', help='app context (namespace)', dest='context' )
  parser.add_option('-v', '--apps', action='store_true', help='return a list of apps')
  parser.add_option('-m', '--commitmessage', action='callback', callback=optional_arg('general message'), help='the commit message', dest='cmessage')
  (option, args) = parser.parse_args()

  # get splunk search environment  
  results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults() 

  # create SVN config object
  cfg = svnconfig.SvnConfig(logger)
  if cfg.check_config() > 0:
    fields = {}
    fields["message"] = "there is a config value missing, please check your svn.conf"
    results.append(fields)
    splunk.Intersplunk.outputResults(results)
    return 0

  # output a list of all apps
  if option.apps:
    token=settings.get('sessionKey')
    s = client.Service(token=token)
    for app in s.apps:
      fields = {}
      fields["app"] = app.name
      results.append(fields)
    splunk.Intersplunk.outputResults(results)
    return 0

  # create custom svn object  
  svn = customsvn.CustomSvn(cfg, logger)

  # get splunk home and create the app path 
  splunk_home = splunk.Intersplunk.splunkHome()
  app_name = settings.get('namespace')
  if option.context:
    if not app_name == 'vcontrol':
      logger.error("you try to reach admin functionality outside of vcontrol app -> bad boy!")
      sys.exit(1)
    else:
      logger.info("option.context=%s" % (option.context))
      app_name = option.context

  app_dir =  os.path.join(sys.path[0],"../..")
  app_path = "%s/%s" % (app_dir,app_name)
  app_user = settings.get('owner')
  session_key = settings.get('sessionKey')

  logger.debug("entering app directory: %s" % (app_path))
  logger.debug("app_user=%s" % (app_user))
  logger.debug("svn-action=%s" % (option.action))

  fields = {}
  fields["type"] = "message"
  fields["message"] = "no message"
  results.append(fields)

 
  # change into app directory and call svn commands
  with utils.cd(app_path):
    if option.local:
      if option.dir:
        dir_or_file = option.dir.rstrip('\/')
        if option.action:
          if option.action == 'commit':
            logger.info("recursively committing: %s" % (dir_or_file))
            svn.commit(results, dir_or_file, app_user, option.cmessage)
          elif option.action == 'add':
            logger.info("recursively adding: %s" % (dir_or_file))
            svn.add(results, dir_or_file)
          elif option.action == 'remove':
            logger.info("recursively removing: %s" % (dir_or_file))
            svn.remove(results, dir_or_file)
          elif option.action == 'update':
            logger.info("executing svn update on %s" % (dir_or_file))
            svn.update(results,dir_or_file)
        svn.ls(results, dir_or_file)
        svn.status(results, dir_or_file)
        svn.info(results, 0, dir_or_file)
        svn.diff(results, dir_or_file)
    if option.remote: 
      if not option.revision_number:
          logger.info("no revision number given for remote operation")
          fields["message"] = "please specify revision number"
          results.append(fields)
          return
      if option.dir:
        dir_or_file = option.dir.rstrip('\/')
        try:
          r = int(option.revision_number)
        except:
          fields["message"] = "revision number must be an integer"
          results.append(fields)
          return
        svn.list(results, r, dir_or_file)
        svn.log(results, r, dir_or_file)
        svn.remote_diff(results, r, dir_or_file)
        svn.info(results, r, dir_or_file)
    if option.get_revisions:
      if option.dir:
        dir_or_file = option.dir.rstrip('\/')
        svn.get_revisions(results, dir_or_file)

  splunk.Intersplunk.outputResults(results)

if __name__ == "__main__": 
  try: 
    main()
  except Exception as e:
    logger.info(e)
    sys.exit(6)
