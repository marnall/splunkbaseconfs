

import splunklib.results as results
import splunklib.client as client
import time
import sys
from datetime import datetime
from random import randint
from inspect import currentframe, getframeinfo
RunningID = str(randint(1000000002,10000000000)-1)


sessionKey = ""

for line in sys.stdin:
  sessionKey = line

import splunk.entity, splunk.Intersplunk
settings = dict()
records = splunk.Intersplunk.readResults(settings = settings, has_header = True)
entity = splunk.entity.getEntity('/server','settings', namespace='search_activity', sessionKey=sessionKey, owner='-')
mydict = dict()
mydict = entity
myPort = mydict['mgmtHostPort']


###################
##### Config Choices
###################
MinimumSearchAge = 600      # Default 600 seconds. Ensures that we have enough time to capture sharing activities

DaysPerBackfillJob = 3      # Default 3 days. This throttles how long we run backup jobs. 

BufferDaysForOldJobs = 1    # Default 1 day. Since we only record completed jobs (with start and end logs) this will allow
                            # us to capture jobs up to 24 hours * BufferDaysForOldJobs long. If set to 1, and a job runs for 26
                            # hours, it will not be captured.
                            # The actual backfill search jobs will run for BufferDaysForOldJobs + DaysPerBackfillJob days in total.

HowManyHoursToRunShortTerm = 1  # At the bottom, we toggle between short term and long term mode. Short term is much faster
                                # but requires a subsearch to work. That subsearch by default needs to complete within 60 
                                # seconds. This setting defines the difference between the timestamp of the newest event and
                                # the current time.  

DEBUG = 1                   # Records debug information. Should almost never be turned off, because we wouldn't detect failures.

###################
##### Global Variables -- Do not change
###################
service = client.Service(token=sessionKey, host="127.0.0.1", port=myPort, user="admin")
kwargs_normalsearch = {"exec_mode": "normal", "app": "search_activity"}
backfill_search_window = -1     # The configured backfill window (does not change)
backfill_search_internal = -1   # The internal tracker for backfill in progress (changes as backfill completes until it equals 1)
actual_backfill_time = -1       # Backfill to actually use for this job
actual_backfill_time_in_seconds_ago = -1       # Backfill to actually use for this job
DoWeHaveDataInTSIDXToday = 0    # Self Explanatory

maxstarttime = -1   # The start time of the most recent search in the tsidx
maxfinaltime = -1   # The end time of the most recent search in the tsidx 
now = -1            # The current time on the search head
tsidxlag = -1       # now - maxfinaltime
newtimetobackfill = -1 # We are going to modify the timetobackfill as we proceed through the backfill. This is the updated time

final_time_earliest = -1    # This is the earliest finaltime that we will accept, and represents the latest end time from 
                            # the last backfill job (remembering that we have a start and end time)
search_time_earliest = -1   # This is the time range of the actual backfill search.
search_time_latest = -1     # This is the time range of the actual backfill search.

BufferInSeconds = BufferDaysForOldJobs * 24 * 3600 # search_time_earliest = final_time_earliest - BufferInSeconds. Same as BufferDaysForOldJobs

GlobalLatestEventBoundary = -1

#uncertainorigin

shouldbackfill = 1


###################
##### Search one: Make sure that no job is already running before we start the backfill work. 
###################
searchquery_normal = '| rest splunk_server=local "/servicesNS/admin/-/search/jobs"| search dispatchState="RUNNING" OR dispatchState="FINALIZING" OR dispatchState="QUEUED" OR dispatchState="PARSING" title!="| rest*" title="*FillSearchHistory*" OR remoteSearch="*info=failed OR info=completed OR info=canceled *total_run_time* *searchid*" '
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

if countjobs > 0:
    sys.stdout.write("[" + str(datetime.now()) + " - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Jobs already running.. canceling\n")
    sys.stdout.flush()
    exit()
if DEBUG == 1:
    sys.stdout.write("[" + str(datetime.now()) + " - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Just ran query (searchid=\"" + job.name + "\"): \n" + searchquery_normal + "\n")

