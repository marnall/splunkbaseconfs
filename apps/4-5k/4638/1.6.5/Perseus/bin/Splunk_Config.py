#COPYRIGHT (C) JOSEPH KOVACIC 2020 - ALL RIGHTS RESERVED
#Unauthorized copying, distribution, or reuse of this file or its contents, via any medium is strictly prohibited without written consent

import Splunk_Main

SPLUNK_PROPERTIES_CONFIG_FILE_SUFFIX_WO_SERVICES_PATH = "properties/"

class SplunkConfigException(Splunk_Main.SplunkException):
    pass
    
class SplunkConfig(object):

    def __init__(self, strConfigFileNameWithoutExtIn, headerIn = None, splunkServerIn = Splunk_Main.splunkServerDefault, strAppContextIn = None, strAppContextUserIn = None):

        self.strConfigFileNameWithoutExt = strConfigFileNameWithoutExtIn
        self.header = headerIn
        self.splunkServer = splunkServerIn
        self.strAppContext = strAppContextIn
        self.strAppContextUser = strAppContextUserIn

    def getConfigFileNameWithoutExtName(self):
        return self.strConfigFileNameWithoutExtName

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

    def getPropertiesRootUrl(self):
        return self.splunkServer.getServicesRootUrl(self.strAppContext, self.strAppContextUser) + SPLUNK_PROPERTIES_CONFIG_FILE_SUFFIX_WO_SERVICES_PATH

    def getConfigFileStanzaRaw(self, strStanzaNameIn, bOutputJsonIn = False):
        try:
        
            strUrl = self.getPropertiesRootUrl() + self.strConfigFileNameWithoutExt + "/" + strStanzaNameIn
            if (bOutputJsonIn):
                strUrl = self.splunkServer.getUrlAppendedForJsonOutput(strUrl)
            
            return self.splunkServer.restGet(strUrl, self.getHeaderLoginIfNone())

        except Splunk_Main.SplunkException as err:
            raise SplunkConfigException(str(err), err.response)
        
        except Exception as err:
            raise SplunkConfigException(str(err))

    def getConfigFileStanzaJson(self, strStanzaNameIn):
        return self.getConfigFileStanzaRaw(strStanzaNameIn, True).json()

    #This function is basically the "Raw" version but the raw version appears to return only the value with no additional formatting
    def getConfigFileStanzaKeyValue(self, strStanzaNameIn, strKeyIn):
        try:
        
            strUrl = self.getPropertiesRootUrl() + self.strConfigFileNameWithoutExt + "/" + strStanzaNameIn + "/" + strKeyIn
            return self.splunkServer.restGet(strUrl, self.getHeaderLoginIfNone()).text

        except Splunk_Main.SplunkException as err:
            raise SplunkConfigException(str(err), err.response)
        
        except Exception as err:
            raise SplunkConfigException(str(err))
        
    #Returns False if stanza already existed, True if it created
    def createConfigFileStanza(self, strStanzaNameIn):
        try:
            strUrl = self.getPropertiesRootUrl() + self.strConfigFileNameWithoutExt
            
            dataStanza = {}
            dataStanza["__stanza"] = strStanzaNameIn

            response = self.splunkServer.restPost(strUrl, dataStanza, self.getHeaderLoginIfNone())

            #Returns a 201 response if the stanza was created, 200 if it already existed
            return (response.status_code == 201)
        
        except Splunk_Main.SplunkException as err:            
            raise SplunkConfigException(str(err), err.response)
        
        except Exception as err:
            raise SplunkConfigException(str(err))

    #Overwrites Value If It Exists
    def setConfigFileStanzaKeyValue(self, strStanzaNameIn, strKeyIn, strValueIn, bErrorIfKeyAlreadyExistsIn = False):

        #If necessary, check if the value already exists
        if (bErrorIfKeyAlreadyExistsIn):
            try:
                self.getConfigFileStanzaKeyValue(strStanzaNameIn, strKeyIn)
                bKeyAlreadyExists = True
            #We treat it as not existing if we get an error
            except:
                bKeyAlreadyExists = False

            if (bKeyAlreadyExists):
                raise SplunkConfigException("Key " + strKeyIn + " already exists")
                
        self.setConfigFileStanzaKeyValues(strStanzaNameIn, {  strKeyIn : strValueIn})

    #Overwrites Values If They Exist
    def setConfigFileStanzaKeyValues(self, strStanzaNameIn, dictKeysAndValuesIn):
        try:
            self.createConfigFileStanza(strStanzaNameIn)

            strUrl = self.getPropertiesRootUrl() + self.strConfigFileNameWithoutExt + "/" + strStanzaNameIn

            self.splunkServer.restPost(strUrl, dictKeysAndValuesIn, self.getHeaderLoginIfNone())
        
        except Splunk_Main.SplunkException as err:            
            raise SplunkConfigException(str(err), err.response)
        
        except Exception as err:
            raise SplunkConfigException(str(err))

    #If the value is not already part of the existing value, this appends it to the value. Returns True the value was added, False if not
    def appendConfigFileStanzaValueToKey(self, strStanzaNameIn, strKeyIn, strValueIn, strAppendDelimiterIn = ", "):

        strExistingValue = None
        strStrippedExistingValueWithoutWhitespaceLC = None

        try:
            strExistingValue = self.getConfigFileStanzaKeyValue(strStanzaNameIn, strKeyIn)
        #Leave strExistingValue as None on error indicating no value exists
        except:
            pass

        if (strExistingValue is not None):
            strStrippedExistingValueWithoutWhitespaceLC = ''.join(strExistingValue.strip().lower().split())
            strValueLC = strValueIn.lower()
            strAppendDelimiterWithoutWhitespaceLC = ''.join(strAppendDelimiterIn.strip().lower().split())

            #Value matches the data exactly
            if (strValueLC == strStrippedExistingValueWithoutWhitespaceLC):
                return False
            #Line starts with the value and is followed by another value
            elif (strStrippedExistingValueWithoutWhitespaceLC.startswith(strValueLC + strAppendDelimiterWithoutWhitespaceLC)):
                return False
            #Line ends with the value after being preceeded by another value
            elif (strStrippedExistingValueWithoutWhitespaceLC.find(strAppendDelimiterWithoutWhitespaceLC + strValueLC) != -1):
                return False

            #Fall Through to Replace the Existing Value with the Appended One
            strValueIn = (strExistingValue + strAppendDelimiterIn + strValueIn)
            
        self.setConfigFileStanzaKeyValues(strStanzaNameIn, {  strKeyIn : strValueIn})
        return True
