import splunk.admin as admin
import splunk.rest as rest
import base_handler as base
import snow_account_manager as samanager
import splunklib.client as client
import util as util

"""
@api {GET} /saas-snow/splunk_app_servicenow_accounts list all service now accounts
@apiName list-snow-accounts
@apiGroup snow-accounts
@apiSuccess {Atom.Entry} entry service now accounts
"""

"""
@api {POST} /saas-snow/splunk_app_servicenow_accounts/:name create a new service now account
@apiName create-snow-accounts
@apiGroup snow-accounts
@apiParam name The name of service now account you want to create, put it in the url
@apiParam snow_url Service now url
@apiParam release  Release version of target service now instance
@apiParam username Service now user name
@apiParam password The password of your service now account
@apiSuccess {Atom.Entry} entry created aws account
"""

"""
@api {delete} /saas-snow/splunk_app_servicenow_accounts/:name remove a service now account
@apiName delete-snow-accounts
@apiParam name the name of the account you want to delete
@apiGroup snow-accounts
"""

logger = util.getLogger()
ARG_TARGET = "target"

TARGET_PROPERTIES_MAPPING = {"snow_url":"url",'username':'username','release':'release','password':'password'}

class ServiceNowAccountsHandler (base.BaseHandler):
    def setup(self):
        self.supportedArgs.addReqArg(ARG_TARGET)
        if self.requestedAction in [admin.ACTION_CREATE, admin.ACTION_EDIT]:
            self.supportedArgs.addReqArg(ARG_TARGET)
            for key in TARGET_PROPERTIES_MAPPING:
                self.supportedArgs.addReqArg(key)

    def handleList(self,confInfo):
        target = self.callerArgs[ARG_TARGET][0]
        service = self._get_ta_target_service(target)
        account_manager = samanager.SnowAccountManager(service)
        account = account_manager.list()[0]
        if account.content.username and account.content.url:
            account_in_response = confInfo[account.name]
            for prop in TARGET_PROPERTIES_MAPPING:
                account_in_response[prop] = account.content[TARGET_PROPERTIES_MAPPING[prop]]

    def handleEdit(self,confInfo):
        target = self.callerArgs[ARG_TARGET][0]
        snow_url = self.callerArgs["snow_url"][0]
        username = self.callerArgs["username"][0]
        password = self.callerArgs["password"][0]
        service = self._get_ta_target_service(target)
        account_manager = samanager.SnowAccountManager(service)
        account = account_manager.add_or_update(snow_url=snow_url,username=username,password=password)
        self.enable_all_data_inputs(True)
        self.enable_all_local_reports(True)
        if target != "127.0.0.1" and target != "localhost":
            local_service = self._get_ta_target_service("127.0.0.1")
            local_account_manager = samanager.SnowAccountManager(local_service)
            local_account_manager.add_or_update(snow_url=snow_url,username=username,password=password)
        return account


    def handleCreate(self,confInfo):
        self.handleEdit(confInfo)

    def handleRemove(self,confInfo):
        '''
        since SNOW TA does not provide delete method in its custom REST service
        we use splunk REST to delete the conf file instead.
        :param confInfo:
        :return:
        '''
        target = self.callerArgs[ARG_TARGET][0]
        service = self._get_ta_target_service(target)
        account_manager = samanager.SnowAccountManager(service)
        account_manager.delete("snow_account")
        self.enable_all_data_inputs(False)
        self.enable_all_local_reports(False)
        if target != "127.0.0.1" and target != "localhost":
            local_service = self._get_ta_target_service("127.0.0.1")
            local_account_manager = samanager.SnowAccountManager(local_service)
            local_account_manager.delete("snow_account")

    def enable_all_local_reports(self,enable_or_disable):
        service = self._get_ta_target_service("127.0.0.1")
        reports = client.SavedSearches(service)
        for report in reports.list():
            if report.state.access["app"] == "Splunk_TA_snow":
                if enable_or_disable:
                    report.enable()
                else:
                    report.disable()

    def enable_all_data_inputs(self, enable_or_disable):
        target = self.callerArgs[ARG_TARGET][0]
        service = self._get_ta_target_service(target)
        inputs = client.Inputs(service)
        for input in inputs.list("snow"):
            if enable_or_disable:
                input.enable()
            else:
                input.disable()

admin.init(ServiceNowAccountsHandler, admin.CONTEXT_APP_ONLY)