#sys.stdout.write("[" + str(datetime.now()) + " - DEBUG - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Variable Debug \nsearch_time_earliest: " + str(search_time_earliest) + "\nfinal_time_earliest: "  + str(final_time_earliest) + "\nsearch_time_latest: " + str(search_time_latest) + "\nmaxfinaltime: " + str(maxfinaltime) + "\nmaxstarttime: " + str(maxstarttime) + "\ntsidxlag: " + str(tsidxlag) + "\nnow: " + str(now) + "\nactual_backfill_time_in_seconds_ago: " + str(actual_backfill_time_in_seconds_ago) + "\nactual_backfill_time: " + str(actual_backfill_time) + "\nnewtimetobackfill:" + str(newtimetobackfill) + "\n")

###################
##### Search two: Make sure that we've configured backfill to run. If this fails, users need to go to the setup page.
###################
searchquery_normal = '| rest splunk_server=local "/servicesNS/admin/search_activity/properties/macros/backfill_search_window/definition"'
job = service.jobs.create(searchquery_normal, **kwargs_normalsearch)

while True:
    job.refresh()
    stats = {"isDone": job["isDone"],
             "doneProgress": float(job["doneProgress"])*100}

    if stats["isDone"] == "1":
        break
    time.sleep(2)

if DEBUG == 1:
        sys.stdout.write("[" + str(datetime.now()) + " - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Just ran query (searchid=\"" + job.name + "\"): \n" + searchquery_normal + "\n")


for result in results.ResultsReader(job.results()):
    backfill_search_window = int(result['value'])
    if DEBUG == 1:
        sys.stdout.write("[" + str(datetime.now()) + " - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Got a backfill_search_window of " + str(backfill_search_window) + "\n")
        sys.stdout.flush()

if backfill_search_window == -1 or backfill_search_window == "" or backfill_search_window is None:
    sys.stdout.write("[" + str(datetime.now()) + " - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] backfill_search_window macro not configured. No visibility into whether we want to backfill or not, so quiting. Please visit setup page to configure.\n")
    sys.stdout.flush()
    exit()


#sys.stdout.write("[" + str(datetime.now()) + " - DEBUG - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Variable Debug \nsearch_time_earliest: " + str(search_time_earliest) + "\nfinal_time_earliest: "  + str(final_time_earliest) + "\nsearch_time_latest: " + str(search_time_latest) + "\nmaxfinaltime: " + str(maxfinaltime) + "\nmaxstarttime: " + str(maxstarttime) + "\ntsidxlag: " + str(tsidxlag) + "\nnow: " + str(now) + "\nactual_backfill_time_in_seconds_ago: " + str(actual_backfill_time_in_seconds_ago) + "\nactual_backfill_time: " + str(actual_backfill_time) + "\nnewtimetobackfill:" + str(newtimetobackfill) + "\n")

###################
##### Search three: Check the current status of our backfill job.
###################

searchquery_normal = '| rest splunk_server=local "/servicesNS/admin/search_activity/properties/macros/backfill_search_internal/definition"'
job = service.jobs.create(searchquery_normal, **kwargs_normalsearch)

while True:
    job.refresh()
    stats = {"isDone": job["isDone"],
             "doneProgress": float(job["doneProgress"])*100}

    if stats["isDone"] == "1":
        break
    time.sleep(2)

if DEBUG == 1:
        sys.stdout.write("[" + str(datetime.now()) + " - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Just ran query (searchid=\"" + job.name + "\"): \n" + searchquery_normal + "\n")


for result in results.ResultsReader(job.results()):
    backfill_search_internal = int(result['value'])
    if DEBUG == 1:
        sys.stdout.write("[" + str(datetime.now()) + " - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Got a backfill_search_internal of " + str(backfill_search_internal) + "\n")
        sys.stdout.flush()
if backfill_search_internal == 0:
    sys.stdout.write("[" + str(datetime.now()) + " - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Seems we are up to date.. using our internal backfill window of 0\n")
    actual_backfill_time = backfill_search_internal
if backfill_search_internal == -1 or backfill_search_internal == "" or backfill_search_internal is None:
    sys.stdout.write("[" + str(datetime.now()) + " - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Got no internal backfill time.. using the configured backfill_search_window (" + str(backfill_search_window) + ")\n")
    actual_backfill_time = backfill_search_window
