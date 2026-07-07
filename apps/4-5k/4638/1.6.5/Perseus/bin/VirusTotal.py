#COPYRIGHT (C) JOSEPH KOVACIC 2020 - ALL RIGHTS RESERVED
#Unauthorized copying, distribution, or reuse of this file or its contents, via any medium is strictly prohibited without written consent

import requests

import csv
import time

VT_DEFAULT_REQUESTS_TIMEOUT = 120

VT_API_KEY_FIELD_NAME = "apikey"

VT_RESPONSE_CODE_FIELD_NAME = "response_code"
VT_RESPONSE_CODE_VALUE_SUCCESS = 1

VT_SCAN_MD5_HASH_FIELD_NAME = "md5"
VT_SCAN_POSITIVES_FIELD_NAME = "positives"
VT_SCAN_TOTAL_FIELD_NAME = "total"
VT_SCAN_LINK_TO_SCAN_FIELD_NAME = "permalink"

VT_SCAN_IF_NO_PREVIOUS_SCAN_VALUE = "1"

#File Scan Report
VT_FILE_SCAN_REPORT_URL = "https://www.virustotal.com/vtapi/v2/file/report"
VT_FILE_SCAN_REPORT_HASH_FIELD_NAME = "resource"

#URL Scan Report
VT_URL_SCAN_REPORT_URL = "https://www.virustotal.com/vtapi/v2/url/report"
VT_URL_SCAN_REPORT_URL_FIELD_NAME = "resource"
VT_URL_SCAN_REPORT_SCAN_FIELD_NAME = "scan"

class VirusTotalException(Exception):
    pass

class VirusTotalPostException(VirusTotalException):
    pass

class VirusTotalGetUrlScanReportException(VirusTotalException):
    pass

class VirusTotalGetFileScanReportException(VirusTotalException):
    pass

