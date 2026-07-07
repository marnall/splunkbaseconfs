#COPYRIGHT (C) JOSEPH KOVACIC 2020 - ALL RIGHTS RESERVED
#Unauthorized copying, distribution, or reuse of this file or its contents, via any medium is strictly prohibited without written consent

import requests
import sys
import os
import codecs
import json
import datetime
import calendar
import distutils.version
import copy

#Exists when this is run on a Splunk Server
try:
    from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError
except ImportError:
    pass

SPLUNK_USERNAME_FIELD_NAME = "username"
SPLUNK_PASSWORD_FIELD_NAME = "password"
SPLUNK_SESSIONKEY_FIELD_NAME = "sessionKey"
SPLUNK_AUTHORIZATION_FIELD_NAME = "Authorization"
SPLUNK_AUTHORIZATION_TYPE_SPLUNK_VALUE = "Splunk"

SPLUNK_NO_APP_CONTEXT = ""
SPLUNK_USER_NOBODY = "nobody"

SPLUNK_SERVICES_NO_APP_CONTEXT_SUFFIX = "/services/"
SPLUNK_SERVICES_WITH_APP_CONTEXT_SUFFIX_PART_1 = "/servicesNS/"

SPLUNK_SERVER_RESTART_SUFFIX_WO_SERVICES = "server/control/restart";
SPLUNK_SERVER_RESTART_WEBUI_SUFFIX_WO_SERVICES = "server/control/restart_webui";

#!TFinish - OPTIONAL - Use getServicesRootSuffixPath for getting the paths
SPLUNK_INDEXES_ROOT_URL_SUFFIX_PART_1 = "/servicesNS/"
SPLUNK_INDEXES_ROOT_URL_SUFFIX_PART_2 = "/data/indexes"

#!TFinish - OPTIONAL - Use getServicesRootSuffixPath for getting the paths
SPLUNK_KV_STORE_ROOT_URL_SUFFIX_PART_1 = "/servicesNS/"
SPLUNK_KV_STORE_ROOT_URL_SUFFIX_PART_2 = "/storage/collections/"
SPLUNK_KV_STORE_CONFIG_URL_SUFFIX_PATH = "config/"
SPLUNK_KV_STORE_DATA_URL_SUFFIX_PATH = "data/"
SPLUNK_KV_STORE_BATCH_SAVE_URL_SUFFIX_PATH = "batch_save"

SPLUNK_USE_INTERSPLUNK_SESSIONKEY_ARG_LC = "-usesession"
g_strIntersplunkSessionKey = ""

class SplunkException(Exception):

    def __init__(self, strErrorMessageIn, responseIn = None):
        super(SplunkException, self).__init__(strErrorMessageIn)
        self.response = responseIn        

#This is not part of SplunkServer because it can be used externally to build authorization headers
def getAuthorizationHeader(strSessionKeyIn):
    return { SPLUNK_AUTHORIZATION_FIELD_NAME : SPLUNK_AUTHORIZATION_TYPE_SPLUNK_VALUE + " " + strSessionKeyIn }
    
