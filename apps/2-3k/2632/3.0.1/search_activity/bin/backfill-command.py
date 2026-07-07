#!/usr/bin/python
import json, csv, re, os
import urllib2
import sys
import time
import requests
import splunklib.results as results
import splunklib.client as client
import splunk.rest
from datetime import datetime
from random import randint
from inspect import currentframe, getframeinfo


#                                                                                   +-----------------------------------+    +------------------------+
#                             +-----------------------+                             |  #6                               |    |   #7                   |
#                             | #1  Done              |                             | Short Term Logic                  | +-->  Set last-end-time to  +----+
#                             | Pull the config from  |                     +------->                                   | |  |  now() - 10 min        |    |
#                             | the REST API          |                     |       |  If last-end-time is empty (aka   +-+  +--------+---------------+    |   +------------------------+
#                             +-----------+-----------+                     |       |  no logs exist)                   |                                  |   |  #8                    |
#                                         |                                 |       |                                   |                                  +---> Do short term summary  +----------------------------+
#                                         |                                 |       |         +-------------------------+                                  |   | search                 |                            |
#                             +-----------+---------------+                 |       |                                   |                                  |   +------------------------+                            |
#                             |  #2   Done                |                 |       |  If now() - last-end-time is less |                                  |                                                         |
#                             | Introspect raw events to  |                 |       |  than config['max-short-term']    +----------------------------------+                                                         |
#                             | determine most recent     |                 |       |                                   |                                                                                            |
#                             | finished search end time. |                 |       |         +-------------------------+   +-------------------------------------+                                                  |
#                             | Only used for #6          |                 |       |                                   |   |  #9                                 |                                                  |
#                             +-----------+---------------+                 |       |  If now() - last-end-time is more |   | Change backfill-status to "general" |                                                  |
#                                         |                                 |       |  than config['max-short-term']    +---> Reset earliestTime to last-end-time |                                                  |
#                                         |                                 |       |                                   |   | Call Primary Logic                  |                                                  |
#                                         |                                 |       +-----------------------------------+   | exit function                       |                                                  |
#                                         |                                 |                                               +----------------+--------------------+                                                  |
#                                         |                                 |                                                                |                                                                       |
#                                         |                      +---------------------------------------------------------------------------+                                                                       |
#                                         |                      |          |                                                                                                                                        |
# +----------------------+    +-----------v------------+         |          |       +----------------------------------+     +----------------------------------------+                                              |
# |  #4  Done            |    | #3  Done               |         |          |       |  #10                             |     |  #11                                   |                                              |
# | If jobs are runnnng, |    | Search One             |         |          |       | Selective                        |     | Run long term search from earliestTime |                                              |
# | log SIDs and exit    <----+ Validate that no other |         |          |       |                                  |     | to earliestTime + config['max-time-    +----------------------------------------------+
# |                      |    | jobs are running       |         |          |       |  If latestTime - earliestTime >  +-----> single-run']                           |                                              |
# +----------------------+    +-----------+------------+         |          |       |  config['max-time-single-run']   |     |                                        |                                              |
#                                         |                      |          |       |                                  |     | Set earliestTime = <that time>         |                                              |
#                                         |                      |          |    +-->        +-------------------------+     |                                        |                                              |
#                                         |                      |          |    |  |                                  |     +----------------------------------------+                                              |
#                             +-----------v----------------------v-------+  |    |  |  If latestTime - earliestTime <= +-+                                                                             +-------------v--------------+
#                             | #5                                       |  |    |  |  config['max-time-single-run']   | |   +-----------------------------------------+                               |  #0                        |
#                             |Primary Logic                             |  |    |  |                                  | |   |  #12                                    |                               |  Produce JSON Log          |
#                             |                                          +--+    |  +----------------------------------+ |   | Run long term search from earliestTime  |                               |  Execution Complete!       |
#                             | if backfill-status="no-backfill"         |       |                                       |   | to latestTime                           |                               |                            |
#                             |                                          |       |                                       |   |                                         |                               |                            |
#                             |                                          |       |                                       +---> Set backfill-status="no-backfill"       +------------------------------->                            |
#                             |        +---------------------------------+       |                                           |                                         |                               |                            |
#                             |                                          |       |                                           | (No short term search here... not worth |                               |                            |
#                             |                                          |       |                                           | the effort to code)                     |                               |                            |
#                             | if backfill-status="selective"           +-------+                                           |                                         |                               +-------------^--------------+
#                             |                                          |                                                   +-----------------------------------------+                                             |
#                             |                                          |                                                                                                                                           |
#                             |        +---------------------------------+          +----------------------------------+     +----------------------------------------+                                              |
#                             |                                          |          |  #13                             |     |  #14                                   |                                              |
#                             |                                          |          | General Backfill                 |     | Run long term search from earliestTime |                                              |
#                             | if backfill-status="general"             +---------->                                  |     | to earliestTime + config['max-time-    +----------------------------------------------+
#                             |                                          |          |  If now() - earleistTime >       +-----> single-run']                           |                                              |
#                             |                                          |          |  config['max-time-single-run']   |     |                                        |                                              |
#                             +------------------------------------------+          |                                  |     | Set earliestTime = <that time>         |                                              |
#                                                                                   |        +-------------------------+     |                                        |                                              |
#                                                                                   |                                  |     +----------------------------------------+                                              |
#                                                                                   |  If now() - earliestTime <=      +-+                                                                                           |
#                                                                                   |  config['max-time-single-run']   | |   +-----------------------------------------+                                             |
#                                                                                   |                                  | |   |  #15                                    |                                             |
#                                                                                   +----------------------------------+ |   | Run long term search from earliestTime  |                                             |
#                                                                                                                        |   | to now()                                |                                             |
#                                                                                                                        |   |                                         |                                             |
#                                                                                                                        +---> Set backfill-status="no-backfill"       +---------------------------------------------+
#                                                                                                                            |                                         |
#                                                                                                                            | (No short term search here... not worth |
#                                                                                                                            | the effort to code)                     |
#                                                                                                                            |                                         |
#                                                                                                                            +-----------------------------------------+


