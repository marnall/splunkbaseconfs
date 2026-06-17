#!/usr/bin/python

# vim: set shiftwidth=2:

import csv
import json
import os
import re
import sys
import time
import pprint
try:
  import argparse
except:
  sys.exit('''This script requires Python 2.7 to run. Please invoke it using Splunk's Python:
$SPLUNK_HOME/bin/python dispatch_inspector.py [options...] [dispatch_dir]''')

""" Dispatch Inspector
    
    Walk a dispatch directory and determine the state of all the dispatch
    directories; Specifically

    * Has the TTL expired or not?
    * Should the search be removed?
    * What search head (if any) generated the search?
    * (etc)
"""

# TODO
# * Get some values from splunk conf if available (eg failed_job_ttl)
# * Report SH of provenance. Use info.csv::owning_server (only relevant to SHP) or the SH name embedded in the SID.
# * Report date of expiration of oldest expired artifact
# * Distinguish scheduled RT search artifacts (ex: rt_scheduler__nobody_QlRfRm9yY2UxMF9TSA__RMD55096664d67ae07ac_at_1362008520_843) from RT search snapshots (ex: rt_scheduler__nobody_QlRfRm9yY2UxMF9TSA__RMD502497d849ec36e30_at_1361939220_16927.0)
# * Continue to refine short_searchid() to deal with all artifact naming schemes
# * Print out Top 10 most represented scheduled searches


def parse_arguments():
  """ Try to handle all the options we might want.
  
  Returns an object that has .value properties that contain our values.
  """
  parser = argparse.ArgumentParser(
    description="Walk a dispatch directory and determine the state of all the dispatch directories",
    epilog="will assume $SPLUNK_HOME/var/run/splunk/dispatch if no dispatch dir argument is given"
  )
  parser.add_argument("dispatch_dir", 
    help="general dispatch directory, which conatins many per-search dispatch directories",
    nargs="?",  # optional
    )
  parser.add_argument("-t","--time-reference", 
    help="Compare the dipatch directory to the current time or guess by "+
         "scanning for the latest modtime in the dispatch directory",
    choices=('current', 'dirscan'),
    default='current'
    )
  # redundant with summary, but i did not like dealing with intial line of 'what
  # dir is being scanned'
  parser.add_argument("-b","--brief", 
    help="suppress informative non-data messages, just emit raw data, useful for grep",
    action="store_true"
    )
  # a turn-on and turn off flag for sumary.  Just because "do it" is default, it
  # seems easier to grasp
  parser.add_argument("-p","--print-summary",
    help="enable final summary report (default: True)",
    dest="summary",
    action='store_true',
    default=True
    )
  parser.add_argument("-d","--disable-summary",
    help="disable final summary report",
    dest="summary",
    action='store_false'
    )
  parser.add_argument("-f","--format", 
    help="select output as formatted text or json objects (default: 'text')",
    default="text",
    choices=("text", "json")
    )
  parser.add_argument("--artifact-format", 
    help="select display of table, short (limited width) or full (no truncation (default: 'short')",
    default="short",
    choices=("short", "full")
    )
  parser.add_argument("--debug", 
    help="produce debug output",
    action='store_true'
    )
  args = parser.parse_args()

  if not args.dispatch_dir:
    splunk_home = os.environ.get('SPLUNK_HOME')
    if not splunk_home:
      sys.stderr.write("no dir given, and SPLUNK_HOME not in environment.\n")
      parser.print_usage(sys.stderr)
      sys.exit(1)
    args.dispatch_dir = os.path.join(splunk_home,'var','run','splunk','dispatch')

  if not os.path.isdir(args.dispatch_dir):
    errmsg = "error: '%s' does not exist, or is not a directory. " + \
             "Please provide the absolute path to the dispatch directory to inspect.\n"
    sys.stderr.write(errmsg % args.dispatch_dir)
    parser.print_usage(sys.stderr)
    sys.exit(1)

  if args.debug:
    sys.stderr.write("ARGS: %s\n" % pprint.pformat(args))

  return args

def get_newest_status_modtime(path):
  """ For a path and all its subdirectories, find the most recent status.csv file
  available and grab its modtime available. """
  # we're going to pretend this is the minimum possible.
  # negative values can GO POUND SAND
  newest_modtime = 0 
  wanted_filename = 'status.csv'
  for root, dirs, files in os.walk(path):
    if wanted_filename in files:
      wanted_filepath = os.path.join(root, wanted_filename)
      try:
        modtime = os.path.getmtime(wanted_filepath)
        if modtime > newest_modtime:
          newest_modtime = modtime
      except OSError, e:
        pass # will happen for getmtime if stuff gets deleted, that's fine
  return newest_modtime