class SplunkServer(object):
    def __init__(self, strServerUrlIn, nManagementPortIn, strUserNameIn, strPasswordIn, bVerifySSLIn, bIsFreeServerIn, strDefaultAppContextIn, strDefaultUserIn):
        
        self.strServerUrl = strServerUrlIn
        self.nManagementPort = nManagementPortIn
        self.strServerUrlWithPort = self.strServerUrl + ":" + str(self.nManagementPort)
        self.strUserName = strUserNameIn
        self.strPassword = strPasswordIn

        self.bVerifySSL = bVerifySSLIn
        if (not self.bVerifySSL):
            if distutils.version.StrictVersion(requests.__version__) <= distutils.version.StrictVersion("2.3.0"):
                pass
            else:
                #!TFinish - OPTIONAL - Implement this in a less global way?
                try:
                    requests.packages.urllib3.disable_warnings()
                except AttributeError:
                    #disable_warnings() not present in the requests 2.22.0 version that ships with Splunk 8.0.1
                    import urllib3
                    urllib3.disable_warnings()
                          
        self.bIsFreeServer = bIsFreeServerIn

        self.strDefaultAppContext = strDefaultAppContextIn
        self.strDefaultUser = strDefaultUserIn

    def getServerUrlWithPort(self):
        return self.strServerUrlWithPort
    
    def getUserName(self):
        return self.strUserName
    
    def getPassword(self):
        return self.strPassword

    def getVerifySSL(self):
        return self.bVerifySSL
        
    def getIsFreeServer(self):
        return self.bIsFreeServer

    def getDefaultAppContext(self):
        return self.strDefaultAppContext

    def getDefaultUser(self):
        return self.strDefaultUser

    def appendServicesUrlIfNecessary(self, strUrlIn):
        
        #No need to append because it already begins with https:// or http://
        if ((strUrlIn.lower().startswith("https://")) or (strUrlIn.lower().startswith("http://"))):
            return strUrlIn
        #Append the Services Url for the default app and user
        else:
            strUrlRet = self.getServicesRootUrl(self.strDefaultAppContext, self.strDefaultUser)

            if (strUrlIn.startswith("/")):
                strUrlRet = strUrlRet[:-1]

            return (strUrlRet + strUrlIn)

    #!TFinish - OPTIONAL - This was an older version of restPost that didn't raise exceptions on http errors. Retire this function when you test all functions that use it behave properly with the new function
    def restPostOld(self, strUrlIn, dataIn, headersIn=None, paramsIn=None, nTimeoutIn = 120):
        return self.restPost(strUrlIn, dataIn, headersIn, paramsIn, nTimeoutIn, False)

    def restPost(self, strUrlIn, dataIn, headersIn=None, paramsIn=None, nTimeoutIn = 120, bRaiseForStatusIn = True):

        strUrlIn = self.appendServicesUrlIfNecessary(strUrlIn)
            
        response = None
        
        try:
            response = requests.post(strUrlIn, data=dataIn, headers=headersIn, params=paramsIn, verify=self.getVerifySSL(), timeout=nTimeoutIn)

            if (bRaiseForStatusIn):
                response.raise_for_status()

            return response
        
        except Exception as err:
            raise SplunkException(str(err), response)

    #Intentionally let errors pass through
    def loginAndRestPost(self, strUrlIn, dataIn, headersIn=None, paramsIn=None, nTimeoutIn = 120, bRaiseForStatusIn = True):
        headerAuth = self.startSession()

        if (headersIn is None):
            headersIn = {}
            
        #The SPLUNK_AUTHORIZATION_FIELD_NAME field may not be present, for instance on Splunk Free where startSession returns {}
        if (SPLUNK_AUTHORIZATION_FIELD_NAME in headerAuth):
            headersIn[SPLUNK_AUTHORIZATION_FIELD_NAME] = headerAuth[SPLUNK_AUTHORIZATION_FIELD_NAME]

        self.restPost(strUrlIn, dataIn, headersIn, paramsIn, nTimeoutIn, bRaiseForStatusIn)
            
    #!TFinish - OPTIONAL - This was an older version of restGet that didn't raise exceptions on http errors. Retire this function when you test all functions that use it behave properly with the new function
    def restGetOld(self, strUrlIn, headersIn=None, nTimeoutIn = 120):
        return self.restGet(strUrlIn, headersIn, None, nTimeoutIn, False)

    def restGet(self, strUrlIn, headersIn=None, paramsIn=None, nTimeoutIn = 120, bRaiseForStatusIn = True):

        strUrlIn = self.appendServicesUrlIfNecessary(strUrlIn)

        response = None
        
        try:
            response = requests.get(strUrlIn, headers=headersIn, params=paramsIn, verify=self.getVerifySSL(), timeout=nTimeoutIn)
            
            if (bRaiseForStatusIn):
                response.raise_for_status()
            
            return response

        except Exception as err:
            raise SplunkException(str(err), response)

    #Intentionally let errors pass through
    def loginAndRestGet(self, strUrlIn, headersIn=None, nTimeoutIn = 120, bRaiseForStatusIn = True):
        headerAuth = self.startSession()

        if (headersIn is None):
            headersIn = {}
            
        #The SPLUNK_AUTHORIZATION_FIELD_NAME field may not be present, for instance on Splunk Free where startSession returns {}
        if (SPLUNK_AUTHORIZATION_FIELD_NAME in headerAuth):
            headersIn[SPLUNK_AUTHORIZATION_FIELD_NAME] = headerAuth[SPLUNK_AUTHORIZATION_FIELD_NAME]

        self.restGet(strUrlIn, headersIn, nTimeoutIn, bRaiseForStatusIn)

    #!TFinish - OPTIONAL - This was an older version of restDelete that didn't raise exceptions on http errors. Retire this function when you test all functions that use it behave properly with the new function
    def restDeleteOld(self, strUrlIn, headersIn=None, nTimeoutIn = 120):
        return self.restDelete(strUrlIn, headersIn, nTimeoutIn, False)

    def restDelete(self, strUrlIn, headersIn=None, nTimeoutIn = 120, bRaiseForStatusIn = True):
        
        strUrlIn = self.appendServicesUrlIfNecessary(strUrlIn)
        
        response = None

        try:
            response = requests.delete(strUrlIn, headers=headersIn, verify=self.getVerifySSL(), timeout=nTimeoutIn)

            if (bRaiseForStatusIn):
                response.raise_for_status()
                
            return response

        except Exception as err:
            raise SplunkException(str(err), response)

    #Intentionally let errors pass through
    def loginAndRestDelete(self, strUrlIn, headersIn=None, nTimeoutIn = 120, bRaiseForStatusIn = True):
        headerAuth = self.startSession()

        if (headersIn is None):
            headersIn = {}
            
        #The SPLUNK_AUTHORIZATION_FIELD_NAME field may not be present, for instance on Splunk Free where startSession returns {}
        if (SPLUNK_AUTHORIZATION_FIELD_NAME in headerAuth):
            headersIn[SPLUNK_AUTHORIZATION_FIELD_NAME] = headerAuth[SPLUNK_AUTHORIZATION_FIELD_NAME]

        self.restDelete(strUrlIn, headersIn, nTimeoutIn, bRaiseForStatusIn)

    #This will raise a python key exception if the field name is not part of the Json
    def getFieldValueFromJsonResponse(self, jsonResponseIn, strFieldNameIn):
        return jsonResponseIn[strFieldNameIn]

    def raiseExceptionIfResponseHasWarningsOrErrors(self, responseIn, bRaiseExceptionForWarningIn, bRaiseExceptionForErrorIn):
        
        jsonResponse = responseIn.json()
        
        MESSAGES_FIELD_NAME = "messages"
        MESSAGE_TYPE_FIELD_NAME = "type"
        MESSAGE_TEXT_FIELD_NAME = "text"
        FATAL_FIELD_NAME = "FATAL"
        ERROR_FIELD_NAME = "ERROR"
        WARNING_FIELD_NAME = "WARN"
        INFO_FIELD_NAME = "INFO"

        #!TFinish - OPTIONAL - When the restGetOld/restPostOld/restDeleteOld get removed, this likely should be removed as well since the new versions already raise on status
        try:
            responseIn.raise_for_status()
        except Exception as err:
            raise SplunkException(str(err), responseIn)

        #If this errors out, it means Splunk didn't return any messages as part of the response. If there are no messages, the aren't any warnings or errors
        try:
            jsonAllMessages = jsonResponse[MESSAGES_FIELD_NAME]
        except:
            return

        #Check each message returned
        for message in jsonAllMessages:

            strMessageTypeUC = message[MESSAGE_TYPE_FIELD_NAME].upper()
            
            #Info-level messages are ignored for now
            if (strMessageTypeUC == INFO_FIELD_NAME):
                continue

            #Warning
            elif (strMessageTypeUC == WARNING_FIELD_NAME):

                #The "unable to distribute to peer" warning does potentially result in data not being returned that should be. We should raise an exception on it (it could be worth adding a function to SplunkServer that allows caller to specify which warnings/errors they want to raise exceptions on. We could potentially have pre-made profiles a user could specify based on whether they need high fidelity or if less fidelity is acceptable
                #This warning message can be ignored because slow performance does not impact the results that are returned
                #The "found no results to append to collection" occurs when outputlookup is called with empty data - we don't want to consider that an error as it can be a valid outcome
                try:
                    if (("took longer than expected" in message[MESSAGE_TEXT_FIELD_NAME].lower()) or
                        ("found no results to append to collection" in message[MESSAGE_TEXT_FIELD_NAME].lower())):
                         pass
                    elif (bRaiseExceptionForWarningIn):
                         raise SplunkException(message[MESSAGE_TEXT_FIELD_NAME], responseIn)
               
                except SplunkException:
                    raise

                except:
                    if (bRaiseExceptionForWarningIn):
                        raise SplunkException("Unspecified Warning Returned By Splunk", responseIn)
                    
            #Error/Fatal
            elif ((strMessageTypeUC == ERROR_FIELD_NAME) or (strMessageTypeUC == FATAL_FIELD_NAME)):
                try:
                    if (bRaiseExceptionForErrorIn):
                        #This error does not appear to actually affect the search results
                        if ("events might not be returned in sub-second order" in message[MESSAGE_TEXT_FIELD_NAME].lower()):
                            pass
                        else:
                            raise SplunkException(message[MESSAGE_TEXT_FIELD_NAME], responseIn)      

                except SplunkException:
                    raise

                except:
                    if (bRaiseExceptionForErrorIn):
                        raise SplunkException("Unspecified Error Returned By Splunk", responseIn)

            else:
                #If we do not recognize the message type, we cannot be sure the results are accurate
                #In this very unlikely scenario (only should happen if Splunk adds a new message type), raise an exception
                raise SplunkException("Unexpected Response Message Type: " + message[MESSAGE_TYPE_FIELD_NAME], responseIn)

    def getUrlAppendedForJsonOutput(self, strUrlIn):
        return strUrlIn + "?output_mode=json"

    def getSessionKey(self):
        try:
            strLoginUrl = self.getServerUrlWithPort() + self.getUrlAppendedForJsonOutput("/services/auth/login")

            response = self.restPost(strLoginUrl, { SPLUNK_USERNAME_FIELD_NAME: self.getUserName(), SPLUNK_PASSWORD_FIELD_NAME: self.getPassword() })

            return self.getFieldValueFromJsonResponse(response.json(), SPLUNK_SESSIONKEY_FIELD_NAME)

        except SplunkException:
            raise

        except Exception as err:
            raise SplunkException(str(err))

    def startSession(self):
                
        #On Splunk Free Servers, there is no authentication so don't need to return any header data (but don't return None so that other header data can be appended)
        if self.getIsFreeServer():
            return {}
        
        strSessionKey = ""
        #We store the key globally so on subsequent calls we don't look up the session key again (which was leading to a failure to retrieve sessionKey during testing)
        global g_strIntersplunkSessionKey

        #If the script is called directly from Splunk, we can use its SessionKey to avoid storing credentials in this file
        if (g_strIntersplunkSessionKey != ""):
            strSessionKey = g_strIntersplunkSessionKey

        elif (any(strArg.lower() == SPLUNK_USE_INTERSPLUNK_SESSIONKEY_ARG_LC for strArg in sys.argv)):
            try:
                import splunk.Intersplunk as si

                results, dummyresults, settings = si.getOrganizedResults()
                g_strIntersplunkSessionKey = settings.get(SPLUNK_SESSIONKEY_FIELD_NAME)
                strSessionKey = g_strIntersplunkSessionKey
                            
            #This will rollover to credentialed login if possible
            except Exception as err:
                pass
            
        #Above method was not used or failed, rollover to credentials
        if (strSessionKey == ""):
            strSessionKey = self.getSessionKey()

        return getAuthorizationHeader(strSessionKey)

    #Let Splunk exceptions pass through
    def restartSplunk(self, bOnlyRestartSplunkWebIn = False, headerAuthIn = None):
        #Use no app context to resolve to /services/
        strServicesRootUrl = self.getServicesRootUrl(SPLUNK_NO_APP_CONTEXT, SPLUNK_USER_NOBODY)
        
        if (bOnlyRestartSplunkWebIn):
            strUrl = strServicesRootUrl + SPLUNK_SERVER_RESTART_WEBUI_SUFFIX_WO_SERVICES
        else:
            strUrl = strServicesRootUrl + SPLUNK_SERVER_RESTART_SUFFIX_WO_SERVICES

        if (headerAuthIn is None):
            self.loginAndRestPost(strUrl, {})
        else:
            self.restPost(strUrl, {}, headerAuthIn)
        

    def getIndexesUrl(self, strAppContextIn = None, strAppContextUserIn = None):
        if (strAppContextIn is None):
            strAppContextIn = self.getDefaultAppContext()

        if (strAppContextUserIn is None):
            strAppContextUserIn = self.getDefaultUser()
            
        return self.getServerUrlWithPort() + SPLUNK_INDEXES_ROOT_URL_SUFFIX_PART_1 + strAppContextUserIn + "/" + strAppContextIn + SPLUNK_INDEXES_ROOT_URL_SUFFIX_PART_2

    #Let Splunk exceptions pass through
    def createSplunkIndex(self, strNewIndexNameIn, strAppContextIn = None, strAppContextUserIn = None):
        if (strAppContextIn is None):
            strAppContextIn = self.getDefaultAppContext()

        if (strAppContextUserIn is None):
            strAppContextUserIn = self.getDefaultUser()
            
        strIndexesUrl = self.getIndexesUrl(strAppContextIn, strAppContextUserIn)

        header = self.startSession()

        dictNewIndex = { "name" : strNewIndexNameIn }     
        self.restPostOld(strIndexesUrl, dictNewIndex, header)

    #Let Splunk exceptions pass through
    def getIndexJson(self, strIndexNameIn, strAppContextIn = None, strAppContextUserIn = None):
        if (strAppContextIn is None):
            strAppContextIn = self.getDefaultAppContext()

        if (strAppContextUserIn is None):
            strAppContextUserIn = self.getDefaultUser()
            
        strIndexesUrl = self.getUrlAppendedForJsonOutput(self.getIndexesUrl(strAppContextIn, strAppContextUserIn) + "/" + strIndexNameIn)

        header = self.startSession()
        response = self.restGetOld(strIndexesUrl, header)

        self.raiseExceptionIfResponseHasWarningsOrErrors(response, True, True)
        
        return response.json()

    #Service Helper Functions

    #None indicates to use the server default
    def resolveAppContextIfDefault(self, strAppContextIn):
        if (strAppContextIn is None):
            return self.getDefaultAppContext()
        else:
            return strAppContextIn

    #None indicates to use the server default
    def resolveAppContextUserIfDefault(self, strAppContextUserIn):
        if (strAppContextUserIn is None):
            return self.getDefaultUser()
        else:
            return strAppContextUserIn

    #I don't think you can provide a user and no app context. But if Splunk allows it, modify this to accommodate it
    def getServicesRootSuffixPath(self, strAppContextIn, strAppContextUserIn):
        strAppContext = self.resolveAppContextIfDefault(strAppContextIn)
        strAppContextUser = self.resolveAppContextUserIfDefault(strAppContextUserIn)

        if (strAppContext == SPLUNK_NO_APP_CONTEXT):
            return SPLUNK_SERVICES_NO_APP_CONTEXT_SUFFIX
        else:
            return (SPLUNK_SERVICES_WITH_APP_CONTEXT_SUFFIX_PART_1 + strAppContextUser + "/" + strAppContext + "/")

    def getServicesRootUrl(self, strAppContextIn, strAppContextUserIn):
        return self.getServerUrlWithPort() + self.getServicesRootSuffixPath(strAppContextIn, strAppContextUserIn)
    
    #Search Related Functions
    
    def getSearchJobsUrl(self, strAppContextIn = None, strAppContextUserIn = None):
        if (strAppContextIn is None):
            strAppContextIn = self.getDefaultAppContext()

        if (strAppContextUserIn is None):
            strAppContextUserIn = self.getDefaultUser()

        #We default to search app context
        if (len(strAppContextIn) == 0):
            strUrlSuffix = self.getUrlAppendedForJsonOutput("/services/search/jobs")
        else:
            strUrlSuffix = self.getUrlAppendedForJsonOutput("/servicesNS/" + strAppContextUserIn + "/" + strAppContextIn + "/search/jobs")
        
        return self.getServerUrlWithPort() + strUrlSuffix

    def getSearchJobUrl(self, strSidIn, strAppContextIn = None, strAppContextUserIn = None):
        #This will work even if the search is running under a different app context
        strUrlSuffix = self.getUrlAppendedForJsonOutput("/services/search/jobs/" + strSidIn + "/")
        return self.getServerUrlWithPort() + strUrlSuffix

    def getSearchJobResultsUrl(self, strSidIn, strAppContextIn = None, strAppContextUserIn = None):
        #This will work even if the search is running under a different app context
        strUrlSuffix = self.getUrlAppendedForJsonOutput("/services/search/jobs/" + strSidIn + "/results")
        return self.getServerUrlWithPort() + strUrlSuffix

    def getSavedSearchRootUrl(self, strAppContextIn = None, strAppContextUserIn = None, bGetUrlAppendedForJsonOutputIn = True):
        if (strAppContextIn is None):
            strAppContextIn = self.getDefaultAppContext()

        if (strAppContextUserIn is None):
            strAppContextUserIn = self.getDefaultUser()

        #We default to search app context
        if (len(strAppContextIn) == 0):
            strUrlSuffix = "/services/saved/searches"
        else:
            strUrlSuffix = "/servicesNS/" + strAppContextUserIn + "/" + strAppContextIn + "/saved/searches"

        if (bGetUrlAppendedForJsonOutputIn):
            strUrlSuffix = self.getUrlAppendedForJsonOutput(strUrlSuffix)
                
        return self.getServerUrlWithPort() + strUrlSuffix

    def getSavedSearchUrl(self, strSavedSearchNameIn, strAppContextIn = None, strAppContextUserIn = None, bGetUrlAppendedForJsonOutputIn = True):

        strUrl = self.getSavedSearchRootUrl(strAppContextIn, strAppContextUserIn, False) + "/" + strSavedSearchNameIn

        if (bGetUrlAppendedForJsonOutputIn):
            strUrl = self.getUrlAppendedForJsonOutput(strUrl)

        return strUrl

    def getSavedSearchScheduledTimesUrl(self, strSavedSearchNameIn, strAppContextIn = None, strAppContextUserIn = None, bGetUrlAppendedForJsonOutputIn = True):

        strUrl = self.getSavedSearchUrl(strSavedSearchNameIn, strAppContextIn, strAppContextUserIn, False) + "/scheduled_times"

        if (bGetUrlAppendedForJsonOutputIn):
            strUrl = self.getUrlAppendedForJsonOutput(strUrl)

        return strUrl

    def getSavedSearchHistoryUrl(self, strSavedSearchNameIn, strAppContextIn = None, strAppContextUserIn = None, bGetUrlAppendedForJsonOutputIn = True):

        strUrl = self.getSavedSearchUrl(strSavedSearchNameIn, strAppContextIn, strAppContextUserIn, False) + "/history"

        if (bGetUrlAppendedForJsonOutputIn):
            strUrl = self.getUrlAppendedForJsonOutput(strUrl)

        return strUrl

    #KV Store Related Functions

    def getKVStoreRootUrl(self, strAppContextIn = None, strAppContextUserIn = None):
        if (strAppContextIn is None):
            strAppContextIn = self.getDefaultAppContext()

        if (strAppContextUserIn is None):
            strAppContextUserIn = self.getDefaultUser()
            
        return self.getServerUrlWithPort() + SPLUNK_KV_STORE_ROOT_URL_SUFFIX_PART_1 + strAppContextUserIn + "/" + strAppContextIn + SPLUNK_KV_STORE_ROOT_URL_SUFFIX_PART_2

    def getKVStoreDataUrl(self, strKVStoreNameIn, strAppContextIn = None, strAppContextUserIn = None):
       return self.getKVStoreRootUrl(strAppContextIn, strAppContextUserIn) + SPLUNK_KV_STORE_DATA_URL_SUFFIX_PATH + strKVStoreNameIn

    def getKVStoreConfigUrl(self, strKVStoreNameIn, strAppContextIn = None, strAppContextUserIn = None):
       return self.getKVStoreRootUrl(strAppContextIn, strAppContextUserIn) + SPLUNK_KV_STORE_CONFIG_URL_SUFFIX_PATH + strKVStoreNameIn

    def getKVStoreBatchSaveUrl(self, strKVStoreNameIn, strAppContextIn = None, strAppContextUserIn = None):
        return self.getKVStoreRootUrl(strAppContextIn, strAppContextUserIn) + SPLUNK_KV_STORE_DATA_URL_SUFFIX_PATH + strKVStoreNameIn + "/" + SPLUNK_KV_STORE_BATCH_SAVE_URL_SUFFIX_PATH
            
