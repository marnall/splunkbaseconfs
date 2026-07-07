#!/usr/bin/env python
###############################################################################
#
# Copyright (C) 2013-2014 Cisco and/or its affiliates. All rights reserved.
#
# THE PRODUCT AND DOCUMENTATION ARE PROVIDED AS IS WITHOUT WARRANTY
# OF ANY KIND, AND CISCO DISCLAIMS ALL WARRANTIES AND REPRESENTATIONS,
# EXPRESS OR IMPLIED, WITH RESPECT TO THE PRODUCT, DOCUMENTATION AND
# RELATED MATERIALS INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE; WARRANTIES
# ARISING FROM A COURSE OF DEALING, USAGE OR TRADE PRACTICE; AND WARRANTIES
# CONCERNING THE NON-INFRINGEMENT OF THIRD PARTY RIGHTS.
#
# IN NO EVENT SHALL CISCO BE LIABLE FOR ANY DAMAGES RESULTING FROM
# LOSS OF DATA, LOST PROFITS, LOSS OF USE OF EQUIPMENT OR LOST CONTRACTS
# OR FOR ANY SPECIAL, INDIRECT, INCIDENTAL, PUNITIVE, EXEMPLARY OR
# CONSEQUENTIAL DAMAGES IN ANY WAY ARISING OUT OF OR IN CONNECTION WITH
# THE USE OR PERFORMANCE OF THE PRODUCT OR DOCUMENTATION OR RELATING TO
# THIS AGREEMENT, HOWEVER CAUSED, EVEN IF IT HAS BEEN MADE AWARE OF THE
# POSSIBILITY OF SUCH DAMAGES.  CISCO'S ENTIRE LIABILITY TO LICENSEE,
# REGARDLESS OF THE FORM OF ANY CLAIM OR ACTION OR THEORY OF LIABILITY
# (INCLUDING CONTRACT, TORT, OR WARRANTY), SHALL BE LIMITED TO THE
# LICENSE FEES PAID BY LICENSEE TO USE THE PRODUCT.
#
###############################################################################
#
#  Change Log
#
#   1.0   - cogrady - ORIGINAL RELEASE WITH INTRODUCTION OF SPLUNK APP
#   1.0.1 - cogrady - Updated to check if client start succeeded
#   1.0.4 - cogrady - Added details error to error messages
#   2.0   - cogrady - Added pkcs12 cert exist check, config change detection
#   2.1   - cogrady - Added support for test command-line option
#   2.1.6 - cogrady - Make config read UTF-8 friendly (e.g. Windows)
#
###############################################################################


###############################################################################
#  Import modules
###############################################################################

import os
import platform
import signal
import sys
import subprocess
import re
import time
import codecs
import ConfigParser


###############################################################################
#  Setup the environment
###############################################################################

# Start by getting the platform
platform = platform.system()

# Set base path based on OS
if (platform == 'Windows'):
  import win32api
  splunk_path = os.getenv('SPLUNK_HOME', 'C:\\Program Files\\Splunk\\')
  splunk_path = win32api.GetShortPathName(splunk_path)
else:
  splunk_path = os.getenv('SPLUNK_HOME', '/opt/splunk')

# Set the rest of the paths relative to the splunk_path
app_path     = os.path.join(splunk_path, 'etc', 'apps', 'eStreamer')
app_bin_path = os.path.join(app_path, 'bin')
config_file  = os.path.join(app_path, 'local', 'estreamer.conf')
log_file     = os.path.join(app_path, 'log', 'estreamer.log')
pid_file     = os.path.join(app_bin_path, 'estreamer_client.pid')
script_file  = os.path.join(app_bin_path, 'estreamer_client.pl')


###############################################################################
#  Functions
###############################################################################

# Run the client
def runClient():

  # Build the environment  
  perl_env = os.environ
  perl_env['LD_LIBRARY_PATH'] = ''

  # First we need to build the command-line
  cmd_line = script_file + ' -d -c ' + config_file + ' -l ' + log_file
  
  # Execute the client with appropriate settings
  client = subprocess.Popen(cmd_line, cwd=app_bin_path, env=perl_env, shell=True)

  # Wait a moment for the process to succeed or fail
  time.sleep(2)

  # Return the recturn code
  return isClientRunning()


