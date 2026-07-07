#COPYRIGHT (C) JOSEPH KOVACIC 2020 - ALL RIGHTS RESERVED
#Unauthorized copying, distribution, or reuse of this file or its contents, via any medium is strictly prohibited without written consent

import Splunk_Main
import Splunk_KV_Store

PERSEUS_MANAGEMENT_LOG_KV_STORE_NAME = "PerseusManagementLog"
PERSEUS_MANAGEMENT_LOG_OPERATION_FIELD_NAME = "strOperation"
PERSEUS_MANAGEMENT_LOG_RETURN_CODE_FIELD_NAME = "nReturnCode"
PERSEUS_MANAGEMENT_LOG_MESSAGE_FIELD_NAME = "strMessage"
PERSEUS_MANAGEMENT_LOG_EXECUTION_TIME_FIELD_NAME = "dtExecutionTime"

PERSEUS_MANAGEMENT_LOG_OPERATION_PERSEUS_INSTALL = "PerseusInstall"
PERSEUS_MANAGEMENT_LOG_OPERATION_POST_INSTALL_CONFIG_WIZARD = "PostInstallConfigWizard" #Used by Engine
PERSEUS_MANAGEMENT_LOG_OPERATION_PERSEUS_REGISTER = "PerseusRegister"
PERSEUS_MANAGEMENT_LOG_OPERATION_PERSEUS_MANAGE = "PerseusManage"
PERSEUS_MANAGEMENT_LOG_OPERATION_RESTART_SPLUNK = "RestartSplunk"
PERSEUS_MANAGEMENT_LOG_OPERATION_PERSEUS_PYTHON_AUTH_CONFIGURED = "PerseusSetPythonAuth"
PERSEUS_MANAGEMENT_LOG_OPERATION_ENABLE_TLS_SUPPORT = "EnableTLSSupport"
PERSEUS_MANAGEMENT_LOG_OPERATION_CREATE_SELF_SIGNED_CERTS_AND_ENABLE_SPLUNK_WEB_SSL = "CreateCertsAndEnableSSL"
PERSEUS_MANAGEMENT_LOG_OPERATION_ENABLE_FREE_LICENSE_WITH_API_SUPPORT = "EnableFreeLicenseWithApiSupport"
PERSEUS_MANAGEMENT_LOG_OPERATION_DISABLE_NONLOCAL_API_ACCESS = "DisableNonLocalApiAccess"
PERSEUS_MANAGEMENT_LOG_OPERATION_DISABLE_NONLOCAL_WEB_ACCESS = "DisableNonLocalWebAccess"
PERSEUS_MANAGEMENT_LOG_OPERATION_PERMIT_WEB_ACCESS_IP = "PermitWebAccessIP"
PERSEUS_MANAGEMENT_LOG_OPERATION_ENABLE_ACQUISITION_UPLOAD = "EnableAcquisitionUpload"
PERSEUS_MANAGEMENT_LOG_OPERATION_DISABLE_ACQUISITION_UPLOAD = "DisableAcquisitionUpload"
PERSEUS_MANAGEMENT_LOG_OPERATION_DISABLE_ADD_INTEGRATION_CREDENTIALS = "AddIntegrationCredentials"

#Scheduled Search Operations

PERSEUS_MANAGEMENT_LOG_OPERATION_PROCESS_HOST_INFO = "ProcessHostInfo"
PERSEUS_MANAGEMENT_LOG_OPERATION_PROCESS_HOST_FIRST_CONTACT = "ProcessHostFirstContact"
PERSEUS_MANAGEMENT_LOG_OPERATION_PROCESS_UNAUTHORIZED_MODS = "ProcessUnauthorizedMods"
PERSEUS_MANAGEMENT_LOG_OPERATION_CREATE_UREG_SNAPSHOT = "CreateURegSnapshot"
PERSEUS_MANAGEMENT_LOG_OPERATION_CREATE_UDRIVE_SNAPSHOT = "CreateUDriveSnapshot"
PERSEUS_MANAGEMENT_LOG_OPERATION_ANALYZE_MD5 = "AnalyzeMD5"
PERSEUS_MANAGEMENT_LOG_OPERATION_CONDUCT_HEALTH_CHECK = "ConductHealthCheck"
PERSEUS_MANAGEMENT_LOG_OPERATION_RECOLLECTION_CACHE_HOST = "RecollectionCacheHost"
#PERSEUS_MANAGEMENT_LOG_OPERATION_ = ""

PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS = 0
PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE = -1
PERSEUS_MANAGEMENT_LOG_RETURN_CODE_USER_CANCELED = -2
PERSEUS_MANAGEMENT_LOG_RETURN_CODE_PENDING = 1
PERSEUS_MANAGEMENT_LOG_RETURN_CODE_PENDING_PROCESSED = 3

PERSEUS_MANAGEMENT_OPERATION_STATUS_FIELD_NAME = "Operation Status"
PERSEUS_MANAGEMENT_OPERATION_STATUS_SUCCESS_MESSAGE = "The Operation Completed Successfully"
PERSEUS_MANAGEMENT_ERROR_MESSAGE_FIELD_NAME = "Error Message"

class PerseusManagementLogException(Exception):
    pass

class PerseusManagementLog(Splunk_KV_Store.SplunkKVStore):

    def __init__(self, headerIn = None):
        super(PerseusManagementLog, self).__init__(PERSEUS_MANAGEMENT_LOG_KV_STORE_NAME, headerIn)    

    #Raises PerseusManagementLogException on Failure if bIgnoreErrorsIn is False
    def addLogEntry(self, strOperationIn, nReturnCodeIn, strMessageIn, dtExecutionTimeIn, bIgnoreErrorsIn):
        try:
            if (dtExecutionTimeIn is None):
                dtExecutionTimeIn = Splunk_Main.getSplunkTimeForNow()

            dictNewEntry = { PERSEUS_MANAGEMENT_LOG_OPERATION_FIELD_NAME : strOperationIn,
                             PERSEUS_MANAGEMENT_LOG_RETURN_CODE_FIELD_NAME : nReturnCodeIn,
                             PERSEUS_MANAGEMENT_LOG_MESSAGE_FIELD_NAME : strMessageIn,
                             PERSEUS_MANAGEMENT_LOG_EXECUTION_TIME_FIELD_NAME : dtExecutionTimeIn   }
                                
            super(PerseusManagementLog, self).addEntry(dictNewEntry)
            
        except Exception as err:
            #!TFinish - OPTIONAL - Add An Alternative Operational Logging of This Somewhere
            if (not bIgnoreErrorsIn):          
                raise PerseusManagementLogException(str(err))

    #Raises PerseusManagementLogException on Failure
    def getLogEntries(self, dictSearchIn = None):
        try:
            return super(PerseusManagementLog, self).getEntries(dictSearchIn)
            
        except Exception as err:
            raise PerseusManagementLogException(str(err))

    #Any of the matches can be None to omit from the match criteria, and any of the fields to be updated can be ommitted by passing None
    def updateLogMatchingLogEntries(self, strOperationIn, nReturnCodeMatchIn, strMessageMatchIn, dtExecutionTimeMatchIn, nNewReturnCodeIn, strNewMessageIn, dtNewExecutionTimeIn):
        dictSearch = { PERSEUS_MANAGEMENT_LOG_OPERATION_FIELD_NAME : strOperationIn }

        if (nReturnCodeMatchIn is not None):
            dictSearch[PERSEUS_MANAGEMENT_LOG_RETURN_CODE_FIELD_NAME] = nReturnCodeMatchIn

        if (strMessageMatchIn is not None):
            dictSearch[PERSEUS_MANAGEMENT_LOG_MESSAGE_FIELD_NAME] = strMessageMatchIn
                              
        if (dtExecutionTimeMatchIn is not None):
            dictSearch[PERSEUS_MANAGEMENT_LOG_EXECUTION_TIME_FIELD_NAME] = dtExecutionTimeMatchIn

        lstEntries = self.getLogEntries(dictSearch)

        for entry in lstEntries:
            entryUpdated = entry

            if (nNewReturnCodeIn is not None):
                entryUpdated[PERSEUS_MANAGEMENT_LOG_RETURN_CODE_FIELD_NAME] = nNewReturnCodeIn

            if (strNewMessageIn is not None):
                entryUpdated[PERSEUS_MANAGEMENT_LOG_MESSAGE_FIELD_NAME] = strNewMessageIn
                              
            if (dtNewExecutionTimeIn is not None):
                entryUpdated[PERSEUS_MANAGEMENT_LOG_EXECUTION_TIME_FIELD_NAME] = dtNewExecutionTimeIn

            super(PerseusManagementLog, self).updateEntry(entryUpdated)
            
    def logPerseusInstallSuccess(self, strMessageIn = None, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_PERSEUS_INSTALL, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS, strMessageIn, None, bIgnoreErrorsIn)

    def logPerseusInstallFailure(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_PERSEUS_INSTALL, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE, strMessageIn, None, bIgnoreErrorsIn)

    def logPerseusRegisterSuccess(self, strMessageIn = None, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_PERSEUS_REGISTER, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS, strMessageIn, None, bIgnoreErrorsIn)

    def logPerseusRegisterFailure(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_PERSEUS_REGISTER, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE, strMessageIn, None, bIgnoreErrorsIn)

    def logPerseusRegisterUserSkip(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_PERSEUS_REGISTER, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_USER_CANCELED, strMessageIn, None, bIgnoreErrorsIn)

    #No success command because if a command succeeded, it logs what command exceeded
    def logPerseusManageFailure(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_PERSEUS_MANAGE, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE, strMessageIn, None, bIgnoreErrorsIn)
    
    def logRestartSplunkSuccess(self, strMessageIn = None, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_RESTART_SPLUNK, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS, strMessageIn, None, bIgnoreErrorsIn)

    def logRestartSplunkFailure(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_RESTART_SPLUNK, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE, strMessageIn, None, bIgnoreErrorsIn)

    def logPerseusPythonAuthConfiguredSuccess(self, strMessageIn = None, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_PERSEUS_PYTHON_AUTH_CONFIGURED, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS, strMessageIn, None, bIgnoreErrorsIn)

    def logPerseusPythonAuthConfiguredFailure(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_PERSEUS_PYTHON_AUTH_CONFIGURED, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE, strMessageIn, None, bIgnoreErrorsIn)

    def logEnableTLSSupportSuccess(self, strMessageIn = None, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_ENABLE_TLS_SUPPORT, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS, strMessageIn, None, bIgnoreErrorsIn)

    def logEnableTLSSupportFailure(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_ENABLE_TLS_SUPPORT, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE, strMessageIn, None, bIgnoreErrorsIn)
        
    def logCreateSelfSignedCertsAndEnableSSLSuccess(self, strMessageIn = None, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_CREATE_SELF_SIGNED_CERTS_AND_ENABLE_SPLUNK_WEB_SSL, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS, strMessageIn, None, bIgnoreErrorsIn)

    def logCreateSelfSignedCertsAndEnableSSLFailure(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_CREATE_SELF_SIGNED_CERTS_AND_ENABLE_SPLUNK_WEB_SSL, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE, strMessageIn, None, bIgnoreErrorsIn)

    def logEnableFreeLicenseWithApiSupportSuccess(self, strMessageIn = None, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_ENABLE_FREE_LICENSE_WITH_API_SUPPORT, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS, strMessageIn, None, bIgnoreErrorsIn)

    def logEnableFreeLicenseWithApiSupportFailure(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_ENABLE_FREE_LICENSE_WITH_API_SUPPORT, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE, strMessageIn, None, bIgnoreErrorsIn)

    def logDisableNonLocalApiAccessSuccess(self, strMessageIn = None, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_DISABLE_NONLOCAL_API_ACCESS, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS, strMessageIn, None, bIgnoreErrorsIn)

    def logDisableNonLocalApiAccessFailure(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_DISABLE_NONLOCAL_API_ACCESS, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE, strMessageIn, None, bIgnoreErrorsIn)

    def logDisableNonLocalWebAccessSuccess(self, strMessageIn = None, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_DISABLE_NONLOCAL_WEB_ACCESS, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS, strMessageIn, None, bIgnoreErrorsIn)

    def logDisableNonLocalWebAccessFailure(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_DISABLE_NONLOCAL_WEB_ACCESS, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE, strMessageIn, None, bIgnoreErrorsIn)

    def logPermitWebAccessIPSuccess(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_PERMIT_WEB_ACCESS_IP, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS, strMessageIn, None, bIgnoreErrorsIn)

    def logPermitWebAccessIPFailure(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_PERMIT_WEB_ACCESS_IP, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE, strMessageIn, None, bIgnoreErrorsIn)

    def logEnableAcquisitionUploadSuccess(self, strMessageIn = None, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_ENABLE_ACQUISITION_UPLOAD, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS, strMessageIn, None, bIgnoreErrorsIn)

    def logEnableAcquisitionUploadFailure(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_ENABLE_ACQUISITION_UPLOAD, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE, strMessageIn, None, bIgnoreErrorsIn)

    def logDisableAcquisitionUploadSuccess(self, strMessageIn = None, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_DISABLE_ACQUISITION_UPLOAD, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS, strMessageIn, None, bIgnoreErrorsIn)

    def logDisableAcquisitionUploadFailure(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_DISABLE_ACQUISITION_UPLOAD, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE, strMessageIn, None, bIgnoreErrorsIn)

    def logAddIntegrationCredentialsSuccess(self, strMessageIn = None, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_DISABLE_ADD_INTEGRATION_CREDENTIALS, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS, strMessageIn, None, bIgnoreErrorsIn)

    def logAddIntegrationCredentialsFailure(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_DISABLE_ADD_INTEGRATION_CREDENTIALS, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE, strMessageIn, None, bIgnoreErrorsIn)

    #Scheduled Search Operations

    def logProcessHostInfoSuccess(self, strMessageIn = None, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_PROCESS_HOST_INFO, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS, strMessageIn, None, bIgnoreErrorsIn)

    def logProcessHostInfoFailure(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_PROCESS_HOST_INFO, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE, strMessageIn, None, bIgnoreErrorsIn)
        
    def logProcessHostFirstContactSuccess(self, strMessageIn = None, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_PROCESS_HOST_FIRST_CONTACT, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS, strMessageIn, None, bIgnoreErrorsIn)

    def logProcessHostFirstContactFailure(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_PROCESS_HOST_FIRST_CONTACT, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE, strMessageIn, None, bIgnoreErrorsIn)

    def logProcessUnauthModsSuccess(self, strMessageIn = None, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_PROCESS_UNAUTHORIZED_MODS, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS, strMessageIn, None, bIgnoreErrorsIn)

    def logProcessUnauthModsFailure(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_PROCESS_UNAUTHORIZED_MODS, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE, strMessageIn, None, bIgnoreErrorsIn)

    def logCreateURegSnapshotSuccess(self, strMessageIn = None, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_CREATE_UREG_SNAPSHOT, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS, strMessageIn, None, bIgnoreErrorsIn)

    def logCreateURegSnapshotFailure(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_CREATE_UREG_SNAPSHOT, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE, strMessageIn, None, bIgnoreErrorsIn)

    def logCreateUDriveSnapshotSuccess(self, strMessageIn = None, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_CREATE_UDRIVE_SNAPSHOT, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS, strMessageIn, None, bIgnoreErrorsIn)

    def logCreateUDriveSnapshotFailure(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_CREATE_UDRIVE_SNAPSHOT, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE, strMessageIn, None, bIgnoreErrorsIn)

    def logAnalyzeMD5Success(self, strMessageIn = None, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_ANALYZE_MD5, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS, strMessageIn, None, bIgnoreErrorsIn)

    def logAnalyzeMD5Failure(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_ANALYZE_MD5, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE, strMessageIn, None, bIgnoreErrorsIn)

    def logAnalyzeMD5Pending(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_ANALYZE_MD5, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_PENDING, strMessageIn, None, bIgnoreErrorsIn)

    def logAnalyzeMD5PendingProcessed(self, strHashIn, bIgnoreErrorsIn = True):
        self.updateLogMatchingLogEntries(PERSEUS_MANAGEMENT_LOG_OPERATION_ANALYZE_MD5, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_PENDING, strHashIn, None, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_PENDING_PROCESSED, None, None)
        
    def logConductHealthCheckSuccess(self, strMessageIn = None, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_CONDUCT_HEALTH_CHECK, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS, strMessageIn, None, bIgnoreErrorsIn)

    def logConductHealthCheckFailure(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_CONDUCT_HEALTH_CHECK, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE, strMessageIn, None, bIgnoreErrorsIn)

    def logRecollectionCacheHostSuccess(self, strMessageIn = None, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_RECOLLECTION_CACHE_HOST, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS, strMessageIn, None, bIgnoreErrorsIn)

    def logRecollectionCacheHostFailure(self, strMessageIn, bIgnoreErrorsIn = True):
        self.addLogEntry(PERSEUS_MANAGEMENT_LOG_OPERATION_RECOLLECTION_CACHE_HOST, PERSEUS_MANAGEMENT_LOG_RETURN_CODE_GENERIC_FAILURE, strMessageIn, None, bIgnoreErrorsIn)

    def perseusInstallCompletedSuccessfully():
        dictSearch = { PERSEUS_MANAGEMENT_LOG_OPERATION_FIELD_NAME : PERSEUS_MANAGEMENT_LOG_OPERATION_PERSEUS_INSTALL,
                       PERSEUS_MANAGEMENT_LOG_RETURN_CODE_FIELD_NAME : PERSEUS_MANAGEMENT_LOG_RETURN_CODE_SUCCESS }
        
        return (len(self.getLogEntries(dictSearch)) > 0)

    #Returns True if either is true, indicating no additional prompting is necessary
    def perseusRegisterSuccessfulOrSkipped():
        dictSearch = { PERSEUS_MANAGEMENT_LOG_OPERATION_FIELD_NAME : PERSEUS_MANAGEMENT_LOG_OPERATION_PERSEUS_REGISTER }
        
        return (len(self.getLogEntries(dictSearch)) > 0)

