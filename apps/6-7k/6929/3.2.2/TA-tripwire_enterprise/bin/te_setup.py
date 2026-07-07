import errno
import os
import os.path
import re
import shutil
import urllib
from sys import platform as _platform

import splunk_helper
import splunk.admin as admin
import splunk.entity as en
from tripwire import pyDes_decrypt


class ConfigApp(admin.MConfigHandler):
    appName = 'TA-tripwire_enterprise'
    config_file = "te_setup"
    config_te_stanza = "te_parameters"

    def setup(self):

        # The triggers section in app.conf reloads the /te_endpoint and executes the code here.
        # The trigger should execute during the installation or update of the addon.

        # determine if the app is using the old encrypted TE password. If yes, switch to using
        # the Splunk password storage
        conf_dict = self.readConf(self.config_file)
        if conf_dict:
            te_parameters = conf_dict.get(self.config_te_stanza)
            te_pass = te_parameters.get("te_pass", None)
            if te_pass:  # old password is stored in .conf file
                te_username = te_parameters.get("te_username")
                te_password = pyDes_decrypt(te_pass)
                # Save old password in Splunk password storage
                pm = splunk_helper.PasswordManager(auth_token=self.getSessionKey())
                pm.set_password(username=te_username, password=te_password)
                # Remove old password from .conf
                te_parameters["te_pass"] = ""
                self.writeConf(self.config_file, self.config_te_stanza, te_parameters)
 
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in [
                'data_location',
                'use_forwarder_bool',
                'workflow_host',
                'te_sslverify',
                'te_ssl_cert_path',
                'listening_port',
                'te_username',
                'te_pass',
                'windows_splunk_dir',
                'scm_int',
                'scm_unit',
                'scm_int_saved',
                'fim_int',
                'fim_unit',
                'fim_int_saved',
                'scm_hour',
                'scm_day',
                'fim_hour',
                'fim_day',
                'fim_timeout',
                'hist_days',
                'showContentDiff',
                'compare_prev_version',
                'fim_use_rest',
                'scm_use_rest',
                'fim_rest_threads',
                'scm_rest_threads',
                'scm_policy_names',
                'scm_daily_reindex',
                'scm_exclude_waivered',
                'scm_detailed_attributes',
                'scm_reindex_policy_names',
                'ecr_int',
                'ecr_unit',
                'ecr_int_saved',
                'ecr_hour',
                'ecr_day',
                'ecr_rpt_names',
                'ecr_parse_sql',
                'tripwire_debug_logging',
                'tripwire_rest_logging',
            ]:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        confDict = self.readConf(self.config_file)
        if confDict is not None:
            # NOTE: Wrapping items() inside list() is unnecessary. Doing it to silence Splunk warnings
            for stanza, settings in list(confDict.items()):
                for key, val in list(settings.items()):
                    if (
                        key
                        in [
                            'data_location',
                            'workflow_host',
                            'listening_port',
                            'te_username',
                            'windows_splunk_dir',
                        ]
                        and val in [None, '']
                    ):
                        val = ''
                    if key in [
                        'use_forwarder_bool',
                        'scm_hour',
                        'scm_day',
                        'fim_hour',
                        'fim_day',
                        'ecr_hour',
                        'ecr_day',
                        'first_run',
                        'showContentDiff',
                        'compare_prev_version',
                    ]:
                        if int(val) == 1:
                            val = '1'
                        else:
                            val = '0'
                    if key in ['scm_int', 'fim_int', 'ecr_int']:
                        val = ''
                    confInfo[stanza].append(key, val)

    def make_sure_path_exists(self, path):
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

    def createTAApp(self):
        targetFolder = 'TA-tripwire_enterprise_FWD'
        if _platform == 'win32':
            confDict = self.readConf(self.config_file)
            slash = '\\'
            # NOTE: Wrapping items() inside list() is unnecessary. Doing it to silence Splunk warnings
            for stanza, settings in list(confDict.items()):
                if stanza == self.config_te_stanza:
                    appsDir = settings['windows_splunk_dir'] + '\\Splunk\\etc\\apps'
                    secDir = settings['windows_splunk_dir'] + '\\Splunk\\etc\\auth'
                    dir = appsDir + slash + self.appName + '\\appserver\\addons'
        else:
            slash = '/'
            homeDir = os.environ.get('SPLUNK_HOME')
            appsDir = homeDir + '/etc/apps'
            secDir = homeDir + '/etc/auth'
            dir = appsDir + slash + self.appName + '/appserver/addons'

        self.make_sure_path_exists(dir + slash + targetFolder)
        for source in ['local', 'default']:
            self.make_sure_path_exists(dir + slash + targetFolder + slash + source)
            for sourceFile in [
                'app.conf',
                'inputs.conf',
                'te_setup.conf',
                'passwords.conf',
                'indexes.conf',
                'props.conf',
                'transforms.conf',
            ]:
                src = (
                    appsDir + slash + self.appName + slash + source + slash + sourceFile
                )
                tgt = dir + slash + targetFolder + slash + source + slash + sourceFile
                if os.path.isfile(src):
                    shutil.copyfile(src, tgt)

        source = 'bin'
        self.make_sure_path_exists(dir + slash + targetFolder + slash + source)
        for sourceFile in [
            'pyDes.py',
            "splunk_helper.py",
            'te_assets.py',
            'tripwire.py',
            'tripwire_ecr.py',
            'tripwire_fim.py',
            'tripwire_logging.py',
            'tripwire_scm.py',
            'tripwire_multiprocess.py',
            'tripwire_rest_api.py',
        ]:
            src = appsDir + slash + self.appName + slash + source + slash + sourceFile
            tgt = dir + slash + targetFolder + slash + source + slash + sourceFile
            if os.path.isfile(src):
                shutil.copyfile(src, tgt)

        secret = 'auth'
        self.make_sure_path_exists(dir + slash + targetFolder + slash + secret)
        for secretShare in [
            'splunk.secret',
        ]:
            src = secDir + slash + secretShare
            tgt = dir + slash + targetFolder + slash + secret + slash + secretShare
            if os.path.isfile(src):
                shutil.copyfile(src, tgt)

    def createSAApp(self):
        targetFolder = 'SA-tripwire_enterprise_IDX'
        if _platform == 'win32':
            confDict = self.readConf(self.config_file)
            slash = '\\'
            # NOTE: Wrapping items() inside list() is unnecessary. Doing it to silence Splunk warnings
            for stanza, settings in list(confDict.items()):
                if stanza == self.config_te_stanza:
                    appsDir = settings['windows_splunk_dir'] + '\\Splunk\\etc\\apps'
                    dir = appsDir + slash + self.appName + '\\appserver\\addons'
        else:
            slash = '/'
            homeDir = os.environ.get('SPLUNK_HOME')
            appsDir = homeDir + '/etc/apps'
            dir = appsDir + slash + self.appName + '/appserver/addons'

        self.make_sure_path_exists(dir + slash + targetFolder)
        for source in ['local', 'default']:
            self.make_sure_path_exists(dir + slash + targetFolder + slash + source)
            for sourceFile in ['indexes.conf', 'props.conf', 'transforms.conf']:
                src = (
                    appsDir + slash + self.appName + slash + source + slash + sourceFile
                )
                tgt = dir + slash + targetFolder + slash + source + slash + sourceFile
                if os.path.isfile(src):
                    shutil.copyfile(src, tgt)

    def handleEdit(self, confInfo):

        # modify te_setup.conf
        # skip any variables without data
        # NOTE: Wrapping keys() inside list() is unnecessary. Doing it to silence Splunk warnings
        for key in list(self.callerArgs.keys()):
            if self.callerArgs.data[key][0] is None:
                self.callerArgs.data[key][0] = ''
        # handle a '\' or '/' at the end of the data location
        if 'data_location' in self.callerArgs:
            if self.callerArgs.data['data_location'][0][-1:] in ['\\', '/']:
                self.callerArgs.data['data_location'][0] = self.callerArgs.data[
                    'data_location'
                ][0][:-1]

        # handle a '\' or '/' at the end of the Windows Splunk directory
        if 'windows_splunk_dir' in self.callerArgs:
            if self.callerArgs.data['windows_splunk_dir'][0][-1:] in ['\\', '/']:
                self.callerArgs.data['windows_splunk_dir'][0] = self.callerArgs.data[
                    'windows_splunk_dir'
                ][0][:-1]
        # standardize boolean values
        if int(self.callerArgs.data['use_forwarder_bool'][0]) == 1:
            self.callerArgs.data['use_forwarder_bool'][0] = '1'
        else:
            self.callerArgs.data['use_forwarder_bool'][0] = '0'
        if int(self.callerArgs.data['showContentDiff'][0]) == 1:
            self.callerArgs.data['showContentDiff'][0] = '1'
        else:
            self.callerArgs.data['showContentDiff'][0] = '0'
        if int(self.callerArgs.data['compare_prev_version'][0]) == 1:
            self.callerArgs.data['compare_prev_version'][0] = '1'
        else:
            self.callerArgs.data['compare_prev_version'][0] = '0'

        # verify an IP address was given for workflow_host
        if 'workflow_host' in self.callerArgs:
            ipAddress = re.search(
                r'^ *(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) *$',
                self.callerArgs.data['workflow_host'][0],
            )
            if ipAddress is None:
                self.callerArgs.data.pop('workflow_host')
            else:
                self.callerArgs.data['workflow_host'][0] = ipAddress.group(1)

        # clean ints
        for interval in [
            'listening_port',
            'scm_int',
            'fim_int',
            'ecr_int',
            'fim_rest_threads',
            'scm_rest_threads',
        ]:
            if interval in self.callerArgs:
                port = re.search(r'^ *(\d+) *$', self.callerArgs.data[interval][0])
                if port is None:
                    self.callerArgs.data.pop(interval)
                else:
                    self.callerArgs.data[interval][0] = port.group(1)

        # set time unit for SCM
        if (
            self.callerArgs.data['scm_hour'][0] == self.callerArgs.data['scm_day'][0]
            or 'scm_int' not in self.callerArgs
        ):
            pass
        else:
            if self.callerArgs.data['scm_hour'][0] == '1':
                self.callerArgs.data['scm_unit'][0] = 'hour'
            elif self.callerArgs.data['scm_day'][0] == '1':
                self.callerArgs.data['scm_unit'][0] = 'day'
            self.callerArgs.data['scm_int_saved'][0] = self.callerArgs.data['scm_int'][
                0
            ]

        # set time unit for FIM
        if (
            self.callerArgs.data['fim_hour'][0] == self.callerArgs.data['fim_day'][0]
            or 'fim_int' not in self.callerArgs
        ):
            pass
        else:
            if self.callerArgs.data['fim_hour'][0] == '1':
                self.callerArgs.data['fim_unit'][0] = 'hour'
            elif self.callerArgs.data['fim_day'][0] == '1':
                self.callerArgs.data['fim_unit'][0] = 'day'
            self.callerArgs.data['fim_int_saved'][0] = self.callerArgs.data['fim_int'][
                0
            ]

        # set time unit for ECR
        if (
            self.callerArgs.data['ecr_hour'][0] == self.callerArgs.data['ecr_day'][0]
            or 'ecr_int' not in self.callerArgs
        ):
            pass
        else:
            if self.callerArgs.data['ecr_hour'][0] == '1':
                self.callerArgs.data['ecr_unit'][0] = 'hour'
            elif self.callerArgs.data['ecr_day'][0] == '1':
                self.callerArgs.data['ecr_unit'][0] = 'day'
            self.callerArgs.data['ecr_int_saved'][0] = self.callerArgs.data['ecr_int'][
                0
            ]

        for param in [
            'scm_hour',
            'scm_day',
            'scm_int',
            'fim_hour',
            'fim_day',
            'fim_int',
            'ecr_hour',
            'ecr_day',
            'ecr_int',
        ]:
            if param in self.callerArgs:
                self.callerArgs.data.pop(param)

        # Encrypt password
        pm = splunk_helper.PasswordManager(auth_token=self.getSessionKey())
        pm.set_password(username=self.callerArgs.data["te_username"][0], password=self.callerArgs.data['te_pass'][0])
        self.callerArgs.data['te_pass'][0] = ""  # do not save password to te_setup.conf
        # write settings to te_setup.conf
        self.writeConf(self.config_file, self.config_te_stanza, self.callerArgs.data)

        # modify inputs.conf
        if 'data_location' in self.callerArgs or 'listening_port' in self.callerArgs:
            confInput = self.readConf("inputs")
            # NOTE: Wrapping items() inside list() is unnecessary. Doing it to silence Splunk warnings
            for stanza, settings in list(confInput.items()):
                origStanza = stanza
                fim = 'FIM/*.(log|csv)'
                scm = 'SCM/*.(log|csv)'
                ecr = 'ECR/*.(log|csv)'
                te_assets = 'te_assets.csv'
                tcp = 'tcp://'  # default config section name  tcp://te_default
                fimscript = 'tripwire_fim.py'
                scmscript = 'tripwire_scm.py'
                ecrscript = 'tripwire_ecr.py'
                teassets_script = 'te_assets.py'

                # change the monitored directories
                if (
                    stanza.find(fim) >= 0
                    or stanza.find(scm) >= 0
                    or stanza.find(ecr) >= 0
                    or stanza.find(te_assets) >= 0
                ) and ('data_location' in self.callerArgs):
                    # get settings from the default stanzas
                    dataLoc = self.callerArgs.data['data_location'][0]
                    if stanza.find('te_default') >= 0:
                        if dataLoc.find('\\') >= 0:
                            newStanza = stanza.replace(
                                '/te_default', self.callerArgs.data['data_location'][0]
                            )
                            newStanza = newStanza.replace('/', '\\')
                            newStanza = newStanza.replace('monitor:\\\\', 'monitor://')
                        else:
                            newStanza = stanza.replace(
                                '/te_default', self.callerArgs.data['data_location'][0]
                            )

                        if self.callerArgs.data['use_forwarder_bool'][0] == '1':
                            settings['disabled'] = '1'
                        else:
                            settings['disabled'] = '0'
                        settings.pop('_rcvbuf', None)
                        settings.pop('evt_resolve_ad_obj', None)
                        settings.pop('host', None)
                        self.writeConf('inputs', newStanza, settings)

                # change the listening port for TE syslog data
                elif stanza.startswith(tcp):
                    if 'listening_port' in self.callerArgs:
                        # disable other listening ports within the app
                        # get settings from the default listening port
                        if stanza.find('te_default') >= 0:
                            newStanza = stanza.replace(
                                'te_default', self.callerArgs.data['listening_port'][0]
                            )
                            if self.callerArgs.data['use_forwarder_bool'][0] == '1':
                                settings['disabled'] = '1'
                            else:
                                settings['disabled'] = '0'
                            settings.pop('_rcvbuf', None)
                            settings.pop('evt_resolve_ad_obj', None)
                            settings.pop('host', None)
                            self.writeConf('inputs', newStanza, settings)
                        elif stanza != f"{tcp}{self.callerArgs.data['listening_port'][0]}":
                            settings["disabled"] = "1"  # disable old entries
                            self.writeConf("inputs", stanza, settings)
                    else:  # no listening port has been provided. Disable all tcp inputs
                        if "te_default" not in stanza:
                            settings["disabled"] = "1"
                            self.writeConf("inputs", stanza, settings)

                # scm script
                elif stanza.find(scmscript) >= 0 and 'scm_int_saved' in self.callerArgs:
                    if self.callerArgs.data['use_forwarder_bool'][0] == '1':
                        newStanza = stanza.replace(
                            '/TA-tripwire_enterprise/', '/TA-tripwire_enterprise_FWD/'
                        )
                        settings['disabled'] = '1'
                    else:
                        newStanza = origStanza
                        settings['disabled'] = '0'

                    if self.callerArgs.data['scm_unit'][0] == 'hour':
                        settings['interval'] = (
                            int(self.callerArgs.data['scm_int_saved'][0]) * 3600
                        )
                    elif self.callerArgs.data['scm_unit'][0] == 'day':
                        settings['interval'] = (
                            int(self.callerArgs.data['scm_int_saved'][0]) * 86400
                        )
                    else:
                        settings['interval'] = 86400
                    settings.pop('_rcvbuf', None)
                    settings.pop('evt_resolve_ad_obj', None)
                    settings.pop('host', None)
                    settings.pop('evt_dns_name', None)
                    settings.pop('evt_dc_name', None)
                    # write the new monitoring stanza to input.conf
                    self.writeConf('inputs', newStanza, settings)

                # fim script
                elif stanza.find(fimscript) >= 0 and 'fim_int_saved' in self.callerArgs:
                    if self.callerArgs.data['use_forwarder_bool'][0] == '1':
                        newStanza = stanza.replace(
                            '/TA-tripwire_enterprise/', '/TA-tripwire_enterprise_FWD/'
                        )
                        settings['disabled'] = '1'
                    else:
                        newStanza = origStanza
                        settings['disabled'] = '0'

                    if self.callerArgs.data['fim_unit'][0] == 'hour':
                        settings['interval'] = (
                            int(self.callerArgs.data['fim_int_saved'][0]) * 3600
                        )
                    elif self.callerArgs.data['fim_unit'][0] == 'day':
                        settings['interval'] = (
                            int(self.callerArgs.data['fim_int_saved'][0]) * 86400
                        )
                    else:
                        settings['interval'] = 3600
                    settings.pop('_rcvbuf', None)
                    settings.pop('evt_resolve_ad_obj', None)
                    settings.pop('host', None)
                    settings.pop('evt_dns_name', None)
                    settings.pop('evt_dc_name', None)
                    # write the new monitoring stanza to input.conf
                    self.writeConf('inputs', newStanza, settings)

                # ecr script
                elif stanza.find(ecrscript) >= 0 and 'ecr_int_saved' in self.callerArgs:
                    if self.callerArgs.data['use_forwarder_bool'][0] == '1':
                        newStanza = stanza.replace(
                            '/TA-tripwire_enterprise/', '/TA-tripwire_enterprise_FWD/'
                        )
                        settings['disabled'] = '1'
                    else:
                        newStanza = origStanza
                        settings['disabled'] = '0'

                    if self.callerArgs.data['ecr_unit'][0] == 'hour':
                        settings['interval'] = (
                            int(self.callerArgs.data['ecr_int_saved'][0]) * 3600
                        )
                    elif self.callerArgs.data['ecr_unit'][0] == 'day':
                        settings['interval'] = (
                            int(self.callerArgs.data['ecr_int_saved'][0]) * 86400
                        )
                    else:
                        settings['interval'] = 86400
                    settings.pop('_rcvbuf', None)
                    settings.pop('evt_resolve_ad_obj', None)
                    settings.pop('host', None)
                    settings.pop('evt_dns_name', None)
                    settings.pop('evt_dc_name', None)
                    # write the new monitoring stanza to input.conf
                    self.writeConf('inputs', newStanza, settings)

                # ecr script
                elif stanza.find(teassets_script) >= 0:
                    if self.callerArgs.data['use_forwarder_bool'][0] == '1':
                        newStanza = stanza.replace(
                            '/TA-tripwire_enterprise/', '/TA-tripwire_enterprise_FWD/'
                        )
                        settings['disabled'] = '1'
                    else:
                        newStanza = origStanza
                        settings['disabled'] = '0'
                    settings['interval'] = 3600
                    settings.pop('_rcvbuf', None)
                    settings.pop('evt_resolve_ad_obj', None)
                    settings.pop('host', None)
                    settings.pop('evt_dns_name', None)
                    settings.pop('evt_dc_name', None)
                    # write the new monitoring stanza to input.conf
                    self.writeConf('inputs', newStanza, settings)

        # modify workflow_actions.conf
        if 'workflow_host' in self.callerArgs:
            session_key = self.getSessionKey()
            endpoint = '/admin/conf-workflow_actions'

            confWorkflow = self.readConf("workflow_actions")
            # NOTE: Wrapping items() inside list() is unnecessary. Doing it to silence Splunk warnings
            for stanza, settings in list(confWorkflow.items()):
                try:
                    entity = en.getEntity(
                        endpoint,
                        stanza,
                        namespace=self.appName,
                        sessionKey=session_key,
                        owner='nobody',
                    )
                    if 'link.uri' in settings and entity is not None:
                        if (
                            re.search(
                                r'te_default|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',
                                settings['link.uri'],
                            )
                            is not None
                        ):
                            settings['link.uri'] = re.sub(
                                r'te_default|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',
                                self.callerArgs.data['workflow_host'][0],
                                settings['link.uri'],
                            )
                            # write changes to workflow_actions.conf
                            self.writeConf('workflow_actions', stanza, settings)
                except Exception:
                    pass

        # Create the folder and files that will be used for the TA app
        self.createTAApp()
        self.createSAApp()
        self.restartRequired = True

        # create banner message alerting user Splunk requires a manual restart
        session_key = self.getSessionKey()
        base_url = splunk_helper.management_url()
        endpoint = '/services/messages'
        payload = {
            'name': 'te_restart',
            'severity': 'warn',
            'value': 'Splunk restart required to complete Tripwire Enterprise installation.',
        }
        headers = {'Authorization': ('Splunk %s' % session_key)}
        r = urllib.request.Request(
            base_url + endpoint,
            data=urllib.parse.urlencode(payload).encode('utf-8'),
            headers=headers,
        )
        try:
            urllib.request.urlopen(r)  # nosec
        except urllib.error.URLError:
            # It's not a huge deal if we can't send this system message
            pass


admin.init(ConfigApp, admin.CONTEXT_NONE)