else:
    sys.stdout.write("[" + str(datetime.now()) + " - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Got an internal backfill time of " + str(backfill_search_internal) + ". Ignoring the default configured backfill_search_window (" + str(backfill_search_window) + ")\n")
    actual_backfill_time = backfill_search_internal
#sys.stdout.write("[" + str(datetime.now()) + " - DEBUG - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Variable Debug \nsearch_time_earliest: " + str(search_time_earliest) + "\nfinal_time_earliest: "  + str(final_time_earliest) + "\nsearch_time_latest: " + str(search_time_latest) + "\nmaxfinaltime: " + str(maxfinaltime) + "\nmaxstarttime: " + str(maxstarttime) + "\ntsidxlag: " + str(tsidxlag) + "\nnow: " + str(now) + "\nactual_backfill_time_in_seconds_ago: " + str(actual_backfill_time_in_seconds_ago) + "\nactual_backfill_time: " + str(actual_backfill_time) + "\nnewtimetobackfill:" + str(newtimetobackfill) + "\n")

###################
##### Search four: pull data from the existing TSIDX
###################



searchquery_normal = '| tstats local=t max(_time) as maxstarttime  from `SA_SearchHistory` | eval range_low=maxstarttime-3600 | eval range_high=maxstarttime+3600 | map search="| tstats local=t max(_time) as maxstarttime max(finaltime) as maxfinaltime  from `SA_SearchHistory` where earliest=$range_low$ latest=$range_high$| eval maxfinaltime=round(coalesce(maxfinaltime, maxstarttime)-0.5,0) | eval now=now() | eval tsidxlag = now-maxfinaltime"'
job = service.jobs.create(searchquery_normal, **kwargs_normalsearch)

while True:
    job.refresh()
    stats = {"isDone": job["isDone"],
             "doneProgress": float(job["doneProgress"])*100}

    if stats["isDone"] == "1":
        break
    time.sleep(2)

if DEBUG == 1:
        sys.stdout.write("[" + str(datetime.now()) + " - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Just ran query (searchid=\"" + job.name + "\"): \n" + searchquery_normal + "\n" )

#sys.stdout.write("[" + str(datetime.now()) + " - DEBUG - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Variable Debug \nsearch_time_earliest: " + str(search_time_earliest) + "\nfinal_time_earliest: "  + str(final_time_earliest) + "\nsearch_time_latest: " + str(search_time_latest) + "\nmaxfinaltime: " + str(maxfinaltime) + "\nmaxstarttime: " + str(maxstarttime) + "\ntsidxlag: " + str(tsidxlag) + "\nnow: " + str(now) + "\nactual_backfill_time_in_seconds_ago: " + str(actual_backfill_time_in_seconds_ago) + "\nactual_backfill_time: " + str(actual_backfill_time) + "\nnewtimetobackfill:" + str(newtimetobackfill) + "\n")



if job.dispatchState != "FAILED": #No TSIDX yet..
    for result in results.ResultsReader(job.results()):
        maxstarttime = int(result['maxstarttime'])
        tsidxlag = int(result['tsidxlag'])
        now = int(result['now'])
        maxfinaltime = int(result['maxfinaltime'])
        DoWeHaveDataInTSIDXToday = 1


#sys.stdout.write("[" + str(datetime.now()) + " - DEBUG - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Variable Debug \nsearch_time_earliest: " + str(search_time_earliest) + "\nfinal_time_earliest: "  + str(final_time_earliest) + "\nsearch_time_latest: " + str(search_time_latest) + "\nmaxfinaltime: " + str(maxfinaltime) + "\nmaxstarttime: " + str(maxstarttime) + "\ntsidxlag: " + str(tsidxlag) + "\nnow: " + str(now) + "\nactual_backfill_time_in_seconds_ago: " + str(actual_backfill_time_in_seconds_ago) + "\nactual_backfill_time: " + str(actual_backfill_time) + "\nnewtimetobackfill:" + str(newtimetobackfill) + "\n")
###################
##### Search five: Only applicable if there's no data in the TSIDX. We need to know what time it is right now, so we can calculate differences.
###################

