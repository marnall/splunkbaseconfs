#COPYRIGHT (C) JOSEPH KOVACIC 2020 - ALL RIGHTS RESERVED
#Unauthorized copying, distribution, or reuse of this file or its contents, via any medium is strictly prohibited without written consent

import Splunk_Main

SPLUNK_SAVED_SEARCH_SUFFIX_WO_SERVICES_PATH = "saved/searches/"

class SplunkManagementException(Splunk_Main.SplunkException):
    pass

class SplunkManagement(object):

    def __init__(self, headerIn = None, splunkServerIn = Splunk_Main.splunkServerDefault, strAppContextIn = None, strAppContextUserIn = None):

        self.header = headerIn
        self.splunkServer = splunkServerIn
        self.strAppContext = strAppContextIn
        self.strAppContextUser = strAppContextUserIn

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
    
    def getSavedSearchesRootUrl(self):
        return self.splunkServer.getServicesRootUrl(self.strAppContext, self.strAppContextUser) + SPLUNK_SAVED_SEARCH_SUFFIX_WO_SERVICES_PATH

    def enableSavedSearch(self, strSavedSearchNameIn, bEnableIn = False):
        try:
        
            strUrl = self.splunkServer.getUrlAppendedForJsonOutput(self.getSavedSearchesRootUrl() + strSavedSearchNameIn)
                                                                   
            return self.splunkServer.restPost(strUrl, { "disabled" : (not bEnableIn) }, self.getHeaderLoginIfNone())

        except Splunk_Main.SplunkException as err:
            raise SplunkManagementException(str(err), err.response)
        
        except Exception as err:
            raise SplunkManagementException(str(err))
