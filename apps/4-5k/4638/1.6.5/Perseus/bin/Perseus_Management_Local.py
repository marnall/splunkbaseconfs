#COPYRIGHT (C) JOSEPH KOVACIC 2020 - ALL RIGHTS RESERVED
#Unauthorized copying, distribution, or reuse of this file or its contents, via any medium is strictly prohibited without written consent

#NOTE: This differs from Perseus_Management.py in that it is designed to be run via the command line $SPLUNKHOME$\bin\python.exe Perseus_Management_Local.py -args
#This runs WITHOUT authentication as a result and must do all of its manipulation directly via the file system unless Splunk_Main's default server settings are modified

try:
    from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError
except:
    #The ConfigParser module was renamed (and some behavior was changed) in Splunk 8
    from configparser import SafeConfigParser, NoSectionError, NoOptionError
    
import Perseus_Management_Log

import sys
import os
import codecs
import platform
import shutil
import shlex
import subprocess
import socket

RESTART_SPLUNK_ARG_LC = "-restart"
ENABLE_TLS_SUPPORT_ARG_LC = "-enabletlssupport"
ENABLE_FREE_LICENSE_WITH_API_SUPPORT_ARG_LC = "-enablefreelicensewithapisupport"
DISABLE_NONLOCAL_API_ACCESS_ARG_LC = "-disablenonlocalapiaccess"
DISABLE_NONLOCAL_WEB_ACCESS_ARG_LC = "-disablenonlocalwebaccess"
PERMIT_WEB_ACCESS_IP_ARG_LC = "-permitwebaccessip"
ENABLE_ACQUISITION_UPLOAD_ARG_LC = "-enableacquisitionupload"
DISABLE_ACQUISITION_UPLOAD_ARG_LC = "-disableacquisitionupload"

logPerseusManagement = Perseus_Management_Log.PerseusManagementLog()
PERSEUS_MANAGEMENT_LOCAL_LOG_MESSAGE_PREPEND_STRING = "Perseus_Management_Local "

#Splunk Web Certificate Constants
SPLUNK_WEB_USE_FQDN_AS_COMMON_NAME = ""

SPLUNK_PERSEUS_GENERATED_CERT_CA_FILE_NAME = "myCACertificate.pem"
SPLUNK_WEB_SERVER_SERVER_KEY_FILE_NAME = "myServerPrivateKey.key"
SPLUNK_WEB_SERVER_COMBINED_PEM_FILE_NAME = "myNewServerCertificate.pem"

def processCommandLine():

    dictCommandLine = {}

    for nArg in range(1, len(sys.argv)):
        strArgLC = sys.argv[nArg].lower()
        
        #No value argument
        if ((strArgLC == ENABLE_TLS_SUPPORT_ARG_LC) or (strArgLC == ENABLE_FREE_LICENSE_WITH_API_SUPPORT_ARG_LC) or (strArgLC == ENABLE_ACQUISITION_UPLOAD_ARG_LC) or (strArgLC == DISABLE_ACQUISITION_UPLOAD_ARG_LC)):
            dictCommandLine[strArgLC] = ""

        #Optionally No/Single Value arguments
        elif ((strArgLC == RESTART_SPLUNK_ARG_LC) or (strArgLC == DISABLE_NONLOCAL_API_ACCESS_ARG_LC) or (strArgLC == DISABLE_NONLOCAL_WEB_ACCESS_ARG_LC)):
            
            if ((nArg + 1) >= len(sys.argv) or (sys.argv[nArg + 1].startswith("-"))):
                dictCommandLine[strArgLC] = ""
            else:
                nArg += 1
                dictCommandLine[strArgLC] = sys.argv[nArg]

        #Single value arguments    
        elif ((strArgLC == PERMIT_WEB_ACCESS_IP_ARG_LC)):
            nArg += 1
            dictCommandLine[strArgLC] = sys.argv[nArg]
  
    return dictCommandLine

def isWindows():
    return (platform.system() == "Windows")

def getSplunkRootPath():
    strPathRet = os.path.abspath(__file__)
    
    nEtcPos = strPathRet.find("/etc/apps/")
    
    #Windows
    if (nEtcPos == -1):
        nEtcPos = strPathRet.find("\\etc\\apps\\")
        if (nEtcPos == -1):
            raise Exception("Could Not Resolve Splunk Root Path")	

    #Parent Directory of etc is the root directory - Include the / or \
    return strPathRet[0:(nEtcPos+1)]

class GetConfValueDataError(Exception):
    pass