if now == -1:

    searchquery_normal = "| stats count | eval now=now()"
    job = service.jobs.create(searchquery_normal, **kwargs_normalsearch)

    while True:
        job.refresh()
        stats = {"isDone": job["isDone"],
                 "doneProgress": float(job["doneProgress"])*100}

        if stats["isDone"] == "1":
            break

        time.sleep(2)

    for result in results.ResultsReader(job.results()):
        now = int(result['now'])

    if backfill_search_internal == 1: #If we have no data, but the backfill has supposedly completed..
        sys.stdout.write("[" + str(datetime.now()) + " - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Resetting internal backfill time (1) to default. This should account for where due to bugs the backfill supposedly completed, but there was actually no data captured. It is intended to be run once after you upgrade the app, fixing the bugs. New backfill time:" + str(backfill_search_window) + "\n")  
        backfill_search_internal = backfill_search_window
        actual_backfill_time = backfill_search_window

GlobalLatestEventBoundary = now - MinimumSearchAge

#sys.stdout.write("[" + str(datetime.now()) + " - DEBUG - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Variable Debug \nsearch_time_earliest: " + str(search_time_earliest) + "\nfinal_time_earliest: "  + str(final_time_earliest) + "\nsearch_time_latest: " + str(search_time_latest) + "\nmaxfinaltime: " + str(maxfinaltime) + "\nmaxstarttime: " + str(maxstarttime) + "\ntsidxlag: " + str(tsidxlag) + "\nnow: " + str(now) + "\nactual_backfill_time_in_seconds_ago: " + str(actual_backfill_time_in_seconds_ago) + "\nactual_backfill_time: " + str(actual_backfill_time) + "\nnewtimetobackfill:" + str(newtimetobackfill) + "\n")

if actual_backfill_time < 24*3600*365*10 and actual_backfill_time >= 2 and backfill_search_internal != -1:

    actual_backfill_time = now - actual_backfill_time
    sys.stdout.write("[" + str(datetime.now()) + " - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Got a legacy internal backfill time of " + str(backfill_search_internal) + ". Switching this to the new and improved epoch format: " + str(actual_backfill_time) + "\n")
    actual_backfill_time_in_seconds_ago = now - actual_backfill_time

elif actual_backfill_time == 1:
    actual_backfill_time_in_seconds_ago = 1
    actual_backfill_time = now - 1
    
elif actual_backfill_time == -1:
    sys.stdout.write("[" + str(datetime.now()) + " - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] ERROR. Got an actual_backfill_time of -1 too far in.. not sure why, but managing it.\n")
    actual_backfill_time_in_seconds_ago = 1 
    actual_backfill_time = now - 1

else:
    actual_backfill_time_in_seconds_ago = now - actual_backfill_time

#sys.stdout.write("[" + str(datetime.now()) + " - DEBUG - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Variable Debug \nsearch_time_earliest: " + str(search_time_earliest) + "\nfinal_time_earliest: "  + str(final_time_earliest) + "\nsearch_time_latest: " + str(search_time_latest) + "\nmaxfinaltime: " + str(maxfinaltime) + "\nmaxstarttime: " + str(maxstarttime) + "\ntsidxlag: " + str(tsidxlag) + "\nnow: " + str(now) + "\nactual_backfill_time_in_seconds_ago: " + str(actual_backfill_time_in_seconds_ago) + "\nactual_backfill_time: " + str(actual_backfill_time) + "\nnewtimetobackfill:" + str(newtimetobackfill) + "\n")


###################
##### Time Management Logic
#####   We have three different conditions we need to account for here. The first is that we are brand new to the world, with no data and no backfill 
#####   placeholder. The second is that we are mid backfill (backfill_search_internal > 1). The third is that our backfill is complete and we are 
#####   going forward with our daily business. For each of these situations, we have to account for whether we have many days of backfill to do or if
#####   we can complete it just one search. 
###################





if DEBUG == 1:
        sys.stdout.write("[" + str(datetime.now()) + " - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Entering time management logic: ")

##### Default out if the backfill time is abnormal.
if actual_backfill_time_in_seconds_ago < 0:
    actual_backfill_time_in_seconds_ago = 1 
    actual_backfill_time = now - 1


