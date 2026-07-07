import re, json, time, os, sys, random

SampleRatio = 1
MinutesIntervalRunAt = 5 # If you change this to run every 60 minutes or something instead... update here.

if len(sys.argv) >= 2:
  try:
    SampleRatio = int(sys.argv[-1])
  except:
    print >> sys.stderr, "Found invalid argument for interval, sticking with all logs"

SH=""
if "SPLUNK_HOME" in os.environ:
        SH = os.environ['SPLUNK_HOME']

launchtime = int(time.time())

def convert_to_epoch(str):
  # 10-18-2014 15:41:32.805
  return time.mktime(time.strptime(str, "%m-%d-%Y %H:%M:%S.%f"))



def parsedata(path):
  insearch = 0
  search = {}
  search['results'] = {}
  search['setup'] = {}
  search['setup']['started'] = ""
  search['LogLevels'] = {}
  search['LogOperator'] = {}
  search['time_operation'] = {}
  search['searchid'] = ""
  search_groups = re.search("\/var\/run\/splunk\/dispatch\/(.*?)\/", path)
  if search_groups:
      if search_groups.groups()>1:
        search['searchid'] = search_groups.group(1)

  with open(path,'r') as f:
    for x in f:
      x = x.rstrip()
      #print x

      search_groups = re.search("^[\d\- \.:]{23}\s*(\w*)\s*(\S*)", x)
      if search_groups:
        if search_groups.groups()>1:
          if search_groups.group(1) not in search['LogLevels'].keys():
            search['LogLevels'][search_groups.group(1)] = 0
          if search_groups.group(2) not in search['LogOperator'].keys():
            search['LogOperator'][search_groups.group(2)] = 0
          search['LogLevels'][search_groups.group(1)] = search['LogLevels'][search_groups.group(1)] + 1
          search['LogOperator'][search_groups.group(2)] = search['LogOperator'][search_groups.group(2)] + 1
          

      if insearch == 0:
        search_groups = re.search("^([\d\- \.:]{23}).*LMConfig - serverName=(\S*)", x)
        if search_groups:
          if search_groups.groups()>1:
            search['_datetime'] = convert_to_epoch(search_groups.group(1))
            search['servername'] = search_groups.group(2)
            insearch = 1

        search_groups = re.search("^([\d\- \.:]{23}).*dispatchRunner - System info: .*?, (\S*?),", x)
        if search_groups:
          if search_groups.groups()>1:
            search['_datetime'] = convert_to_epoch(search_groups.group(1))
            search['servername'] = search_groups.group(2)
            insearch = 1
      
      if insearch == 1:
      # 01-08-2016 17:48:01.531 INFO  BatchSearch - PREAD_HISTOGRAM: usec_1_8=48 usec_8_64=1 usec_64_512=0 usec_512_4096=0 usec_4096_32768=0 usec_32768_262144=0 usec_262144_INF=0 
        searchidsearch = re.search("PREAD_HISTOGRAM:\s(\S*?)=(\d*)\s*(\S*?)=(\d*)\s*(\S*?)=(\d*)\s*(\S*?)=(\d*)\s*(\S*?)=(\d*)\s*(\S*?)=(\d*)\s*(\S*?)=(\d*)\s*", x)
        if searchidsearch:
          if searchidsearch.groups()>1:
            search['time_operation'][searchidsearch.group(1)] = searchidsearch.group(2)
            search['time_operation'][searchidsearch.group(3)] = searchidsearch.group(4)
            search['time_operation'][searchidsearch.group(5)] = searchidsearch.group(6)
            search['time_operation'][searchidsearch.group(7)] = searchidsearch.group(8)
            search['time_operation'][searchidsearch.group(9)] = searchidsearch.group(10)
            search['time_operation'][searchidsearch.group(11)] = searchidsearch.group(12)
            search['time_operation'][searchidsearch.group(13)] = searchidsearch.group(14)
  
        searchidsearch = re.search("loader - Arguments are:.*\"--id=(.*?)\"", x)
        if searchidsearch:
          if searchidsearch.groups()>1:
            search['searchid'] = searchidsearch.group(1)
  
  
        readresultssearch = re.search("Read (\d*) results from result provider peername=(\S*), version=(\S*), .*timetaken=([\d\.]*)", x)
        if readresultssearch:
          if readresultssearch.groups()>1:
            srv = readresultssearch.group(2)
            if srv not in search['results']:
              search['results'][srv] = {}
              search['results'][srv]['result_count'] = 0
              search['results'][srv]['time'] = 0
  
            search['results'][srv]['result_count'] += int(readresultssearch.group(1))
            search['results'][srv]['version'] = readresultssearch.group(3)
            search['results'][srv]['time'] += float(readresultssearch.group(4))
  
  
        ResultProviderSearch = re.search("([\d\- \.:]{23}) .* Successfully created result provider for peer: (\S*) .* in ([\d\.]*) seconds", x)
        if ResultProviderSearch:
          if ResultProviderSearch.groups()>1:
            srv = ResultProviderSearch.group(2)
            search['setup'][srv] = ResultProviderSearch.group(3)
            if search['setup']['started'] == "":
              search['setup']['started'] = convert_to_epoch(ResultProviderSearch.group(1))
              #print ResultProviderSearch.group(1)
  
            search['setup']['last'] = convert_to_epoch(ResultProviderSearch.group(1))
            #print ResultProviderSearch.group(1)
  
  
  
  
        shutdownsearch = re.search("Shutdown complete in \d* microseconds", x)
        if shutdownsearch:
          print json.dumps(search, sort_keys=True) + "\n"
          insearch = 0
          search = {}
          search['results'] = {}
          search['setup'] = {}
          search['setup']['started'] = ""
  
  
# 11-10-2014 09:10:05.424 INFO  ShutdownHandler - Shutdown complete in 1637 microseconds
folderpath = SH + "/var/run/splunk/dispatch"
for dirname,subdirs,files in os.walk(folderpath):
  for fname in files:
    if re.match("search\.log$", fname) is not None and random.randint(0,SampleRatio) % SampleRatio == 0:
      full_path = os.path.join(dirname, fname)
      mtime = os.stat(full_path).st_mtime
      if mtime> launchtime-(MinutesIntervalRunAt + 2) *60 and mtime < launchtime-2*60:
        match = False
        with open(full_path) as f:
          for line in f:
            if re.search("Shutdown complete in", line):
              match = True
        if match == True:  
          # print full_path, mtime
          
          parsedata(full_path)
          #else: 
          #  print "Skipping...."
