#COPYRIGHT (C) JOSEPH KOVACIC 2020 - ALL RIGHTS RESERVED
#Unauthorized copying, distribution, or reuse of this file or its contents, via any medium is strictly prohibited without written consent

import Perseus_Management_Log
import Perseus_Management_Local
import Splunk_Main
import Splunk_Config

import six
import sys
import os
import shutil
import subprocess
import base64

NO_VALUE_ARGUMENT = ""

RESTART_SPLUNK_ARG_LC = "-restart"
SET_PYTHON_AUTHENTICATION_CREDENTIALS_ARG_LC = "-setpythonauth"
ENABLE_TLS_SUPPORT_ARG_LC = "-enabletlssupport"
CREATE_SELF_SIGNED_CERTS_AND_ENABLE_SPLUNK_WEB_SSL_ARG_LC = "-createcertsandenablessl"
WRITE_SELF_SIGNED_ROOT_CERT_TO_PERSEUS_MANAGEMENT_LOG_LC = "-writerootcerttolog"
CREATE_SELF_SIGNED_CERTS_AND_ENABLE_INPUTS_SSL_ARG_LC = "-createcertsandenableinputsssl"
ENABLE_FREE_LICENSE_WITH_API_SUPPORT_ARG_LC = "-enablefreelicensewithapisupport"
DISABLE_NONLOCAL_API_ACCESS_ARG_LC = "-disablenonlocalapiaccess"
DISABLE_NONLOCAL_WEB_ACCESS_ARG_LC = "-disablenonlocalwebaccess"
PERMIT_WEB_ACCESS_IP_ARG_LC = "-permitwebaccessip"
ENABLE_ACQUISITION_UPLOAD_ARG_LC = "-enableacquisitionupload"
DISABLE_ACQUISITION_UPLOAD_ARG_LC = "-disableacquisitionupload"

SPLUNK_SERVER_RESTART_SUFFIX_WO_SERVICES = "/server/control/restart";
SPLUNK_SERVER_RESTART_WEBUI_SUFFIX_WO_SERVICES = "/server/control/restart_webui";

PERSEUS_CERT_DIRECTORY_NAME = "PerseusGeneratedCerts"

logPerseusManagement = Perseus_Management_Log.PerseusManagementLog()

def processCommandLine():

    dictCommandLine = {}

    for nArg in range(1, len(sys.argv)):
        strArgLC = sys.argv[nArg].lower()
        
        #No value argument
        if ((strArgLC == ENABLE_TLS_SUPPORT_ARG_LC) or (strArgLC == WRITE_SELF_SIGNED_ROOT_CERT_TO_PERSEUS_MANAGEMENT_LOG_LC) or (strArgLC == ENABLE_FREE_LICENSE_WITH_API_SUPPORT_ARG_LC) or (strArgLC == ENABLE_ACQUISITION_UPLOAD_ARG_LC) or (strArgLC == DISABLE_ACQUISITION_UPLOAD_ARG_LC)):
            dictCommandLine[strArgLC] = ""
    
        #Optionally No/Single Value arguments
        elif ((strArgLC == RESTART_SPLUNK_ARG_LC) or (strArgLC == CREATE_SELF_SIGNED_CERTS_AND_ENABLE_SPLUNK_WEB_SSL_ARG_LC) or (strArgLC == CREATE_SELF_SIGNED_CERTS_AND_ENABLE_INPUTS_SSL_ARG_LC) or (strArgLC == DISABLE_NONLOCAL_API_ACCESS_ARG_LC) or (strArgLC == DISABLE_NONLOCAL_WEB_ACCESS_ARG_LC)):
            
            if ((nArg + 1) >= len(sys.argv) or (sys.argv[nArg + 1].startswith("-"))):
                dictCommandLine[strArgLC] = NO_VALUE_ARGUMENT
            else:
                nArg += 1
                dictCommandLine[strArgLC] = sys.argv[nArg]

        #Single value arguments    
        elif ((strArgLC == PERMIT_WEB_ACCESS_IP_ARG_LC)):
            nArg += 1
            dictCommandLine[strArgLC] = sys.argv[nArg]

        #Optionally No/Double value arguments
        elif ((strArgLC == SET_PYTHON_AUTHENTICATION_CREDENTIALS_ARG_LC)):
            #Indicates Free Server With No Authentication
            if ((nArg + 1) >= len(sys.argv) or (sys.argv[nArg + 1].startswith("-"))):
                dictCommandLine[strArgLC] = ("", "")
            #Indicates Store User Name But Not Password
            elif ((nArg + 2) >= len(sys.argv) or (sys.argv[nArg + 2].startswith("-"))):
                dictCommandLine[strArgLC] = (sys.argv[nArg + 1], "")
                nArg +=1
            #Indicates Store User Name and Password
            else:
                tupUserNameAndPassword = (sys.argv[nArg + 1], sys.argv[nArg + 2])
                nArg +=2
                 
                dictCommandLine[strArgLC] = tupUserNameAndPassword
              
    return dictCommandLine

