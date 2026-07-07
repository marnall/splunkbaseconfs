#!/usr/bin/python
import json, csv, re, os
import urllib2
import sys
import time
import splunklib.results as results
import splunklib.client as client
import urllib
import datetime
import hashlib
from operator import itemgetter

# Global variables for application logic
DEBUG = 0
earliest = "0"
latest = "100000000000000000" #very large very future timestamp
SearchConfig = []
shouldAggregate = {}
minrisklevel = 0
mode="summarize"

# First we pull the some data from the incoming tokens. There are, I'm sure, better ways to do this... but this has worked for me for 4 years so let it roll!
sessionKey = ""
owner = "" 
app = "" 
sids = dict()
stdinlines = []
for line in sys.stdin:
  stdinlines.append(line)
  m = re.search("sessionKey:\s*(.*?)$", line)
  if m:
          sessionKey = m.group(1)
  m = re.search("^search:\s*(.*?)$", line)
  if m:
    searchString = urllib.unquote(m.group(1)).split(' ')
    for term in searchString:
        pair = term.split('=')
        if len(pair) == 2 and pair[0] == "debug":
            DEBUG = int(re.sub('[^0-9]', '', pair[1]))
        elif len(pair) == 2 and pair[0] == "earliest":
            earliest = re.sub('[^0-9]', '', pair[1])
        elif len(pair) == 2 and pair[0] == "minrisklevel":
            minrisklevel = re.sub('[^0-9]', '', pair[1])
        elif len(pair) == 2 and pair[0] == "mode":
            mode = re.sub('[^a-zA-Z]', '', pair[1])
        elif len(pair) == 2 and pair[0] == "latest":
            latest = re.sub('[^0-9]', '', pair[1])
        elif len(pair) == 2:
            sids[pair[0]] = re.sub('[\'"]', '', pair[1])
  m = re.search("owner:\s*(.*?)$", line)
  if m:
          owner = m.group(1)
  m = re.search("namespace:\s*(.*?)$", line)
  if m:
          app = m.group(1)

# Now we detect the splunkd port, so we can define the base_url. 
import splunk.entity, splunk.Intersplunk
settings = dict()
records = splunk.Intersplunk.readResults(settings = settings, has_header = True)
entity = splunk.entity.getEntity('/server','settings', namespace=app, sessionKey=sessionKey, owner='-')
mydict = dict()
mydict = entity
myPort = mydict['mgmtHostPort']
base_url = "https://127.0.0.1:" + myPort

def decideOnTime(earliestTime, latestTime):
    if latestTime - earliestTime == 0:
        return earliestTime
    return earliestTime - earliestTime % 60

def addRiskContributor(result, new_contributor):
    if "risk_contributors" not in result:
        result["risk_contributors"] = new_contributor
    else:
        if type(new_contributor) != list:
            new_contributor = new_contributor.split(", ")
        if type(result["risk_contributors"]) != list:
            result["risk_contributors"] = result["risk_contributors"].split(", ")

        temp = result["risk_contributors"]
        for contributor in new_contributor:
            if contributor not in temp:
                temp.append(contributor)


        temp = list(set(temp))
        if "" in temp:
            temp.remove("")
        result["risk_contributors"] = ", ".join(temp)