############################################
##### Global Variables for Program Operation
############################################
sessionKey = ""
owner = "" 
app = "" 
mydict = dict()
settings = dict()
myPort = ""
config = {}
logs = []
config["last_end_time"] = 0
server_now = 0

################################
##### Pull Authentication Tokens
################################
# First we pull the some data from the incoming tokens. There are, I'm sure, better ways to do this... but this has worked for me for 4 years so let it roll!
for line in sys.stdin:
    m = re.search("sessionKey:\s*(.*?)$", line)
    if m:
        sessionKey = m.group(1)
    m = re.search("owner:\s*(.*?)$", line)
    if m:
        owner = m.group(1)
    m = re.search("namespace:\s*(.*?)$", line)
    if m:
        app = m.group(1)

#####################################
##### Initialize Connection to Splunk
#####################################
import splunk.entity, splunk.Intersplunk

records = splunk.Intersplunk.readResults(settings = settings, has_header = True)
entity = splunk.entity.getEntity('/server','settings', namespace=app, sessionKey=sessionKey, owner='-')

mydict = entity
myPort = mydict['mgmtHostPort']
base_url = "https://127.0.0.1:" + myPort
service = client.Service(token=sessionKey, host="127.0.0.1", port=myPort, user="admin")
kwargs_normalsearch = {"exec_mode": "normal", "app": "search_activity"}

###################
##### Config Choices
###################
MinimumSearchAge = 600      # Default 600 seconds. Ensures that we have enough time to capture sharing activities

