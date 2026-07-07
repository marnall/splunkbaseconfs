import splunk.admin as admin
import splunk.entity as en
import splunk.rest
import json
from collections import OrderedDict
from requests.exceptions import SSLError
import splunk.auth
import requests
# import your required python modules
from Utils.app_env import AppEnv
from domaintools import API
from domaintools.exceptions import NotAuthorizedException

'''
Copyright (C) 2005 - 2010 Splunk Inc. All Rights Reserved.
Description:  This skeleton python script handles the parameters in the configuration page.

      handleList method: lists configurable parameters in the configuration page
      corresponds to handleractions = list in restmap.conf

      handleEdit method: controls the parameters and saves the values
      corresponds to handleractions = edit in restmap.conf

'''
# set root path name
REST_ROOT_PATH = '/services'

class DToolsConfig(admin.MConfigHandler):
    '''
    Set up supported arguments
    '''
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['server', 'disabled']:
                self.supportedArgs.addOptArg(arg)

    def getCredentials(self):
        """Get the api_key from the Splunk password store.
        """
        sessionKey=self.getSessionKey()
        headers, payloadstr = splunk.rest.simpleRequest('/services/domaintools_credentials', method='POST',
                                            sessionKey=sessionKey,
                                            postargs={})
        payload = json.loads(payloadstr)
        if 'username' in payload:
            return payload['username'], payload['password']
        return '', ''

    '''
    Read the initial values of the parameters from the custom file
    myappsetup.conf, and write them to the setup page.

    If the app has never been set up,
    uses ./static/app_name/default/myappsetup.conf.

    If app has been set up, looks at
    .../local/myappsetup.conf first, then looks at
    .../default/myappsetup.conf only if there is no value for a field in
    .../local/myappsetup.conf

    For boolean fields, may need to switch the true/false setting.

    For text fields, if the conf file says None, set to the empty string.
    '''

    def handleList(self, confInfo):
        s = self.getSessionKey()

        confInfo["config"]["username"] = None
        confInfo["config"]["api_key"] = None
        app_env = AppEnv()
        try:
            api_hostname = self.readConfCtx("domaintools")["domaintools"].get("server", None)
            username, api_key = self.getCredentials()
            # username, api_key = dtools_crypto.readCreds()
            confInfo["config"]["username"] = username
            confInfo["config"]["api_key"] = "<encrypted>"
            try:
                api = API(username, api_key, api_hostname, app_partner='splunk', app_name=app_env.package_id, app_version=app_env.integration_version)
                confInfo["config"]["rate_limits"] = self.getRateLimits(api)
            except SSLError:
                confInfo["config"]["connect_success"] = False
                confInfo["config"]["auth_success"] = False
            except NotAuthorizedException:
                confInfo["config"]["connect_success"] = True
                confInfo["config"]["auth_success"] = False
            except:
                confInfo["config"]["connect_success"] = False
                confInfo["config"]["auth_success"] = False
            else:
                confInfo["config"]["connect_success"] = True
                confInfo["config"]["auth_success"] = True
                limits = json.loads(confInfo["config"]["rate_limits"])
                if 'parsed-whois' in limits:
                    self.writeConf('macros', 'per_minute_limit', {'definition': limits['parsed-whois']['per_minute_limit']})
                    self.writeConf('macros', 'cron_limit', {'definition': int(int(limits['parsed-whois']['per_minute_limit'])*5*.9)})
                    self.writeConf('macros', 'per_month_limit', {'definition': limits['parsed-whois']['per_month_limit']})
                if 'reputation' in limits:
                    self.writeConf('macros', 'per_minute_limit', {'definition': limits['reputation']['per_minute_limit']})
                    self.writeConf('macros', 'cron_limit', {'definition': int(int(limits['reputation']['per_minute_limit'])*5*.9)})
                    self.writeConf('macros', 'per_month_limit', {'definition': limits['reputation']['per_month_limit']})
                if 'risk' in limits:
                    self.writeConf('macros', 'per_minute_limit', {'definition': limits['risk']['per_minute_limit']})
                    self.writeConf('macros', 'cron_limit', {'definition': int(int(limits['risk']['per_minute_limit'])*5*.9)})
                    self.writeConf('macros', 'per_month_limit', {'definition': limits['risk']['per_month_limit']})

        except IOError:
            confInfo["config"]["username"] = None
            confInfo["config"]["api_key"] = None
            confInfo["config"]["rate_limits"] = None
            if "auth_success" not in confInfo:
                confInfo["config"]["auth_success"] = False
        confInfo["config"]["server"] = splunk.entity.getEntity('/configs/conf-domaintools', 'domaintools', namespace=app_env.package_id, sessionKey=s, owner='nobody')["server"]

    '''
    After user clicks Save on setup page, take updated parameters,
    normalize them, and save them somewhere
    '''
    def handleEdit(self, confInfo):
        name = self.callerArgs.id
        args = self.callerArgs

        '''
        Since we are using a conf file to store parameters,
        write them to the [setupentity] stanza
        in app_name/local/myappsetup.conf
        '''
        if "server" in args:
            self.writeConf('domaintools', 'domaintools', {'server': args['server'][0]})
        if "username" and "api_key" in args:
            # dtools_crypto.writeCreds(args['username'][0], args['api_key'][0])
            # self.writeConf('domaintools', 'domaintools', {'username': args['username'][0]})
            # self.writeConf('domaintools', 'domaintools', {'api_key': args['api_key'][0]})
            # self.setCredentials(args['username'][0], args['api_key'][0], self.getSessionKey())
            self.writeConf('app', 'install', {'is_configured': 'true'})
            splunk.rest.simpleRequest('/services/admin/localapps/_reload', method='GET', sessionKey=self.getSessionKey())


    def getRateLimits(self, api):
        limits = {}
        for product in api.account_information():
            limits[product['id']] = {'per_minute_limit': product['per_minute_limit'], 'per_month_limit': product['per_month_limit'], 'usage_this_month': product['usage']['month']}
        # Put parsed-whois, reputation, and risk first
        ordered_limits = OrderedDict()
        if 'parsed-whois' in limits:
            ordered_limits['parsed-whois'] = limits['parsed-whois']
            del limits['parsed-whois']
        if 'reputation' in limits:
            ordered_limits['reputation'] = limits['reputation']
            del limits['reputation']
        if 'risk' in limits:
            ordered_limits['risk'] = limits['risk']
            del limits['risk']
        for limit in limits:
            ordered_limits[limit] = limits[limit]
        return json.dumps(ordered_limits)

# initialize the handler
admin.init(DToolsConfig, admin.CONTEXT_NONE)