class RestartSplunkError(Exception):

    def __init__(self, strErrorMessageIn):
        super(RestartSplunkError, self).__init__(strErrorMessageIn)
        logPerseusManagement.logRestartSplunkFailure(strErrorMessageIn)

def restartSplunk(bOnlyRestartSplunkWebIn = False):

    try:
        #We log this BEFORE issuing a restart because a successfull restart means we won't get the opportunity to add this KV Store entry when the operation returns
        if (bOnlyRestartSplunkWebIn):
            logPerseusManagement.logRestartSplunkSuccess("Attempting Restart of Splunk Web")
        else:
            logPerseusManagement.logRestartSplunkSuccess("Attempting Restart")

        Splunk_Main.splunkServerDefault.restartSplunk(bOnlyRestartSplunkWebIn)
        
    except Exception as err:
        #Logged in RestartSplunkError constructor
        raise RestartSplunkError(str(err))

def setPythonAuthenicationCredentials(strEncodedUserNameIn, strEncodedPasswordIn):

    try:
        if (len(strEncodedUserNameIn) > 0):
            strUserName = six.ensure_str(base64.b64decode(strEncodedUserNameIn))
        else:
            strUserName = ""

        if (len(strEncodedPasswordIn) > 0):
            strPassword = six.ensure_str(base64.b64decode(strEncodedPasswordIn))
        else:
            strPassword = ""

        #We are a free server 
        bIsFreeServer = (len(strUserName) == 0)

        strSplunkMainFile = os.path.dirname(os.path.realpath(__file__)) + "/Splunk_Main.py"
        strTempFile = strSplunkMainFile + ".tmp"

        with open(strTempFile, "w") as outFile:
        
            with open(strSplunkMainFile, "r") as inFile:
                for strLine in inFile:
                    if (strLine.startswith('DEFAULT_SPLUNK_USERNAME = "')):
                        strLine = 'DEFAULT_SPLUNK_USERNAME = "' + strUserName + '"\r\n'
                    elif (strLine.startswith('DEFAULT_SPLUNK_PASSWORD = "')):
                        strLine = 'DEFAULT_SPLUNK_PASSWORD = "' + strPassword + '"\r\n'
                    elif (strLine.startswith("DEFAULT_SPLUNK_IS_FREE_SERVER = ")):
                        strLine = "DEFAULT_SPLUNK_IS_FREE_SERVER = " + str(bIsFreeServer) + "\r\n"
                    elif (strLine.startswith("DEFAULT_SPLUNK_SERVER_MANAGEMENT_PORT = ")):
                        strLine = "DEFAULT_SPLUNK_SERVER_MANAGEMENT_PORT = " + str(Perseus_Management_Local.getManagementPort()) + "\r\n"
                        
                    outFile.write(strLine)
                                
        #Overwrites automatically
        shutil.move(strTempFile, strSplunkMainFile)

        #We need to give this user Perseus App write permission
        Perseus_Management_Local.giveUserOrRolePerseusAppWritePermission(strUserName)
            
        logPerseusManagement.logPerseusPythonAuthConfiguredSuccess()
        
    except Exception as err:
        
        logPerseusManagement.logPerseusPythonAuthConfiguredFailure(str(err))
        raise