def main():
    ###################
    ##### Main: Initial Setup function
    ###################
    sys.stdout.write("_time,jobid,level,step,item,message\n")
    pull_rest_config()
    if config["conversion-status"] == "converting":
        log(0,"INFO","Conversion Check", "Conversion in progress -- cancelling backfill until it is complete.")
        finish()
    else:
        config["last_end_time"] = check_for_existing_data()
        check_for_coexisting()
        launch_primary_logic()
        finish()
    ## End of main()

def finish():
    ###################
    ##### UTILITY Function: Pull together log messages, kick them out, and exit
    ###################
    RunningID = str(randint(1000000002,10000000000)-1)
    myindex = service.indexes["_internal"]
    for log in logs:
        if int(config["debug"]) == 1 or log["level"] != "DEBUG":
            sys.stdout.write('"' + str(log["time"]) + '","' + RunningID + '","' + str(log["level"]) + '","' + str(log["step"]) + '","' + log["item"].replace('"', '""').replace(r'\n', " ") + '", "' + log["message"].replace('"', '""').replace(r'\n', " ") + '"\n')
            log["jobid"] = RunningID
            log["_time"] = log["time"]
            log.pop('time', None)
            myindex.submit(json.dumps(log, sort_keys=True), sourcetype="searchactivity:log", source="searchactivity:log")
    sys.stdout.write('"' + str(time.time()) + '","' + RunningID + '","INFO","99","Finish", "Processing Complete"\n')
    sys.stdout.flush()
    exit()


def log(num, level, item, message):
    ###################
    ##### UTILITY Function: Collect log messages
    ###################
    log = {}
    log["item"] = item
    log["step"] = num
    log["level"] = level
    log["message"] = message
    log["time"] = time.time()
    logs.append(log)

    # When tracing variables, it can be convenient to add an output every single time log is called. Do that here
    #if num!=0:
        #sys.stdout.write('"' + str(time.time()) + '","moot","INFO","99","Finish", "' + json.dumps(config).replace('"', '""').replace(r'\n', " ") + '"\n')
        


def update_rest_config(name, value):
    ###################
    ##### UTILITY Function: Update the kvstore configuration
    ###################
    post_args = { "_key": name, "_time": time.time(), "name": name, "value": value }
    config[name] = value
    headers={'Authorization': 'Splunk %s' % sessionKey, "Content-type": "application/json"}
    r = requests.post('https://127.0.0.1:' + myPort + '/servicesNS/nobody/search_activity/storage/collections/data/sa_app_configuration/' + name, headers=headers, data=json.dumps(post_args), verify=False)
    if r.status_code == 200:
        log(0, "INFO", "Updating REST Config", "Success: Set " + str(name) + ": " + str(value))
    else:
        log(0, "ERROR", "Updating REST Config", "Failed to update " + str(name) + ": " + str(value) + "\r" + r.content)
        log(0, "DEBUG", "Updating REST Config", json.dumps(headers))

def pull_rest_config():
    ###################
    ##### #1 above
    ###################
    _, content = splunk.rest.simpleRequest('/servicesNS/nobody/search_activity/storage/collections/data/sa_app_configuration', sessionKey=sessionKey, getargs={'output_mode': 'json'})
    
    for row in json.loads(content):
            config[ row['name'] ] = row['value']
    log(1, "INFO", "Pull kvstore Config", "Just pulled " + str(len(config.keys())) + " keys")
    log(1, "DEBUG", "Pull kvstore Config", json.dumps(config))
    return True


def check_for_coexisting():
    ###################
    ##### #3 above
    ###################
    searchquery_normal = '| rest splunk_server=local "/servicesNS/admin/-/search/jobs"| search dispatchState="RUNNING" OR dispatchState="FINALIZING" OR dispatchState="QUEUED" OR dispatchState="PARSING" title!="| rest*" title="*sabackfill*" '
    job = service.jobs.create(searchquery_normal, **kwargs_normalsearch)
    while True:
        job.refresh()
        stats = {"isDone": job["isDone"],
                "doneProgress": float(job["doneProgress"])*100}
                
        if stats["isDone"] == "1":
            break

        time.sleep(2)

    countjobs = 0
    for result in results.ResultsReader(job.results()):
        countjobs += 1

    if countjobs > 1:
        log(3, "WARN", "Co-existing Job Count", "Jobs already running.. canceling")
        finish()
    else:
        log(3, "INFO", "Co-existing Job Count", "No jobs working -- okay to proceed.")
    log(3, "DEBUG", "Co-existing Job Count", "Just ran query (searchid=\"" + job.name + "\"): \n" + searchquery_normal)
    return True