def describeEvents(obj):
    if "type" not in obj:
        obj["ERROR"] = "No type found"
        return obj

    localSearchConfig = {}
    for search in SearchConfig:
        if search['paramname'] == obj['type']:
            localSearchConfig = search

    if len(localSearchConfig.keys())>0:
        if DEBUG==15: 
            print '"' + json.dumps(obj).replace('"', '""') + '"'
        counter = 0
        obj["risk_score"] = 0
        obj["risk_contributors"] = ""
        summations = {}
        for field in localSearchConfig["sumfields"]:
            summations[field] = float(0.0000)
        for field in localSearchConfig["countfields"]:
            summations[field] = {}
        obj['eventDrilldown'] = localSearchConfig['drilldownConfig']
        obj['_time'] = obj['rounded_time']
        earliestTime = 1000000000000
        latestTime = 0
        for search in obj['supplement']:
            counter += 1
            if earliestTime > search['actual_time']:
                earliestTime = search['actual_time']
            if latestTime < search['actual_time']:
                latestTime = search['actual_time']
            if "risk_score" in search and "risk_score" != "":
                if obj["risk_score"] < int(search["risk_score"]):
                    obj["risk_score"] = int(search["risk_score"])
            if "risk_contributors" in search and search["risk_contributors"] != "":
                #addRiskContributor(search, search["risk_contributors"])
                if type(search["risk_contributors"]) != list:
                    search["risk_contributors"] = search["risk_contributors"].split(", ")
                if type(obj["risk_contributors"]) != list:
                    obj["risk_contributors"] = obj["risk_contributors"].split(", ")

                temp = obj["risk_contributors"]
                for contributor in search["risk_contributors"]:
                    if contributor not in temp:
                        temp.append(contributor)
                temp = list(set(temp))
                if "" in temp:
                    temp.remove("")
                obj["risk_contributors"] = ", ".join(temp)
            for field in localSearchConfig["sumfields"]:
                try:
                    if field in search and search[field] != "":
                        summations[field] += float(search[field])
                        if DEBUG==14: 
                            print '"' + json.dumps(field).replace('"', '""') + '","' + json.dumps(search).replace('"', '""') + '","' + json.dumps(summations).replace('"', '""') + '","' + json.dumps(float(search[field])).replace('"', '""') + '"'
                except ValueError:
                        if DEBUG==20: 
                            print '"' + json.dumps(field).replace('"', '""') + '","' + json.dumps(search).replace('"', '""') + '","' + json.dumps(summations).replace('"', '""') + '","' + json.dumps(float(search[field])).replace('"', '""') + '"'
            for field in localSearchConfig["countfields"]:
                try:
                    if field in search and search[field] != "" and (type(search[field]) == str or type(search[field]) == unicode):
                        if DEBUG==26: 
                            print '"1","' + json.dumps(field).replace('"', '""') + '","' + json.dumps(search).replace('"', '""') + '","' + json.dumps(summations).replace('"', '""') + '"'
                        if search[field] in summations[field]:
                            if DEBUG==26: 
                                print '"11","' + json.dumps(field).replace('"', '""') + '","' + json.dumps(search).replace('"', '""') + '","' + json.dumps(summations).replace('"', '""') + '"'
                            summations[field][search[field]] += 1
                        else:
                            if DEBUG==26: 
                                print '"12","' + json.dumps(field).replace('"', '""') + '","' + json.dumps(search).replace('"', '""') + '","' + json.dumps(summations).replace('"', '""') + '"'
                            summations[field][search[field]] = 1
                    elif field in search and search[field] != "" and type(search[field]) == list:
                        if DEBUG==26: 
                            print '"2","' + json.dumps(field).replace('"', '""') + '","' + json.dumps(search).replace('"', '""') + '","' + json.dumps(summations).replace('"', '""') + '"'
                        for fieldvalue in search[field]:
                            if fieldvalue in summations[field]:
                                if DEBUG==26: 
                                    print '"21","' + json.dumps(field).replace('"', '""') + '","' + json.dumps(search).replace('"', '""') + '","' + json.dumps(summations).replace('"', '""') + '"'
                                summations[field][fieldvalue] += 1
                            else:
                                if DEBUG==26: 
                                    print '"22","' + json.dumps(field).replace('"', '""') + '","' + json.dumps(search).replace('"', '""') + '","' + json.dumps(summations).replace('"', '""') + '"'
                                summations[field][fieldvalue] = 1
                    else:
                        if DEBUG==26: 
                            print '"3 - ' + str(field in search) + '; ' + str(type(search[field])) + '","' + json.dumps(field).replace('"', '""') + '","' + json.dumps(search).replace('"', '""') + '","' + json.dumps(summations).replace('"', '""') + '"'
                    if DEBUG==15: 
                        print '"' + json.dumps(field).replace('"', '""') + '","' + json.dumps(search).replace('"', '""') + '","' + json.dumps(summations).replace('"', '""') + '","' + json.dumps(float(search[field])).replace('"', '""') + '"'
                except ValueError:
                        if DEBUG==20: 
                            print '"' + json.dumps(field).replace('"', '""') + '","' + json.dumps(search).replace('"', '""') + '","' + json.dumps(summations).replace('"', '""') + '","' + json.dumps(float(search[field])).replace('"', '""') + '"'
        obj["grouping_earliest"] = earliestTime
        obj["grouping_latest"] = latestTime
        obj["_time"] = decideOnTime(earliestTime, latestTime)
        obj['Message'] = localSearchConfig["summarytext"]
        obj['Message'] = obj['Message'].replace("counter", str(counter))
        textFields = localSearchConfig["summarytextfields"]
        textFields.extend(localSearchConfig["sumfields"])
        textFields.extend(localSearchConfig["countfields"])
        if DEBUG==25: 
            print '"' + json.dumps(field).replace('"', '""') + '","' + json.dumps(summations).replace('"', '""') + '","' + json.dumps(summations[field]).replace('"', '""') + '"'

        for field in textFields:
            if field in localSearchConfig["sumfields"]:
                obj['Message'] = obj['Message'].replace(field, str(summations[field]))
            if field in localSearchConfig["countfields"]:
                obj['Message'] = obj['Message'].replace(field, str(len(summations[field])))
                if DEBUG==16: 
                    print '"' + json.dumps(field).replace('"', '""') + '","' + json.dumps(summations).replace('"', '""') + '","' + json.dumps(summations[field]).replace('"', '""') + '","' + json.dumps(float(search[field])).replace('"', '""') + '"'

            else:
                if field in obj:
                    obj['Message'] = obj['Message'].replace(field, str(obj[field]))
                elif "supplement" in obj and obj["supplement"] != "" and len(obj["supplement"])>0 and field in obj['supplement'][0]:
                    obj['Message'] = obj['Message'].replace(field, str(obj["supplement"][0][field]))
        if "risk_contributors" in obj and obj["risk_contributors"] != "":
            obj['Message'] += '\r' + obj["risk_contributors"]
        return obj
    else:
        return obj

