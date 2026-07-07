import splunk.admin as admin
import splunk.entity as en
from requests import get, post
from splunk import getLocalServerInfo

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
            for arg in ['api_key', 'clientid', 'use_proxy_server', 'use_proxy', 'enable_ctc', 'ctc_hours', 'ctc_TM', 'ctc_VD', 'ctc_KI', 'ctc_GI']:
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
        PERMITTED_CHARS = r'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_=:+-., []@*{}%;\'"'
        input_validated_string = "".join(char for char in input_to_validate if char in PERMITTED_CHARS)

        return input_validated_string

    def handleList(self, confInfo):
        confDict = self.readConf("splunk_ctc")

        if confDict is not None:
            for stanza, settings in confDict.items():
                for key, val in settings.items():
                    if key in ['api_key', 'clientid', 'use_proxy_server'] and val in [None, '']:
                        val = ''
                    if key in ['use_proxy', 'enable_ctc', 'ctc_hours', 'ctc_TM', 'ctc_VD', 'ctc_KI', 'ctc_GI'] and val in [None, '']:
                        val = '0'

                    confInfo[stanza].append(key, val)

    '''
    After user clicks Save on setup screen, take updated parameters,
    normalize them, and save them somewhere
    '''
    def handleEdit(self, confInfo):
        name = self.callerArgs.id
        args = self.callerArgs
        lg_app = 'Splunk_TA_lookingglasscyber_ctc'

        if int(self.callerArgs.data['enable_ctc'][0]) == 1:
            self.callerArgs.data['enable_ctc'][0] = '1'
        else:
            self.callerArgs.data['enable_ctc'][0] = '0'

        if self.callerArgs.data['api_key'][0] in [None, '', ' ']:
            self.callerArgs.data['api_key'][0] = ''

        if self.callerArgs.data['clientid'][0] in [None, '', ' ']:
            self.callerArgs.data['clientid'][0] = ''

        if int(self.callerArgs.data['ctc_hours'][0]) == 1:
            self.callerArgs.data['ctc_hours'][0] = '1'

        if int(self.callerArgs.data['ctc_TM'][0]) == 1:
            self.callerArgs.data['ctc_TM'][0] = '1'

        if int(self.callerArgs.data['ctc_VD'][0]) == 1:
            self.callerArgs.data['ctc_VD'][0] = '1'

        if int(self.callerArgs.data['ctc_KI'][0]) == 1:
            self.callerArgs.data['ctc_KI'][0] = '1'

        if int(self.callerArgs.data['ctc_GI'][0]) == 1:
            self.callerArgs.data['ctc_GI'][0] = '1'

        if self.callerArgs.data['use_proxy_server'][0] in [None, '', ' ']:
            self.callerArgs.data['use_proxy_server'][0] = ''

        '''
        Since we are using a conf file to store parameters,
        write them to the [scoutvision] stanza
        in <appname>/local/myappsetup.conf
        '''

        # Validate input before writing it to the configuration file
        for param in ['api_key', 'clientid', 'use_proxy_server', 'use_proxy', 'enable_ctc', 'ctc_hours', 'ctc_TM', 'ctc_VD', 'ctc_KI', 'ctc_GI']:
            self.callerArgs.data[param][0] = self.validateInput(self.callerArgs.data[param][0])

        self.writeConf('splunk_ctc', "setupentity", self.callerArgs.data)


# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