def getConfValueData(strConfigFileIn, strStanzaIn, strValueNameIn):

    if (not os.path.isfile(strConfigFileIn)):
        raise GetConfValueDataError(strConfigFileIn + " file not found")
        
    try:
        parser = SafeConfigParser()
        #Try opening as UTF-8 (appears to work with ANSI as well)
        try:           
            with codecs.open(strConfigFileIn, "r", encoding="utf-8-sig") as inFile:
                parser.readfp(inFile)
                    
        #Rollover to default parser read      
        except:
            parser.read(strConfigFileIn)

        return parser.get(strStanzaIn, strValueNameIn)
        
    except NoSectionError:
        raise GetConfValueDataError(strStanzaIn + " stanza not found")

    except NoOptionError:
        raise GetConfValueDataError(strValueNameIn + " value not found")

    except GetConfValueDataError:
        raise

class SetConfValueDataError(Exception):
    pass

class SetConfValueDataExistsError(SetConfValueDataError):
    pass

class SetConfValueDataValueNotFoundError(SetConfValueDataError):
    pass

class SetConfValueDataMultipleValuesFoundError(SetConfValueDataError):
    pass

class SetConfValueDataAppendDataAlreadyPresentError(SetConfValueDataError):
    pass

def setConfValueData(strConfigFileIn, strStanzaIn, strValueNameIn, strValueDataIn, bModifyValueDataIfAlreadyExistsIn, strAppendDelimiterIfAlreadyExistsIn = None, bThrowErrorOnAppendIfDataToAppendAlreadyExistsIn = True):

    try:
        parser = SafeConfigParser()
        parser.read(strConfigFileIn)

        strCurrentValueData = parser.get(strStanzaIn, strValueNameIn)

        if (not bModifyValueDataIfAlreadyExistsIn):
            raise SetConfValueDataExistsError(strValueNameIn + " already exists in " + strConfigFileIn)
        
        bInStanza = False
        nReplacementCount = 0
        bAppendDataAlreadyPresent = False

        strTempFile = strConfigFileIn + ".tmp"
        with open(strTempFile, "w") as outFile:
            with open(strConfigFileIn) as inFile:
                for strLine in inFile:
                    strOutputLine = strLine.replace("\n", "")
                    
                    strStrippedLoweredLine = strLine.strip().lower()

                    #We only match the value if it is in the expected stanza
                    strStrippedLoweredLineWithoutWhitespace = ''.join(strStrippedLoweredLine.split())
                    if (bInStanza and strStrippedLoweredLineWithoutWhitespace.startswith(strValueNameIn.lower() + "=")):

                        if strAppendDelimiterIfAlreadyExistsIn is not None:
                            if (strStrippedLoweredLine.find(strValueDataIn.lower()) == -1):
                                strOutputLine += strAppendDelimiterIfAlreadyExistsIn + strValueDataIn
                                nReplacementCount += 1
                            else:
                                #Nothing to do, already exists
                                bAppendDataAlreadyPresent = True
                                
                        else:
                            strOutputLine = strValueNameIn + "=" + strValueDataIn
                            nReplacementCount += 1
                            
                    elif (bInStanza and strStrippedLoweredLine.startswith("[")):
                        bInStanza = False
                        #On the outside chance it is the exact same stanza defined again twice in a row, the if below will mark us in the proper stanza
                        
                    if (strStrippedLoweredLine == ("[" + strStanzaIn.lower() + "]")):
                        bInStanza = True

                    outFile.write(strOutputLine + "\n")
                    
        if ((nReplacementCount == 1) and (not bAppendDataAlreadyPresent)):
            #Overwrites automatically
            shutil.move(strTempFile, strConfigFileIn)
        else:
            os.remove(strTempFile)

            if (bAppendDataAlreadyPresent):
                if (bThrowErrorOnAppendIfDataToAppendAlreadyExistsIn):
                    raise SetConfValueDataAppendDataAlreadyPresentError(strValueDataIn + " exists already in " + strValueNameIn + " in config file " + strConfigFileIn)
            elif (nReplacementCount > 1):
                raise SetConfValueDataMultipleValuesFoundError(strValueNameIn + " exists multiple times in " + strConfigFileIn)
            else:
                raise SetConfValueDataValueNotFoundError(strValueNameIn + " was not found in " + strConfigFileIn)
            
        return
    
    except NoSectionError:
        #Fall Through Below to Append Value to File
        pass

    except NoOptionError:
        #Fall Through Below to Append Value to File
        pass

    except SetConfValueDataError:
        raise
    
    except Exception as err:
        raise SetConfValueDataError(str(err))
        
    with open(strConfigFileIn, "a") as outFile:
        outFile.write("\n[" + strStanzaIn + "]\n")
        outFile.write(strValueNameIn + "=" + strValueDataIn + "\n")        