def splunkTimeToDatetimeObj(str):
    return datetime.datetime.strptime(str[:23] + "000", "%Y-%m-%dT%H:%M:%S.%f") - datetime.timedelta(hours=float(str[-6:-3]), minutes=-1*float(str[-2:])) # I hate python

def pullData(type, sid, allResults, includeTime=True, calculateMD5=True):
    searchquery_normal = '| loadjob ' + str(sid)
    if includeTime:
        searchquery_normal += ' | search _time>=' + earliest + ' _time<=' + latest
    job = service.jobs.create(searchquery_normal, **kwargs_normalsearch)
    stats = dict()
    while True:
        job.refresh()
        stats = {"isDone": job["isDone"],
                "doneProgress": float(job["doneProgress"])*100}
        if job["isDone"] == "1":
            break
        time.sleep(0.1)
    resultCount = job["resultCount"]  # Number of results this job returned
    offset = 0;                       # Start at result 0
    count = 40000;                       # Get sets of 10 results at a time
    if resultCount > 0:
        while (offset < int(resultCount)):
            kwargs_paginate = {"count": count,
                            "offset": offset,
                                "output_mode": "json"}

            # Get the search results and display them
            blocksearch_results = job.results(**kwargs_paginate)
            result_obj = json.loads(blocksearch_results.read())
            if "results" in result_obj:
                result_set = result_obj['results']
                for result in result_set:
                    if DEBUG == 1:
                        print '"' + json.dumps(result).replace('"', '""') + '"'
                    result['type'] = type
                    if calculateMD5:
                        result['unique_identifier'] = hashlib.md5( json.dumps(result, sort_keys=True) ).hexdigest()
                    if "risk_score" not in result:
                        result['risk_score'] = 0
                    if "risk_contributors" not in result:
                        result['risk_contributors'] = ""
                    if includeTime:
                        now = splunkTimeToDatetimeObj(result['_time'])
                        
                        result['actual_time'] = (now - datetime.datetime(1970,1,1)).total_seconds()
                        result['_time'] = result['actual_time']
                        round_mins = 15
                        mins = now.minute - (now.minute % round_mins) #Rounding down to nearest 5 minutes
                        newTime = datetime.datetime(now.year, now.month, now.day, now.hour, mins) + datetime.timedelta(minutes=round_mins)
                        result["rounded_time"] = (newTime - datetime.datetime(1970,1,1)).total_seconds()
                    allResults.append(result)
                offset += count