#Not strictly necessary anymore as long as the .NET versions on the systems support TLS 1.2: This allowed early versions of Powershell (such as the Powershell 2.0 that ships with the first version of Windows 7) to connect via SSL
def enableTLSSupport():

    try:
        configServer = Splunk_Config.SplunkConfig("server", None, Splunk_Main.splunkServerDefault, Splunk_Main.SPLUNK_NO_APP_CONTEXT)

        configServer.appendConfigFileStanzaValueToKey("sslConfig", "sslVersions", "tls")
        configServer.appendConfigFileStanzaValueToKey("sslConfig", "cipherSuite", "TLSv1+HIGH:TLSv1.2+HIGH", ":")

        logPerseusManagement.logEnableTLSSupportSuccess()
        
    except Exception as err:
        logPerseusManagement.logEnableTLSSupportFailure(str(err))
        raise

#IMPORTANT NOTE: If we add any additional configuration to this process, update the installation wizards in the Perseus Engine (particularly the Sysmon Configuration Wizard with existing certs which uses SSL config settings set here)
def createSelfSignedCertsAndEnableSplunkWebSSL(strCommonNameIn):
    
    try:
        strRootCert = Perseus_Management_Local.createSelfSignedSplunkWebCerts(PERSEUS_CERT_DIRECTORY_NAME, strCommonNameIn)

        strSplunkWebDirectoryName = "splunkweb"
        if (Perseus_Management_Local.isWindows()):
            strSplunkWebDirectory = "etc\\auth\\" + strSplunkWebDirectoryName + "\\"
        else:
            strSplunkWebDirectory = "etc/auth/" + strSplunkWebDirectoryName + "/"
                    
        configWeb = Splunk_Config.SplunkConfig("web", None, Splunk_Main.splunkServerDefault, Splunk_Main.SPLUNK_NO_APP_CONTEXT)
        configWeb.setConfigFileStanzaKeyValue("settings", "enableSplunkWebSSL", "true", False)
        configWeb.setConfigFileStanzaKeyValue("settings", "privKeyPath", strSplunkWebDirectory + Perseus_Management_Local.SPLUNK_WEB_SERVER_SERVER_KEY_FILE_NAME, False)
        configWeb.setConfigFileStanzaKeyValue("settings", "serverCert", strSplunkWebDirectory + Perseus_Management_Local.SPLUNK_WEB_SERVER_COMBINED_PEM_FILE_NAME, False)

        configServer = Splunk_Config.SplunkConfig("server", None, Splunk_Main.splunkServerDefault, Splunk_Main.SPLUNK_NO_APP_CONTEXT)
        configServer.setConfigFileStanzaKeyValue("sslConfig", "enableSplunkdSSL", "true", False)
        #We are not using a passphrase, so we don't set this (though Splunk will auto-generate this field even though we don't include it - I believe it hashes the empty password)
        #configServer.setConfigFileStanzaKeyValue("sslConfig", "sslPassword", "", False)

        #The relative path starts at etc/auth. We can also use / even on Windows
        configServer.setConfigFileStanzaKeyValue("sslConfig", "serverCert", strSplunkWebDirectoryName + "/" + Perseus_Management_Local.SPLUNK_WEB_SERVER_COMBINED_PEM_FILE_NAME, False)
        
        #Not strictly necessary anymore as long as the .NET versions on the systems support TLS 1.2: This allowed early versions of Powershell (such as the Powershell 2.0 that ships with the first version of Windows 7) to connect via SSL enableTLSSupport()

        #Write the Root Cert to the Log So We Can Easily Retrieve It
        logPerseusManagement.logCreateSelfSignedCertsAndEnableSSLSuccess(strRootCert)
    
    except Exception as err:        
        logPerseusManagement.logCreateSelfSignedCertsAndEnableSSLFailure(str(err))
        raise

def writeSelfSignedRootCertToPerseusManagementLog():

    try:
        strRootCert = Perseus_Management_Local.getPerseusCreatedRootCert()
        
        if (strRootCert):
            logPerseusManagement.logCreateSelfSignedCertsAndEnableSSLSuccess(strRootCert)
        else:
            raise Exception("Could Not Read Root Cert File")
        
    except Exception as err:
        raise Exception("Could Not Write Root Cert: " + str(err))
                        
