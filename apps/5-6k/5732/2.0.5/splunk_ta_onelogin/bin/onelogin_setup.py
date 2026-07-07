#!/usr/bin/env python

import splunk.admin as admin


class ConfigApp(admin.MConfigHandler):
    # Set up supported arguments
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in self.parameters:
                self.supportedArgs.addOptArg(arg)

    # Read the initial values of the parameters from the default
    # onelogin.conf and inputs.conf files. Then write them to the setup screen.
    def handleList(self, configuration_info):
        conf_dict = self.readConf('onelogin')
        if conf_dict is not None:
            onelogin_api = conf_dict.get('onelogin_api')
            for key, val in list(onelogin_api.items()):
                configuration_info['onelogin_api'].append(key, val)

        conf_dict = self.readConf('inputs')
        if conf_dict is not None:
            interval_data = conf_dict.get(self.unix_path)
            configuration_info['onelogin_api'].append(
                'interval',
                interval_data['interval']
            )

    # After user clicks Save on setup screen, take updated parameters,
    # normalize them, and save them into local onelogin.conf and inputs.conf
    def handleEdit(self, configuration_info):
        for param in self.parameters:
            if self.callerArgs.data[param][0] in [None, '']:
                self.callerArgs.data[param][0] = ''

        self.writeConf(
            'inputs',
            self.unix_path,
            {
                'interval': self.callerArgs.data['interval'],
                'disabled': ['0']
            }
        )

        del(self.callerArgs.data['interval'])
        self.writeConf('onelogin', 'onelogin_api', self.callerArgs.data)

    # Keys list from setup screen
    @property
    def parameters(self):
        return ['host', 'client_id', 'start_userdate', 'interval']

    # Using inside inputs.conf file to support reading interval
    # in unix based system
    @property
    def unix_path(self):
        return 'script://$SPLUNK_HOME/' \
               'etc/apps/splunk_ta_onelogin/bin/onelogin_events.py'

# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
