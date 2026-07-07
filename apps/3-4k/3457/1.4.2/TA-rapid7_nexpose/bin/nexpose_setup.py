from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import int
from future import standard_library
standard_library.install_aliases()
import splunk
import splunk.admin as admin
import splunk.entity as entity
import os
from api.utils import Utils
import requests


APPNAME = 'TA-rapid7_nexpose'

# Get Splunk home
SPLUNK_HOME = os.environ['SPLUNK_HOME']

# Setup Splunk logger
logger = Utils.setup_logging()

logger.info('Executing nexpose_setup.py')

"""
Copyright (C) 2005 - 2010 Splunk Inc. All Rights Reserved.
Description:  This skeleton python script handles the parameters in the configuration page.

      handleList method: lists configurable parameters in the configuration page
      corresponds to handleractions = list in restmap.conf

      handleEdit method: controls the parameters and saves the values 
      corresponds to handleractions = edit in restmap.conf

"""


class ConfigApp(admin.MConfigHandler):
    """
    Set up supported arguments
    """
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['username', 'password', 'port', 'hostname', 'new_scans_only', 'import_solution']:
                self.supportedArgs.addOptArg(arg)

    """
    Read the initial values of the parameters from the custom file
      nexpose_details.conf, and write them to the setup screen. 

    If the app has never been set up,
      uses .../<appname>/default/nexpose_details.conf. 

    If app has been set up, looks at 
      .../local/nexpose_details.conf first, then looks at 
      .../default/nexpose_details.conf only if there is no value for a field in
      .../local/nexpose_details.conf

    For boolean fields, may need to switch the true/false setting.

    For text fields, if the conf file says None, set to the empty string.
    """

    def handleList(self, confInfo):
        logger.info('Listing the fields for the set up screen...')

        confDict = self.readConf("nexpose_details")
        if None == confDict:
            return

        for stanza, settings in confDict.items():
            for key, val in settings.items():
                if key in ['enableCIM']:
                    val = self.convert_int(val)
                if key in ['port'] and val in [None, '']:
                    val = ''
                if key in ['hostname'] and val in [None, '']:
                    val = ''
                if key in ['enableNexpose']:
                    val = self.convert_int(val)
                if key in ['new_scans_only']:
                    val = self.convert_int(val)
                if key in ['import_solution']:
                    val = self.convert_int(val)
                if key in ['username'] and val in [None, '']:
                    val = ''
                if key in ['password']:
                    val = ''

                confInfo[stanza].append(key, val)

    def convert_int(self, val):
        if val == "" or val is None or int(val) != 1:
            return '0'
        return '1'

    def bool_arg(self, args, name, confDict):
        if(name in args):
            if args.data[name][0] in ['True', '1', True]:
                args.data[name][0] = '1'
            else:
                args.data[name][0] = '0'
        else:
            logger.info("No config data for field '%s' passed to setup script!" % name)
            if None != confDict:
                args[name] = confDict.get(name)

    def string_arg(self, args, name, confDict):
        if(name in args):
            if args.data[name][0] in [None, '']:
                args.data[name][0] = ''
        else:
            logger.info("No config data for field '%s' passed to setup script!" % name)
            if None != confDict:
                args[name] = confDict.get(name)

    def password_arg(self, args):
        if args.data['password'][0] in [None, '']:
            logger.info('Password invalid, not saving.')    
            return

        password = args.data['password']
        if password in [None, ''] or password == len(password) * '*':
            return

        # Get Session key to enable talking to the REST API    
        session_key = self.getSessionKey()
        server_uri = splunk.getLocalServerInfo()    
        credential_name = 'nexpose_password'

        response = requests.post(
           url= '{}/servicesNS/nobody/{}/storage/passwords/%3A{}%3A?output_mode=json'.format(server_uri, APPNAME, credential_name),
           data= { 'password': password },
           headers={'Authorization': 'Splunk ' + session_key},
           verify=False)

        if response.status_code != 200:
            logger.error('Error saving password: ' + repr(response))
            raise Exception('Error saving password: ' + repr(response))

        logger.info('Password retrieved.')    

    def handleEdit(self, confInfo):
        logger.info('Saving changes made on configuration screen...')

        name = self.callerArgs.id
        args = self.callerArgs

        confDict = self.readConf("nexpose_details")
        if None != confDict:
            logger.info("Sucessfully retrieved stored config for Nexpose.")
        else:
            logger.error("Failed to retrieved stored config for Nexpose.")

        self.bool_arg(args, 'new_scans_only', confDict)
        self.string_arg(args, 'port', confDict)
        self.string_arg(args, 'hostname', confDict)
        self.string_arg(args, 'username', confDict)

        self.password_arg(args)

        # Remove Username and Password from args passed to custom endpoint (as these are stored at /storage/passwords/).
        # Keep arbitrary values stored in this endpoint for form load. 
        dictWithoutCredentials = args.data
        dictWithoutCredentials['password'] =  'admin'

        # Save the rest of the details - overwites any exisitng details.
        self.writeConf('nexpose_details', 'setupentity', dictWithoutCredentials)


# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
