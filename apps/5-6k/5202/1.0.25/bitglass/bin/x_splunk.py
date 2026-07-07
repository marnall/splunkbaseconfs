#!/usr/bin/python
# -*- coding: utf-8 -*-
# -----------------------------------------
# Splunk integration for Bitglass
# -----------------------------------------

import sys
import logging
from datetime import datetime, time

try:
    import splunk.admin as admin
    import splunk.entity as entity
    from splunk.clilib import cli_common as cli
    undersplunk = True
except ImportError:
    undersplunk = False

from app.consts import GC_LOGTYPE_CLOUDAUDIT, \
                       GC_LOGTYPE_ACCESS, \
                       GC_LOGTYPE_ADMIN, \
                       GC_LOGTYPE_CLOUDSUMMARY, \
                       GC_LOGTYPE_SWGWEB, \
                       GC_LOGTYPE_SWGWEBDLP, \
                       GC_LOGTYPE_HEALTHPROXY, \
                       GC_LOGTYPE_HEALTHAPI, \
                       GC_LOGTYPE_HEALTHSYSTEM

logger = logging.getLogger('com.bitglass.lss')


SPLUNK_APP_NAME = 'bitglass'


# ================================================================
# setup.xml UI support
# ----------------------------------------------------------------

fields = ['auth_token',
          'username',
          'password',
          'log_types',
          'access',
          'admin',
          'cloud_audit',
          'cloud_summary',
          'log_interval',
          'api_url',
          'proxies'
          ]


old_setup = False
if undersplunk and old_setup:
    class ConfigApp(admin.MConfigHandler):
        def setup(self):
            if self.requestedAction == admin.ACTION_EDIT:
                for myarg in fields:
                    self.supportedArgs.addOptArg(myarg)

        def handleList(self, confInfo):
            confDict = self.readConf("appsetup")
            if confDict is not None:
                for stanza, settings in confDict.items():
                    for key, val in settings.items():
                        if key in fields and val in [None, '']:
                            val = ''
                        confInfo[stanza].append(key, val)

        def handleEdit(self, confInfo):
            name = self.callerArgs.id   # noqa
            args = self.callerArgs      # noqa
            self.writeConf('appsetup', 'app_config', self.callerArgs.data)

    admin.init(ConfigApp, admin.CONTEXT_NONE)


# ================================================================
# Data script support
# ----------------------------------------------------------------

def fixBrokenFields(d):
    # patterns, multifield but components contain comma's
    # put in an attempt to separate into multi-value fields
    if 'patterns' not in d or d['patterns'] == '':
        return(d)
    # HACK
    s = ''
    bReplace = True
    for i, c in enumerate(d['patterns']):
        if c == ',' and bReplace:
            s += ';'
        else:
            s += c
        if c == '(':
            bReplace = False
        elif c == ')':
            bReplace = True
    d['patterns'] = s
    return(d)


def splunkFieldName(key):
    # a-z, A-Z, _ -
    key = ''.join(c for c in key if ord(c) in range(97, 123) or
                   ord(c) in range(65, 91) or ord(c) in (45, 95))
    # strip leading underbars
    key = key.lstrip('_')
    return(key)


def TranslateLogMessage(d):
    """
    Should be all unicode strings in d. Potential time stamp: _time
    Cleans keys according to Splunk fieldname syntax.
    Returns unicode string in kv-format

    TODO Add more test cases to cover all branches
    logeventdaemon -u jack@bitglass-tme.com -k Pa$$word -r :5514
    echo '<14>Jun 10 20:15:35 bitglass :{"pagetitle": "", "emailsubject": "", "action": "Expire Session", "logtype": "access", "emailbcc": "", "filename": "", "application": "Bitglass", "dlppattern": "", "location": "Almaty||Almaty||ALA||KZ", "email": "jack@bitglass-tme.com", "details": "Session Expired", "emailcc": "", "time": "02 Jul 2020 18:20:14", "emailfrom": "", "user": "Jack Jack", "syslogheader": "<110>1 2020-07-02T18:20:14.490000Z api.bitglass.com NILVALUE NILVALUE access", "device": "Ubuntu", "transactionid": "99d74ff0002be948e2b456f5e8417abf9a2a0c8b [02 Jul 2020 18:20:14]", "ipaddress": "95.59.177.29", "customer": "Bitglass", "url": "/accounts/login/", "request": "", "_time": "07/02/2020 18:20:14", "activity": "Login", "emailsenttime": "", "useragent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:77.0) Gecko/20100101 Firefox/77.0", "emailto": ""}' > /dev/udp/0.0.0.0/5514
    """

    strFormat = ''

    fixBrokenFields(d)
    for k, v in d.items():
        # remaining fields
        # Remove empty fields
        if v is None or v == '':
            # Allow empty fields afterall
            # continue
            v = '\"\"'
        sv = '{0}'.format(v)
        # We rely on splunks default KV_MODE detection, based on key=value,
        # so need to take pre-caution for values containing = and/or ,
        if ',' in sv or '=' in sv and sv[0] != '\"':
            # Surround value by " if required, and remove any newlines -
            # questionable practice....
            sv = '\"{0}\"'.format(sv)
        # Delete newlines from values - questionable practice really - we
        # should not tamper with any content....
        sv = sv.replace('\n', '')
        strFormat += ',{0}={1}'.format(splunkFieldName(k), sv)
    strFormat += ',\n'

    # Skip leading comma
    return strFormat[1:]