#IMPORTANT NOTE: If we add any additional configuration to this process, update the installation wizards in the Perseus Engine (particularly the Sysmon Configuration Wizard with existing certs which does not install the Perseus Splunk App and does this configuration via the REST API)
def createSelfSignedCertsAndEnableInputsSSL(strCommonNameIn):
    try:
        strRootCert = Perseus_Management_Local.createSelfSignedSplunkWebCerts("PerseusGeneratedCerts", strCommonNameIn)

        strSplunkWebDirectoryName = "splunkweb"
        if (Perseus_Management_Local.isWindows()):
            strSplunkWebDirectory = "$SPLUNK_HOME\\etc\\auth\\" + strSplunkWebDirectoryName + "\\"
            #strPerseusCertDirectory = "$SPLUNK_HOME\\etc\\auth\\" + PERSEUS_CERT_DIRECTORY_NAME + "\\"
        else:
            strSplunkWebDirectory = "$SPLUNK_HOME/etc/auth/" + strSplunkWebDirectoryName + "/"
            #strPerseusCertDirectory = "$SPLUNK_HOME/etc/auth/" + PERSEUS_CERT_DIRECTORY_NAME + "/"
            
        configInputs = Splunk_Config.SplunkConfig("inputs", None, Splunk_Main.splunkServerDefault, Splunk_Main.SPLUNK_NO_APP_CONTEXT)            
        configInputs.setConfigFileStanzaKeyValue("SSL", "serverCert", strSplunkWebDirectory + Perseus_Management_Local.SPLUNK_WEB_SERVER_COMBINED_PEM_FILE_NAME, False)
        configInputs.setConfigFileStanzaKeyValue("SSL", "requireClientCert", "false", False)

        #This do NOT appear to be necessary to get an SSL connection between the Forwarder and the server
        #configServer = Splunk_Config.SplunkConfig("server", None, Splunk_Main.splunkServerDefault, Splunk_Main.SPLUNK_NO_APP_CONTEXT)
        #configServer.setConfigFileStanzaKeyValue("sslConfig", "sslRootCAPath", strPerseusCertDirectory + Perseus_Management_Local.SPLUNK_PERSEUS_GENERATED_CERT_CA_FILE_NAME, False)

        #Write the Root Cert to the Log So We Can Easily Retrieve It
        logPerseusManagement.logCreateSelfSignedCertsAndEnableSSLSuccess(strRootCert)
    
    except Exception as err:        
        logPerseusManagement.logCreateSelfSignedCertsAndEnableSSLFailure(str(err))
        raise
    
#Errors intentionally unhandled in this function
def switchSplunkLicenseToSplunkFreeAndEnableRestAPI():
    
    try:

        configServer = Splunk_Config.SplunkConfig("server", None, Splunk_Main.splunkServerDefault, Splunk_Main.SPLUNK_NO_APP_CONTEXT)
                
        #Set The License to Free
        configServer.setConfigFileStanzaKeyValue("license", "active_group", "Free")
        
        #Enable Rest API on Free
        configServer.setConfigFileStanzaKeyValue("general", "allowRemoteLogin", "always")

        logPerseusManagement.logEnableFreeLicenseWithApiSupportSuccess()
        
    except Exception as err:
        logPerseusManagement.logEnableFreeLicenseWithApiSupportFailure(str(err))
        raise

#Errors intentionally unhandled in this function
def disableNonLocalRestApiAccess(strAdditionalCommaSeparatedPermittedIPsIn = ""):
    
    try:
        strKeyValue = "127.0.0.1, localhost, 0.0.0.0, ::1, ::"
        
        if (len(strAdditionalCommaSeparatedPermittedIPsIn)):
            strKeyValue += (", "  + strAdditionalCommaSeparatedPermittedIPsIn)
            
        configRestmap = Splunk_Config.SplunkConfig("restmap", None, Splunk_Main.splunkServerDefault, Splunk_Main.SPLUNK_NO_APP_CONTEXT)
        configRestmap.setConfigFileStanzaKeyValue("default", "acceptFrom", strKeyValue)

        strMessage = None
        if (len(strAdditionalCommaSeparatedPermittedIPsIn)):
            strMessage = "Permitting Access to: " + strAdditionalCommaSeparatedPermittedIPsIn
            
        logPerseusManagement.logDisableNonLocalApiAccessSuccess(strMessage)
        
    except Exception as err:
        logPerseusManagement.logDisableNonLocalApiAccessFailure(str(err))
        raise
    