def get_artifact_info(artifact_path, reference_time):
  """ Gather information similarly to how the dispatch reaper would do from a
  particular search directory d.

  reference_time can be one of:
     None, in which case this function compares modtimes to the current time.
     a python time_t float, in which case this function compares modtimes to that

  Return determined information as a dictionary, fields may be None when not
  determinable.
    {
      'dispatcher'      : running search head or other info,
      'state'           : ???,
      'TTR'             : integer, seconds until it should be deleted (negative if overdue),
      'modtime'         : integer, seconds from ecpoch
      'modtime_failinfo': string, modtime of ???,
      'TTL'             : integer, quantity of seconds to keep searchdir after modtime,
      'TTL_failinfo'    : string, describes failure of acquiring TTL if it is None
      'status'          : string, computed description of search status,
      'SID'             : string, search id}
  """
  dispatcher = None
  TTL = None
  TTR = None
  TTL_failinfo = None
  modtime = None
  modtime_failinfo = None
  state = None

  # is the artifact directory empty?
  if len(os.listdir(artifact_path)) == 0:
    dir_is_empty = True
    modtime_failinfo = "n/a"
    TTL_failinfo = "n/a"

  else:
    dir_is_empty = False
    # let's read the artifact TTL from metadata.csv
    metadata_file_path = os.path.join(artifact_path,'metadata.csv')
    if os.path.exists(metadata_file_path):
      try:
        metadata_file = open(metadata_file_path)
        rows = csv.DictReader(metadata_file,delimiter=",")
        for row in rows:
          TTL = int(row['ttl'])
      except:
        TTL_failinfo = "Couldn't read TTL from metadata.csv"
    else:
      TTL_failinfo = "metadata.csv not found"

  # let's read the modtime of status.csv as well as the state of the search
  status_file_path = os.path.join(artifact_path,'status.csv')
  if os.path.exists(status_file_path):
    try:
      modtime = os.stat(status_file_path).st_mtime
      status_file = open(status_file_path)
      rows = csv.DictReader(status_file,delimiter=",")
      for row in rows:
        state = row['state']
    except:
      modtime_failinfo = "Couldn't read modtime of status.csv"
      state = "Couldn't read state from status.csv"
  else:
    modtime = os.stat(artifact_path).st_mtime

  # If the job was actually failed, we don't honor the ttl from the artifact
  if state == "FAILED":
    TTL = 86400 # TODO, get this from conf

  # let's calculate the TTR (Time To Reaping)
  if TTL and modtime:
    if not reference_time:
      reference_time = time.time()
    TTR = modtime + TTL - reference_time

  # let's read the search-head of origin, when relevant. This will either
  # be the owning SH (in the case of SHP) or the remote dispatcher (in the
  # case of distributed search)
  info_file_path = os.path.join(artifact_path,'info.csv')
  if os.path.exists(info_file_path):
    try:
      info_file = open(info_file_path)
      rows = csv.DictReader(info_file,delimiter=",")
      for row in rows:
        if len(row['_sid'])>0:
          dispatcher = row['_owning_server']
    except:
      dispatcher = "Couldn't read SH from info.csv"
  else:
    dispatcher = "info.csv not found"

  # let's calculate the status field based on all of the information we gathered
  status = ""
  if dir_is_empty:
    status = "empty dir"
  elif TTR == None:
    status = "unknown"
  elif TTR <= 0:
    status = "late, reaping due %.0fs ago" % -TTR
  elif TTR > 0:
    status = "on time, reaping scheduled in %.0fs" % TTR

  # Now that we have all of our values, return them
  return {
    'dispatcher' : dispatcher,
    'state' : state,
    'TTR' : TTR,
    'modtime' : modtime,
    'modtime_failinfo' : modtime_failinfo,
    'TTL' : TTL,
    'TTL_failinfo' : TTL_failinfo,
    'status' : status,
    'SID' : os.path.basename(artifact_path)}

def short_searchid(full_searchid):
  """Try to show the searchid in a short way
  """
  cutoff = 25
  if len(full_searchid) < cutoff:
    return full_searchid

  try:
    result = ""
    segments = filter(None, full_searchid.split('_'))
    
    if segments and segments[0] == 'rt':
      segments.pop(0)
      result += "RT"

    if segments and segments[0] == 'scheduler':
      segments.pop(0)
      result += "sched"

    if len(segments) >= 3:
      search_hash = segments[2]
      result += "-" + search_hash
    else:
      # not scheduled
      result = full_searchid[:cutoff] + "..."
    return result
  except:
    return full_searchid


def get_headers(output_format):
  if output_format == "full":
    # 'full' format is self-describing inline, so none
    return None
  headers = ['SID (shortened)', 'status', 'TTL', 'modtime', 'TTR', 'state', 'dispatcher']
  upper_bar = '-'*117+'\n'
  lower_bar = '\n'+'-'*29+'|'+'-'*11+'|'+'-'*8+'|'+'-'*21+'|'+'-'*9+'|'+'-'*12+'|'+'-'*21
  h_template = upper_bar + '{0:28} | {1:9} | {2:6} | {3:19} | {4:7} | {5:10} | {6:20}' + lower_bar
  return h_template.format(*headers)