def getSplunkCLIFile():
    return getSplunkRootPath() + "bin/splunk"

def getSystemServerConfigFile():
    return getSplunkRootPath() + "etc/system/local/server.conf"

def getSystemDefaultServerConfigFile():
    return getSplunkRootPath() + "etc/system/default/server.conf"

def getSystemWebConfigFile():
    return getSplunkRootPath() + "etc/system/local/web.conf"

def getSystemRestmapConfigFile():
    return getSplunkRootPath() + "etc/system/local/restmap.conf"

def getPerseusRestmapConfigFile():
    return getSplunkRootPath() + "etc/apps/Perseus/local/restmap.conf"

def getPerseusLocalMetaFile():
    return getSplunkRootPath() + "etc/apps/Perseus/metadata/local.meta"

class ExecuteSplunkCLICommandError(Exception):
    pass

def executeSplunkCLICommand(strCommandLineIn):

    try:

        #We need to split the command line into parameters, preserving quoted strings as they are
        subprocess.check_output(shlex.split('"' + getSplunkCLIFile() + '" ' + strCommandLineIn))        

    except subprocess.CalledProcessError as err:
        raise ExecuteSplunkCLICommandError("Splunk CLI returned exit code " + str(err.returncode) + " executing " + strCommandLineIn)

    except Exception as err:
        raise ExecuteSplunkCLICommandError("Splunk CLI command failed with error " + str(err) + " executing " + strCommandLineIn)


class ExecuteCommandLineCommandError(Exception):
    pass

def executeCommandLineCommand(strCommandLineIn, bUseShellIn = False):

    try:

        #We need to split the command line into parameters, preserving quoted strings as they are
        subprocess.check_output(shlex.split(strCommandLineIn), shell=bUseShellIn)        

    except subprocess.CalledProcessError as err:
        raise ExecuteCommandLineCommandError("Command Line returned exit code " + str(err.returncode))

    except Exception as err:
        raise ExecuteCommandLineCommandError("Command Line command failed with error " + str(err))
    
class RestartSplunkError(Exception):

    def __init__(self, strErrorMessageIn):
        super(RestartSplunkError, self).__init__(strErrorMessageIn)
        logPerseusManagement.logRestartSplunkFailure(PERSEUS_MANAGEMENT_LOCAL_LOG_MESSAGE_PREPEND_STRING + strErrorMessageIn)

def restartSplunk(strAdditionalParamsIn = ""):
    try:
        strSplunkCLIFile = getSplunkCLIFile()
        strParams = "restart"

        if (len(strAdditionalParamsIn)):
            strParams += (" " + strAdditionalParamsIn)

        subprocess.check_output([strSplunkCLIFile, strParams])
        
        logPerseusManagement.logRestartSplunkSuccess(PERSEUS_MANAGEMENT_LOCAL_LOG_MESSAGE_PREPEND_STRING)

    except subprocess.CalledProcessError as err:
        raise RestartSplunkError("Splunk Restart Failed: CLI returned exit code " + str(err.returncode))

    except Exception as err:
        raise RestartSplunkError("Splunk Restart Failed with error " + str(err))

def giveUserOrRolePerseusAppWritePermission(strUserNameOrRoleIn):

    #Intentionally let errors pass through
    try:

        #admin and power already have write permission by default
        if ((strUserNameOrRoleIn == "admin") or (strUserNameOrRoleIn == "power")):
            return
        
        strMetaFile = getPerseusLocalMetaFile()
        strTempFile = strMetaFile + ".tmp"

        strDelimiter = ", "

        if (not os.path.isfile(strMetaFile)):
            open(strMetaFile, "w")

        with open(strTempFile, "w") as outFile:

            bAppStanzaWritten = False
            
            with open(strMetaFile, "r") as inFile:
                bAppStanza = False
                for strLine in inFile:
                    
                    strLine = strLine.rstrip()
                    
                    if (strLine == "[]"):
                        bAppStanza = True
                    elif (strLine.startswith("[")):
                        bAppStanza = False
                    elif (bAppStanza and strLine.startswith("access")):
                        #This assumes the user/role will never appear in the read stanza as it is * by default
                        if (strLine.find(strDelimiter + strUserNameOrRoleIn) == -1):
                            strLine = (strLine[:-(len(strLine) - strLine.rfind("]"))].rstrip() + strDelimiter + strUserNameOrRoleIn + " ]")
                            bAppStanzaWritten = True
                        #It already exists, so we ditch the temp file and return since nothing needs to be modified
                        else:
                            outFile.close()
                            os.remove(strTempFile)
                            return
                        
                    outFile.write(strLine + "\n")

            if (not bAppStanzaWritten):
                outFile.write("\n")
                outFile.write("[]\n")
                
                outFile.write("access = read : [ * ], write : [ admin, power, " + strUserNameOrRoleIn + " ]\n")
                
        #Overwrites automatically
        shutil.move(strTempFile, strMetaFile)
        
    except Exception as err:
        raise
        