# def grabAllData(allResults):
#     for job in service.jobs.list():
#         isSearch = False
#         type = ""
#         for param in sids:
#             if param!="":
#                 if sids[param] == job["sid"]:
#                     isSearch = True
#                     type = param
#         if isSearch:
#             stats = dict()
#             while True:
#                 job.refresh()
#                 stats = {"isDone": job["isDone"],
#                         "doneProgress": float(job["doneProgress"])*100}
#                 if job["isDone"] == "1":
#                     break
#                 time.sleep(0.1)
#             resultCount = job["resultCount"]  # Number of results this job returned
#             offset = 0;                       # Start at result 0
#             count = 10000;                       # Get sets of 10 results at a time

#             while (offset < int(resultCount)):
#                 kwargs_paginate = {"count": count,
#                                 "offset": offset,
#                                 "output_mode": "json"}

#                 # Get the search results and display them
#                 r = job.results(**kwargs_paginate)
#                 obj = json.loads(r.read())['results']
#                 for result in obj:
#                     if DEBUG == 1:
#                         print '"' + json.dumps(result).replace('"', '""') + '"'
#                     result['type'] = type
#                     result['unique_identifier'] = hashlib.md5( json.dumps(result, sort_keys=True) ).hexdigest()
#                     now = datetime.datetime.strptime(result['_time'][:23] + "000", "%Y-%m-%dT%H:%M:%S.%f") + datetime.timedelta(hours=float(result['_time'][-6:-3]), minutes=-1*float(result['_time'][-2:])) # I hate python
#                     round_mins = 15
#                     mins = now.minute - (now.minute % round_mins) #Rounding down to nearest 5 minutes
#                     newTime = datetime.datetime(now.year, now.month, now.day, now.hour, mins) + datetime.timedelta(minutes=round_mins)
#                     result["_time"] = (newTime - datetime.datetime(1970,1,1)).total_seconds()
#                     allResults.append(result)
#                 offset += count

def pull_rest_config():
    _, content = splunk.rest.simpleRequest('/servicesNS/nobody/' + app + '/storage/collections/data/sa_chronology_view', sessionKey=sessionKey, getargs={'output_mode': 'json'})
    for row in json.loads(content):    
        if DEBUG == 10:
            print '"' + json.dumps(row).replace('"', '""') + '"'    
        row["drilldownConfig"] = json.loads(row["drilldownConfig"]) 
        row["summarytextfields"] = json.loads(row["summarytextfields"])
        row["sumfields"] = json.loads(row["sumfields"])
        row["countfields"] = json.loads(row["countfields"])
        shouldAggregate[row["paramname"]] = row["aggregate"]
        SearchConfig.append(row)
        if DEBUG == 11:
            print '"' + json.dumps(row).replace('"', '""') + '"'    
    return True

def new_risk_entry(result, new_score, reason):
    if "risk_score" not in result:
        result["risk_score"] = new_score
    else:
        result["risk_score"] = int(new_score) + int(result["risk_score"])
    addRiskContributor(result, reason)
    


#####
# Start of actual application logic 
####

if DEBUG > 0: 
    print "_time,user,status,message"
