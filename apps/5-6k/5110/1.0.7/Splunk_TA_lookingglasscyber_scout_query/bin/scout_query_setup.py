import splunk.admin as admin
import splunk.entity as en
from requests import get, post

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
            for arg in ['enable_scout', 'time_interval', 'time_delay', 'scout_api_token', 'scout_query', 'scouthost',
                        'use_proxy', 'use_proxy_server', 'verify_ssl']:
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
        confDict = self.readConf("splunk_scout_query")

        if confDict is not None:
            for stanza, settings in confDict.items():
                for key, val in settings.items():
                    if key in ['scout_api_token', 'scout_query', 'scouthost'] and val in [None, '']:
                        val = ''
                    if key in ['enable_scout', 'time_interval', 'time_delay', 'use_proxy', 'verify_ssl'] and val in [None, '']:
                        val = '0'

                    confInfo[stanza].append(key, val)

    '''
    After user clicks Save on setup screen, take updated parameters,
    normalize them, and save them somewhere
    '''
    def handleEdit(self, confInfo):
        name = self.callerArgs.id
        args = self.callerArgs

        if self.callerArgs.data['scout_api_token'][0] in [None, '', ' ']:
            self.callerArgs.data['scout_api_token'][0] = ''

        if self.callerArgs.data['scout_query'][0] in [None, '', ' ']:
            self.callerArgs.data['scout_query'][0] = ''

        if self.callerArgs.data['scouthost'][0] in [None, '', ' ']:
            self.callerArgs.data['scouthost'][0] = ''

        if self.callerArgs.data['use_proxy_server'][0] in [None, '', ' ']:
            self.callerArgs.data['use_proxy_server'][0] = ''

        if int(self.callerArgs.data['enable_scout'][0]) == 1:
            self.callerArgs.data['enable_scout'][0] = '1'
        else:
            self.callerArgs.data['enable_scout'][0] = '0'

        if int(self.callerArgs.data['time_interval'][0]) == 15:
            self.callerArgs.data['time_interval'][0] = '15'

        if int(self.callerArgs.data['time_delay'][0]) == 1440:
            self.callerArgs.data['time_delay'][0] = '1440'

        if int(self.callerArgs.data['use_proxy'][0]) == 1:
            self.callerArgs.data['use_proxy'][0] = '1'
        else:
            self.callerArgs.data['use_proxy'][0] = '0'

        if int(self.callerArgs.data['verify_ssl'][0]) == 1:
            self.callerArgs.data['verify_ssl'][0] = '1'
        else:
            self.callerArgs.data['verify_ssl'][0] = '0'

        '''
        Since we are using a conf file to store parameters,
        write them to the [scoutvision] stanza
        in <appname>/local/myappsetup.conf
        '''

        # Validate input before writing it to the configuration file
        for param in ['enable_scout', 'time_interval', 'time_delay', 'scout_api_token', 'scout_query', 'scouthost',
                      'use_proxy', 'use_proxy_server', 'verify_ssl']:
            self.callerArgs.data[param][0] = self.validateInput(self.callerArgs.data[param][0])

        self.writeConf('splunk_scout_query', "setupentity", self.callerArgs.data)


# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