#Default Splunk Server
DEFAULT_SPLUNK_SERVER_URL = "https://localhost"
DEFAULT_SPLUNK_SERVER_MANAGEMENT_PORT = 8089
DEFAULT_SPLUNK_USERNAME = ""
DEFAULT_SPLUNK_PASSWORD = ""
DEFAULT_SPLUNK_VERIFY_SSL = False
DEFAULT_SPLUNK_IS_FREE_SERVER = False
DEFAULT_SPLUNK_APP_CONTEXT = "Perseus"
DEFAULT_SPLUNK_USER = SPLUNK_USER_NOBODY
#!TFinish - OPTIONAL - Move this into a Perseus-Specific Module
#!STANDARD: IS_PERSEUS_DEMO = False
#!DEMO: 
IS_PERSEUS_DEMO = True

#This will rollover to the server default if the server url is NOT localhost or if an error is encountered
def getManagementPortFromWebConfigFileRolloverToServerDefault():

        #We only read this locally if we recognize it is connecting to the local host
        if ((DEFAULT_SPLUNK_SERVER_URL != "https://localhost") and (DEFAULT_SPLUNK_SERVER_URL != "https://127.0.0.1")):
            return DEFAULT_SPLUNK_SERVER_MANAGEMENT_PORT
        
        try:
            strRootPath = os.path.abspath(__file__)
    
            nEtcPos = strRootPath.find("/etc/apps/")

            strDelimiter = "/"
            
            #Windows
            if (nEtcPos == -1):
                nEtcPos = strRootPath.find("\\etc\\apps\\")
                strDelimiter = "\\"
                if (nEtcPos == -1):
                    raise Exception("Could Not Resolve Splunk Root Path")	

            #Parent Directory of etc is the root directory - Include the / or \
            strRootPath = strRootPath[0:(nEtcPos+1)]

            #We try local first since it overrides default
            strWebConfigFile = strRootPath + "etc" + strDelimiter + "system" + strDelimiter + "local" + strDelimiter + "web.conf"
            strDefaultWebConfigFile = strRootPath + "etc" + strDelimiter + "system" + strDelimiter + "default" + strDelimiter + "web.conf"
            if (not os.path.isfile(strWebConfigFile)):
                strWebConfigFile = strDefaultWebConfigFile
                if (not os.path.isfile(strWebConfigFile)):
                    raise Exception(strWebConfigFile + " file not found")        

            while (True):
                try:
                    parser = SafeConfigParser()
                    #Try opening as UTF-8 (appears to work with ANSI as well)
                    try:           
                        with codecs.open(strWebConfigFile, "r", encoding="utf-8-sig") as inFile:
                            parser.readfp(inFile)
                                
                    #Rollover to default parser read      
                    except:
                        parser.read(strWebConfigFile)

                    strPortString = parser.get("settings", "mgmtHostPort")
                    break
                
                #If we encounter any failure with the local web.conf file (likely because the port hasn't been overridden), we rollover to the default web.conf file
                except:
                    if (strWebConfigFile != strDefaultWebConfigFile):
                        strWebConfigFile = strDefaultWebConfigFile
                    else:
                        raise
                    
            #We expect this to start with an IP Address, but just in case we'll try it as a port number only as well
            nColonPos = strPortString.find(":")
            if (nColonPos == -1):
                return int(strPortString)
            else:
                return int(strPortString[nColonPos + 1:])
            
        except Exception as err:
            return DEFAULT_SPLUNK_SERVER_MANAGEMENT_PORT

