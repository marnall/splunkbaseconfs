# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import saDbUtils
import fnmatch
import os
import platform
import re
import csv
import sys
import saUtils
import six.moves.urllib.request, six.moves.urllib.parse, six.moves.urllib.error
import shutil
import time
import datetime
from datetime import timedelta
import splunk.Intersplunk as si
from xml.dom import minidom
import json
import splunk.rest
from time import localtime, strftime, sleep
import logging as logger
from io import open
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')


#
# Helper to apply local TZ offset to a UTC timestamp in datetime object.
#
def datetime_from_utc_to_local(utc_datetime):
    now_timestamp = time.time()
    offset = datetime.datetime.fromtimestamp(now_timestamp) - datetime.datetime.utcfromtimestamp(now_timestamp)
    return utc_datetime + offset

if __name__ == '__main__':
    analysis = ''
    model = ''
    app = ''

    python3 = sys.version_info[0] >= 3
    rmode = "rb"
    wmode = "wb"
    if python3:
        rmode = "r"
        wmode = "w"

    try:
        print ('Saved Search, Status')
        if len(sys.argv) >2:
            for arg in sys.argv[1:]:
                if arg.lower().startswith('analysis='):
                    eqsign = arg.find('=')
                    analysis = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('app='):
                    eqsign = arg.find('=')
                    app = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('model='):
                    eqsign = arg.find('=')
                    model = arg[eqsign+1:len(arg)]
        else:
            raise Exception('xmRunSearches-F-001: Usage: xmRunSearches analysis=<string> app=<string> model=<string>')

        logger.info('xmRunSearches - (' + analysis + ') started')

        if analysis == '':
            raise Exception("xmRunSearches-F-002: parameter 'analysis' not found")
        if app == '':
            raise Exception("xmRunSearches-F-003: parameter 'app' not found")

        if model == '':
            raise Exception("xmRunSearches-F-003: parameter 'model' not found")

        settings = saUtils.getSettings(sys.stdin)
        sessionKey = settings['sessionKey']

        db = saDbUtils.connectToDb (saUtils.getScmPropertiesFileName(),'', sessionKey)
        ecoSystemCollection = db['ecoSystem']

        modelFromDB = ecoSystemCollection.find_one ({"modelName" : model})

        # Actor with the specified primary or alternateId not found in the database.
        if modelFromDB == None:
            logger.info("xmRunSearches - Failed to look-up ecoSystem for model: [" + model + "] and app: [" + app.upper() + "] not found!")
            raise Exception ("xmRunSearches - Failed to look-up ecoSystem for model: [" + model + "] and app: [" + app.upper() + "] not found!")

        # Retrieve max model event max event time time to use for search earliest.
        modelMaxEventTime = modelFromDB['maxEventTime'];
        # This time is in UTC so local timezone offset must be applied before it's used for search as splunk will
        # perform the reverse (apply UTC offset) when search is performed.
        adjustedModelMaxTime = datetime_from_utc_to_local (modelMaxEventTime);
        logger.info ("modelMaxEventTime: (" + str(modelMaxEventTime) + ") UTC, adjustedTime: (" + str(adjustedModelMaxTime) + ") LOCAL")
        searchEarliest = int (time.mktime (adjustedModelMaxTime.timetuple()))

        # Move search earliest 1 second beyond max model time. This time will be earliest_time on all saved searches with
        # search_latest = now
        searchEarliest += 1

        # Get property for model.directory
        modelDir = ''
        with open(saUtils.getScmPropertiesFileName()) as propertyFile:
            for line in propertyFile:
                propname, propval = line.partition("=")[::2]
                if propname.strip() == "model.directory":
                    modelDir = propval[:-1]

        splunkHome=os.environ.get('SPLUNK_HOME')
        modelDir = modelDir.replace("$(SPLUNK_HOME)",splunkHome)
        tmpAnalysis = analysis.replace(" ","_")

        # Get epoch time for event interval
        analysisInterval = ''
        configurationFilename=modelDir + "/" + model + "/analysis_" + tmpAnalysis + "_configuration.csv"
        f_obj = open(configurationFilename, rmode)
        reader = csv.reader(f_obj, quoting=csv.QUOTE_NONE);
        for row in reader:
            analysisInterval = row[20];
        f_obj.close();
        logger.info('xmRunSearches - (' + analysis + ') analysisInterval='+ analysisInterval)

        searchString = '| makeresults | eval modifier="'+analysisInterval+'" | eval timeEpoch=relative_time(now(),modifier) | table timeEpoch'
        #logger.info('xmRunSearches - (' + analysis + ') searchString='+ searchString)
        endpoint = '/services/search/jobs'
        postArgs = {'search':searchString}
        response, content = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=sessionKey, raiseAllErrors=False, postargs=postArgs)

        sid = minidom.parseString(content).getElementsByTagName('sid')[0].childNodes[0].nodeValue
        if response.status != 201:
            logger.info('xmRunSearches - (' + analysis + ') FAILURE retrieving event interval')
        else:
            #logger.info('xmRunSearches - sid=' + sid)
            endpoint = '/services/search/jobs/%s' % sid
            notDone = True
            while notDone:
                response, content = splunk.rest.simpleRequest(endpoint, method='GET', sessionKey=settings['sessionKey'], raiseAllErrors=False)
                notDoneStatus = re.compile(b'isDone">(0|1)')
                notDoneStatus = notDoneStatus.search(content).groups()[0]
                #logger.info('xmRunSearches - notDoneStatus=' + str(notDoneStatus))
                if notDoneStatus == b'1' :
                    notDone = False

            #endTime = strftime("%m/%d/%Y %H:%M:%S", localtime())
            #logger.info('xmRunSearches - (' + analysis + ') Got Event Interval: at ' + endTime)
            #logger.info('xmRunSearches - content=' + content)
            #logger.info('xmRunSearches - response=' + str(response))
            sleep(1)

            endpoint = '/services/search/jobs/%s/results' % sid
            response, content = splunk.rest.simpleRequest(endpoint, method='GET', sessionKey=settings['sessionKey'], raiseAllErrors=False)
            analysisInterval = minidom.parseString(content).getElementsByTagName('text')[0].childNodes[0].nodeValue
            logger.info('xmRunSearches - analysisInterval=' + str(analysisInterval))


        searchFilename=modelDir + "/" + model + "/analysis_" + tmpAnalysis + "_saved_searches.csv"
        tmpFilename=modelDir + "/" + model + "/" + tmpAnalysis + "_tmp.csv"

        f_obj = open(searchFilename, rmode)
        reader = csv.reader(f_obj, quoting=csv.QUOTE_NONE);
        logger.info('xmRunSearches - (' + analysis + ') processing file=' + searchFilename)

        w_obj = open(tmpFilename, wmode)
        c = csv.writer(w_obj, delimiter=',', quoting=csv.QUOTE_NONE, quotechar='')

        # now - should be latest in current search
        epoch_time = int(time.time())
        logger.info('xmRunSearches - (' + analysis + ') epoch_time=' + str(epoch_time))

        for row in reader:
            name = row[0];
            type = row[1];
            search = row[2];
            range = row[3];
            status = row[4];
            selected = row[5];
            cron = row[6];
            lastrun = row[7];

            logger.info('xmRunSearches - (' + analysis + ') processing name=' + name + ' type=' + type)
            if type != "CUSTOM":

                # Need to update 'latest' for each search so they align on the same end time boundary
                # Note - the searches 'earliest' for each search will be updated to this latest time after search completes.
                endpoint = '/servicesNS/nobody/bv_xv/saved/searches/'+name

                # Update searchEarliest and searchLatest in saved search. The same values will be used across
                # all searches so that data acquired has a consistent time range across all data sources.
                postArgs = {'dispatch.earliest_time': searchEarliest, 'dispatch.latest_time': epoch_time}

                response2, content = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=sessionKey, raiseAllErrors=False, postargs=postArgs)
                #logger.info('respons2.status=' + str(response2.status))
                #logger.info(content);
                if response2.status != 200:
                    logger.info('xmRunSearches - (' + analysis + ') Failure updating earliest_time in Saved Search: ' + name)
                else:
                    logger.info('xmRunSearches - (' + analysis + ') Updated earliest_time in Saved Search: ' + name + ' to ' + str(searchEarliest))


                # Determine if enough time has lapsed based on interval and lastrun to run the search
                doSearch = 'true'
                current_epoch_time = int(time.time())
                #logger.info('xmRunSearches - current_epoch_time: ' + str(current_epoch_time))
                # CALCULATE, DENSITY, ACTOR, ACTOR_DAY_OF_WEEK, and PEER have set intervals that are longer
                if type == 'CALCULATE':
                    timeDiff = 9999999999
                    oneDay = 24 * 60 * 60
                    if lastrun != '':
                        timeDiff = current_epoch_time - int(lastrun)
                    logger.info('xmRunSearches - (' + analysis + ') timeDiff=' + str(timeDiff) + ', oneDay=' + str(oneDay));
                    if (lastrun == '') or (timeDiff > oneDay) :
                        doSearch = 'true'
                        logger.info('xmRunSearches - (' + analysis + ') running CALCULATE Thresholds');
                    else:
                        doSearch = 'false'
                        logger.info('xmRunSearches - (' + analysis + ') skipping CALCULATE Thresholds');
                elif type == 'DENSITY':
                    timeDiff = 9999999999
                    oneDay = 24 * 60 * 60
                    if lastrun != '':
                        timeDiff = current_epoch_time - int(lastrun)
                    logger.info('xmRunSearches - (' + analysis + ') timeDiff=' + str(timeDiff) + ', oneDay=' + str(oneDay));
                    if (lastrun == '') or (timeDiff > oneDay) :
                        doSearch = 'true'
                        logger.info('xmRunSearches - (' + analysis + ') running Calculate Information DENSITY');
                    else:
                        doSearch = 'false'
                        logger.info('xmRunSearches - (' + analysis + ') skipping Calculate Information DENSITY');
                elif type == 'ACTOR' or type == 'ACTOR_DAY_OF_WEEK' or type == 'P2P':
                    timeDiff = 9999999999
                    if lastrun != '':
                        timeDiff = current_epoch_time - int(lastrun)
                    tokens = range.split(":")
                    interval = tokens[0];
                    day = tokens[1];
                    hour = tokens[2];
                    dayOfMonth = tokens[3];
                    currentHour = datetime.datetime.now().hour
                    currentDay = datetime.datetime.now().weekday() - 1
                    currentDayOfMonth = datetime.datetime.now().day
                    oneDay = 24 * 60 * 60
                    oneWeek = 7 * 24 * 60 * 60
                    oneMonth = 4 * 7 * 24 * 60 * 60
                    logger.info('xmRunSearches - (' + analysis + ') type=' + type + ', lastrun=' + str(lastrun) + ',timeDiff=' + str(timeDiff) + ',oneDay=' + str(oneDay) + ', oneWeek=' + str(oneWeek) + ', oneMonth=' + str(oneMonth) + ',interval=' + str(interval) + ', hour=' + str(hour) + ', currentHour=' + str(currentHour) +', day=' + str(day) + ', currentDay=' + str(currentDay) + ',dayOfMonth=' + str(dayOfMonth) + ', currentDayOfMonth=' + str(currentDayOfMonth))

                    if interval == 'daily':
                        if (lastrun == '') or (currentHour == int(hour)):
                            logger.info('xmRunSearches - (' + analysis + ') setting doSearch to false') 
                            if timeDiff < oneDay:
                                doSearch = 'false'
                        else:
                            doSearch = 'false'
                            
                    elif interval == 'weekly':
                        if (lastrun == '') or (timeDiff > oneWeek) :
                            if (currentDay == int(day)) and (currentHour == int(hour)):
                                doSearch = 'true'
                            else:
                                doSearch = 'false'
                        else:
                            doSearch = 'false'
                    elif interval == 'monthly':
                        if (lastrun == '') or (timeDiff > oneMonth) :
                            if (currentDayOfMonth == ind(dayOfMonth)) and (currentHour == int(hour)):
                                doSearch = 'true'
                            else:
                                doSearch = 'false'
                        else:
                            doSearch = 'false'
                elif type == 'METADATA':
                    doSearch = 'true'
                else:
                    # NEW - Run the analysis by default.
                    doSearch = 'true';

                    #logger.info('xmRunSearches - lastrun=' + str(lastrun) + ', analysisInterval=' + str(analysisInterval));

                    #if (lastrun == '') or (float(lastrun) < float(analysisInterval)) :
                    #    doSearch = 'true'
                    #else:
                    #    doSearch = 'false'
                    #    logger.info('xmRunSearches - skipping Search');

                logger.info('xmRunSearches - (' + analysis + ') doSearch= ' + doSearch)
                if doSearch == 'true':

                    currentTime = strftime("%m/%d/%Y %H:%M:%S", localtime())
                    logger.info('xmRunSearches - (' + analysis + ') Starting Saved Search: ' + name + ' at ' + currentTime)

                    # Run the Saved Search
                    searchString = "| savedsearch " + name
                    #endpoint = '/services/search/jobs?output_mode=json'
                    endpoint = '/services/search/jobs'
                    postArgs = {'search':searchString};
                    response, content = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=sessionKey, raiseAllErrors=False, postargs=postArgs)
                    #logger.info('response.status=' + str(response.status))
                    #logger.info(content);
                    sid = minidom.parseString(content).getElementsByTagName('sid')[0].childNodes[0].nodeValue
                    isFailed = False
                    if response.status != 201:
                        logger.info('xmRunSearches - (' + analysis + ') FAILURE running saved search: ' + name)
                    else:
                        logger.info('xmRunSearches - sid=' + sid)
                        endpoint = '/services/search/jobs/%s/' % sid
                        notDone = True
                        while notDone:
                            #response, content = splunk.rest.simpleRequest(endpoint, method='GET', sessionKey=settings['sessionKey'], raiseAllErrors=False)
                            response, content = splunk.rest.simpleRequest(endpoint, method='GET', sessionKey=settings['sessionKey'], raiseAllErrors=False)
                            #logger.info('response.status=' + str(response.status))
                            #logger.info(content);
                            notDoneStatus = re.compile(b'isDone">(0|1)')
                            notDoneStatus = notDoneStatus.search(content).groups()[0]
                            #logger.info('xmRunSearches - notDoneStatus=' + str(notDoneStatus))
                            if notDoneStatus == b'1' :
                                notDone = False

                            isFailedStatus = re.compile(b'isFailed">(0|1)')
                            isFailedStatus = isFailedStatus.search(content).groups()[0]
                            #logger.info('xmRunSearches - isFailedStatus=' + str(isFailedStatus))
                            if isFailedStatus == b'1' :
                                isFailed = True
                            #endpoint = '/services/search/jobs'

                        endTime = strftime("%m/%d/%Y %H:%M:%S", localtime())
                        logger.info('xmRunSearches - (' + analysis + ') Saved Search Completed: ' + name + ' at ' + endTime + ' isFailed=' + str(isFailed) )
                        sleep(1)

                        #
                        # HARRY - COMMENTED OUT BECAUSE SEARCH EARLIEST IS UPDATED ABOVE, CURRENTLY NOT MODIFING LATEST AFTER RUN,
                        # THE VALUE OF NOW WILL ALWAYS BE USED FOR LATEST.
                        #
                        #endpoint = '/servicesNS/nobody/bv_xv/saved/searches/'+name
                        #postArgs = {'dispatch.earliest_time':epoch_time}
                        #response2, content = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=sessionKey, raiseAllErrors=False, postargs=postArgs)
                        #
                        #if response2.status != 200:
                        #   logger.info('xmRunSearches - (' + analysis + ') Failure updating earliest_time in Saved Search: ' + name)
                        #else:
                        #   logger.info('xmRunSearches - (' + analysis + ') Updated earliest_time in Saved Search: ' + name + ' to ' + str(epoch_time))
                        #
                        # END HARRY

                        # NOTE Some analysis will not generate a profile signal if there is no data (e.g., Relevancy Analysis, TransactionPathAnalysis)
                        if type != 'CALCULATE' and type != 'DENSITY' and type != 'METADATA' and isFailed != True:
                            profileSearchString = ''
                            if type == 'ACQUIRE':
                                profileSearchString = 'search index=scm_signal id=S0001 analysisName="'+analysis+'" earliest='+str(current_epoch_time)
                            elif type == 'THRESHOLD':
                                profileSearchString = 'search index=scm_signal id=A0229 analysisName="'+analysis+'" earliest='+str(current_epoch_time)
                            elif type == 'SEQUENCE':
                                profileSearchString = 'search index=scm_signal id=A0419 analysisName="'+analysis+'" earliest='+str(current_epoch_time)
                            elif type == 'ACTOR':
                                profileSearchString = 'search index=scm_signal id=A0101 analysisName="'+analysis+'" earliest='+str(current_epoch_time)
                            elif type == 'ACTOR_DAY_OF_WEEK':
                                profileSearchString = 'search index=scm_signal id=A0301 analysisName="'+analysis+'" earliest='+str(current_epoch_time)
                            elif type == 'P2P':
                                profileSearchString = 'search index=scm_signal id=A0031 analysisName="'+analysis+'" earliest='+str(current_epoch_time)
                            elif type == 'RULE':
                                profileSearchString = 'search index=scm_signal id=A0501 analysisName="'+analysis+'" earliest='+str(current_epoch_time)
                            elif type == 'RELEVANCY':
                                profileSearchString = 'search index=scm_signal id=S0201 analysisName="'+analysis+'" earliest='+str(current_epoch_time)
                            elif type == 'TRANSACTION':
                                profileSearchString = 'search index=scm_signal id=S0301 analysisName="'+analysis+'" earliest='+str(current_epoch_time)
                            elif type == 'HAZARD':
                                profileSearchString = 'search index=scm_signal id=H0101 analysisName="'+analysis+'" earliest='+str(current_epoch_time)
                            elif type == 'THREAT':
                                profileSearchString = 'search index=scm_signal id=T0101 analysisName="'+analysis+'" earliest='+str(current_epoch_time)
                            elif type == 'METADATA':
                                profileSearchString = 'search index=scm_signal id=A0109 analysisName="'+analysis+'" earliest='+str(current_epoch_time)
                            else:
                                logger.error ("Unsupported analysis type: " + type + ", cannot define profileSearchString!");

                            logger.info('xmRunSearches - (' + analysis + ') Profile Signal Search:' + profileSearchString)
                            profileNotDone = True
                            count = 0
                            while profileNotDone == True:
                                endpoint = '/services/search/jobs'
                                postArgs = {'search':profileSearchString}
                                response, content = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=sessionKey, raiseAllErrors=False, postargs=postArgs)
                                sid = minidom.parseString(content).getElementsByTagName('sid')[0].childNodes[0].nodeValue
                                logger.info('xmRunSearches - (' + analysis + ') Checking for Profile Signal ... (response='+str(response.status)+')')
                                if response.status != 201:
                                    logger.info('xmRunSearches - (' + analysis + ') FAILURE running profile search')
                                else:
                                    #logger.info('xmRunSearches - sid=' + sid)
                                    endpoint = '/services/search/jobs/%s/' % sid
                                    notDone = True
                                    while notDone:
                                        response, content = splunk.rest.simpleRequest(endpoint, method='GET', sessionKey=settings['sessionKey'], raiseAllErrors=False)
                                        notDoneStatus = re.compile(b'isDone">(0|1)')
                                        notDoneStatus = notDoneStatus.search(content).groups()[0]
                                        #logger.info('xmRunSearches - notDoneStatus=' + str(notDoneStatus))
                                        if notDoneStatus == b'1' :
                                            notDone = False
                                            #logger.info('xmRunSearches - content=' + content)
                                            eventCount = re.compile(b'eventCount">(0|1)')
                                            eventCount = eventCount.search(content).groups()[0]
                                            #logger.info('xmRunSearches - eventCount='+ str(eventCount));
                                            if eventCount == b'1':
                                                logger.info('xmRunSearches - (' + analysis + ') Profile Signal Found')
                                                profileNotDone = False
    
                                # only make 5 attempts
                                count = count + 1
                                if profileNotDone == True:
                                    if count >= 5:
                                        logger.info('xmRunSearches - (' + analysis + ') No Profile Signal After 5 Attempts ... skipping to next analysis')
                                        profileNotDone = False
                                    else:
                                        sleep(10)
                    finalStatus = response.status
                    if isFailed != False:
                        finalStatus = 400
                    print (name + "," + str(finalStatus))

                    # update lastrun
                    lastrun = epoch_time
                else:
                    logger.info('xmRunSearches - (' + analysis + ') Saved Search skipped: ' + name + ' because not enough time has lapsed')

            # Write out updated saved search
            c.writerow([name,type,search,range,status,selected,cron,lastrun])
        f_obj.close();
        w_obj.close();
        shutil.move(tmpFilename, searchFilename)
        logger.info('xmRunSearches - (' + analysis + ') DONE')

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)


    except Exception as e:
        logger.error ("xmRunSearches Exception:");
        logger.error (e, exc_info=True);
        si.generateErrorResults(e)

    if platform.system() == 'Windows':
        sys.stdout.flush()
        time.sleep(1.0)
