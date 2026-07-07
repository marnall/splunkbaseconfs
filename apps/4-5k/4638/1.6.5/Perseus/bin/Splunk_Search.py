#COPYRIGHT (C) JOSEPH KOVACIC 2020 - ALL RIGHTS RESERVED
#Unauthorized copying, distribution, or reuse of this file or its contents, via any medium is strictly prohibited without written consent

import requests
import json
import ssl

import Splunk_Main
import time
import datetime

SPLUNK_SEARCH_FIELD_NAME = "search"
SPLUNK_SEARCH_QUERY_PREFIX = "search"
SPLUNK_SID_FIELD_NAME = "sid"
SPLUNK_SEARCH_QUERY_ENTRY_FIELD_NAME = "entry"
SPLUNK_SEARCH_QUERY_CONTENT_FIELD_NAME = "content"
SPLUNK_SEARCH_QUERY_ISDONE_FIELD_NAME = "isDone"
SPLUNK_SEARCH_QUERY_RESULTS_FIELD_NAME = "results"
SPLUNK_SEARCH_QUERY_MESSAGE_FIELD_NAME = "messages"
SPLUNK_SEARCH_QUERY_MESSAGE_TYPE_FIELD_NAME = "type"
SPLUNK_SEARCH_QUERY_MESSAGE_TEXT_FIELD_NAME = "text"
SPLUNK_SEARCH_QUERY_WARNING_FIELD_NAME = "WARN"
SPLUNK_SEARCH_QUERY_ERROR_FIELD_NAME = "ERROR"
SPLUNK_SEARCH_QUERY_INFO_FIELD_NAME = "INFO"
SPLUNK_SEARCH_QUERY_RESULT_RAW_FIELD_NAME = "_raw"

SPLUNK_SEARCH_PAGE_SIZE = 50000
SPLUNK_SEARCH_ALL_PAGES = -1

class SplunkQueryException(Splunk_Main.SplunkException):
    pass

class SplunkSearchQuery(object):

    def __init__(self, strQueryIn, bAppendQueryPrefixIn = True, headerIn = None, splunkServerIn = Splunk_Main.splunkServerDefault, strAppContextIn = None, strAppContextUserIn = None):

        self.strQuery = strQueryIn
        self.bAppendQueryPrefix = bAppendQueryPrefixIn
        self.header = headerIn
        self.splunkServer = splunkServerIn
        self.strAppContext = strAppContextIn
        self.strAppContextUser = strAppContextUserIn

    def getQuery(self):
        return self.strQuery

    def getAppendQueryPrefix(self):
        return self.bAppendQueryPrefix

    def getHeader(self):
        return self.header
    
    def getSplunkServer(self):
        return self.splunkServer

    def getSplunkAppContext(self):
        return self.strAppContext

    def getSplunkAppContextUser(self):
        return self.strAppContextUser

    def executeQueryAndGetJsonResults(self, nPageIn = SPLUNK_SEARCH_ALL_PAGES):
        strSid = self.startQuery()
        self.waitForQueryCompletion(strSid)
        return self.getQueryJsonResults(strSid, nPageIn)
        
    #Returns the sid associated with the search
    def startQuery(self):

        splunkServer = self.getSplunkServer()
        strSearchUrl = splunkServer.getSearchJobsUrl(self.getSplunkAppContext(), self.getSplunkAppContextUser())
        
        strSearchQuery = self.getQuery()
        if (self.getAppendQueryPrefix() and (not strSearchQuery.startswith(SPLUNK_SEARCH_QUERY_PREFIX))):
            strSearchQuery = SPLUNK_SEARCH_QUERY_PREFIX + " " + strSearchQuery

        #If no header was provided, we start a new session for this query
        if (self.getHeader() is None):
            self.header = splunkServer.startSession()
            
        response = splunkServer.restPostOld(strSearchUrl, {SPLUNK_SEARCH_FIELD_NAME: strSearchQuery}, self.getHeader() )

        return splunkServer.getFieldValueFromJsonResponse(response.json(), SPLUNK_SID_FIELD_NAME)

    def waitForQueryCompletion(self, strSidIn):

        splunkServer = self.getSplunkServer()
        
        strJobUrl = splunkServer.getSearchJobUrl(strSidIn)
        
        #!TFinish - OPTIONAL PERFORMANCE - Can we do better than a busy wait without a 50 ms sleep?
        bLoop = True
        while (bLoop):
            response = splunkServer.restGetOld(strJobUrl, self.getHeader())

            #!TFinish - OPTIONAL - We could add error handling if SPLUNK_SEARCH_QUERY_ISDONE_FIELD_NAME missing or if there is not exactly one element (the [0] assumption) and raise a more informative exception
            
            #Sets Loop to the opposite of the IsDone value
            bLoop = (not (splunkServer.getFieldValueFromJsonResponse(response.json(), SPLUNK_SEARCH_QUERY_ENTRY_FIELD_NAME)[0][SPLUNK_SEARCH_QUERY_CONTENT_FIELD_NAME][SPLUNK_SEARCH_QUERY_ISDONE_FIELD_NAME]))
            if (bLoop):
                #Sleep for 50 ms
                time.sleep(0.05)

    def getQueryJsonResults(self, strSidIn, nPageIn = SPLUNK_SEARCH_ALL_PAGES, bRaiseExceptionForWarningIn = True, bRaiseExceptionForErrorIn = True):
        #!TFinish - OPTIONAL - We could add more specific error handling, especially for resultsCurrent.json()[SPLUNK_SEARCH_QUERY_RESULTS_FIELD_NAME] to raise a more informative exception
        
        splunkServer = self.getSplunkServer()
        
        jsonResults = None
        nCurrentPage = nPageIn
        if (nCurrentPage == SPLUNK_SEARCH_ALL_PAGES):
            nCurrentPage = 0

        while (True):
            
            strJobResultsUrl = splunkServer.getSearchJobResultsUrl(strSidIn) + ("&count=" + str(SPLUNK_SEARCH_PAGE_SIZE) + "&offset=" + str(SPLUNK_SEARCH_PAGE_SIZE * nCurrentPage))
            
            resultsCurrent = splunkServer.restGetOld(strJobResultsUrl, self.getHeader())
            splunkServer.raiseExceptionIfResponseHasWarningsOrErrors(resultsCurrent, bRaiseExceptionForWarningIn, bRaiseExceptionForErrorIn)
            
            if (jsonResults is None):
                jsonResults = resultsCurrent.json()[SPLUNK_SEARCH_QUERY_RESULTS_FIELD_NAME]
            else:
                jsonResults += (resultsCurrent.json()[SPLUNK_SEARCH_QUERY_RESULTS_FIELD_NAME])
                
            if (nPageIn == SPLUNK_SEARCH_ALL_PAGES):
                #No more rows were returned, so we can return
                if (len(resultsCurrent.json()[SPLUNK_SEARCH_QUERY_RESULTS_FIELD_NAME]) != SPLUNK_SEARCH_PAGE_SIZE):
                    break
                    
            #When a specific page is requested, we do only that page 
            else:
                break

            nCurrentPage += 1

        return jsonResults