#Errors intentionally unhandled in this function
def switchSplunkLicenseToSplunkFreeAndEnableRestAPI():
    
    try:
        strConfigFile = getSystemServerConfigFile()
        
        #Set The License to Free
        strStanza = "license"
        strValueName = "active_group"
        strValueData = "Free"
        
        setConfValueData(strConfigFile, strStanza, strValueName, strValueData, False)
                    
        #Enable Rest API on Free
        strStanza = "general"
        strValueName = "allowRemoteLogin"
        strValueData = "always"
        setConfValueData(strConfigFile, strStanza, strValueName, strValueData, False)

        logPerseusManagement.logEnableFreeLicenseWithApiSupportSuccess(PERSEUS_MANAGEMENT_LOCAL_LOG_MESSAGE_PREPEND_STRING)
        
    except Exception as err:
        logPerseusManagement.logEnableFreeLicenseWithApiSupportFailure(PERSEUS_MANAGEMENT_LOCAL_LOG_MESSAGE_PREPEND_STRING + str(err))
        raise

#Errors intentionally unhandled in this function
def disableNonLocalRestApiAccess(strAdditionalCommaSeparatedPermittedIPsIn = ""):
    
    try:
        strConfigFile = getSystemRestmapConfigFile()    
        strStanza = "default"
        strValueName = "acceptFrom"
        strValueData = "127.0.0.1, localhost, 0.0.0.0, ::1, ::"

        if (len(strAdditionalCommaSeparatedPermittedIPsIn)):
            strValueData += (", "  + strAdditionalCommaSeparatedPermittedIPsIn)
        
        setConfValueData(strConfigFile, strStanza, strValueName, strValueData, False)

        strMessage = None
        if (len(strAdditionalCommaSeparatedPermittedIPsIn)):
            strMessage = "Permitting Access to: " + strAdditionalCommaSeparatedPermittedIPsIn
            
        logPerseusManagement.logDisableNonLocalApiAccessSuccess(PERSEUS_MANAGEMENT_LOCAL_LOG_MESSAGE_PREPEND_STRING + strMessage)
        
    except Exception as err:
        logPerseusManagement.logDisableNonLocalApiAccessFailure(PERSEUS_MANAGEMENT_LOCAL_LOG_MESSAGE_PREPEND_STRING + str(err))
        raise


        
#Errors intentionally unhandled in this function
def disableNonLocalWebAccess(strAdditionalCommaSeparatedPermittedIPsIn = ""):

    try:
        strConfigFile = getSystemWebConfigFile()    
        strStanza = "settings"
        strValueName = "acceptFrom"
        strValueData = "127.0.0.1, localhost, 0.0.0.0, ::1, ::"

        if (len(strAdditionalCommaSeparatedPermittedIPsIn)):
            strValueData += (", "  + strAdditionalCommaSeparatedPermittedIPsIn)
        
            setConfValueData(strConfigFile, strStanza, strValueName, strValueData, False)

            strMessage = None
            if (len(strAdditionalCommaSeparatedPermittedIPsIn)):
                strMessage = "Permitting Access to: " + strAdditionalCommaSeparatedPermittedIPsIn
            
            logPerseusManagement.logDisableNonLocalWebAccessSuccess(PERSEUS_MANAGEMENT_LOCAL_LOG_MESSAGE_PREPEND_STRING + strMessage)

    except Exception as err:
        
        logPerseusManagement.logDisableNonLocalWebAccessFailure(PERSEUS_MANAGEMENT_LOCAL_LOG_MESSAGE_PREPEND_STRING + str(err))
        raise

