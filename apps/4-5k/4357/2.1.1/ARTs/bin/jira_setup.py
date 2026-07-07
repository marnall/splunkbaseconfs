"""
Copyright (C) 2005 - 2010 Splunk Inc. All Rights Reserved.
Description:  This skeleton python script handles the parameters in the
configuration page.

    handleList method: lists configurable parameters in the configuration page
    corresponds to handleractions = list in restmap.conf

    handleEdit method: controls the parameters and saves the values
    corresponds to handleractions = edit in restmap.conf
"""
import sys
import os.path as op
import splunk.clilib.cli_common as scc
import splunk.admin as admin


from solnlib.splunkenv import get_conf_key_value


from solnlib import log
from solnlib import conf_manager
from solnlib import credentials as cred
import jira_consts as c

_LOGGER = log.Logs().get_logger("setup")


class ConfigApp(admin.MConfigHandler):
    valid_args = (c.enabled_jira, c.jira_server_url, c.jira_username, c.jira_password)

    encrypted = "******"
    dummy = 'user'
    conf_file = c.jira_conf

    def setup(self):
        """
        Set up supported arguments
        """

        if self.requestedAction == admin.ACTION_EDIT:
            for arg in self.valid_args:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        """
        Read the initial values of the parameters from the custom file
        jira_settings.conf, and write them to the setup screen.

        If the app has never been set up, uses default/jira_settings.conf.

        If app has been set up, looks at local/jira_settings.conf first,
        then looks at default/jira_settings.conf only if there is no value for
        a field in local/jira_settings.conf

        For text fields, if the conf file says None, set to the empty string.
        """

        _LOGGER.debug("start list")
        conf_mgr = conf_manager.ConfManager(self.getSessionKey(), self.appName,
                                            realm=get_conf_key_value(
                                                c.jira_conf, c.jira_settings,
                                                c.jira_server_url))
        conf = conf_mgr.get_conf(self.conf_file)
        conf.reload()

        confDict = self.readConf(self.conf_file)

        if confDict is not None:
            self._decrypt_username_password(confDict)
            for stanza, settings in confDict.items():
                for key, val in settings.items():
                    if key in self.valid_args and val is None:
                        val = ""

                    if key is c.jira_password:
                        val = ""

                    confInfo[stanza].append(key, val)

        _LOGGER.debug("end list")

    def handleEdit(self, confInfo):
        """
        After user clicks Save on setup screen, take updated parameters,
        normalize them, and save them somewhere
        """

        _LOGGER.debug("start edit")
        args = self.callerArgs.data
        for arg in self.valid_args:
            if args.get(arg, None) and args[arg][0] is None:
                args[arg][0] = ""

        if c.jira_username in args:
            self._handleUpdatejiraSettings(confInfo, args)

        conf_mgr = conf_manager.ConfManager(self.getSessionKey(), self.appName)
        conf = conf_mgr.get_conf(self.conf_file)
        conf.reload()

        _LOGGER.debug("end edit")

    def _getSettings(self, stanza, args, keys, confInfo):
        settings = {}
        for k in keys:
            if args.get(k):
                settings[k] = args[k][0]
                confInfo[stanza].append(k, args[k][0])
        return settings

    def _handleUpdatejiraSettings(self, confInfo, args):
        keys = self.valid_args
        stanza = c.jira_settings
        settings = self._getSettings(stanza, args, keys, confInfo)
        if bool(int(settings[c.enabled_jira])):
            for key in keys:
                if key != c.enabled_jira and not settings.get(key):
                    msg = "{} is required, but it is not configured.".format(key)
                    _LOGGER.error(msg)
                    raise admin.ArgValidationException(msg)

        jira_username, jira_password, jira_server_url = settings.get(
            c.jira_username), settings.get(c.jira_password), settings.get(c.jira_server_url)

        conf_mgr = conf_manager.ConfManager(self.getSessionKey(), self.appName,
                                            realm=jira_server_url)
    
        cred_mgr = cred.CredentialManager(self.getSessionKey(), self.appName,
                                          realm=jira_server_url)

        if (jira_username and jira_password and jira_username != self.encrypted and
                jira_password != self.encrypted):
            _LOGGER.debug("encrypting")
            jira_userpass_encrpted = cred_mgr.SEP.join((jira_username, jira_password))

            cred_mgr.set_password(self.dummy, jira_userpass_encrpted)
            settings[c.jira_username] = self.encrypted
            settings[c.jira_password] = self.encrypted

        elif jira_username and jira_username != self.encrypted:
            settings[c.jira_username] = self.encrypted

        elif jira_password and jira_password != self.encrypted:
            settings[c.jira_password] = self.encrypted

        if settings:
            self.writeConf(self.conf_file, stanza, settings)


    def _decrypt_username_password(self, confDict):
        stanza = c.jira_settings
        if not confDict.get(stanza):
            return

        account = confDict[stanza]
        encrypted = all(account.get(k) == self.encrypted
                        for k in (self.valid_args[0], self.valid_args[1]))
        if encrypted:
            _LOGGER.debug("decrypting")
            cred_mgr = cred.CredentialManager(self.getSessionKey(), self.appName,
                                              realm=account[c.jira_server_url] or c.jira_server_url)

            password = cred_mgr.get_password(self.dummy)
            if password:
                user_pass = password.split(cred_mgr.SEP)
                account[c.jira_username], account[c.jira_password] = user_pass


admin.init(ConfigApp, admin.CONTEXT_APP_ONLY)