#We use getManagementPortFromWebConfigFileRolloverToServerDefault because when non-default ports are used in a distributed configuration, it may be difficult to populate this with the proper value on each Splunk Server. Reading it locally solves that problem
splunkServerDefault = SplunkServer(DEFAULT_SPLUNK_SERVER_URL, getManagementPortFromWebConfigFileRolloverToServerDefault(), DEFAULT_SPLUNK_USERNAME, DEFAULT_SPLUNK_PASSWORD, DEFAULT_SPLUNK_VERIFY_SSL, DEFAULT_SPLUNK_IS_FREE_SERVER, DEFAULT_SPLUNK_APP_CONTEXT, DEFAULT_SPLUNK_USER)

#You can add extra Splunk Server configurations here or in other source files

def getSplunkIndexesUrl(splunkServerIn = splunkServerDefault, strAppContextIn = None, strAppContextUserIn = None):
    return splunkServerIn.getIndexesUrl(strAppContextIn, strAppContextUserIn)

#Let Splunk exceptions pass through
def createSplunkIndex(strNewIndexNameIn, splunkServerIn = splunkServerDefault, strAppContextIn = None, strAppContextUserIn = None):
    splunkServerIn.createSplunkIndex(strNewIndexNameIn, strAppContextIn, strAppContextUserIn)

#Let Splunk exceptions pass through
def getSplunkIndexJson(strIndexNameIn, splunkServerIn = splunkServerDefault, strAppContextIn = None, strAppContextUserIn = None):
    return splunkServerIn.getIndexJson(strIndexNameIn, strAppContextIn, strAppContextUserIn)

#General Helper Functions

def getSplunkTimeTextFromDateTime(dtIn):
    return dtIn.strftime("%m/%d/%Y:%H:%M:%S")

#!TFinish - OPTIONAL - If deemed necessary, we can later have a specific exception for time errors
def getDateTimeFromSplunkTime(strSplunkTimeIn):
    try:
        return datetime.datetime.strptime(strSplunkTimeIn, "%m/%d/%Y:%H:%M:%S")
    except Exception as err:
        raise SplunkException("Invalid Splunk Time for " + strSplunkTimeIn + " with error " + str(err))

def getSplunkTimeFromDateTime(dtIn):
    return calendar.timegm(dtIn.timetuple())

def getSplunkTimeForNow():
    return getSplunkTimeFromDateTime(datetime.datetime.utcnow())

def getCopyOfSplunkServer(splunkServerIn):
    return copy.deepcopy(splunkServerIn)