# Run the client
def getClientError():

  # Build the environment
  perl_env = os.environ
  perl_env['LD_LIBRARY_PATH'] = ''

  # First we need to build the command-line
  cmd_line = script_file + ' -t -c ' + config_file + ' -l ' + log_file

  # Execute the client with appropriate settings
  try:
    output = subprocess.check_output(cmd_line, cwd=app_bin_path, env=perl_env, shell=True, stderr=subprocess.STDOUT)
  except subprocess.CalledProcessError, e:
    output = e.output

  # Return the recturn code
  return output.replace('\n', '')


# Kill off the client by PID
def killClient():
  
  # Look to see if the PID file exists
  if (os.path.exists(pid_file)):
    
    # Read the PID from the file
    pf = open(pid_file, 'r')
    pid = pf.readline()
    pf.close()
    
    # Kill the process
    os.kill(int(pid), signal.SIGHUP)


# Determine if the client is running
def isClientRunning():
  
  # Set some assumptions
  running = False
  
  # Look to see if the PID file exists
  if (os.path.exists(pid_file)):
    
    # Read the PID from the file
    pf = open(pid_file, 'r')
    pid = pf.readline()
    pf.close()
    
    # Check to see if the process exists
    if (os.path.exists('/proc/' + pid)):
      running = True
    else:
      os.remove(pid_file)
  
  # Return the result
  return running


###############################################################################
#  Main
###############################################################################

# Set some defaults
error_msg = ""
output_msg = ""
config_changed = '0'

# Has the app been setup yet?
if (not os.path.exists(config_file)):
  error_msg = 'The app has not yet been setup.'

# If the app has been setup
else:

  # Use config parser to read config
  conf_parser = ConfigParser.ConfigParser()

  # Read in a UTF-8 friendly way
  with codecs.open(config_file, 'r', encoding='utf-8') as config_fp:
    first = hex(ord(config_fp.read(1)))
    if first != '0xfeff':
      config_fp.close()
      conf_parser.read(config_file)
    else:
      conf_parser.readfp(config_fp)

  # Check the settings out of the config and read defaults where applicable or error out

  try:
    server = conf_parser.get('estreamer', 'server')
  except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
    error_msg = 'There is no Defense Center defined.'

  # Check for cert definition and existence
  try:
    cert_file = conf_parser.get('estreamer', 'pkcs12_file')
    if (not os.path.exists(cert_file)):
      error_msg = 'The pkcs12 certificate does not exist where specified.'
  except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
    error_msg = 'There is no pkcs12 certificate defined.'

  try:
    client_disabled = conf_parser.get('estreamer', 'client_disabled')
  except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
    # Default to disabled if unable to make determination
    client_disabled = '1'

  try:
    config_changed = conf_parser.get('estreamer', 'changed')
    # If the config is marked as changed, we need to unset it
    if (config_changed == '1'):
      conf_parser.set('estreamer', 'changed', '0')
      with open(config_file, 'w') as config_fo:
        conf_parser.write(config_fo)
  except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
    config_changed = '0'

# Are we in a condition where we can't continue?
if (len(error_msg)):
  output_msg = 'status_id=-1 status="ERROR: ' + error_msg + '"'

# No errors, we're good to go
else:

  # If the client is disabled
  if (client_disabled == '1'):
    
    # If the client is running
    if (isClientRunning()):
      output_msg = 'status_id=3 status="eStreamer client is running, but disabled. Stopping the client."'
      killClient()
      
    # The client is not running, no need to do anything else
    else:
      output_msg = 'status_id=0 status="eStreamer client is disabled."'
      
  # If the client is enabled
  else:

    # If the config has changed, kill the client and we'll restart it on the next polling interval
    if (config_changed == '1'):
      killClient()
      output_msg = 'status_id=4 status="Configuration changed. Restarting eStreamer client."'

    # The config did not change
    else:

      # If the client is running...
      if (isClientRunning()):
        output_msg = 'status_id=1 status="eStreamer client is running."'

      # If the client is not running, let's start it
      else:

        # Attempt to run the client
        if (runClient()):
          output_msg = 'status_id=2 status="Started eStreamer client."'

        # Something happened
        else:

          # Get the output from the error
          output = getClientError()

          # Compsee the message
          output_msg = 'status_id=-1 status="ERROR: Problems starting the eStreamer client (' + output + ')"'

print('event_sec=' + str(int(time.time())) + ' ' + output_msg)
