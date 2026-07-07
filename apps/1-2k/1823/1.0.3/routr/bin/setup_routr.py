__author__ = 'Levonne Key <levonnekey@gmail.com>'
__license__ = 'Apache License, Version 2.0'

# Reference: http://docs.splunk.com/Documentation/Splunk/latest/AdvancedDev/SetupExampleCustom

import base64
import logging
import os
import shutil
import time

import splunk.admin

TOKEN_DELIMITER = '###'
logger = logging.getLogger(__name__)

class SetupRoutr(splunk.admin.MConfigHandler):
    def setup(self):
        if self.requestedAction == splunk.admin.ACTION_EDIT:
            for arg in [
                    'twitter_consumer_key', 'twitter_consumer_secret',
                    'twitter_access_token', 'twitter_access_token_secret',
                    'tumblr_blogname', 'tumblr_consumer_key',
                    'tumblr_consumer_secret', 'tumblr_access_token',
                    'tumblr_access_token_secret']:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        '''
        Read the initial values of the parameters from the custom file
        routrcreds.conf, and write them to the setup screen. 
        '''
        confDict = self.readConf('routrcreds')
        if confDict:
            for stanza, settings in confDict.items():
                compiled_creds = None
                if stanza == 'twittercreds':
                    compiled_creds = [
                        ['twitter_consumer_key', ''],
                        ['twitter_consumer_secret', ''],
                        ['twitter_access_token', ''],
                        ['twitter_access_token_secret', '']]
                elif stanza == 'tumblrcreds':
                    compiled_creds = [
                        ['tumblr_blogname', ''],
                        ['tumblr_consumer_key', ''],
                        ['tumblr_consumer_secret', ''],
                        ['tumblr_access_token', ''],
                        ['tumblr_access_token_secret', '']]

                decoded_creds = base64.urlsafe_b64decode(settings['hashed_creds'])
                decoded_creds = decoded_creds.split(TOKEN_DELIMITER)
                for _index in range(0, len(decoded_creds)):
                    compiled_creds[_index][1] = decoded_creds[_index]

                '''
                Dump all the values into the "socialmediacreds" entity in setup.xml
                The values are placed correctly based on the field names of the 
                textfields in setup.xml
                For example, in the Twitter configuration section, the saved string
                of "Twitter consumer key" will be populated in the textfield with 
                field name "twitter_consumer_key"
                '''
                for item in compiled_creds:
                    confInfo['socialmediacreds'].append(item[0], item[1])

    def handleEdit(self, confInfo):
        '''
        After user clicks Save on setup screen, take updated parameters,
        normalize them, and save them into routrcreds.conf
        We check if each of the input is empty. Set the value to empty
        string if there is no input provided. Then break the loop and 
        don't save the changes or updates
        '''
        save_twtr_creds = True
        twitter_dict_keys = [
            'twitter_consumer_key', 'twitter_consumer_secret', 
            'twitter_access_token', 'twitter_access_token_secret']
        twitter_user_creds = []
        for twtr_dict_key in twitter_dict_keys:
            if twtr_dict_key in self.callerArgs.data:
                if self.callerArgs.data[twtr_dict_key][0] in [None, '']:
                    self.callerArgs.data[twtr_dict_key][0] = ''
                    save_twtr_creds = False
                    break
                twitter_user_creds.append(
                    self.callerArgs.data[twtr_dict_key][0])
        if save_twtr_creds:
            twitter_user_creds = TOKEN_DELIMITER.join(twitter_user_creds)
            self.writeConf('routrcreds', 'twittercreds',
                           {'hashed_creds': base64.urlsafe_b64encode(twitter_user_creds)})
            self.install_alert_script(
                os.environ.get('SPLUNK_HOME'), 'tweetalert.py')

        save_tumblr_creds = True
        tumblr_dict_keys = [
            'tumblr_blogname', 'tumblr_consumer_key',
            'tumblr_consumer_secret', 'tumblr_access_token',
            'tumblr_access_token_secret']
        tumblr_user_creds = []
        for tumblr_dict_key in tumblr_dict_keys:
            if tumblr_dict_key in self.callerArgs.data:
                if self.callerArgs.data[tumblr_dict_key][0] in [None, '']:
                    self.callerArgs.data[tumblr_dict_key][0] = ''
                    save_tumblr_creds = False
                    break
                tumblr_user_creds.append(
                    self.callerArgs.data[tumblr_dict_key][0])
        if save_tumblr_creds:
            tumblr_user_creds = TOKEN_DELIMITER.join(tumblr_user_creds)
            self.writeConf('routrcreds', 'tumblrcreds',
                           {'hashed_creds': base64.urlsafe_b64encode(tumblr_user_creds)})
            self.install_alert_script(
                os.environ.get('SPLUNK_HOME'), 'tumblralert.py')

    def install_alert_script(self, splunk_home_dir, script_name):
        '''
        Move alert script into $SPLUNK_HOME/bin/scripts directory
        '''
        tweetalert_path = os.path.join(
            splunk_home_dir, 'etc', 'apps', 'routr', script_name)
        splunk_bin_scripts_dir = os.path.join(
            splunk_home_dir, 'bin', 'scripts')
        shutil.copy(tweetalert_path, splunk_bin_scripts_dir)

if __name__ == '__main__':
    splunk.admin.init(SetupRoutr, splunk.admin.CONTEXT_NONE)
