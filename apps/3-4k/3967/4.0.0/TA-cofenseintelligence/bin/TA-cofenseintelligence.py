"""
Copyright 2013-2016 Cofense, Inc.  All rights reserved.

This software is provided by Cofense, Inc. ("Cofense") on
an "as is" basis and any express or implied warranties, including but
not limited to the implied warranties of merchantability and fitness
for a particular purpose, are disclaimed in all aspects.  In no event
will Cofense be liable for any direct, indirect, special, incidental
or consequential damages relating to the use of this software, even if
advised of the possibility of such damage.

TA-CofenseIntelligence (for python 2.x)
Author: Josh Larkins
Support: support@cofense.com
ChangesetID:

"""

from configparser import ConfigParser
import os
import platform
import sys
import logging
import traceback

from splunklib.modularinput import *
import splunklib.client as client
import cofense_intelligence_to_splunk

# ENVIRONMENTAL INFORMATION
__author__ = 'Josh Larkins, Robert McMahon'
_MI_APP_NAME = 'TA-cofenseintelligence'
_SPLUNK_HOME = os.getenv('SPLUNK_HOME')
if _SPLUNK_HOME is None:
    _SPLUNK_HOME = os.getenv('SPLUNKHOME')
if _SPLUNK_HOME is None:
    _SPLUNK_HOME = '/opt/splunk'

_OPERATING_SYSTEM = platform.system()
_APP_HOME = _SPLUNK_HOME + '/etc/apps/' + _MI_APP_NAME
_APP_BIN = _APP_HOME + '/bin'

if _OPERATING_SYSTEM.lower() == 'windows':
    _IS_WINDOWS = True
    _APP_HOME.replace('/', '\\')
    _APP_BIN.replace('/', '\\')

# Mask is to mask the API and proxy passwords
MASK = "--------"

# Setup logging
logging.root
logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(formatter)
logging.root.addHandler(handler)

LOGGER = logging.getLogger('cofense')