def check_for_existing_data():
    ###################
    ##### #2 above
    ###################
    #Original: searchquery_normal = '| tstats count max(_time) as maxtime where index=`FillSearchHistory_SummaryIndex` sourcetype=searchactivity:searchhistory | fillnull value="0" maxtime | eval server_now = now() '
    searchquery_normal = 'search [| tstats count max(_time) as maxtime where index=`FillSearchHistory_SummaryIndex` sourcetype=searchactivity:searchhistory | table maxtime | fillnull value="0" maxtime | rename maxtime as earliest]  index=`FillSearchHistory_SummaryIndex` sourcetype=searchactivity:searchhistory  | stats count max(finaltime) as maxtime | eval maxtime=round(maxtime,0)  | fillnull value="0" maxtime | eval server_now = now()'
    job = service.jobs.create(searchquery_normal, **kwargs_normalsearch)
    while True:
        job.refresh()
        stats = {"isDone": job["isDone"],
                "doneProgress": float(job["doneProgress"])*100}
                
        if stats["isDone"] == "1":
            break

        time.sleep(2)

    countjobs = 0
    for result in results.ResultsReader(job.results()):
        config["server_now"] = int(result["server_now"])
        log(2, "DEBUG", "Existing Data", str(config["server_now"]))
        if result["count"] == "0":
            log(2, "WARN", "Existing Data", "No existing data found! Result: " + json.dumps(result))
            return 0
        else:
            log(2, "INFO", "Existing Data", "Existing data found! Result: " + json.dumps(result))
            return int(result['maxtime'])
        
def launch_primary_logic():
    ###################
    ##### #5 above
    ###################
    if config["backfill-status"] == "normal":
        log(5, "INFO", "Primary Logic", "Going for normal mode")
        normal_logic()
        
    elif config["backfill-status"] == "no-backfill":
        log(5, "INFO", "Primary Logic", "Going for no-backfill (will run one time after user selects to not backfill via setup)")
        no_backfill_logic()
        
    elif config["backfill-status"] == "selective":
        log(5, "INFO", "Primary Logic", "Going for selective backfill (will run until selective backfill completes -- see step 10 logs for remaining time)")
        selective_backfill_logic()
        
    elif config["backfill-status"] == "general":
        log(5, "INFO", "Primary Logic", "Going for general backfill (will occur because of user selection in setup, system downtime, or infrequent scheduled runtimes. Will run until general backfill completes -- see step 13 logs for remaining time)")
        general_backfill_logic()

    else:  
        log(5, "WARN", "Primary Logic", "No backfill-status defined, meaning that setup hasn't been completed yet. Cancelling.")
        
def normal_logic():
    ###################
    ##### #6 above
    ###################
    if config["last_end_time"] == "" or int(config["last_end_time"]) == 0:
        log(6, "INFO", "Normal Logic", "No existing data, doing a short term backfill for 10 minutes")
        default_config_last_end_time()
        short_term_backfill()
    elif int(config["server_now"]) - int(config["last_end_time"]) <= int(config['max-short-term']): 
        log(6, "DEBUG", "Normal Logic", "Existing data found, doing a short term backfill for " + str(int(config["server_now"]) - int(config["last_end_time"])) + " seconds\rlast_end_time: " + str(config["last_end_time"]) + "\rnow: " + str(config["server_now"]) + "\rdelta: " + str(int(config["server_now"]) - int(config["last_end_time"])) + "\rmax-short-term: " + str(config["max-short-term"]))
        short_term_backfill()
    else:
        log(6, "WARN", "Normal Logic", "Very long time-range found (" + str(int(config["server_now"]) - int(config["last_end_time"])) + " seconds), so pushing to general backfill logic.")
        update_rest_config("backfill-status", "general")
        update_rest_config("earliest-time", config["last_end_time"])
        update_rest_config("latest-time", "")
        launch_primary_logic()
                