def LoadCredentials(conf, appName=SPLUNK_APP_NAME):
    """
    Access the credentials in /servicesNS/nobody/<YourApp>/storage/passwords
    """

    # Try getting the session key
    if undersplunk and 'key' not in conf._session:
        sessionKey = sys.stdin.readline().strip()
        if sessionKey == '':
            logger.warning('Splunk app "%s": No session key found' % appName)
            return False
        conf._session['key'] = sessionKey
    try:
        # List all credentials
        entities = entity.getEntities(['admin', 'passwords'], namespace=appName,
                                      owner='nobody', sessionKey=conf._session['key'])
    except NameError as e:
        # Not under Splunk?
        logger.warning('Splunk app "%s": No entity: %s' % (appName, e))
        logger.error(
            'The Splunk SDK Python modules (like entity.py in the above message) must be present in the environment. '
            'They are present in the default Splunk environment. If they are missing, like in this case, this has been '
            'the result of either modifying the Splunk environment or running the code outside of the Splunk '
            'environment entirely. For example, the latter would be the case if one tried to run the app code directly '
            'from an SSH console and thus bypassing the invocation of the app by the Splunk system.'
        )
        return False
    except Exception as e:
        raise Exception('Splunk app "%s": Error while getting credentials: %s' % (appName, e))
    if len(entities) == 0:
        logger.warning('Splunk app "%s": No credential entities found' % appName)
        return False

    # Return LAST set of credentials
    # BANDIT    Missing password, not 'hardcoded password'. Empty token is never valid
    token = ''  # nosec
    passw = ''
    proxies = ''
    try:
        for i, c in entities.items():
            user = c['username']
            if user == 'oauth2_token':
                token = c['clear_password']
            elif user == 'proxies':
                proxies = c['clear_password']
            else:
                conf._username = user
                passw = c['clear_password']
    except BaseException as e:
        logger.warning('Splunk app "%s": Error while getting credentials: %s' % (appName, e))
        return False

    if passw not in ['', '__notset__']:
        conf._password.pswd = passw
    if token not in ['', '__notset__']:
        conf._auth_token.pswd = token
    if proxies not in ['', '__notset__']:
        # Parse the wholly encrypted proxies multistring, without separating the passwords
        try:
            conf.proxies = conf._getMergedProxies(proxies)
        except BaseException as e:
            logger.warning('Splunk app "%s": Bad proxy expression "%s" ignored: %s' % (appName, proxies, e))
    return True


def getDatetimeFence(fence):
    return time.min if not fence else datetime.strptime(fence, '%Y-%m-%dT%H:%M:%S.%fZ')


def LoadConfiguration(conf, appName=SPLUNK_APP_NAME):
    """
    Use Splunk api to override forward config params
    """

    # Try getting creds first
    try:
        if not LoadCredentials(conf, appName):
            # TODO Store password and token properly encrypted
            # return False

            # Still OK if will get a valid token below (as long as it's loaded outside of LoadCredentials)
            pass
    except Exception as e:
        logger.error('Unexpected error getting credentials: %s' % e)
        return False

    try:
        cfg = cli.getConfStanza('appsetup', 'app_config')

        # TODO Support everywhere or remove from the UI?
        # version = cfg.get('version')

        conf.log_types = []

        # TODO Handle missing params properly with default values
        if int(cfg.get('access')):
            conf.log_types.append(GC_LOGTYPE_ACCESS)
        if int(cfg.get('admin')):
            conf.log_types.append(GC_LOGTYPE_ADMIN)
        if int(cfg.get('cloud_audit')):
            conf.log_types.append(GC_LOGTYPE_CLOUDAUDIT)
        if int(cfg.get('cloud_summary')):
            conf.log_types.append(GC_LOGTYPE_CLOUDSUMMARY)
        if int(cfg.get('swgweb')):
            conf.log_types.append(GC_LOGTYPE_SWGWEB)
        if int(cfg.get('swgwebdlp')):
            conf.log_types.append(GC_LOGTYPE_SWGWEBDLP)

        if conf._isEnabled('health'):
            if int(cfg.get('healthproxy')):
                conf.log_types.append(GC_LOGTYPE_HEALTHPROXY)
            if int(cfg.get('healthapi')):
                conf.log_types.append(GC_LOGTYPE_HEALTHAPI)
            if int(cfg.get('healthsystem')):
                conf.log_types.append(GC_LOGTYPE_HEALTHSYSTEM)

        conf.log_types.sort()

        conf.api_url = cfg.get('api_url')

        # Get the fence which is in the ISO date format like created in js code 'new Date().toJSON()'
        reset_fence = getDatetimeFence(cfg.get('reset_fence'))
        if reset_fence > getDatetimeFence(conf.reset_fence):
            # Fresh reset request
            conf._reset_time = cfg.get('reset_time')

        # Use default 'Bitglass' to avoid adding it to the form
        # conf.customer = cfg.get('customer')
    except Exception as e:
        logger.error('Splunk app "%s" error while getting configuration params: %s' % (appName, e))
        return False

    # Alarm right here if niether creds nor token available
    # BANDIT    Missing password, not 'hardcoded password'. Empty token is never valid
    if ((conf._auth_token is None or conf._auth_token == '') and    # nosec
        (conf._username is None or conf._username == '' or
         conf._password is None or conf._password == '')):          # nosec
        logger.error('Splunk app "%s": No valid authentication options available, please run the setup page' % appName)
        return False

    logger.info('x_splunk.LoadConfiguration SUCCESS')
    logger.debug(conf.__dict__)
    return True
