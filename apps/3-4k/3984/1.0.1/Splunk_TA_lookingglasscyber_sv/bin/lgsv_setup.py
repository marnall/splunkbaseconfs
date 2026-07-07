import splunk.admin as admin
import splunk.entity as en
from requests import get, post
from splunk import getLocalServerInfo
from os import environ, path

'''
Copyright (C) 2005 - 2010 Splunk Inc. All Rights Reserved.
Description:  This skeleton python script handles the parameters in the configuration page.

handleList method: lists configurable parameters in the configuration page
corresponds to handleractions = list in restmap.conf

handleEdit method: controls the parameters and saves the values
corresponds to handleractions = edit in restmap.conf

'''

class ConfigApp(admin.MConfigHandler):
    '''
    Set up supported arguments
    '''
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['sv_user', 'sv_password', 'svproject', 'svhost', 'use_proxy_server', 'use_proxy', 'enable_sv']:
                self.supportedArgs.addOptArg(arg)

    '''
    Read the initial values of the parameters from the custom file
    myappsetup.conf, and write them to the setup screen.

    If the app has never been set up,
    uses .../<appname>/default/myappsetup.conf.

    If app has been set up, looks at
    .../local/myappsetup.conf first, then looks at
    .../default/myappsetup.conf only if there is no value for a field in
    .../local/myappsetup.conf

    For boolean fields, may need to switch the true/false setting.

    For text fields, if the conf file says None, set to the empty string.
    '''

    def validateInput(self, input_to_validate):
        PERMITTED_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_-., "
        input_validated_string = "".join(char for char in input_to_validate if char in PERMITTED_CHARS)

        return input_validated_string

    def handleList(self, confInfo):
        confDict = self.readConf("splunk_sv")

        if None != confDict:
            for stanza, settings in confDict.items():
                for key, val in settings.items():
                    if key in ['sv_user', 'svproject', 'svhost'] and val in [None, '']:
                        val = ''
                    if key in ['use_proxy', 'enable_sv'] and val in [None, '']:
                        val = '0'
                    if key in ['sv_password', 'use_proxy_server'] and val in [None, '', ' ']:
                        val = ''

                    confInfo[stanza].append(key, val)

    '''
    After user clicks Save on setup screen, take updated parameters,
    normalize them, and save them somewhere
    '''
    def handleEdit(self, confInfo):
        name = self.callerArgs.id
        args = self.callerArgs
        lg_app = 'Splunk_TA_lookingglasscyber_sv'

        api_accounts = {
            'sv_user': 'sv_password'
        }

        validate_cert = True

        if getLocalServerInfo() == 'https://127.0.0.1:8089':
            validate_cert = False

        # Check if password exists
        for api_account in api_accounts.keys():
            url = getLocalServerInfo() + '/servicesNS/nobody/' + lg_app + '/storage/passwords/' + \
                  args[api_account][0] + '%3A?output_mode=json'

            r = get(url=url,
                    headers={'Authorization': 'Splunk ' + self.getSessionKey()},
                    verify=validate_cert)

            if args.data[api_accounts[api_account]][0] is not None:
                if r.status_code == 200:
                    # Update in password store via REST interface
                    print(getLocalServerInfo())
                    url = getLocalServerInfo() + '/servicesNS/nobody/' + lg_app + '/storage/passwords/' + \
                          args[api_account][0] + '?output_mode=json'
                    r = post(url=url,
                             data={'password': args.data[api_accounts[api_account]][0]},
                             headers={'Authorization': 'Splunk ' + self.getSessionKey()},
                             verify=validate_cert)

                else:
                    # Create in password store via REST interface (Will have no effect if the user exists)
                    url = getLocalServerInfo() + '/servicesNS/nobody/' + lg_app + '/storage/passwords?output_mode=json'
                    r = post(url=url,
                             data={'name': args.data[api_account][0], 'password': args.data[api_accounts[api_account]][0],
                                   'realm': lg_app},
                             headers={'Authorization': 'Splunk ' + self.getSessionKey()},
                             verify=validate_cert)

            # Zero-out password so that it is not written in plain text to the config file
            args[api_accounts[api_account]][0] = ''

        if self.callerArgs.data['svproject'][0] in [None, '']:
            self.callerArgs.data['svproject'][0] = ''
        if self.callerArgs.data['svhost'][0] in [None, '', ' ']:
            self.callerArgs.data['svhost'][0] = ''

        if int(self.callerArgs.data['enable_sv'][0]) == 1:
            self.callerArgs.data['enable_sv'][0] = '1'
        else:
            self.callerArgs.data['enable_sv'][0] = '0'

        if int(self.callerArgs.data['use_proxy'][0]) == 1:
            self.callerArgs.data['use_proxy'][0] = '1'
        else:
            self.callerArgs.data['use_proxy'][0] = '0'

        if self.callerArgs.data['use_proxy_server'][0] in [None, '', ' ']:
            self.callerArgs.data['use_proxy_server'][0] = ''

        '''
        Since we are using a conf file to store parameters,
        write them to the [scoutvision] stanza
        in <appname>/local/myappsetup.conf
        '''

        # Validate input before writing it to the configuration file
        for param in ['sv_user', 'sv_password', 'svproject', 'svhost', 'use_proxy_server', 'use_proxy', 'enable_sv']:
            self.callerArgs.data[param][0] = self.validateInput(self.callerArgs.data[param][0])

        self.writeConf('splunk_sv', "setupentity", self.callerArgs.data)


# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