# print "blah,dveuve,Hello,There"
# print '"' + json.dumps(mydict.keys()).replace('"', '""') + '"'
# print '"' + json.dumps(stdinlines).replace('"', '""') + '"'
# print '"' + json.dumps(sids).replace('"', '""') + '"'

pull_rest_config()


if DEBUG == 12:
    print '"' + json.dumps(SearchConfig).replace('"', '""') + '"'
service = client.Service(token=sessionKey, host="127.0.0.1", port=myPort, user=owner)
kwargs_normalsearch = {"exec_mode": "normal", "app": app}
allResults = []

firstTimeSeenBaseline = {}
timeSeriesBaseline = {}

# grabAllData(allResults);    
# sys.exit(0)

if mode=="noaggregation":

    for search in SearchConfig:
        if search['paramname'] in sids:
            pullData(search['paramname'], sids[search['paramname']], allResults)


    dict_writer = csv.DictWriter(sys.stdout, ["_time","Message", "risk_score", "risk_contributors"], extrasaction='ignore')
    dict_writer.writeheader()
    for record in allResults:
        if "risk_score" not in record or int(record["risk_score"]) < int(minrisklevel):
            continue
        
        supplement = dict()
        
        for key in record.keys():
            if key=="_time" or ((not "_" in key or key.index("_") != 0 ) and key!="type" and key!="Message" and key!="by" and record[key]!=""):
                supplement[key] = record[key]
        record['supplement'] = list()
        record['supplement'].append(supplement)
        dict_writer.writerow(describeEvents(record))


elif mode=="annotate":
    if "riskyevents" in sids:
        print "_time,annotation_label,annotation_category"
        allRisks = []
        pullData("riskyevents" , sids["riskyevents"], allRisks)
        allRisks = sorted(allRisks, key=itemgetter('rounded_time')) 
        finalResults = []
        lastVal = {}
        for risk in allRisks:
            if risk["risk_score"] >= minrisklevel:
                #print '"' + json.dumps(risk).replace('"', '""') + '"'
                if len(lastVal) == 0:
                    lastVal = risk
                    lastVal['count'] = 1
                else:
                    if risk["rounded_time"] == lastVal["rounded_time"] and risk["risk_score"] == lastVal["risk_score"]:
                        lastVal['count'] += 1
                        addRiskContributor(lastVal, risk["risk_contributors"])
                    else:
                        lastVal['count'] += 1
                        addRiskContributor(lastVal, risk["risk_contributors"])
                        finalResults.append(lastVal)
                        
                        lastVal = risk
                        lastVal['count'] = 1
        finalResults.append(lastVal)

        for result in finalResults:
            print '"' + str(result['rounded_time']) + '","' + str(result['risk_contributors']) + '","Score: ' + str(result['risk_score']) + '"'
    else:
        print "_time,annotation_label,annotation_category"