def no_backfill_logic():
    ###################
    ##### #6 above
    ###################
    if config["last_end_time"] == "" or config["last_end_time"] == 0:
        log(6, "INFO", "No-Backfill Logic", "No existing data, doing a short term backfill for 10 minutes")
        default_config_last_end_time()
        short_term_backfill()
    elif int(config["server_now"]) - int(config["last_end_time"]) <= int(config['max-short-term']): 
        log(6, "DEBUG", "No-Backfill Logic", "Existing data found, doing a short term backfill for " + str(config["server_now"] - config["last_end_time"]) + " seconds\rlast_end_time: " + str(config["last_end_time"]) + "\rnow: " + str(config["server_now"]) + "\rdelta: " + str(int(config["server_now"]) - int(config["last_end_time"])) + "\rmax-short-term: " + str(config["max-short-term"]))
        short_term_backfill()
    else:
        log(6, "WARN", "No-Backfill Logic", "Very long time-range found (" + str(config["server_now"] - config["last_end_time"]) + " seconds). Under normal logic we would push to a general backfill, but because no-backfill is selected, we are going to start over with recent data.")
        default_config_last_end_time()
        short_term_backfill()
    update_rest_config("backfill-status", "normal")
    update_rest_config("earliest-time", "")
    update_rest_config("latest-time", "")
        
def general_backfill_logic():
    ###################
    ##### #13 above
    ###################
    if int(config["server_now"]) - int(config["earliest-time"]) > int(config['long-term-range']): 
        log(13, "INFO", "General Backfill Logic", "Time delta between now and earliest-time is greater than long-term-range, so backfilling and then moving to next window.\rearliest-time: " + str(config["earliest-time"]) + "\rnow: " + str(config["server_now"]) + "\rdelta: " + str(int(config["server_now"]) - int(config["earliest-time"])) + "\rmax backfill time range: " + str(config["long-term-range"]))
        earliest = int(config["earliest-time"])
        latest = int(config["earliest-time"]) + int(config['long-term-range'])
        duplicate_result = check_for_duplicates(earliest, latest)
        if duplicate_result == 0:
            long_term_backfill(earliest, latest)
            update_rest_config("earliest-time", latest)
        else:
            update_rest_config("earliest-time", duplicate_result+1)
        log(13, "INFO", "General Backfill Logic", "Remaining Time in backfill is " + str(round((config["server_now"] - int(latest)) / 3600 / 24)) + " days.")
    else:
        log(13, "INFO", "General Backfill Logic", "Time delta between now and earliest-time is less than long-term-range, so backfilling and then switching to normal mode.\rearliest-time: " + str(config["earliest-time"]) + "\rnow: " + str(config["server_now"]) + "\rdelta: " + str(int(config["server_now"]) - int(config["earliest-time"])) + "\rmax backfill time range: " + str(config["long-term-range"]))
        earliest = int(config["earliest-time"])
        latest = int(config["server_now"])
        duplicate_result = check_for_duplicates(earliest, latest)
        if duplicate_result == 0:
            long_term_backfill(earliest, latest)
            update_rest_config("backfill-status", "normal")
            update_rest_config("earliest-time", "")
            update_rest_config("latest-time", "")
        else:
            update_rest_config("earliest-time", duplicate_result+1)
        
      