#Errors intentionally unhandled in this function
def disableNonLocalWebAccess(strAdditionalCommaSeparatedPermittedIPsIn = ""):
    try:
        strKeyValue = "127.0.0.1, localhost, 0.0.0.0, ::1, ::"

        if (len(strAdditionalCommaSeparatedPermittedIPsIn)):
            strKeyValue += (", "  + strAdditionalCommaSeparatedPermittedIPsIn)
            
        configWeb = Splunk_Config.SplunkConfig("web", None, Splunk_Main.splunkServerDefault, Splunk_Main.SPLUNK_NO_APP_CONTEXT)
        configWeb.setConfigFileStanzaKeyValue("settings", "acceptFrom", strKeyValue)

        strMessage = None
        if (len(strAdditionalCommaSeparatedPermittedIPsIn)):
            strMessage = "Permitting Access to: " + strAdditionalCommaSeparatedPermittedIPsIn
        
        logPerseusManagement.logDisableNonLocalWebAccessSuccess(strMessage)

    except Exception as err:
        logPerseusManagement.logDisableNonLocalWebAccessFailure(str(err))
        raise

#Errors intentionally unhandled in this function
#IMPORTANT NOTE: To have functioning Web Access, an IP address also needs API Access
#!TFinish - OPTIONAL - Add detection of API Access for IP and raise exception, add API Access, and/or return success message indicating missing API Access if missing
def permitWebAccessIp(strSingleIpIn, bErrorIfAlreadyPresentIn = False):

    #Note: From web.conf file comments for acceptFrom "this setting only takes effect when appServerPorts is set to a non-zero value". This condition appears to be satisfied with default settings

    if (strSingleIpIn.find(",") != -1):
        strErrorMessage = "You may only add one IP Address at a time. Please try again with a single IP"
        logPerseusManagement.logPermitWebAccessIPFailure(strErrorMessage)
        raise Exception(strErrorMessage)
    
    try:

        configWeb = Splunk_Config.SplunkConfig("web", None, Splunk_Main.splunkServerDefault, Splunk_Main.SPLUNK_NO_APP_CONTEXT)
        bIpAdded = configWeb.appendConfigFileStanzaValueToKey("settings", "acceptFrom", strSingleIpIn)

        if (bErrorIfAlreadyPresentIn and (not bIpAdded)):
            #Logged in except handler
            raise Exception("Entry for " + strSingleIpIn + " already existed")

        logPerseusManagement.logPermitWebAccessIPSuccess("Added Access for " + strSingleIpIn)

    except Exception as err:
        logPerseusManagement.logPermitWebAccessIPFailure(str(err))
        raise

#Errors intentionally unhandled in this function                                                                  
def setPerseusAcqRepoUploadRestApiCapability(bEnabledIn):

    try:
        #We control the availability of this capability by either accepting uploads from all IPs or none
        if (bEnabledIn):
            strKeyValue = "*"
        else:
            strKeyValue = "!*"

        configPerseusRestmap = Splunk_Config.SplunkConfig("restmap")

        configPerseusRestmap.setConfigFileStanzaKeyValue("script:perseusacquisition", "acceptFrom", strKeyValue)
        configPerseusRestmap.setConfigFileStanzaKeyValue("script:getrawfilecopyutility32", "acceptFrom", strKeyValue)
        configPerseusRestmap.setConfigFileStanzaKeyValue("script:getrawfilecopyutility64", "acceptFrom", strKeyValue)
    
        if (bEnabledIn):
            logPerseusManagement.logEnableAcquisitionUploadSuccess()
        else:
            logPerseusManagement.logDisableAcquisitionUploadSuccess()
            
    except Exception as err:
        if (bEnabledIn):
            logPerseusManagement.logEnableAcquisitionUploadFailure(str(err))
        else:
            logPerseusManagement.logDisableAcquisitionUploadFailure(str(err))
            
        raise
    
