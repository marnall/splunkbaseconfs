#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Script for handling setup of Recorded Future for Splunk ES app."""

import logging
import os
import sys
import splunk  # pylint: disable=import-error
import splunk.admin as admin  # pylint: disable=import-error
# Relative imports for bundled modules and files.
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__),
                 '..', 'lib', 'python')))
# pylint: disable=import-error,wrong-import-position
from app_env import splunk_home  # nopep8
import rf_logger  # nopep8
sys.path.append(
    os.path.realpath(
        os.path.join(
            os.path.dirname(__file__),
            '..', 'lib', 'python',
            'splunk_sdk-1.6.2-py2.7.egg')))
# pylint: disable=wrong-import-position,import-error
import splunklib.client as client  # nopep8


LGR = logging.getLogger()
rf_logger.setup_logging(LGR, splunk_home(),
                        'TA-recorded_future',
                        'rf_es_setup.py')
LGR.setLevel(level=logging.INFO)


class RFEAIHandler(admin.MConfigHandler):
    """Config handler for TA-recorded_future."""
    conf_file = 'recorded_future'

    def setup(self):
        """Setup the handler."""
        assert self.requestedAction in [admin.ACTION_EDIT, admin.ACTION_LIST]
        action = {
            admin.ACTION_LIST: 'list',
            admin.ACTION_EDIT: 'edit',
            }[self.requestedAction]

        LGR.info('Starting %s run (%s)', action,
                 self.callerArgs.id)
        if self.requestedAction == admin.ACTION_EDIT:
            self.supportedArgs.addOptArg('log_level')
            self.supportedArgs.addOptArg('proxy')
            self.supportedArgs.addOptArg('token')

    def handleList(self, conf_info):  # pylint: disable=invalid-name
        """Handle a list request."""
        LGR.info('handleList entered (%s).', self.callerArgs.id)
        # Set the settings from recorded_future.conf
        # log_level
        conf_dict = self.readConf(self.conf_file)
        if 'logging' in conf_dict:
            log_level = conf_dict['logging'].get('log_level', 'info')
        else:
            log_level = 'info'
        if log_level == 'debug':
            conf_info['misc'].append('log_level', '1')
        else:
            conf_info['misc'].append('log_level', '0')
        LGR.debug('  handleList read logging[log_level]: %s.', log_level)

        # proxy
        if 'network' in conf_dict:
            val = conf_dict['network'].get('proxy', '')
        else:
            val = ''
        conf_info['misc'].append('proxy', val)
        LGR.debug('  handleList read network[proxy]: %s.', val)

        # token
        # Set the setting from storage passwords
        restapi = splunk.getLocalServerInfo()
        host, port = restapi.split('//')[1].split(':')
        session_key = self.getSessionKey()
        service = client.connect(token=session_key,
                                 app='TA-recorded_future',
                                 host=host, port=port)
        storage_passwords = service.storage_passwords.list()
        api_key_list = [ent.clear_password for ent in storage_passwords
                        if ent.name == 'TA-recorded_future:api_key:']
        if api_key_list == []:
            token = 'not set'
        else:
            token = '*' * len(api_key_list[0])
        conf_info['misc'].append('token', token)
        LGR.info('handleEdit finished (%s).', self.callerArgs.id)

    # pylint: disable=unused-argument, invalid-name
    def handleEdit(self, conf_info):
        """Handle edit requests."""
        LGR.info('handleEdit entered (%s).', self.callerArgs.id)

        # Store settings in recorded_future.conf
        if self.callerArgs.id == 'misc':
            LGR.debug('callerArgs.data: %s', self.callerArgs.data)

            # log_level
            if self.callerArgs.data['log_level'] == ['1']:
                val = {'log_level': 'debug'}
            else:
                val = {'log_level': 'info'}
            LGR.debug('handleEdit middle (%s).', self.callerArgs.id)
            self.writeConf('recorded_future', 'logging', val)
            LGR.debug('handleEdit part log_level done (%s).',
                      self.callerArgs.id)

            # proxy
            if self.callerArgs.data['proxy'][0] is None:
                val = {'proxy': ''}
            else:
                new_value = self.callerArgs.data['proxy'][0]
                if not new_value.startswith('https://'):
                    LGR.error('Validation for proxy setting failed. '
                              'A https proxy is required.')
                    raise admin.ArgValidationException(
                        'Proxy must be a https proxy '
                        '(requirement from Splunk).')
                else:
                    val = {'proxy': new_value}
                    LGR.debug('handleEdit middle (%s).',
                              self.callerArgs.id)
            self.writeConf('recorded_future', 'network', val)
            LGR.debug('handleEdit part proxy done (%s).',
                      self.callerArgs.id)

            # token
            new_token = self.callerArgs.data['token'][0]
            if new_token.strip().replace('*', '') == '':
                LGR.debug('Token not set')
            else:
                restapi = splunk.getLocalServerInfo()
                host, port = restapi.split('//')[1].split(':')
                session_key = self.getSessionKey()
                service = client.connect(token=session_key,
                                         app='TA-recorded_future',
                                         host=host, port=port)
                api_key_list = [ent.clear_password
                                for ent in service.storage_passwords.list()
                                if ent.name == 'TA-recorded_future:api_key:']
                if api_key_list != []:
                    service.storage_passwords.delete(
                        'TA-recorded_future:api_key:')
                service.storage_passwords.create(new_token,
                                                 'api_key',
                                                 'TA-recorded_future')
        LGR.info('handleEdit finished (%s).', self.callerArgs.id)


admin.init(RFEAIHandler, admin.CONTEXT_NONE)
