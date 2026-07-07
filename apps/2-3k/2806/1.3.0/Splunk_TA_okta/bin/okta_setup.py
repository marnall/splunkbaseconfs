import splunk.admin as admin
import splunk.clilib.cli_common as scc
from splunktalib import credentials as cred
from splunktalib.conf_manager import conf_manager as conf
from splunktalib.common import log
from splunktalib.common import util
import logging
import traceback

logger = log.Logs().get_logger('ta_okta', level=logging.INFO)

util.remove_http_proxy_env_vars()

"""
Copyright (C) 2005 - 2015 Splunk Inc. All Rights Reserved.
Description:  This skeleton python script handles the parameters in the configuration page.

      handleList method: lists configurable parameters in the configuration page
      corresponds to handleractions = list in restmap.conf

      handleEdit method: controls the parameters and saves the values
      corresponds to handleractions = edit in restmap.conf
"""

class ConfigApp(admin.MConfigHandler):

    encrypted = "********"

    """
    Set up supported arguments
    """
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['proxy_enabled', 'proxy_type', 'proxy_url',
                        'proxy_port', 'proxy_username', 'proxy_password',
                        'proxy_rdns', 'loglevel', 'custom_cmd_enabled',
                        'okta_server_url', 'okta_server_token']:
                self.supportedArgs.addOptArg(arg)

    """
    Read the initial values of the parameters from the custom file
      okta.conf, and write them to the setup screen.

    If the app has never been set up,
      uses .../<appname>/default/okta.conf.

    If app has been set up, looks at
      .../local/okta.conf first, then looks at
    .../default/okta.conf only if there is no value for a field in
      .../local/okta.conf

    For boolean fields, may need to switch the true/false setting.

    For text fields, if the conf file says None, set to the empty string.

    """

    def handleList(self, confInfo):
        confDict = self.readConf("okta")
        if confDict is not None:
            self._decrypt_username_password(confDict)
            proxy = confDict.get('okta_proxy')
            assert proxy is not None, "OKTA proxy file doesn't contain 'proxy stanza' inside"

            for key, val in proxy.items():
                confInfo['okta_proxy'].append(key, val)

            confInfo["okta_loglevel"].append('loglevel',
                confDict.get('okta_loglevel', {}).get('loglevel', "INFO"))

            okta_server = confDict.get('okta_server')
            assert okta_server is not None, "OKTA conf file doesn't contain 'okta_server stanza' inside"

            for key, val in okta_server.items():
                confInfo['okta_server'].append(key, val)

    """
    After user clicks Save on setup screen, take updated parameters,
    normalize them, and save them somewhere
    """
    def handleEdit(self, confInfo):
        args = self.callerArgs.data
        for key, val in args.items():
            if val[0] is None:
                val[0] = ''
        conf_mgr = conf.ConfManager(splunkd_uri=scc.getMgmtUri(), session_key=self.getSessionKey(),
                                    app_name=self.appName, owner='-')

        success = False
        if self.callerArgs.id == 'okta_loglevel':
            loglevel_stanza = {}
            loglevel = args['loglevel'][0]
            loglevel_stanza['loglevel'] = loglevel
            success = conf_mgr.update_stanza('okta','okta_loglevel',loglevel_stanza)
            log.Logs().set_level(loglevel)

        elif self.callerArgs.id == 'okta_proxy':
            proxy_stanza = {}
            proxy_enabled = args['proxy_enabled'][0]
            proxy_stanza['proxy_enabled'] = proxy_enabled
            if proxy_enabled.lower().strip() in ("1", "true", "yes", "t", "y"):
                proxy_port = args['proxy_port'][0].strip()
                proxy_url = args['proxy_url'][0].strip()
                proxy_type = args['proxy_type'][0]
                proxy_rdns = args['proxy_rdns'][0]
                # Validate args
                if proxy_url != '' and proxy_port == '':
                    raise admin.ArgValidationException("Port should not be blank")

                if proxy_url == '' and proxy_port != '':
                    raise admin.ArgValidationException("URL should not be blank")

                if proxy_port != '' and not proxy_port.isdigit():
                    raise admin.ArgValidationException("Port should be digit")

                # Proxy is enabled, but proxy url or port is empty
                if proxy_url == '' or proxy_port == '':
                    raise admin.ArgValidationException("URL and port should not be blank")

                # Password is filled but username is empty
                if args['proxy_password'][0] != '' and args['proxy_username'][0] == '':
                    raise admin.ArgValidationException("Username should not be blank")

                if proxy_type not in ('http', 'http_no_tunnel', 'socks4', 'socks5'):
                    raise admin.ArgValidationException("Unsupported proxy type")

                confDict = self.readConf("okta")
                self._decrypt_username_password(confDict)
                proxy = confDict['okta_proxy']

                proxy_stanza['proxy_url'] = proxy_url
                proxy_stanza['proxy_port'] = proxy_port
                proxy_stanza['proxy_type'] = proxy_type
                proxy_stanza['proxy_rdns'] = proxy_rdns

                cred_mgr = cred.CredentialManager(session_key=self.getSessionKey(),
                            app=self.appName, splunkd_uri=scc.getMgmtUri())
                proxy_username = args['proxy_username'][0].strip()
                proxy_password = args['proxy_password'][0].strip()
                if not proxy_username:
                    try:
                        result = cred_mgr.delete('__Splunk_TA_okta_proxy__')
                        logger.info("Update result:"+str(result))
                    except Exception:
                        logger.warn("ERROR in deleting cred stanza")
                        logger.warn(traceback.format_exc())
                elif proxy_password != '' or \
                        proxy['proxy_username'] != proxy_username:
                    stanza = {}
                    proxy = {'proxy_username': proxy_username,
                                'proxy_password': proxy_password}
                    stanza['__Splunk_TA_okta_proxy__'] = proxy

                    try:
                        result = cred_mgr.update(stanza)
                        logger.info("Update result:"+str(result))
                    except Exception:
                        logger.error("ERROR in creating cred stanza")
                        logger.error(traceback.format_exc())
                        raise admin.HandlerSetupException(
                                "fail to encrypt proxy username and password.")

                if proxy_password != '' or proxy_username != '':
                    proxy_stanza['proxy_username'] = self.encrypted
                    proxy_stanza['proxy_password'] = self.encrypted
                else:
                    proxy_stanza['proxy_username'] = ''
                    proxy_stanza['proxy_password'] = ''
            success = conf_mgr.update_stanza('okta', 'okta_proxy', proxy_stanza)

        elif self.callerArgs.id == 'okta_server':
            okta_server_stanza = {}
            custom_cmd_enabled = args['custom_cmd_enabled'][0]
            okta_server_stanza['custom_cmd_enabled'] = custom_cmd_enabled
            if custom_cmd_enabled.lower().strip() in ("1", "true", "yes", "t", "y"):
                okta_server_url = args['okta_server_url'][0].strip()
                okta_server_token = args['okta_server_token'][0].strip()
                if okta_server_url != '' and okta_server_token == '':
                    raise admin.ArgValidationException("token should not be blank")
                if okta_server_token != '' and okta_server_url == '':
                    raise admin.ArgValidationException("server url should not be blank")
                confDict = self.readConf('okta')
                okta_server = confDict['okta_server']
                cred_mgr = cred.CredentialManager(session_key=self.getSessionKey(),
                                app=self.appName, splunkd_uri=scc.getMgmtUri())
                if not okta_server_url:
                    try:
                        result = cred_mgr.delete('__Splunk_TA_okta_server__')
                        logger.info("Update result:" + str(result))
                    except Exception:
                        logger.warn("ERROR in deleting cred stanza")
                        logger.warn(traceback.format_exc())
                elif (okta_server_token != '' and okta_server_token!= self.encrypted) \
                        or okta_server['okta_server_url'] != okta_server_url:
                    if okta_server_token == self.encrypted:
                        okta_server_token = okta_server['okta_server_token']
                    stanza = {}
                    okta_server_info = {'okta_server_url': okta_server_url,
                                'okta_server_token': okta_server_token}
                    stanza['__Splunk_TA_okta_server__'] = okta_server_info

                    try:
                        result = cred_mgr.update(stanza)
                        logger.info("Update result:" + str(result))
                    except Exception:
                        logger.error("ERROR in creating cred stanza")
                        logger.error(traceback.format_exc())
                        raise admin.HandlerSetupException(
                                "fail to encrypt okta server url and token.")
                if okta_server_url != '' or okta_server_token != '':
                    okta_server_stanza['okta_server_url'] = okta_server_url
                    okta_server_stanza['okta_server_token'] = self.encrypted
                else:
                    okta_server_stanza['okta_server_url'] = ''
                    okta_server_stanza['okta_server_token'] = ''
            success = conf_mgr.update_stanza('okta','okta_server',okta_server_stanza)

        if not success:
            logger.error("ERROR in writing okta conf file.")
            raise admin.HandlerSetupException("fail to store data into okta.conf file.")

    def _decrypt_username_password(self, conf_dict):
        candidates = [('okta_proxy', '__Splunk_TA_okta_proxy__',
                       ['proxy_username', 'proxy_password'],
                       ['proxy_password']),
                      ('okta_server', '__Splunk_TA_okta_server__',
                       ['okta_server_url', 'okta_server_token'],
                       ['okta_server_token'])]
        try:
            cred_mgr = cred.CredentialManager(session_key=self.getSessionKey(),
                                              app=self.appName,
                                              splunkd_uri=scc.getMgmtUri())
            for stz, pwd_st, encrypts, clears in candidates:
                if conf_dict.get(stz) is None:
                    continue
                stanza = conf_dict[stz]
                if all(stanza.get(k, '') == self.encrypted for k in encrypts):
                    clear_pwd = cred_mgr.get_clear_password(pwd_st)
                    if not clear_pwd:
                        continue
                    for k in encrypts:
                        stanza[k] = '' if k in clears else clear_pwd[pwd_st][k]
        except Exception:
            logger.error("decryption error. fail to decrypt encrypted"
                         " username/pwd. %s", traceback.format_exc())

# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