##### There's no data in the sytem yet (i.e., our first search)
if DoWeHaveDataInTSIDXToday == 0: 
    if DEBUG == 1:
        sys.stdout.write(" 1 ")
    
    final_time_earliest = now - actual_backfill_time_in_seconds_ago  
    search_time_earliest = final_time_earliest - BufferInSeconds # Buffer for long searches

    if actual_backfill_time_in_seconds_ago < DaysPerBackfillJob*24*3600: # Short Term Backfill
    
        if DEBUG == 1:
          sys.stdout.write(" - a")
        search_time_latest = GlobalLatestEventBoundary
        newtimetobackfill = 1
    else: #We are going to backfill

        if DEBUG == 1:
          sys.stdout.write(" - b")
        search_time_latest = final_time_earliest + DaysPerBackfillJob*24*3600 #Make our latest =  now - our current backfill position + 3 days (effectively, four days of data)
        newtimetobackfill = actual_backfill_time + DaysPerBackfillJob*24*3600 #Reduce time to backfill by 3 days


##### We do have data in the TSIDX, but we still have some backfilling to do. 
elif actual_backfill_time_in_seconds_ago >= 2:

    if DEBUG == 1:
        sys.stdout.write(" 2 ")

    final_time_earliest = actual_backfill_time 
    search_time_earliest = final_time_earliest - BufferInSeconds # Buffer for long searches

    if actual_backfill_time_in_seconds_ago < DaysPerBackfillJob*24*3600: # We are not going to backfill

        if DEBUG == 1:
          sys.stdout.write(" - a")
        search_time_latest = GlobalLatestEventBoundary
        newtimetobackfill = 1
    else:

        if DEBUG == 1:
          sys.stdout.write(" - b")
        search_time_latest = final_time_earliest + DaysPerBackfillJob*24*3600 #Make our latest =  now - our current backfill position + 3 days (effectively, four days of data)
        newtimetobackfill = actual_backfill_time + DaysPerBackfillJob*24*3600



###### We do have data in the TSIDX, we have no backfilling to do, and there's been at least two seconds between now and the most recent data point in our TSIDX
###### Effectively, this is going to backfill up to 3 days from the last point that we have data. If there's a gap of more than 3 days, that will need to be manually bridged.
elif tsidxlag > 1:

    if DEBUG == 1:
        sys.stdout.write(" 3 ")
    final_time_earliest = int(maxfinaltime)
    search_time_earliest = final_time_earliest - BufferInSeconds

    if tsidxlag < DaysPerBackfillJob*24*3600:

        if DEBUG == 1:
          sys.stdout.write("  - a")
        search_time_latest = GlobalLatestEventBoundary

    else:
        if DEBUG == 1:
          sys.stdout.write("  - b")
        search_time_latest = final_time_earliest + DaysPerBackfillJob*24*3600


# Eeesh
else:
    sys.stdout.write("[" + str(datetime.now()) + " - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Something went dramatically wrong here... (timeago not defined when latest is)\n")
    sys.stdout.flush()
    exit()


#sys.stdout.write("[" + str(datetime.now()) + " - DEBUG - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Variable Debug \nsearch_time_earliest: " + str(search_time_earliest) + "\nfinal_time_earliest: "  + str(final_time_earliest) + "\nsearch_time_latest: " + str(search_time_latest) + "\nmaxfinaltime: " + str(maxfinaltime) + "\nmaxstarttime: " + str(maxstarttime) + "\ntsidxlag: " + str(tsidxlag) + "\nnow: " + str(now) + "\nactual_backfill_time_in_seconds_ago: " + str(actual_backfill_time_in_seconds_ago) + "\nactual_backfill_time: " + str(actual_backfill_time) + "\nnewtimetobackfill:" + str(newtimetobackfill) + "\n")

#abcd
# In all eventualities..
if DEBUG == 1:
        sys.stdout.write("\n")
        sys.stdout.flush()
        sys.stdout.write("[" + str(datetime.now()) + " - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Just ran query (searchid=\"" + job.name + "\"): \n" + searchquery_normal + "\n")
        sys.stdout.write("[" + str(datetime.now()) + " - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] We are running our search over " + str(search_time_earliest) + " to " + str(search_time_latest) + ". Also:\nsearch_time_earliest: " + str(search_time_earliest) + "\nfinal_time_earliest: "  + str(final_time_earliest) + "\nsearch_time_latest: " + str(search_time_latest) + "\nmaxfinaltime: " + str(maxfinaltime) + "\nmaxstarttime: " + str(maxstarttime) + "\ntsidxlag: " + str(tsidxlag) + "\nnow: " + str(now) + "\nactual_backfill_time_in_seconds_ago: " + str(actual_backfill_time_in_seconds_ago) + "\nactual_backfill_time: " + str(actual_backfill_time) + "\nnewtimetobackfill:" + str(newtimetobackfill) + "\n")
        sys.stdout.flush()