def selective_backfill_logic():
    ###################
    ##### #10 above
    ###################
    if int(config["latest-time"]) - int(config["earliest-time"]) > int(config['long-term-range']): 
        log(10, "INFO", "Selective Backfill Logic", "Time delta between now and earliest-time is greater than long-term-range, so backfilling and then moving to next window.\rearliest-time: " + str(config["earliest-time"]) + "\rlatest-time: " + str(config["latest-time"]) + "\rdelta: " + str(int(config["latest-time"]) - int(config["earliest-time"])) + "\rmax backfill time range: " + str(config["long-term-range"]))
        earliest = int(config["earliest-time"])
        latest = int(config["earliest-time"]) + int(config['long-term-range'])
        duplicate_result = check_for_duplicates(earliest, latest)
        if duplicate_result == 0:
            long_term_backfill(earliest, latest)
            update_rest_config("earliest-time", latest)
        else:
            update_rest_config("earliest-time", duplicate_result+1)
        log(10, "INFO", "Selective Backfill Logic", "Remaining Time in backfill is " + str(round((int(config["latest-time"]) - int(latest)) / 3600 / 24)) + " days.")
    else:
        log(10, "INFO", "Selective Backfill Logic", "Time delta between now and earliest-time is less than long-term-range, so backfilling and then switching to normal mode.\rearliest-time: " + str(config["earliest-time"]) + "\rlatest-time: " + str(config["latest-time"]) + "\rdelta: " + str(int(config["latest-time"]) - int(config["earliest-time"])) + "\rmax backfill time range: " + str(config["long-term-range"]))
        earliest = int(config["earliest-time"])
        latest = int(config["latest-time"])
        duplicate_result = check_for_duplicates(earliest, latest)
        if duplicate_result == 0:
            long_term_backfill(earliest, latest)
            update_rest_config("backfill-status", "normal")
            update_rest_config("earliest-time", "")
            update_rest_config("latest-time", "")
        else:
            update_rest_config("earliest-time", duplicate_result+1)


def default_config_last_end_time():
    ###################
    ##### #7 above
    ###################
    config["last_end_time"] = config["server_now"] - 600
    log(7, "INFO", "Defaulting Backfill Time", "Set default config[\"last_end_time\"] to " + str(config["last_end_time"]) + " (server_now: " + str(config["server_now"]) + ")")


def short_term_backfill():
    ###################
    ##### #8 above
    ###################
    log(8, "INFO", "Short Term Backfill", "Kicking off backfill from config[\"last_end_time\"]: " + str(config["last_end_time"]))
    log(8, "DEBUG", "Short Term Backfill", "Conf:\r" + json.dumps(config, indent=4))
    searchquery_normal = 'search [search earliest=' + str(config["last_end_time"]) + ' `auditindex` `auditsourcetype` info=failed OR info=completed OR info=canceled "total_run_time" total_run_time>=0 | stats values(searchid) as search | eval search="(searchid=" . mvjoin(search, " OR searchid=") . ")" ] `FillSearchHistory_Search` | where finaltime>=' + str(config["last_end_time"]) + ' | search NOT [search index=`FillSearchHistory_SummaryIndex` sourcetype=searchactivity:searchhistory finaltime=' + str(config["last_end_time"]) + '* | stats count by searchid | eval search="(searchid=" . mvjoin(searchid, " OR searchid=") . ")"| stats values(search) as search | eval search="(" . mvjoin(search, " OR ") . ")"] | collect index=`FillSearchHistory_SummaryIndex` sourcetype=searchactivity:searchhistory '
    log(8, "DEBUG", "Short Term Backfill", "Running query: " + searchquery_normal)
    job = service.jobs.create(searchquery_normal, **kwargs_normalsearch)
    stats = {}
    while True:
        while not job.is_ready():
            pass
        job.refresh()
        stats = {"isDone": job["isDone"],
             "doneProgress": float(job["doneProgress"])*100,
              "eventCount": int(job["eventCount"]),
              "resultCount": int(job["resultCount"])}
                
        if stats["isDone"] == "1":
            break

        time.sleep(2)
    log(8, "DEBUG", "Short Term Backfill", "Search Complete. Stats:\r" + json.dumps(stats))
    

