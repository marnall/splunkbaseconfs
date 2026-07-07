#COPYRIGHT (C) JOSEPH KOVACIC 2020 - ALL RIGHTS RESERVED
#Unauthorized copying, distribution, or reuse of this file or its contents, via any medium is strictly prohibited without written consent

import six

import Splunk_Main
import Splunk_Search

import sys
import json
import csv

#StringIO is not available in Python 3
if (six.PY2):
    import StringIO

import requests

SPLUNK_KV_STORE_DATA_KEY_FIELD_NAME = "_key"

SPLUNK_KV_STORE_PAGE_SIZE = 50000
SPLUNK_KV_STORE_MAX_BATCH_SAVE_ENTRIES = 1000

class SplunkKVStoreException(Splunk_Main.SplunkException):
    pass

class SplunkAddEntryMaxSizeExceededKVStoreException(SplunkKVStoreException):
    pass

class SplunkLoadCsvFileToKVStoreException(SplunkKVStoreException):
    pass

class SplunkKVStore(object):
    def __init__(self, strKVStoreNameIn, headerIn = None, splunkServerIn = Splunk_Main.splunkServerDefault, strAppContextIn = None, strAppContextUserIn = None):

        self.strKVStoreName = strKVStoreNameIn
        self.header = headerIn
        self.splunkServer = splunkServerIn
        self.strAppContext = strAppContextIn
        self.strAppContextUser = strAppContextUserIn

    def getKVStoreName(self):
        return self.strKVStoreName

    def getHeader(self):
        return self.header

    def getHeaderLoginIfNone(self):
        if (self.header is None):
            self.header = self.splunkServer.startSession()

        return self.header
    
    def getSplunkServer(self):
        return self.splunkServer

    def getSplunkAppContext(self):
        return self.strAppContext

    def getSplunkAppContextUser(self):
        return self.strAppContextUser

    #Returns JSON
    def getEntries(self, dictQueryParamsIn = None, nPageIn = 0, strAppContextIn = None, strAppContextUserIn = None):

        try:
            if strAppContextIn is None:
                strAppContextIn = self.strAppContext

            if strAppContextUserIn is None:
                strAppContextUserIn = self.strAppContextUser
                
            splunkServer = self.getSplunkServer()
     
            strUrl = splunkServer.getKVStoreDataUrl(self.getKVStoreName(), strAppContextIn, strAppContextUserIn)

            if dictQueryParamsIn is not None:
                strUrl += ("?query=" + six.moves.urllib.parse.quote_plus(str(json.dumps(dictQueryParamsIn))))

                #Append an & because we'll be adding limit and skip below
                strUrl += "&" 

            else:
                #Append a ? because we'll be adding limit and skip below but don't have any other query params
                strUrl += "?"

            #!TFinish - OPTIONAL - I originally intended to sort by id but it seemed to slow things down tremendously. Either find a way to improve performance or delete: strUrl += "&sort=id&limit=" + str(SPLUNK_KV_STORE_PAGE_SIZE) + "&skip=" + str(SPLUNK_KV_STORE_PAGE_SIZE * nPageIn)    
            strUrl += ("limit=" + str(SPLUNK_KV_STORE_PAGE_SIZE) + "&skip=" + str(SPLUNK_KV_STORE_PAGE_SIZE * nPageIn))
       
            response = splunkServer.restGetOld(strUrl, self.getHeaderLoginIfNone())

            try:
                splunkServer.raiseExceptionIfResponseHasWarningsOrErrors(response, True, True)
            except Exception as err:
                raise SplunkKVStoreException(str(err))
        
            return (response.json())

        except SplunkKVStoreException:
            raise
        
        except Exception as err:
            raise SplunkKVStoreException(str(err))

    #Returns JSON
    def getEntriesNoMax(self, dictQueryParamsIn = None, strAppContextIn = None, strAppContextUserIn = None):
        jsonResultsRet = []

        nResultsCount = SPLUNK_KV_STORE_PAGE_SIZE
        nPageNumber = 0
        
        while (True):
            jsonResultsRet += self.getEntries(dictQueryParamsIn, nPageNumber, strAppContextIn, strAppContextUserIn)

            nPageNumber += 1

            #Page number was incremented previously so nPageNumber * SPLUNK_KV_STORE_PAGE_SIZE is correct
            if (len(jsonResultsRet) < (nPageNumber * SPLUNK_KV_STORE_PAGE_SIZE)):
                break

        return jsonResultsRet

    #dictMatchInfoIn maps FieldName to a tuple of Value Names and associated Value Name case sensitivity requirement
    def searchEntriesJson(self, jsonEntriesIn, dictMatchInfoIn, strAppContextIn = None, strAppContextUserIn = None):
        
        try:
            jsonResultsRet = []

            for jsonEntry in jsonEntriesIn:
                bEntryIsMatch = True

                for strFieldName, tupFieldValueAndCase in six.iteritems(dictMatchInfoIn):

                    if isinstance(tupFieldValueAndCase, tuple):
                        strFieldValue = tupFieldValueAndCase[0]
                        bCaseSensitiveMatch = tupFieldValueAndCase[1]
                    #If a tuple is not provided, that means we are looking for a case sensitive match
                    else:
                        strFieldValue = tupFieldValueAndCase
                        bCaseSensitiveMatch = True
                    
                    if ((bCaseSensitiveMatch and (strFieldValue != jsonEntry[strFieldName])) or
                        ((not bCaseSensitiveMatch) and (strFieldValue.upper() != jsonEntry[strFieldName].upper()))):

                        bEntryIsMatch = False
                        break

                if (bEntryIsMatch):
                    jsonResultsRet.append(jsonEntry)
                        
            return jsonResultsRet
        
        except Exception as err:
            raise SplunkKVStoreException(str(err))

    #dictMatchInfoIn maps FieldName to either a single string that is the case-sensitive Field Value or a tuple of Field Value and a Bool specifying whether Field Value comparison should be case sensitive
    def searchEntries(self, dictMatchInfoIn, strAppContextIn = None, strAppContextUserIn = None):

        try:
            return self.searchEntriesJson(self.getEntriesNoMax(), dictMatchInfoIn, strAppContextIn, strAppContextUserIn)
        
        except Exception as err:
            raise SplunkKVStoreException(str(err))


    def addEntry(self, dataToAddIn, strAppContextIn = None, strAppContextUserIn = None):

        try:
            if strAppContextIn is None:
                strAppContextIn = self.strAppContext

            if strAppContextUserIn is None:
                strAppContextUserIn = self.strAppContextUser
                
            splunkServer = self.getSplunkServer()

            header = self.getHeaderLoginIfNone()
            header["content-type"] = "application/json"

        
            #If the data provided is a list, we do a batch add
            if isinstance(dataToAddIn, list):
                #If it is empty we simply return because it will error out trying to bulk write an empty list
                if (len(dataToAddIn) == 0):
                    return

                elif(len(dataToAddIn) > SPLUNK_KV_STORE_MAX_BATCH_SAVE_ENTRIES):

                    for nBatchStartIndex in range(0, len(dataToAddIn), SPLUNK_KV_STORE_MAX_BATCH_SAVE_ENTRIES):
                        self.addEntry(dataToAddIn[nBatchStartIndex:(nBatchStartIndex + SPLUNK_KV_STORE_MAX_BATCH_SAVE_ENTRIES)])

                    #Already added all entries during the for loop above
                    return

                else:
                    #If it is a list with less than or equal SPLUNK_KV_STORE_MAX_BATCH_SAVE_ENTRIES entries, we can post below using the batch url
                    strUrl = splunkServer.getKVStoreBatchSaveUrl(self.getKVStoreName(), strAppContextIn, strAppContextUserIn)
            else:
                strUrl = splunkServer.getKVStoreDataUrl(self.getKVStoreName(), strAppContextIn, strAppContextUserIn)

            strUrl = splunkServer.getUrlAppendedForJsonOutput(strUrl)
            
            response = splunkServer.restPostOld(strUrl, json.dumps(dataToAddIn), header)

            try:
                splunkServer.raiseExceptionIfResponseHasWarningsOrErrors(response, True, True)
            except Exception as err:

                bMaxSizeError = False
                
                try:
                    bMaxSizeError = ("request exceeds api limits" in response.json()["messages"][0]["text"].lower())
                #We ignore any errors
                except:
                    pass
                
                if (bMaxSizeError):
                    raise SplunkAddEntryMaxSizeExceededKVStoreException(str(err))
                else:                
                    raise SplunkKVStoreException(str(err))

        except SplunkKVStoreException:
            raise
        
        except Exception as err:
            raise SplunkKVStoreException(str(err))

    #dataToUpdateIn will clobber whatever existing data was present (so any missing fields will be absent in the updated KV store entry)
    def updateEntry(self, dataToUpdateIn, strAppContextIn = None, strAppContextUserIn = None):

        try:
            if strAppContextIn is None:
                strAppContextIn = self.strAppContext

            if strAppContextUserIn is None:
                strAppContextUserIn = self.strAppContextUser
                
            splunkServer = self.getSplunkServer()
            
            strKey = dataToUpdateIn[SPLUNK_KV_STORE_DATA_KEY_FIELD_NAME]
                
            header = self.getHeaderLoginIfNone()
            header["content-type"] = "application/json"

            strUrl = splunkServer.getUrlAppendedForJsonOutput(splunkServer.getKVStoreDataUrl(self.getKVStoreName() + "/" + strKey, strAppContextIn, strAppContextUserIn))

            response = splunkServer.restPostOld(strUrl, json.dumps(dataToUpdateIn), header)

            try:
                splunkServer.raiseExceptionIfResponseHasWarningsOrErrors(response, True, True)

            except Exception as err:
                raise SplunkKVStoreException(str(err))

        except SplunkKVStoreException:
            raise
        
        except Exception as err:
            raise SplunkKVStoreException(str(err))

    #dictMatchInfoIn maps FieldName to either a single string that is the case-sensitive Field Value or a tuple of Field Value and a Bool specifying whether Field Value comparison should be case sensitive
    #dataToAddOrUpsertIn will clobber whatever existing data was present (so any missing fields will be absent in the updated KV store entry)
    def upsertOrAddIfMissingEntryUsingEntriesJson(self, jsonEntriesIn, dataToAddOrUpsertIn, dictMatchInfoIn, bUpsertIn, strAppContextIn = None, strAppContextUserIn = None):

        try:
                
            #If no specific matching info is passed in, search for all entries that are a case insensitive match of the whole entry
            if (dictMatchInfoIn is None):
                dictMatchInfoIn = {}
                for strFieldName, strFieldValue in six.iteritems(dataToAddOrUpsertIn):
                    dictMatchInfoIn[strFieldName] = (strFieldValue, False)

            jsonMatches = self.searchEntriesJson(jsonEntriesIn, dictMatchInfoIn, strAppContextIn, strAppContextUserIn)
            
            if (len(jsonMatches) == 0):
                self.addEntry(dataToAddOrUpsertIn, strAppContextIn, strAppContextUserIn)
            elif bUpsertIn:
                for jsonEntry in jsonMatches:
                    dataToAddOrUpsertIn[SPLUNK_KV_STORE_DATA_KEY_FIELD_NAME] = jsonEntry[SPLUNK_KV_STORE_DATA_KEY_FIELD_NAME]
                    self.updateEntry(dataToAddOrUpsertIn, strAppContextIn, strAppContextUserIn)

        except SplunkKVStoreException:
            raise
        
        except Exception as err:
            raise SplunkKVStoreException(str(err))

    #dictMatchInfoIn maps FieldName to either a single string that is the case-sensitive Field Value or a tuple of Field Value and a Bool specifying whether Field Value comparison should be case sensitive
    #dataToAddOrUpsertIn will clobber whatever existing data was present (so any missing fields will be absent in the updated KV store entry)
    def upsertOrAddIfMissingEntry(self, dataToAddOrUpsertIn, dictMatchInfoIn, bUpsertIn, strAppContextIn = None, strAppContextUserIn = None):

        try:
            #!TFinish - OPTIONAL PERFORMANCE - If we have matching info, we should probably use it here when retrieving the entries (make sure you pay attention to case sensitivity when doing this search)
            jsonEntries = self.getEntriesNoMax(None, strAppContextIn, strAppContextUserIn)
            self.upsertOrAddIfMissingEntryUsingEntriesJson(jsonEntries, dataToAddOrUpsertIn, dictMatchInfoIn, bUpsertIn, strAppContextIn, strAppContextUserIn)           

        except SplunkKVStoreException:
            raise
        
        except Exception as err:
            raise SplunkKVStoreException(str(err))

    #!TFinish - OPTIONAL - Add an upsert that updates only the fields provided and preserves the values of non-specified fields
    #dictMatchInfoIn maps FieldName to either a single string that is the case-sensitive Field Value or a tuple of Field Value and a Bool specifying whether Field Value comparison should be case sensitive
    #dataToAddOrUpsertIn will clobber whatever existing data was present (so any missing fields will be absent in the updated KV store entry)
    def upsertEntry(self, dataToUpsertIn, dictMatchInfoIn = None, strAppContextIn = None, strAppContextUserIn = None):
        self.upsertOrAddIfMissingEntry(dataToUpsertIn, dictMatchInfoIn, True, strAppContextIn, strAppContextUserIn)

    #dictMatchInfoIn maps FieldName to either a single string that is the case-sensitive Field Value or a tuple of Field Value and a Bool specifying whether Field Value comparison should be case sensitive
    def addKVStoreEntryIfMissing(self, dataToAddIn, dictMatchInfoIn = None, strAppContextIn = None, strAppContextUserIn = None):
        self.upsertOrAddIfMissingEntry(dataToAddIn, dictMatchInfoIn, False, strAppContextIn, strAppContextUserIn)

    def removeEntryByKey(self, strKeyIn, strAppContextIn = None, strAppContextUserIn = None):

        try:
            if strAppContextIn is None:
                strAppContextIn = self.strAppContext

            if strAppContextUserIn is None:
                strAppContextUserIn = self.strAppContextUser
                
            splunkServer = self.getSplunkServer()

            strUrl = splunkServer.getUrlAppendedForJsonOutput(splunkServer.getKVStoreDataUrl(self.getKVStoreName() + "/" + strKeyIn, strAppContextIn, strAppContextUserIn))

            response = splunkServer.restDeleteOld(strUrl, self.getHeaderLoginIfNone())            

            #Does not appear to get a json response object in success case, so just return
            if (response.status_code == requests.codes.ok):
                return
            
            try:
                splunkServer.raiseExceptionIfResponseHasWarningsOrErrors(response, True, True)
            except Exception as err:
                raise SplunkKVStoreException(str(err))

        except SplunkKVStoreException:
            raise
            
        except Exception as err:
            raise SplunkKVStoreException(str(err))

    def removeEntriesInJsonList(self, lstEntriesIn, strAppContextIn = None, strAppContextUserIn = None):

        try:
            for dictEntry in lstEntriesIn:
                self.removeEntryByKey(dictEntry[SPLUNK_KV_STORE_DATA_KEY_FIELD_NAME], strAppContextIn, strAppContextUserIn)

        except SplunkKVStoreException:
            raise
        
        except Exception as err:
            raise SplunkKVStoreException(str(err))


    def removeMatchingEntries(self, dictQueryParamsIn, strAppContextIn = None, strAppContextUserIn = None):

        try:
            lstEntries = self.getEntriesNoMax(dictQueryParamsIn, strAppContextIn, strAppContextUserIn)
            self.removeEntriesInJsonList(lstEntries, strAppContextIn, strAppContextUserIn)   

        except Exception as err:
            raise SplunkKVStoreException(str(err))

    #!TFinish - OPTIONAL - Implement a version of this function that removes entries for all _user values in the KV Store (there may be permission issues to consider - may want to verify a user has rights before attempting)
    def removeAllEntries(self, strAppContextIn = None, strAppContextUserIn = None):
        try:
            if strAppContextIn is None:
                strAppContextIn = self.strAppContext

            if strAppContextUserIn is None:
                strAppContextUserIn = self.strAppContextUser
                
            splunkServer = self.getSplunkServer()
            
            strUrl = splunkServer.getUrlAppendedForJsonOutput(splunkServer.getKVStoreDataUrl(self.getKVStoreName(), strAppContextIn, strAppContextUserIn))

            response = splunkServer.restDeleteOld(strUrl, self.getHeaderLoginIfNone())

            #Does not appear to get a json response object in success case, so just return
            if (response.status_code == requests.codes.ok):
                return

            try:
                splunkServer.raiseExceptionIfResponseHasWarningsOrErrors(response, True, True)
            except Exception as err:
                raise SplunkKVStoreException(str(err))

        except SplunkKVStoreException:
            raise
        
        except Exception as err:
            raise SplunkKVStoreException(str(err))

    #CSV File to KV Store Functions

    #The CSV File must start with a line containing the field names
    def loadCsvFileToKVStore(self, strCsvFileIn, bErrorIfAnyEntriesExistAlreadyIn, bClearExistingEntriesIn, strAppContextIn = None, strAppContextUserIn = None):

        try:
            #!TFinish - OPTIONAL - We can replace this with io.open for consistency (though I encountered some differences in csv parsing a file with CR-CR-LF endings as is the case with WinXP notepad bug (open works, io.open has empty csv lines)
            with open(strCsvFileIn) as csvfile:
                lstAllCsvEntries = csv.reader(csvfile)

                self.loadCsvFileReaderEntriesToKVStore(lstAllCsvEntries, bErrorIfAnyEntriesExistAlreadyIn, bClearExistingEntriesIn, strAppContextIn, strAppContextUserIn)

        except SplunkLoadCsvFileToKVStoreException:
            raise

        except Exception as err:
            raise SplunkLoadCsvFileToKVStoreException(str(err))

    #The CSV File Content must start with a line containing the field names
    #StringIO is not available in Python 3
    if (six.PY2):
        def loadCsvFileContentToKVStore(self, strCsvFileContentIn, bErrorIfAnyEntriesExistAlreadyIn, bClearExistingEntriesIn, strAppContextIn = None, strAppContextUserIn = None):

            try:
                csvfile = StringIO.StringIO(strCsvFileContentIn)
                lstAllCsvEntries = csv.reader(csvfile)
                
                self.loadCsvFileReaderEntriesToKVStore(lstAllCsvEntries, bErrorIfAnyEntriesExistAlreadyIn, bClearExistingEntriesIn, strAppContextIn, strAppContextUserIn)
                                                         
            except SplunkLoadCsvFileToKVStoreException:
                raise

            except Exception as err:
                raise SplunkLoadCsvFileToKVStoreException(str(err))

    def loadCsvFileReaderEntriesToKVStore(self, lstCsvEntriesIn, bErrorIfAnyEntriesExistAlreadyIn, bClearExistingEntriesIn, strAppContextIn = None, strAppContextUserIn = None):

        try:

            #!TFinish - OPTIONAL PERFORMANCE - Limit this to a single entry just to check if it is empty
            lstEntries = self.getEntries(None, 0, strAppContextIn, strAppContextUserIn)

            if (bErrorIfAnyEntriesExistAlreadyIn and (len(lstEntries) > 0)):
                raise SplunkLoadCsvFileToKVStoreException()
            elif bClearExistingEntriesIn:
                self.removeAllEntries(strAppContextIn, strAppContextUserIn)

            lstFieldNames = []
            lstNewEntries = []

            #Read each CSV file line and batch add them to the KV Store            
            for lstCsvEntry in lstCsvEntriesIn:
                #Read in Field Names
                if (len(lstFieldNames) == 0):
                    lstFieldNames = lstCsvEntry
                else:
                    dictEntry = {}
                    for strFieldName, strFieldData in zip(lstFieldNames, lstCsvEntry):
                        dictEntry[strFieldName] = strFieldData
                    
                    lstNewEntries.append(dictEntry)

            #Batch add for performance reasons
            self.addEntry(lstNewEntries, strAppContextIn, strAppContextUserIn)
        
        except SplunkLoadCsvFileToKVStoreException:
            raise

        except Exception as err:
            raise SplunkLoadCsvFileToKVStoreException(str(err))                               

    #Throws SplunkLoadCsvFileToKVStoreException
    def clearKVStoreAndLoadCsvFile(self, strCsvFileIn):
        self.loadCsvFileToKVStore(strCsvFileIn, False, True, strAppContextIn, strAppContextUserIn)

    #Throws SplunkLoadCsvFileToKVStoreException
    def clearKVStoreAndLoadCsvFileContent(self, strCsvFileContentIn, strAppContextIn = None, strAppContextUserIn = None):
        self.loadCsvFileContentToKVStore(strCsvFileContentIn, False, True, strAppContextIn, strAppContextUserIn)