#Errors intentionally unhandled in this function
#IMPORTANT NOTE: To have functioning Web Access, an IP address also needs API Access
#!TFinish - OPTIONAL - Add detection of API Access for IP and raise exception, add API Access, and/or return success message indicating missing API Access if missing
def permitWebAccessIp(strSingleIpIn, bErrorIfAlreadyPresentIn = False):

    #Note: From web.conf file comments for acceptFrom "this setting only takes effect when appServerPorts is set to a non-zero value". This condition appears to be satisfied with default settings

    if (strSingleIpIn.find(",") != -1):
        strErrorMessage = "You may only add one IP Address at a time. Please try again with a single IP"
        logPerseusManagement.logPermitWebAccessIPFailure(PERSEUS_MANAGEMENT_LOCAL_LOG_MESSAGE_PREPEND_STRING + strErrorMessage)
        raise Exception(strErrorMessage)
    
    try:
        strConfigFile = getSystemWebConfigFile()    
        strStanza = "settings"
        strValueName = "acceptFrom"
        strValueData = strSingleIpIn

        setConfValueData(strConfigFile, strStanza, strValueName, strValueData, True, ", ")

        logPerseusManagement.logPermitWebAccessIPSuccess(PERSEUS_MANAGEMENT_LOCAL_LOG_MESSAGE_PREPEND_STRING + "Added Access for " + strSingleIpIn)

    except SetConfValueDataAppendDataAlreadyPresentError:

        #Only raise the error if caller specifies - otherwise nothing to do so we can just return                                                            
        if bErrorIfAlreadyPresentIn:
            logPerseusManagement.logPermitWebAccessIPFailure(PERSEUS_MANAGEMENT_LOCAL_LOG_MESSAGE_PREPEND_STRING + "Entry for " + strSingleIpIn + " already existed")
            raise
        else:
            logPerseusManagement.logPermitWebAccessIPSuccess(PERSEUS_MANAGEMENT_LOCAL_LOG_MESSAGE_PREPEND_STRING + "Access Already Present for " + strSingleIpIn)

    except Exception as err:
        logPerseusManagement.logPermitWebAccessIPFailure(PERSEUS_MANAGEMENT_LOCAL_LOG_MESSAGE_PREPEND_STRING + str(err))
        raise

#Errors intentionally unhandled in this function                                                                  
def setPerseusAcqRepoUploadRestApiCapability(bEnabledIn):

    try:
        strConfigFile = getPerseusRestmapConfigFile()
        
        #We control the availability of this capability by either accepting uploads from all IPs or none
        strValueName = "acceptFrom"
        if (bEnabledIn):
            strValueData = "*"
        else:
            strValueData = "!*"

        setConfValueData(strConfigFile, "script:perseusacquisition", strValueName, strValueData, True)
        setConfValueData(strConfigFile, "script:getrawfilecopyutility32", strValueName, strValueData, True)
        setConfValueData(strConfigFile, "script:getrawfilecopyutility64", strValueName, strValueData, True)
        
        if (bEnabledIn):
            logPerseusManagement.logEnableAcquisitionUploadSuccess(PERSEUS_MANAGEMENT_LOCAL_LOG_MESSAGE_PREPEND_STRING)
        else:
            logPerseusManagement.logDisableAcquisitionUploadSuccess(PERSEUS_MANAGEMENT_LOCAL_LOG_MESSAGE_PREPEND_STRING)
            
    except Exception as err:
        if (bEnabledIn):
            logPerseusManagement.logEnableAcquisitionUploadFailure(PERSEUS_MANAGEMENT_LOCAL_LOG_MESSAGE_PREPEND_STRING + str(err))
        else:
            logPerseusManagement.logDisableAcquisitionUploadFailure(PERSEUS_MANAGEMENT_LOCAL_LOG_MESSAGE_PREPEND_STRING + str(err))
            
        raise

def getManagementPort():

    try:
    
        strConfigFile = getSystemWebConfigFile()
        strStanza = "settings"
        strValueName = "mgmtHostPort"
        
        strValueData = getConfValueData(strConfigFile, strStanza, strValueName)

        return int(strValueData[(strValueData.find(":") + 1):])
            
    except Exception as err:
        #On Error Use the Default Management Port
        return 8089