elif mode=="anomalydetection":
    print "_time,unique_identifier,risk_score,risk_contributors"

    allBaselines = []
    for search in SearchConfig:
        if "baseline" + search['paramname'] in sids:
            if DEBUG==31:
                print '"runningsearch","' + json.dumps("baseline" + search['paramname']).replace('"', '""') + '"'
            pullData("baseline" + search['paramname'], sids["baseline" + search['paramname']], allBaselines, includeTime=False)

    for baseline in allBaselines:
        if DEBUG==32:
            print '"baseline","' + json.dumps(baseline).replace('"', '""') + '"'
        for keyName in baseline.keys():
            if not ( ("risk_" in keyName and keyName.index("risk_") == 0) or  ("values_" in keyName and keyName.index("values_") == 0) or  ("avg_" in keyName and keyName.index("avg_") == 0) or  ("stdev_" in keyName and keyName.index("stdev_") == 0) ):
                if baseline[keyName] == "values" and "values_" + keyName in baseline:
                    firstTimeSeenBaseline[keyName] = {}
                    if "risk_" + keyName in baseline:
                        firstTimeSeenBaseline[keyName]["risk"] = baseline["risk_" + keyName]
                    else:
                        firstTimeSeenBaseline[keyName]["risk"] = 2
                    firstTimeSeenBaseline[keyName]["values"] = baseline["values_" + keyName]
                if baseline[keyName] == "threshold" and "avg_" + keyName in baseline and "stdev_" + keyName in baseline:
                    timeSeriesBaseline[keyName] = {}
                    if "risk_" + keyName in baseline:
                        timeSeriesBaseline[keyName]["risk"] = baseline["risk_" + keyName]
                    else:
                        timeSeriesBaseline[keyName]["risk"] = 2
                    timeSeriesBaseline[keyName]["avg"] = baseline["avg_" + keyName]
                    timeSeriesBaseline[keyName]["stdev"] = baseline["stdev_" + keyName]
    if DEBUG==30:
        print '"firsttime","' + json.dumps(firstTimeSeenBaseline).replace('"', '""') + '"'
        print '"timeseries","' + json.dumps(timeSeriesBaseline).replace('"', '""') + '"'
    for search in SearchConfig:
        if search['paramname'] in sids:
            pullData(search['paramname'], sids[search['paramname']], allResults)

    newlist = sorted(allResults, key=itemgetter('_time')) 

    for result in newlist:
        for key in result.keys():
            if key in firstTimeSeenBaseline:
                if type(result[key]) == list:
                    for value in result[key]:
                        if value not in firstTimeSeenBaseline[key]['values']:
                            firstTimeSeenBaseline[key]['values'].append(value)
                            new_risk_entry(result, firstTimeSeenBaseline[key]['risk'], "First Time Seen: " + key + " (" + value + ")")
                else:
                    if result[key] not in firstTimeSeenBaseline[key]['values']:
                        firstTimeSeenBaseline[key]['values'].append(result[key])
                        new_risk_entry(result, firstTimeSeenBaseline[key]['risk'], "First Time Seen: " + key + " (" + result[key] + ")")
            
            if key in timeSeriesBaseline:
                try:
                    if float(result[key]) > float(timeSeriesBaseline[key]['avg']) + 10 * float(timeSeriesBaseline[key]['stdev']):
                        new_risk_entry(result, timeSeriesBaseline[key]['risk'], "Spike: " + key)
                except ValueError:
                    thisthing="shouldnotoccur"

        if "risk_score" in result:
            if int(result["risk_score"]) > 0:
                if type(result["risk_contributors"]) == list:
                    result["risk_contributors"] = ", ".join(result["risk_contributors"])
                print '"' + str(result['_time']) + '","' + result['unique_identifier'] + '","' + str(result['risk_score']) + '","' + result['risk_contributors'].replace('"', '""') + '"'


    
    sys.exit(0)