###################
##### Search six: Let's double check one last time that we're not running another backfill...
###################

searchquery_normal = '| rest splunk_server=local "/servicesNS/admin/-/search/jobs"| search dispatchState="RUNNING" OR dispatchState="FINALIZING" OR dispatchState="QUEUED" OR dispatchState="PARSING" title!="| rest*" title="*FillSearchHistory*" OR remoteSearch="*info=failed OR info=completed OR info=canceled *total_run_time* *searchid*" '
job = service.jobs.create(searchquery_normal, **kwargs_normalsearch)

while True:
    job.refresh()
    stats = {"isDone": job["isDone"],
             "doneProgress": float(job["doneProgress"])*100}
             
    if stats["isDone"] == "1":
        break

    time.sleep(1)

countjobs = 0
for result in results.ResultsReader(job.results()):
    countjobs += 1

if countjobs > 0:
    sys.stdout.write("[" + str(datetime.now()) + " - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Jobs already running.. canceling\n")
    sys.stdout.flush()
    exit()
if DEBUG == 1:
        sys.stdout.write("[" + str(datetime.now()) + " - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Just ran query (searchid=\"" + job.name + "\"): \n" + searchquery_normal + "\n")




###################
##### Update Macro Logic: If we are in the middle of the backfill, we want to have code that will update the macro once the search completes.
###################

UpdateMacroSearchString = ""

if newtimetobackfill != -1:
    UpdateMacroSearchString = '| stats count | map search="| stats count | eval count=$count$ | where count > 0  | updatemacro macroname=\\"backfill_search_internal\\" macrovalue=\\"' + str(newtimetobackfill) + '\\"" '

else:
    sys.stdout.write("[" + str(datetime.now()) + " - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] No Backfill Macro Update Required\n")
    sys.stdout.flush()


###################
##### Short Term vs Long Term Logic
###################


searchquery_normal = ""
if (now - maxfinaltime) > HowManyHoursToRunShortTerm*3600: # If we're running over more than an hour of data
    searchquery_normal = 'search `FillSearchHistory_Search` | where finaltime >= ' + str(final_time_earliest) + ' | search NOT [| tstats local=t count from `SA_SearchHistory` where finaltime = ' + str(final_time_earliest) + '* by searchid | eval search="(searchid=" . mvjoin(searchid, " OR searchid=") . ")"| stats values(search) as search | eval search= "(" . mvjoin(search, " OR ") . ")"] `FillSearchHistory_TSCollect` ' + UpdateMacroSearchString
else:
    searchquery_normal = 'search [search earliest=' + str(final_time_earliest) + ' `auditindex` `auditsourcetype` info=failed OR info=completed OR info=canceled "total_run_time" total_run_time>=0 | stats values(searchid) as search | eval search="(searchid=" . mvjoin(search, " OR searchid=") . ")" ] `FillSearchHistory_Search` | where finaltime >= ' + str(final_time_earliest) + ' | search NOT [| tstats local=t count from `SA_SearchHistory` where finaltime = ' + str(final_time_earliest) + '* by searchid | eval search="(searchid=" . mvjoin(searchid, " OR searchid=") . ")"| stats values(search) as search | eval search="(" . mvjoin(search, " OR ") . ")"] `FillSearchHistory_TSCollect` ' + UpdateMacroSearchString



###################
##### Search seven: The Backfill.
###################


kwargs_normalsearch = {"exec_mode": "normal", "app": "search_activity", "earliest_time": str(search_time_earliest), "latest_time": str(search_time_latest)}

job = service.jobs.create(searchquery_normal, **kwargs_normalsearch)

if DEBUG == 1:
        sys.stdout.write("[" + str(datetime.now()) + " - id=" + RunningID + " line=" + str(getframeinfo(currentframe()).lineno) + "] Just ran query (searchid=\"" + job.name + "\"): \n" + searchquery_normal + "\n")