#This allows early versions of Powershell (such as the Powershell 2.0 that ships with the first version of Windows 7) to connect via SSL
def enableTLSSupport():

    try:
        strDefaultConfigFile = getSystemDefaultServerConfigFile()
        strConfigFile = getSystemServerConfigFile()

        strSSLVersionsValueData = "tls"
        try:
            #We just do this to see if it exists in this config file - if it does we append to it below
            getConfValueData(strConfigFile, "sslConfig", "sslVersions")
            setConfValueData(strConfigFile, "sslConfig", "sslVersions", strSSLVersionsValueData, True, ", ", False)

        #If the value doesn't exists already in the local file, we read from the default
        except GetConfValueDataError:
            #This default is guaranteed to exist
            strDefaultValue = getConfValueData(strDefaultConfigFile, "sslConfig", "sslVersions")                 
            setConfValueData(strConfigFile, "sslConfig", "sslVersions", strDefaultValue + ", " + strSSLVersionsValueData, False)

        strCipherSuiteValueData = "TLSv1+HIGH:TLSv1.2+HIGH"
        try:
            #We just do this to see if it exists in this config file - if it does we append to it below
            getConfValueData(strConfigFile, "sslConfig", "cipherSuite")
            setConfValueData(strConfigFile, "sslConfig", "cipherSuite", strCipherSuiteValueData, True, ":", False)

        #If the value doesn't exists already in the local file, we read from the default
        except GetConfValueDataError:
            #This default is guaranteed to exist
            strDefaultValue = getConfValueData(strDefaultConfigFile, "sslConfig", "cipherSuite")                 
            setConfValueData(strConfigFile, "sslConfig", "cipherSuite", strDefaultValue + ":" + strCipherSuiteValueData, False)

            logPerseusManagement.logEnableTLSSupportSuccess(PERSEUS_MANAGEMENT_LOCAL_LOG_MESSAGE_PREPEND_STRING)
        
    except Exception as err:
        logPerseusManagement.logEnableTLSSupportFailure(PERSEUS_MANAGEMENT_LOCAL_LOG_MESSAGE_PREPEND_STRING + str(err))
        raise

class CreateSelfSignedSplunkWebCertsError(Exception):
    pass