else:



    allRisks = []
    risks = {}
    if "riskyevents" in sids:
        pullData("riskyevents" , sids["riskyevents"], allRisks, calculateMD5=False)
        for risk in allRisks:
            risks[ risk['unique_identifier'] ] = risk
    for search in SearchConfig:
        if search['paramname'] in sids:
            pullData(search['paramname'], sids[search['paramname']], allResults)


    if DEBUG == 2:
        for result in allResults:
            print '"' + json.dumps(result).replace('"', '""') + '"'

    
    newlist = sorted(allResults, key=itemgetter('_time')) 

    if DEBUG == 3:
        for result in newlist:
            print '"' + json.dumps(result).replace('"', '""') + '"'
    if DEBUG == 21:
        for risk in risks:
            print '"' + risk + '"'
            
    if DEBUG == 23:
        for record in newlist:
            print '"' + record['unique_identifier'] + '"'
            
    newReturn = list()
    lastVal = dict()

    ## Here is the 
    for record in newlist:
        record["risk_score"] = 0
        record["risk_contributors"] = ""
        if DEBUG == 22:
            #print '"' + record["unique_identifier"] + '","' + json.dumps(risks.keys(), sort_keys=True).replace('"', '""') + '"'
            print '"' + record['unique_identifier'] + '","DEBUG22","' + str(record['unique_identifier'] in risks) + '"'
        if record["unique_identifier"] in risks:
            if DEBUG == 26:
                print '"' + json.dumps(record).replace('"', '""') + '","' + json.dumps(risks[ record["unique_identifier"] ]).replace('"', '""') + '"'
            new_risk_entry(record, risks[ record["unique_identifier"] ]["risk_score"], risks[ record["unique_identifier"] ]["risk_contributors"])

            
        try:
            # record.update({"doubled": ", ".join(record.keys())})
            # newReturn.append(record)
            supplement = dict()
            
            for key in record.keys():
                if key=="_time" or ((not "_" in key or key.index("_") != 0 ) and key!="type" and key!="Message" and key!="by" and record[key]!=""):
                    supplement[key] = record[key]
        
        except ValueError:
            record.update({"ERROR": "ValueError - Initial Parsing"})
            record["dvtest"] = json.dumps(record)
            newReturn.append(record)
        except KeyError:
            record.update({"ERROR": "KeyError - Initial Parsing"})
            record["dvtest"] = json.dumps(record)
            newReturn.append(record)

        if not "risk_score" in record:
            record["risk_score"] = 0
            record["risk_contributors"] = ""
        if int(record["risk_score"]) < int(minrisklevel):
            continue
            
        try:
            # Moved higher up
            # now = datetime.datetime.fromtimestamp( float(record["_time"]) )
            # round_mins = 5
            # mins = now.minute - (now.minute % round_mins) #Rounding down to nearest 5 minutes
            # newTime = datetime.datetime(now.year, now.month, now.day, now.hour, mins) + datetime.timedelta(minutes=round_mins)
            # record["_time"] = (newTime - datetime.datetime(1970,1,1)).total_seconds()
            if len(lastVal) == 0:
                lastVal = record
                lastVal['count'] = 1
                lastVal['supplement'] = list()
                lastVal['supplement'].append(supplement)
            else:
                if record['type'] == lastVal['type'] and record["rounded_time"] == lastVal["rounded_time"] and record["risk_score"] == lastVal["risk_score"] and shouldAggregate[record['type']] == "true":
                    lastVal['count'] += 1
                    lastVal['supplement'].append(supplement)
                else:
                    try:
                        if DEBUG==5:
                            newReturn.append(lastVal)
                        else:
                            newReturn.append(describeEvents(lastVal))
                    except ValueError:
                        record.update({"ERROR": "ValueError - describing"})
                        record["dvtest"] = json.dumps(record)
                        newReturn.append(record)
                    except KeyError:
                        record.update({"ERROR": "KeyError - describing"})
                        record["dvtest"] = json.dumps(record)
                        newReturn.append(record)

                    lastVal = record
                    lastVal['count'] = 1
                    lastVal['supplement'] = list()
                    lastVal['supplement'].append(supplement)
        except ValueError:
            record.update({"ERROR": "ValueError - Secondary Parsing"})
            record["dvtest"] = json.dumps(record)
            newReturn.append(record)
        except KeyError:
            record.update({"ERROR": "KeyError - Secondary Parsing"})
            record["dvtest"] = json.dumps(record)
            newReturn.append(record)

    if DEBUG >= 4 and DEBUG < 10:
        for result in newReturn:
            print '"' + json.dumps(result).replace('"', '""') + '"'
            
    for item in newReturn:
        if "supplement" in item and len(item["supplement"]) > 0:
            item['supplement'] = json.dumps(item['supplement'])
        else:
            item["supplement"] = ""
        if "eventDrilldown" in item and len(item["eventDrilldown"]) > 0:
            item['eventDrilldown'] = json.dumps(item['eventDrilldown'])
        else:
            item["eventDrilldown"] = ""

    if DEBUG == 0:
        dict_writer = csv.DictWriter(sys.stdout, ["_time","Message", "supplement","eventDrilldown", "risk_score", "risk_contributors", "grouping_earliest", "grouping_latest"], extrasaction='ignore')
        dict_writer.writeheader()
        dict_writer.writerows(newReturn)