def executeCommands():
    try:
        dictArgs = processCommandLine()

        if (len(dictArgs) == 0):
            strErrorMessage = "No Valid Operation Was Specified (Did You Forget to Add a Leading - Before Your Operation?)"

            logPerseusManagement.logPerseusManageFailure(strErrorMessage + " for command line " + " ".join(sys.argv[:]))
            raise Exception(strErrorMessage)

        if (SET_PYTHON_AUTHENTICATION_CREDENTIALS_ARG_LC in dictArgs):
            tupUserNameAndPassword = dictArgs[SET_PYTHON_AUTHENTICATION_CREDENTIALS_ARG_LC]
            setPythonAuthenicationCredentials(tupUserNameAndPassword[0], tupUserNameAndPassword[1])

        if (ENABLE_TLS_SUPPORT_ARG_LC in dictArgs):
            enableTLSSupport()
            
        if (CREATE_SELF_SIGNED_CERTS_AND_ENABLE_SPLUNK_WEB_SSL_ARG_LC in dictArgs):
            strCommonName = dictArgs[CREATE_SELF_SIGNED_CERTS_AND_ENABLE_SPLUNK_WEB_SSL_ARG_LC]
            if (strCommonName == NO_VALUE_ARGUMENT):
                strCommonName = Perseus_Management_Local.SPLUNK_WEB_USE_FQDN_AS_COMMON_NAME

            createSelfSignedCertsAndEnableSplunkWebSSL(strCommonName)            

        if (WRITE_SELF_SIGNED_ROOT_CERT_TO_PERSEUS_MANAGEMENT_LOG_LC in dictArgs):
            writeSelfSignedRootCertToPerseusManagementLog()
            
        if (CREATE_SELF_SIGNED_CERTS_AND_ENABLE_INPUTS_SSL_ARG_LC in dictArgs):
            strCommonName = dictArgs[CREATE_SELF_SIGNED_CERTS_AND_ENABLE_INPUTS_SSL_ARG_LC]
            if (strCommonName == NO_VALUE_ARGUMENT):
                strCommonName = Perseus_Management_Local.SPLUNK_WEB_USE_FQDN_AS_COMMON_NAME

            createSelfSignedCertsAndEnableInputsSSL(strCommonName)            
                
        if (ENABLE_FREE_LICENSE_WITH_API_SUPPORT_ARG_LC in dictArgs):
            switchSplunkLicenseToSplunkFreeAndEnableRestAPI()

        if (DISABLE_NONLOCAL_API_ACCESS_ARG_LC in dictArgs):
            disableNonLocalRestApiAccess(dictArgs[DISABLE_NONLOCAL_API_ACCESS_ARG_LC])
            
        if (DISABLE_NONLOCAL_WEB_ACCESS_ARG_LC in dictArgs):
            disableNonLocalWebAccess(dictArgs[DISABLE_NONLOCAL_WEB_ACCESS_ARG_LC])

        if (PERMIT_WEB_ACCESS_IP_ARG_LC in dictArgs):
            permitWebAccessIp(dictArgs[PERMIT_WEB_ACCESS_IP_ARG_LC], True)

        if (ENABLE_ACQUISITION_UPLOAD_ARG_LC in dictArgs):
            setPerseusAcqRepoUploadRestApiCapability(True)
            
        if (DISABLE_ACQUISITION_UPLOAD_ARG_LC in dictArgs):
            setPerseusAcqRepoUploadRestApiCapability(False)
            
        #We do this last as it is likely called after making other changes that require a restart to take effect
        if (RESTART_SPLUNK_ARG_LC in dictArgs):
            restartSplunk(dictArgs[RESTART_SPLUNK_ARG_LC].lower() == "splunkweb")
                
        print (Perseus_Management_Log.PERSEUS_MANAGEMENT_OPERATION_STATUS_FIELD_NAME)
        print (Perseus_Management_Log.PERSEUS_MANAGEMENT_OPERATION_STATUS_SUCCESS_MESSAGE)
    
        return 0

    except Exception as err:
        #Already Added to Perseus Management Log by Whatever Raised the Exception
        print (Perseus_Management_Log.PERSEUS_MANAGEMENT_ERROR_MESSAGE_FIELD_NAME)
        print (str(err))
        
        #Still return 0 to indicate script ran
        return 0

if __name__ == "__main__":
    sys.exit(executeCommands())
    