class VirusTotal(object):

    def __init__(self, strAPIKeyIn):
        self.strAPIKey = strAPIKeyIn

    def getAPIKey(self):
        return self.strAPIKey

    #Automatically appends API Key to Params
    def restPostOld(self, strUrlIn, jsonParamsIn, nTimeoutIn = VT_DEFAULT_REQUESTS_TIMEOUT):

        #!TFinish - OPTIONAL - May want to add throttling code into here, into API Key Retrieval, or into a seperate non-class function that has a list of VirusTotal objects to cycle through
        
        try:
            jsonParamsIn[VT_API_KEY_FIELD_NAME] = self.getAPIKey()
            
            response = requests.post(strUrlIn, params=jsonParamsIn, timeout=nTimeoutIn)
            if (response.status_code != requests.codes.ok):
                raise VirusTotalPostException("HTTP Error: " + str(response))

            return response

        except VirusTotalPostException:
            raise

        except Exception as err:
            raise VirusTotalPostException(str(err))

    #Automatically appends API Key to Params
    def restPostOldWithJsonResponse(self, strUrlIn, jsonParamsIn, nTimeoutIn = VT_DEFAULT_REQUESTS_TIMEOUT):
            
        try:
            return self.restPostOld(strUrlIn, jsonParamsIn, nTimeoutIn).json()
        
        except VirusTotalPostException:
            raise
        
        except Exception as err:
            raise VirusTotalPostException(str(err))

    #Returns JSON
    def getUrlScanReport(self, strUrlIn):
        try:
            jsonParams = { VT_URL_SCAN_REPORT_URL_FIELD_NAME : strUrlIn,
                           VT_URL_SCAN_REPORT_SCAN_FIELD_NAME : VT_SCAN_IF_NO_PREVIOUS_SCAN_VALUE }
            
            return self.restPostOldWithJsonResponse(VT_URL_SCAN_REPORT_URL, jsonParams)

        except Exception as err:
            raise VirusTotalGetUrlScanReportException(str(err))

    #Returns Number of AV Engines flagging the site as bad, Total AV Engines, and Permalink to the analysis for the site
    def getUrlScanReportImportantFields(self, strUrlIn):
        try:
            jsonUrlReport = self.getUrlScanReport(strUrlIn)
            return int(jsonUrlReport[VT_SCAN_POSITIVES_FIELD_NAME]), int(jsonUrlReport[VT_SCAN_TOTAL_FIELD_NAME]), jsonUrlReport[VT_SCAN_LINK_TO_SCAN_FIELD_NAME]

        except VirusTotalGetUrlScanReportException:
            raise
        
        except Exception as err:
            raise VirusTotalGetUrlScanReportException(str(err))

    #Returns True if the API Key Could Be Verified
    def verifyApiKey(self):
        try:
            VIRUS_TOTAL_TEST_MD5_HASH = "1edb3b4d1bea11dede192b3972dd94c8"
            self.getFileScanReport(VIRUS_TOTAL_TEST_MD5_HASH)
            return True
        
        except:
            return False
            
    #Returns JSON
    def getFileScanReport(self, strHashIn):
        try:
            jsonParams = { VT_FILE_SCAN_REPORT_HASH_FIELD_NAME : strHashIn }
            
            return self.restPostOldWithJsonResponse(VT_FILE_SCAN_REPORT_URL, jsonParams)

        except Exception as err:
            raise VirusTotalGetFileScanReportException(str(err))

    #Returns Number of AV Engines flagging the file as bad, Total AV Engines, and Permalink to the analysis for the file
    def getFileScanReportImportantFields(self, strHashIn):
        try:
            jsonFileReport = self.getFileScanReport(strHashIn)
            #!TFinish - OPTIONAL - Optionally add check of the response code like we do in getFileScanReportsImportantFields
            return int(jsonFileReport[VT_SCAN_POSITIVES_FIELD_NAME]), int(jsonFileReport[VT_SCAN_TOTAL_FIELD_NAME]), jsonFileReport[VT_SCAN_LINK_TO_SCAN_FIELD_NAME]

        except VirusTotalGetFileScanReportException:
            raise
        
        except Exception as err:
            raise VirusTotalGetFileScanReportException(str(err))
        
    #Returns a List of tuples containing the MD5 Hash for the file, Number of AV Engines flagging the file as bad, Total AV Engines, and Permalink to the analysis for the file
    def getFileScanReportsImportantFields(self, lstHashesIn):      
        try:
            strCommaDelimittedHashes = ",".join(lstHashesIn)
     
            jsonParams = { VT_FILE_SCAN_REPORT_HASH_FIELD_NAME : strCommaDelimittedHashes }
            jsonFileReports = self.restPostOldWithJsonResponse(VT_FILE_SCAN_REPORT_URL, jsonParams)

            lstImportantFieldsRet = []

            if (len(lstHashesIn) > 1): 
                for jsonFileReport in jsonFileReports:
                    if (jsonFileReport[VT_RESPONSE_CODE_FIELD_NAME] == VT_RESPONSE_CODE_VALUE_SUCCESS):
                        tupFields = jsonFileReport[VT_SCAN_MD5_HASH_FIELD_NAME].upper(), int(jsonFileReport[VT_SCAN_POSITIVES_FIELD_NAME]), int(jsonFileReport[VT_SCAN_TOTAL_FIELD_NAME]), jsonFileReport[VT_SCAN_LINK_TO_SCAN_FIELD_NAME]
                        lstImportantFieldsRet.append(tupFields)

            #If only hash was proivded, a list of JSON Reports is not returned - only a single JSON Report
            else:
                jsonFileReport = jsonFileReports
                if (jsonFileReport[VT_RESPONSE_CODE_FIELD_NAME] == VT_RESPONSE_CODE_VALUE_SUCCESS):
                    tupFields = jsonFileReport[VT_SCAN_MD5_HASH_FIELD_NAME].upper(), int(jsonFileReport[VT_SCAN_POSITIVES_FIELD_NAME]), int(jsonFileReport[VT_SCAN_TOTAL_FIELD_NAME]), jsonFileReport[VT_SCAN_LINK_TO_SCAN_FIELD_NAME]
                    lstImportantFieldsRet.append(tupFields)


            return lstImportantFieldsRet

        except Exception as err:
            raise VirusTotalGetFileScanReportException(str(err))
    
DEFAULT_VT_API_KEY = ""
virusTotalDefault = VirusTotal(DEFAULT_VT_API_KEY)

#Returns a List of tuples containing the MD5 Hash for the file, Number of AV Engines flagging the file as bad, Total AV Engines, and Permalink to the analysis for the file
def getFileScanReportsImportantFields(lstHashesIn, virusTotalIn = virusTotalDefault):
    return virusTotalIn.getFileScanReportsImportantFields(lstHashesIn)