class Cofense(Script):

    def get_scheme(self):
        """When Splunk starts, it looks for all the modular inputs defined by
        its configuration, and tries to run them with the argument --scheme.
        Splunkd expects the modular inputs to print a description of the
        input in XML on stdout. The modular input framework takes care of all
        the details of formatting XML and printing it. The user need only
        override get_scheme and return a new Scheme object.

        :return: scheme, a Scheme object
        """

        scheme = Scheme('Cofense Intelligence')
        scheme.description = 'Retrieve Cofense Intelligence from Cofense\'s RESTful API.'

        scheme.use_external_validation = True
        scheme.use_single_instance = False

        # Username
        api_username = Argument('user')
        api_username.title = 'API Username'
        api_username.data_type = Argument.data_type_string
        api_username.description = 'Your Cofense API User Name'
        api_username.required_on_create = True
        scheme.add_argument(api_username)

        # Password
        api_password = Argument('pass')
        api_password.title = 'API Password'
        api_password.data_type = Argument.data_type_string
        api_password.description = 'Your Cofense API Password'
        api_password.required_on_create = True
        scheme.add_argument(api_password)

        # When to start
        # TODO: Set start date to default to one month ago
        start_date = Argument('init_date')
        start_date.title = 'Start Date'
        start_date.data_type = Argument.data_type_string
        start_date.description = 'Cofense Intelligence will be retrieved from this date forward. Format according to YYYY-MM-DD.'
        start_date.required_on_create = True
        scheme.add_argument(start_date)

        # Base API url
        # TODO: Default to https://www.threathq.com/apiv1
        base_api_url = Argument('base_url')
        base_api_url.title = 'Base API URL'
        base_api_url.data_type = Argument.data_type_string
        base_api_url.description = 'This should be properly populated by default.'
        base_api_url.required_on_create = True
        scheme.add_argument(base_api_url)


        base_api_url = Argument('max_page_size')
        base_api_url.title = 'Max Page Size'
        base_api_url.data_type = Argument.data_type_string
        base_api_url.description = 'Typically set to 100, but may be reduced at the request of Cofense Support.'
        base_api_url.required_on_create = True
        scheme.add_argument(base_api_url)

        proxy_http = Argument('proxy_http')
        proxy_http.title = 'Proxy HTTP'
        proxy_http.data_type = Argument.data_type_string
        proxy_http.description = 'Enter HTTP proxy URL.'
        proxy_http.required_on_create = True
        scheme.add_argument(proxy_http)

        proxy_https = Argument('proxy_https')
        proxy_https.title = 'Proxy HTTPS'
        proxy_https.data_type = Argument.data_type_string
        proxy_https.description = 'Enter HTTPS proxy URL.'
        proxy_https.required_on_create = True
        scheme.add_argument(proxy_https)
        
        proxy_auth_basic_user = Argument(name = 'proxy_auth_basic_user',
                                        title = 'Proxy User',
                                        data_type = Argument.data_type_string,
                                        description = 'Enter BASIC proxy username')
        scheme.add_argument(proxy_auth_basic_user)

        proxy_auth_basic_pass = Argument(name = 'proxy_auth_basic_pass',
                                        title = 'Proxy Password',
                                        data_type = Argument.data_type_string,
                                        description = 'Enter BASIC proxy password')
        scheme.add_argument(proxy_auth_basic_pass)

        output_json_raw = Argument('output_json_raw')
        output_json_raw.title = 'JSON - raw'
        output_json_raw.data_type = Argument.data_type_boolean
        output_json_raw.description = 'Data output will include complete JSON objects for each campaign produced by Cofense.'
        output_json_raw.required_on_create = False
        scheme.add_argument(output_json_raw)

        output_json_blockset = Argument('output_json_blockset')
        output_json_blockset.title = 'JSON - Block set (recommended)'
        output_json_blockset.data_type = Argument.data_type_boolean
        output_json_blockset.description = 'Data output will include all blockset items in a flat JSON object.'
        output_json_blockset.required_on_create = False
        scheme.add_argument(output_json_blockset)

        output_json_executableset = Argument('output_json_executableset')
        output_json_executableset.title = 'JSON - Executable set (recommended)'
        output_json_executableset.data_type = Argument.data_type_boolean
        output_json_executableset.description = 'Data output will include all executable items in a flat JSON object.'
        output_json_executableset.required_on_create = False
        scheme.add_argument(output_json_executableset)

        output_json_senderemailset = Argument('output_json_senderemailset')
        output_json_senderemailset.title = 'JSON - Sender Email Address set'
        output_json_senderemailset.data_type = Argument.data_type_boolean
        output_json_senderemailset.description = 'Data output will include all sender email addresses in a flat JSON object.'
        output_json_senderemailset.required_on_create = False
        scheme.add_argument(output_json_senderemailset)

        output_json_sendersubjectset = Argument('output_json_sendersubjectset')
        output_json_sendersubjectset.title = 'JSON - Subject Lines set'
        output_json_sendersubjectset.data_type = Argument.data_type_boolean
        output_json_sendersubjectset.description = 'Data output will include all subject lines in a flat JSON object.'
        output_json_sendersubjectset.required_on_create = False
        scheme.add_argument(output_json_sendersubjectset)

        scheme.add_argument(Argument( name = 'output_brand_json_raw',
                                     title = 'JSON - raw user reported intelligence',
                                     data_type = Argument.data_type_boolean,
                                     description = 'Data output will include complete JSON objects for each phishing site recorded by Cofense', required_on_create = True))


        scheme.add_argument(Argument( name = 'output_brand_action_urls',
                                     title = 'JSON - Action URLs',
                                     data_type = Argument.data_type_boolean,
                                     description = 'This is the next URL to be called when the victim submits their information to the phishing site.', required_on_create = True))

        scheme.add_argument(Argument(name = 'output_brand_reported_urls',
                                     title = 'JSON - Reported URLs',
                                     data_type = Argument.data_type_boolean,
                                     description='This is the original URL reported to Cofense. It might be the same as the Phishing URL or it might be a re-director of some type, either a compromised site or a shortened URL like bit.ly or tinyurl.', required_on_create=True))

        scheme.add_argument(Argument(name = 'output_brand_kits',
                                     title = 'JSON - Kits',
                                     data_type = Argument.data_type_boolean,
                                     description='These are the phishing kits retrieved during our processing of a phishing site.', required_on_create=True))
        
        scheme.add_argument(Argument(name = 'output_brand_kit_files',
                                     title = 'JSON - Kit Files',
                                     data_type = Argument.data_type_boolean,
                                     description='These are the files within a phishing kit that contained a drop email address detected by Cofense.', required_on_create=True))

        scheme.add_argument(Argument(name = 'output_brand_kit_file_emails',
                                     title = 'JSON - Kit File Emails',
                                     data_type = Argument.data_type_boolean,
                                     description='These are the email addresses found within a phishing kit detected by Cofense.', required_on_create=True))

        scheme.add_argument(Argument(name = 'output_brand_web_components',
                                     title = 'JSON - Web Components',
                                     data_type = Argument.data_type_boolean,
                                     description='These are the web components used to build a phishing website within a victim\'s browser.', required_on_create=True))

        scheme.add_argument(Argument(name = 'output_brand_phish_url',
                                     title = 'JSON - Phish URL',
                                     data_type = Argument.data_type_boolean,
                                     description='T hese components represent the current location of a phishing page, whether hosted on a compromised website or a domain specifically registered for phishing purposes.', required_on_create=True))
        return scheme

    @staticmethod
    def _encrypt_password(session_key, username, password):
        args = {'token': session_key}
        service = client.connect(**args)
        try:
            for storage_password in service.storage_passwords:
                if storage_password.username == username:
                    service.storage_passwords.delete(username=storage_password.username)
                    break
            service.storage_passwords.create(password, username)
        except Exception as e:
            raise Exception('An error occured updating credentials. Please ensure your user account has admin_all_objects and/or list_storage_passwords capabilities Details: %s' % str(e))

    @staticmethod
    def _mask_password(session_key, username, username_key, password_key, input_name):
        try:
            args = {'token': session_key}
            service = client.connect(**args)
            kind, input_name = input_name.split('://')
            item = service.inputs.__getitem__((input_name, kind))

            kwargs = {
                    username_key: username,
                    password_key: MASK
            }

            item.update(**kwargs).refresh()
        except Exception as e:
            raise Exception('Error updating inputs.conf: %s' % str(e))

    @staticmethod
    def _get_password(session_key, username):
        args = {'token': session_key}
        service = client.connect(**args)

        for storage_password in service.storage_passwords:
            if storage_password.username == username:
                return storage_password.content.clear_password


    def validate_input(self, validation_definition):
        # Validates input.
        LOGGER.info("Calling validate_input")
        if validation_definition.parameters.get('base_url') and not validation_definition.parameters.get('base_url').startswith('https://'):
            raise ValueError('The base url must use https:// for the protocol')

    def stream_events(self, inputs, ew):
        """This function handles all the action: splunk calls this modular input
        without arguments, streams XML describing the inputs to stdin, and waits
        for XML on stdout describing events.

        If you set use_single_instance to True on the scheme in get_scheme, it
        will pass all the instances of this input to a single instance of this
        script.

        :param inputs: an InputDefinition object
        :param ew: an EventWriter object
        """
        try:
            LOGGER.info('Starting')
            self.stream(inputs, ew)
            LOGGER.info('Complete')
        except Exception:
            LOGGER.error('There was an uncaught python exception while running the integration: %s'%traceback.format_exc())    

    def stream(self, inputs, ew):
        for input_name, input_item in inputs.inputs.items():

            checkpoint_dir = inputs.metadata.get('checkpoint_dir')

            session_key = self._input_definition.metadata['session_key']
            
            try:
                if input_item.get('pass') != MASK:
                    Cofense._encrypt_password(session_key=session_key, username=input_item.get('user'), password=input_item.get('pass'))
                    Cofense._mask_password(session_key=session_key, username=input_item.get('user'), username_key='user', password_key='pass', input_name=input_name)

            except Exception as e:
                ew.log('error', 'There was an error when encrypting/masking the Cofense API password: %s' % e)

            # Mask the proxy password.
            try:
                if input_item.get('proxy_auth_basic_pass', 'MASK') != MASK:
                    Cofense._encrypt_password(session_key=session_key, username=input_item.get('proxy_auth_basic_user'), password=input_item.get('proxy_auth_basic_pass'))
                    Cofense._mask_password(session_key=session_key, username=input_item.get('proxy_auth_basic_user'), username_key='proxy_auth_basic_user', password_key='proxy_auth_basic_pass', input_name=input_name)

            except Exception as e:
                ew.log('error', 'There was an error when encrypting/masking the proxy password: %s' % e)

            LOGGER.info('Setting up the config')
            config = ConfigParser()
            def safe_set(section, key, value):
                if value:
                    config.set(section, key, value)
                else:
                    LOGGER.debug("Not Found: section: %s, key: %s, value: %s" % (section, key, value))

            config.add_section('integration')
            safe_set('integration', 'version', '4.0.0')

            LOGGER.info('Setting up the Cofense section')
            config.add_section('cofense')
            safe_set('cofense', 'user', input_item.get('user'))
            safe_set('cofense', 'pass', Cofense._get_password(session_key=session_key, username=input_item.get('user')))
            safe_set('cofense', 'init_date', input_item.get('init_date'))
            safe_set('cofense', 'base_url', input_item.get('base_url'))
            safe_set('cofense', 'max_page_size', input_item.get('max_page_size'))
            safe_set('cofense', 'checkpoint_dir', checkpoint_dir)
            config.set('cofense', 'position', cofense_intelligence_to_splunk.load_checkpoint(checkpoint_dir))

            LOGGER.info('Setting up the proxy section')
            config.add_section('proxy')
            safe_set('proxy', 'http', input_item.get('proxy_http'))
            safe_set('proxy', 'https', input_item.get('proxy_https'))
            safe_set('proxy', 'auth_basic_user', input_item.get('proxy_auth_basic_user'))
            safe_set('proxy', 'auth_basic_pass', Cofense._get_password(session_key=session_key, username=input_item.get('proxy_auth_basic_user')))

            LOGGER.info('Setting up the output section')
            config.add_section('output')
            safe_set('output', 'json_raw', input_item.get('output_json_raw'))
            safe_set('output', 'json_blockset', input_item.get('output_json_blockset'))
            safe_set('output', 'json_executableset', input_item.get('output_json_executableset'))
            safe_set('output', 'json_senderemailset', input_item.get('output_json_senderemailset'))
            safe_set('output', 'json_sendersubjectset', input_item.get('output_json_sendersubjectset'))
            
            safe_set('output', 'brand_json_raw', input_item.get('output_brand_json_raw'))
            safe_set('output', 'brand_action_urls', input_item.get('output_brand_action_urls'))
            safe_set('output', 'brand_reported_urls', input_item.get('output_brand_reported_urls'))
            safe_set('output', 'brand_kits', input_item.get('output_brand_kits'))
            safe_set('output', 'brand_kit_files', input_item.get('output_brand_kit_files'))
            safe_set('output', 'brand_kit_file_emails', input_item.get('output_brand_kit_file_emails'))
            safe_set('output', 'brand_web_components', input_item.get('output_brand_web_components'))
            safe_set('output', 'brand_phish_url', input_item.get('output_brand_phish_url'))

            config.add_section('concurrency')
            safe_set('concurrency', 'use', 'False')

            LOGGER.info('Calling intel_to_splunk')
            cofense_intelligence_to_splunk.main(config=config, input_name=input_name)

            ew.close()

    
if __name__ == "__main__":
    sys.exit(Cofense().run(sys.argv))