#Returns the Root Cert So It Can Be Added to a Trust Store
def createSelfSignedSplunkWebCerts(strCertSubdirectoryNameIn, strCommonNameIn = SPLUNK_WEB_USE_FQDN_AS_COMMON_NAME, strCountryCodeIn = "", strStateProvinceNameIn = "", strLocalityNameIn = "", strOrganizationNameIn = "", strOrganizationalUnitNameIn = ""):

    #All steps taken from https://docs.splunk.com/Documentation/Splunk/7.2.0/Security/Howtoself-signcertificates
    try:

        #If no explicit common name is provided, we use the fully qualified domain name. We want to fail here before we do anything else if we can't get the FQDN
        if (strCommonNameIn == SPLUNK_WEB_USE_FQDN_AS_COMMON_NAME):
            strCommonNameIn = socket.getfqdn()

        #Create Certificate Directory in /etc/auth/[strCertSubdirectoryNameIn]

        if (isWindows()):
            strCertDirectory = getSplunkRootPath() + "etc\\auth\\" + strCertSubdirectoryNameIn + "\\"
            strSplunkWebDirectory = getSplunkRootPath() + "etc\\auth\\splunkweb\\"
            strOpenSSLDefaultConfigFile = getSplunkRootPath() + "openssl.cnf"
        else:
            strCertDirectory = getSplunkRootPath() + "etc/auth/" + strCertSubdirectoryNameIn + "/"
            strSplunkWebDirectory = getSplunkRootPath() + "etc/auth/splunkweb/"
            strOpenSSLDefaultConfigFile = getSplunkRootPath() + "openssl/openssl.cnf"

        if (not os.path.isdir(strCertDirectory)):
            os.mkdir(strCertDirectory)

        strPrivateKeyFileName = "myCAPrivateKey.key"
        strPrivateKeyFile = '"' + strCertDirectory + strPrivateKeyFileName + '"'

        strCertSigningRequestFileName = "myCACertificate.csr"
        strCertSigningRequestFile = '"' + strCertDirectory + strCertSigningRequestFileName + '"'

        strPemFileName = SPLUNK_PERSEUS_GENERATED_CERT_CA_FILE_NAME
        strPemFile = strCertDirectory + strPemFileName 
        strPemFileWithQuotes = '"' + strPemFile + '"'

        strServerKeyFileName = SPLUNK_WEB_SERVER_SERVER_KEY_FILE_NAME
        strServerKeyFile = strCertDirectory + strServerKeyFileName
        strServerKeyFileWithQuotes = '"' + strServerKeyFile + '"'

        strServerCertSigningRequestFileName = "myServerCertificate.csr"
        strServerCertSigningRequestFile = strCertDirectory + strServerCertSigningRequestFileName
        strServerCertSigningRequestFileWithQuotes = '"' + strServerCertSigningRequestFile + '"'
        
        strServerPemFileName = "myServerCertificate.pem"
        strServerPemFile = strCertDirectory + strServerPemFileName
        strServerPemFileWithQuotes = '"' + strServerPemFile + '"'
        
        strServerCombinedPemFileName = SPLUNK_WEB_SERVER_COMBINED_PEM_FILE_NAME
        strServerCombinedPemFile = strCertDirectory + strServerCombinedPemFileName
        
        strRootCAConfigFileName = "myCACertificate.cnf"
        strRootCAConfigFile =  strCertDirectory + strRootCAConfigFileName

        #Splunk Web does NOT currently support pass phrases
        strPassPhrase = ""

        #Generate a private key for your root certificate
        if (strPassPhrase):
            executeSplunkCLICommand("cmd openssl genrsa -aes256 -passout pass:" + strPassPhrase + " -out " + strPrivateKeyFile + " 2048")
        else:
            executeSplunkCLICommand("cmd openssl genrsa -out " + strPrivateKeyFile + " 2048")

        #Generate the certificate
        if (len(strCountryCodeIn) == 0):
            strCountryCodeIn = "US"

        if (len(strStateProvinceNameIn) == 0):
            strStateProvinceNameIn = "Ohio"

        if (len(strLocalityNameIn) == 0):
            strLocalityNameIn = "Cleveland"

        if (len(strOrganizationNameIn) == 0):
            strOrganizationNameIn = "Perseus"
            
        if (len(strOrganizationalUnitNameIn) == 0):
            strOrganizationalUnitNameIn = "ClientAutomation"

        if (not os.path.isfile(strPemFile)):
            #The common name of the root certificate does not have to match the server name
            #!TFinish -  OPTIONAL - We create one root cert per server with this - but it'd be better to have one root cert for all our servers. We could accomplish this by storing the private key/pem in the engine the first time we create one (with a separate create root cert function perhaps) and then pass that key/pem to sign each server's certs
            strUserInput = '"/C=' + strCountryCodeIn + '/ST=' + strStateProvinceNameIn + '/L=' + strLocalityNameIn + '/O=' + strOrganizationNameIn + '/OU=' + strOrganizationalUnitNameIn + '/CN=Perseus Root Certificate for ' + strCommonNameIn + '"'

            #The commented out section is Splunk's instructions for creating a Root Certificate, but this approach works better
            executeSplunkCLICommand("cmd openssl req -x509 -new -nodes -sha512 -key " + strPrivateKeyFile + " -out " + strPemFileWithQuotes + " -days 1095 -subj " + strUserInput)                              

        if (not os.path.isfile(strServerKeyFile)):
            #!TFinish - OPTIONAL - If the user provides a comma delimitted strCommonNameIn, we could use subjectAltName in an extensions file we create to support multiple common names (provided ones, FQDN, private IP, public IP)
            #Generate a key for your server certificate
            if (strPassPhrase):
                executeSplunkCLICommand("cmd openssl genrsa -aes256 -passout pass:" + strPassPhrase + " -out " + strServerKeyFileWithQuotes + " 2048")
            else:
                 executeSplunkCLICommand("cmd openssl genrsa -out " + strServerKeyFileWithQuotes + " 2048")
             
        #Generate and sign a new server certificate
        if (not os.path.isfile(strServerCertSigningRequestFile)):
            strUserInput = '"/C=' + strCountryCodeIn + '/ST=' + strStateProvinceNameIn + '/L=' + strLocalityNameIn + '/O=' + strOrganizationNameIn + '/OU=' + strOrganizationalUnitNameIn + '/CN=' + strCommonNameIn + '"'

            if (strPassPhrase):
                executeSplunkCLICommand("cmd openssl req -new -key " + strServerKeyFileWithQuotes + " -passin pass:" + strPassPhrase + " -out " + strServerCertSigningRequestFileWithQuotes + " -subj " + strUserInput)
            else:
                executeSplunkCLICommand("cmd openssl req -new -key " + strServerKeyFileWithQuotes + " -out " + strServerCertSigningRequestFileWithQuotes + " -subj " + strUserInput)

        if (not os.path.isfile(strServerPemFile)):
            if (strPassPhrase):
                executeSplunkCLICommand("cmd openssl x509 -req -in " + strServerCertSigningRequestFileWithQuotes + " -SHA256 -CA " + strPemFileWithQuotes + " -CAkey " + strPrivateKeyFile + " -passin pass:" + strPassPhrase + " -CAcreateserial -out " + strServerPemFileWithQuotes + " -days 1095")
            else:
                executeSplunkCLICommand("cmd openssl x509 -req -in " + strServerCertSigningRequestFileWithQuotes + " -SHA256 -CA " + strPemFileWithQuotes + " -CAkey " + strPrivateKeyFile + " -CAcreateserial -out " + strServerPemFileWithQuotes + " -days 1095")
            
        #Create Single Server Pem File
        if (not os.path.isfile(strServerCombinedPemFile)):
            lstFiles = [strServerPemFile, strServerKeyFile, strPemFile]
            with open(strServerCombinedPemFile, 'w') as outFile:
                for strFile in lstFiles:
                    with open(strFile) as inFile:
                        outFile.write(inFile.read())        
            
        #Copy Server Key and Server Combined Pem into /etc/auth/splunkweb
        strSplunkWebKeyFile = strSplunkWebDirectory + strServerKeyFileName
        if (not os.path.isfile(strSplunkWebKeyFile)):            
            shutil.copy(strServerKeyFile, strSplunkWebKeyFile)

        strSplunkWebPemFile = strSplunkWebDirectory + strServerCombinedPemFileName
        if (not os.path.isfile(strSplunkWebPemFile)):        
            shutil.copy(strServerCombinedPemFile, strSplunkWebPemFile)

        #Return the Root Certificate to Add to Trust Store - Return Nothing on Failure
        try:
            return getPerseusCreatedRootCert(strPemFile)
        except:
            return ""

    #Exceptions Fall Through Below
    except socket.error as err:
        strErrorMessage = "No host name was provided, and the fully qualified domain name could not be obtained automatically"

    except OSError as err:
        strErrorMessage = "Could not create certificates directory with error " + str(err)
        
    except ExecuteSplunkCLICommandError as err:
        strErrorMessage = str(err)

    except ExecuteCommandLineCommandError as err:
        strErrorMessage = str(err)

    except IOError as err:
        strErrorMessage = "Copying Files to Splunk Web Failed with error " + str(err)
        
    except Exception as err:
        strErrorMessage = str(err)

    raise CreateSelfSignedSplunkWebCertsError(strErrorMessage)

