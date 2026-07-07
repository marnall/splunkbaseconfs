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


####
# Conversion Script To Do:
# 1. Add Disable Search after conversion-status = complete



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
service = client.Service(token=sessionKey, host="127.0.0.1", port=myPort, user="admin", app="search_activity")
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
            myindex.submit(json.dumps(log, sort_keys=True), sourcetype="searchactivity:log", source="searchactivity:conversion")
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
        
def disable_search(name):
    ###################
    ##### UTILITY Function: Disable a given search
    ###################
    service2 = client.Service(token=sessionKey, host="127.0.0.1", port=myPort, user="nobody")
    for ss in service.saved_searches:
        if name == ss.name:
            log(15, "INFO", "Disabling Search", "Disabling search " + name)
            ss.disable()

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
    searchquery_normal = '| rest splunk_server=local "/servicesNS/admin/-/search/jobs"| search dispatchState="RUNNING" OR dispatchState="FINALIZING" OR dispatchState="QUEUED" OR dispatchState="PARSING" title!="| rest*" title="*saconversion*" '
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
        
def launch_primary_logic():
    ###################
    ##### #5 above
    ###################
    if config["conversion-status"] == "complete":
        log(5, "INFO", "Primary Logic", "Conversion Complete -- this scheduled search should be disabled (or if you're running this manually, this command is designed to convert data from Search Activity App 2.x to 3.x... so you probably don't need this.)")
        finish()
        
    elif config["conversion-status"] == "none":
        log(5, "INFO", "Primary Logic", "No conversion -- this scheduled search should be disabled (or if you're running this manually, this command is designed to convert data from Search Activity App 2.x to 3.x... so you probably don't need this.) If conversion is still needed, go through the setup process to configure it.")
        finish()
        
    elif config["conversion-status"] == "converting":
        log(5, "INFO", "Primary Logic", "Conversion in progress")
        conversion_logic()

    else:  
        log(5, "WARN", "Primary Logic", "No conversion-status defined, meaning that setup hasn't been completed yet. Cancelling.")
        finish()
        
                
def conversion_logic(): # Based on selective_backfill_logic
    ###################
    ##### #10 above
    ###################
    if int(config["conversion-latest-time"]) - int(config["conversion-earliest-time"]) > int(config['conversion-long-term-range']): 
        log(10, "INFO", "Selective Conversion Logic", "Time delta between conversion-latest-time and conversion-earliest-time is greater than conversion-long-term-range, so converting and then moving to next window.\rconversion-earliest-time: " + str(config["conversion-earliest-time"]) + "\rconversion-latest-time: " + str(config["conversion-latest-time"]) + "\rdelta: " + str(int(config["conversion-latest-time"]) - int(config["conversion-earliest-time"])) + "\rmax backfill time range: " + str(config["conversion-long-term-range"]))
        earliest = int(config["conversion-earliest-time"])
        latest = int(config["conversion-earliest-time"]) + int(config['conversion-long-term-range'])
        duplicate_result = check_for_duplicates(earliest, latest)
        if duplicate_result == 0:
            long_term_conversion(earliest, latest)
            update_rest_config("conversion-earliest-time", int(latest)+1)
        else:
            update_rest_config("conversion-earliest-time", duplicate_result+1)
        log(13, "INFO", "Selective Conversion Logic", "Remaining Time in conversion is " + str(round((int(config["conversion-latest-time"]) - int(latest)) / 3600 / 24)) + " days.")
    else:
        log(10, "INFO", "Selective Conversion Logic", "Time delta between conversion-latest-time and conversion-earliest-time is less than conversion-long-term-range, so converting and then completing.\rconversion-earliest-time: " + str(config["conversion-earliest-time"]) + "\rconversion-latest-time: " + str(config["conversion-latest-time"]) + "\rdelta: " + str(int(config["conversion-latest-time"]) - int(config["conversion-earliest-time"])) + "\rmax backfill time range: " + str(config["conversion-long-term-range"]))
        earliest = int(config["conversion-earliest-time"])
        latest = int(config["conversion-latest-time"])
        duplicate_result = check_for_duplicates(earliest, latest)
        if duplicate_result == 0:
            long_term_conversion(earliest, latest)
            update_rest_config("conversion-backfill-status", "complete")
            update_rest_config("conversion-earliest-time", "")
            update_rest_config("conversion-latest-time", "")
            disable_search("Convert Search Activity 2.x Summaries")
        else:
            update_rest_config("conversion-earliest-time", duplicate_result+1)



def long_term_conversion(earliest, latest):
    ###################
    ##### #11 above (also #12)
    ###################
    log(11, "INFO", "Long Term Conversion", "Kicking off conversion from " + str(earliest) + " to " + str(latest))
    log(11, "DEBUG", "Long Term Conversion", "Conf:\r" + json.dumps(config, indent=4))
    searchquery_normal = '| tstats values(searchspan_s) as searchspan_s values(searchspan_m) as searchspan_m values(searchspan_h) as searchspan_h values(searchspan_d) as searchspan_d values(total_run_time) as total_run_time values(result_count) as result_count values(scan_count) as scan_count values(event_count) as event_count values(Accuracy) as Accuracy values(searchtype) as searchtype values(search_status) as search_status values(savedsearch_name) as savedsearch_name values(searchcommands) as searchcommands values(user) as user values(exec_time) as exec_time values(earliest) as earliest values(latest) as latest values(actualsearch) as actualsearch values(search_et_diff) as search_et_diff values(search_lt_diff) as search_lt_diff values(time_bucket) as time_bucket values(ShouldInvestigate) as ShouldInvestigate   from splunk_search_usage.searchhistory where earliest=' + str(earliest) + ' latest=' + str(latest) + ' by searchid SearchHead _time span=1s | collect index=`FillSearchHistory_SummaryIndex` sourcetype=searchactivity:searchhistory source=searchactivity:conversion'
    log(11, "DEBUG", "Long Term Conversion", "Running query: " + searchquery_normal)
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
    log(11, "DEBUG", "Long Term Conversion", "Search Complete. Stats:\r" + json.dumps(stats))
    
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
    searchquery_normal = '| tstats count min(_time) as mintime max(_time) as maxtime where earliest=' + str(dup_check_earliest) + ' latest=' + str(dup_check_latest) + ' index=`FillSearchHistory_SummaryIndex` sourcetype=searchactivity:searchhistory source=searchactivity:conversion'
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