def long_term_backfill(earliest, latest):
    ###################
    ##### #11 above (also #12)
    ###################
    log(11, "INFO", "Long Term Backfill", "Kicking off backfill from " + str(earliest) + " to " + str(latest))
    log(11, "DEBUG", "Long Term Backfill", "Conf:\r" + json.dumps(config, indent=4))
    searchquery_normal = 'search earliest=' + str(int(earliest) - int(config["buffer-in-hours-for-long-term-backfill"])*3600) + ' latest=' + str(latest) + ' `FillSearchHistory_Search` | where finaltime >= ' + str(earliest) + ' | search NOT [search index=`FillSearchHistory_SummaryIndex` sourcetype=searchactivity:searchhistory finaltime=' + str(earliest) + '* | stats count by searchid | eval search="(searchid=" . mvjoin(searchid, " OR searchid=") . ")"| stats values(search) as search | eval search="(" . mvjoin(search, " OR ") . ")"] | collect index=`FillSearchHistory_SummaryIndex` sourcetype=searchactivity:searchhistory'
    log(11, "DEBUG", "Long Term Backfill", "Running query: " + searchquery_normal)
    stats = {}
    job = service.jobs.create(searchquery_normal, **kwargs_normalsearch)
    while True:
        while not job.is_ready():
            pass
        job.refresh()
        stats = {"isDone": job["isDone"],
             "doneProgress": float(job["doneProgress"])*100,
              "eventCount": int(job["eventCount"]),
              "resultCount": int(job["resultCount"])}
                
        if stats["isDone"] == "1":
            break

        time.sleep(2)
    log(11, "DEBUG", "Long Term Backfill", "Search Complete. Stats:\r" + json.dumps(stats))
    
def check_for_duplicates(earliest, latest):
    ###################
    ##### Not in diagram! Idea is that if I'm about to backfill a window, but there's already data there, I probably don't want to end up with duplicates, so I'll skip it.
    ##### This is a very coarse tool (skipping the entire window if even one event is found), but it's the safest tool I can find. 
    ##### If you run into duplicates, you should manually fill the gaps with the selective filter. By default, we will continue on with the next time window. 
    ###################
    if int(config["check-for-duplicates"]) != 1:
        log(91, "WARN", "Duplicate Check", "Duplicate data check disabled by config[\"check-for-duplicates\"]. Adjust in advanced configuration if not desired (probably should never be anything other than 1, unless instructed due to a bug).")
        return 0
    dup_check_earliest = earliest + 1 #There is special handling for the first second of a timeslot, so we automatically skip that here (it's expected, and handled in the normal backfill search)
    dup_check_latest = latest
    searchquery_normal = '| tstats count min(_time) as mintime max(_time) as maxtime where earliest=' + str(dup_check_earliest) + ' latest=' + str(dup_check_latest) + ' index=`FillSearchHistory_SummaryIndex` sourcetype=searchactivity:searchhistory'
    job = service.jobs.create(searchquery_normal, **kwargs_normalsearch)
    while True:
        job.refresh()
        stats = {"isDone": job["isDone"],
                "doneProgress": float(job["doneProgress"])*100}
                
        if stats["isDone"] == "1":
            break

        time.sleep(2)

    countjobs = 0
    for result in results.ResultsReader(job.results()):
        if result["count"] == "0":
            log(91, "INFO", "Duplicate Check", "Duplicate data check found no existing data, so backfill can continue. Result:\r" + json.dumps(result))
            return 0
        else:
            log(91, "WARN", "Duplicate Check", "Duplicate data check found existing data! Don't backfill (you can fill manually with selective backfills). Result:\r" + json.dumps(result))
            return int(result["maxtime"])
        
    
# Let's call our main function!

main()