def getPerseusCreatedRootCert(strPemFileIn = None):

    #Let Errors Pass Through
    strPemFile = strPemFileIn

    if (not strPemFile):    
        strPemFileName = SPLUNK_PERSEUS_GENERATED_CERT_CA_FILE_NAME
        strPemFile = getSplunkRootPath() + "etc/auth/PerseusGeneratedCerts/" + strPemFileName 

    with open(strPemFile, "r") as inFile:
        return inFile.read()
    
def executeCommands():
    try:
        dictArgs = processCommandLine()

        if (len(dictArgs) == 0):
            strErrorMessage = "No Valid Operation Was Specified (Did You Forget to Add a Leading - Before Your Operation?)"

            logPerseusManagement.logPerseusManageFailure(PERSEUS_MANAGEMENT_LOCAL_LOG_MESSAGE_PREPEND_STRING + strErrorMessage + " for command line " + " ".join(sys.argv[:]))
            raise Exception(strErrorMessage)

        if (ENABLE_TLS_SUPPORT_ARG_LC in dictArgs):
            enableTLSSupport()
            
        if (ENABLE_FREE_LICENSE_WITH_API_SUPPORT_ARG_LC in dictArgs):
            switchSplunkLicenseToSplunkFreeAndEnableRestAPI()

        if (DISABLE_NONLOCAL_API_ACCESS_ARG_LC in dictArgs):
            disableNonLocalRestApiAccess(dictArgs[DISABLE_NONLOCAL_API_ACCESS_ARG_LC])
            
        if (DISABLE_NONLOCAL_WEB_ACCESS_ARG_LC in dictArgs):
            disableNonLocalWebAccess(dictArgs[DISABLE_NONLOCAL_WEB_ACCESS_ARG_LC])

        if (PERMIT_WEB_ACCESS_IP_ARG_LC in dictArgs):
            permitWebAccessIp(dictArgs[PERMIT_WEB_ACCESS_IP_ARG_LC], False)

        if (ENABLE_ACQUISITION_UPLOAD_ARG_LC in dictArgs):
            setPerseusAcqRepoUploadRestApiCapability(True)
            
        if (DISABLE_ACQUISITION_UPLOAD_ARG_LC in dictArgs):
            setPerseusAcqRepoUploadRestApiCapability(False)
            
        #We do this last as it is likely called after making other changes that require a restart to take effect
        if (RESTART_SPLUNK_ARG_LC in dictArgs):
            restartSplunk(dictArgs[RESTART_SPLUNK_ARG_LC])
    
        return 0

    except Exception as err:
        #Already Added to Perseus Management Log by Whatever Raised the Exception
        print (str(err))

        #Since this is called from a command line and not via splunk | script, we do want to return a negative return value so caller can process failure appropriately
        return -1
        

if __name__ == "__main__":
    sys.exit(executeCommands())
    