class SplunkSavedSearch(object):
    
    def __init__(self, strSavedSearchNameIn, headerIn = None, splunkServerIn = Splunk_Main.splunkServerDefault, strAppContextIn = None, strAppContextUserIn = None):
        self.strSavedSearchName = strSavedSearchNameIn
        self.header = headerIn
        self.splunkServer = splunkServerIn
        self.strAppContext = strAppContextIn
        self.strAppContextUser = strAppContextUserIn

        #If no header was provided, we start a new session for these operations
        if (self.getHeader() is None):
            self.header = self.splunkServer.startSession()

    def getSavedSearchName(self):
        return self.strSavedSearchName

    def getHeader(self):
        return self.header
    
    def getSplunkServer(self):
        return self.splunkServer

    def getSplunkAppContext(self):
        return self.strAppContext

    def getSplunkAppContextUser(self):
        return self.strAppContextUser

    def getSavedSearchRaw(self):
        #Intentionally let errors pass through
        splunkServer = self.getSplunkServer()
        
        strSavedSearchUrl = splunkServer.getSavedSearchUrl(self.getSavedSearchName(), self.getSplunkAppContext(), self.getSplunkAppContextUser())

        response = splunkServer.restGet(strSavedSearchUrl, self.getHeader())
        
        return response.json()["entry"][0]["content"]

    def getSearch(self):
        return self.getSavedSearchRaw()["search"]

    def executeSearch(self, bWaitForCompletionIn):

        savedSearch = SplunkSearchQuery(self.getSearch(), True, self.getHeader(), self.getSplunkServer(), self.getSplunkAppContext(), self.getSplunkAppContextUser())

        if (bWaitForCompletionIn):
            savedSearch.executeQueryAndGetJsonResults()
        else:
            savedSearch.startQuery()
        
    def getSavedSearchNextScheduledUnixTime(self, dtEarliestUnixTimeIn = "+0s", dtLatestUnixTimeIn = "+1y"):
        #We don't use self.getSavedSearchRaw()["next_scheduled_time"] because it can contain a string representation with a non-trivially converted Full Time Zone name
                    
        #Intentionally let errors pass through
        splunkServer = self.getSplunkServer()
        strScheduledTimesUrl = splunkServer.getSavedSearchScheduledTimesUrl(self.getSavedSearchName(), self.getSplunkAppContext(), self.getSplunkAppContextUser())

        #If no header was provided, we start a new session for this operation
        if (self.getHeader() is None):
            self.header = splunkServer.startSession()

        dictParams = { "earliest_time" : dtEarliestUnixTimeIn, "latest_time" : dtLatestUnixTimeIn } 

        try:
            response = splunkServer.restGet(strScheduledTimesUrl, self.getHeader(), dictParams)                
            return int(response.json()["entry"][0]["content"]["scheduled_times"][0])
        
        #We are seeing 404 failures in this endpoint for some reason (first noted on a Search Head Cluster). We will try another technique instead based on history
        except Exception as err:
            try:
                strHistoryUrl = splunkServer.getSavedSearchHistoryUrl(self.getSavedSearchName(), self.getSplunkAppContext(), self.getSplunkAppContextUser())

                #We compare the time of the 2nd most recent and most recent start times to determine frequency of search, then we add that to the most recent time to find out when it will run next
                jsonResponse = splunkServer.restGet(strHistoryUrl, self.getHeader()).json()

                if (len(jsonResponse["entry"]) < 2):
                    raise Exception("Could Not Determine Next Scheduled Search Time")
                
                dtSecondMostRecentUnixTime = jsonResponse["entry"][0]["content"]["start"]
                dtMostRecentUnixTime = jsonResponse["entry"][1]["content"]["start"]

                return (dtMostRecentUnixTime + (dtMostRecentUnixTime - dtSecondMostRecentUnixTime))
                
            except Exception as err:
                 
                try:
                    strNextScheduledTime = self.getSavedSearchRaw()["next_scheduled_time"]
                    return (time.mktime(datetime.datetime.strptime(strNextScheduledTime, "%Y-%m-%d %H:%M:%S %Z").timetuple()))
            
                #Let the error from the more reliable getSavedSearchHistoryUrl method pass through for troubleshooting
                except:
                    pass
                
                raise

            



    