def artifact_info_to_string(artifact_info, output_format):
  #print artifact_info, output_format
  if output_format == 'full':
    a_template = "SID: {SID} | status: {status} | TTL: {0} | Last touched: {1} | Seconds to reaping: {2} | State: {state} | Dispatcher: {dispatcher}"

  elif output_format == "short":
    a_template = "{short_SID:28} | {status:9} | {0:>6} | {1:19} | {2:>7} | {state:10} | {dispatcher:20}" 
    # hack to get the 'status' text before the first comma
    status_start = artifact_info['status'].split(',', 1)[0] 
    artifact_info['status'] = status_start
    artifact_info['short_SID'] = short_searchid(artifact_info['SID'])
    artifact_info['TTL_failinfo'] = 'nofile'
  else:
    raise Exception("Bad output_format")

  # kludgery for printing
  ttl_for_printing = artifact_info['TTL'] or artifact_info['TTL_failinfo']

  if artifact_info['TTR']:
    ttr_for_printing = '%.0f' % artifact_info['TTR']
  else:
    ttr_for_printing = "n/a"

  if artifact_info['modtime']:
    modtime_for_printing = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(artifact_info['modtime']))
  else:
    modtime_for_printing = artifact_info['modtime_failinfo']

  return a_template.format(ttl_for_printing, modtime_for_printing, 
                           ttr_for_printing, **artifact_info)


def main():
  args = parse_arguments()

  if not args.brief:
    print "Scanning dispatch directory @ %s\n" % args.dispatch_dir

  artifact_dirs = [dir for dir in os.listdir(args.dispatch_dir) 
                   if os.path.isdir(os.path.join(args.dispatch_dir, dir))]

  if args.time_reference == "current":
    # keep determining current time right after we stat
    reference_time = None 
  elif args.time_reference == "dirscan":
    reference_time = get_newest_status_modtime(args.dispatch_dir)
    time_str = time.asctime(time.localtime(reference_time))
    print("CALCULATED REFERENCE TIME: %s\n" % time_str)
  else:
    sys.stderr.write("OMG BUG BUG, unhandled time_reference %s" % args.time_reference)

  if args.debug:
      sys.stderr.write("DIRS TO SCAN ... \n")
      sys.stderr.write(pprint.pformat(artifact_dirs) + "\n")

  # initialize the result set, which is a list of dictionaries: 1 artifact -> 1 dictionary
  artifacts = []

  for artifact in artifact_dirs:
    artifact_path = os.path.join(args.dispatch_dir, artifact)

    # let's only proceed if the artifact path still exists
    if os.path.exists(artifact_path):
      artifact_info = get_artifact_info(artifact_path, reference_time)
      artifacts.append(artifact_info)
    elif args.debug:
      sys.stderr.write("skipping vanished dir '%s'\n" % artifact_info)

  headers = get_headers(args.artifact_format)
  if headers:
    print headers

  for artifact in artifacts:
    if args.format == 'json':
      print json.dumps(artifact)
    else:
      print artifact_info_to_string(artifact, args.artifact_format)
      
  if args.summary and not (args.brief or args.format =='json'):
    print
    print "================= SUMMARY for dispatch directory %s =================" % args.dispatch_dir
    print
    print "TOTAL: %i" % len(artifacts)
    print
    print "-------- Artifact status breakdown --------"
    print "On time for reaping: %i" % len([a for a in artifacts if a['status'].startswith('on time')])
    print "Late for reaping: %i" % len([a for a in artifacts if a['status'].startswith('late')])
    print "Status unknown: %i" % len([a for a in artifacts if a['status'].startswith('unknown')])
    print "Empty directories: %i" % len([a for a in artifacts if a['status'].startswith('empty')])
    print
    print "Expiration date of oldest expired artifact: "
    print
    print
    print "--------- Artifact type breakdown ---------"
    print "Scheduled, historical: %i" % len([a for a in artifacts if re.match('(?<!rt_)scheduler',a['SID'])])
    print "Scheduled, real-time: %i" % len([a for a in artifacts if re.match('rt_scheduler',a['SID'])])
    print "Scheduled, summarization: %i" % len([a for a in artifacts if re.match('SmmaryDirector',a['SID'])])
    print "Ad-hoc, historical: %i" % len([a for a in artifacts if re.match('13[6-9]\d{7}',a['SID'])])
    print "Ad-hoc, real-time: %i" % len([a for a in artifacts if re.match('rt_13[6-9]\d{7}',a['SID'])])
    print "Remote: %i" % len([a for a in artifacts if re.match('remote',a['SID'])])
    print "Subsearch: %i" % len([a for a in artifacts if re.match('subsearch',a['SID'])])
    print
    print
    print "--------- Artifact state breakdown ---------"
    print "DONE: %i" % len([a for a in artifacts if a['state'] == 'DONE'])
    print "FAILED: %i" % len([a for a in artifacts if a['state'] == 'FAILED'])
    print "RUNNING: %i" % len([a for a in artifacts if a['state'] == 'RUNNING'])
    print "PAUSED: %i" % len([a for a in artifacts if a['state'] == 'PAUSED'])
    print "QUEUED: %i" % len([a for a in artifacts if a['state'] == 'QUEUED'])
    print "PARSING: %i" % len([a for a in artifacts if a['state'] == 'PARSING'])
    print "FINALIZING: %i" % len([a for a in artifacts if a['state'] == 'FINALIZING'])


if __name__ == "__main__":
  main()
