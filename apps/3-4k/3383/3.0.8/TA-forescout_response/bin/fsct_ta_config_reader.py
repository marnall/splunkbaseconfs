from __future__ import absolute_import
from builtins import str
from builtins import object
import sys
import os
import re
from splunk.clilib import cli_common as cli
import splunk.entity as entity

from fsct_exception import Error
from splunk_infra_reader import SplunkInfraReader
import fsct_defaults
import six

class TAForescoutConfigFetcher(object):

	def __init__(self, logger):
		self.logger = logger

	def get_fsct_config(self):
		app_bin_dir     = os.path.dirname(os.path.realpath(__file__))
		app_root_dir    = os.path.dirname(app_bin_dir)
		splunk_apps_dir = os.path.dirname(app_root_dir)
		ta_root_dir     = os.path.join(splunk_apps_dir, fsct_defaults.FS_TA_APP_NAME)
		if os.path.exists(ta_root_dir):
			os.chdir(ta_root_dir)
			# read configuration stanza from setup conf file, if TA-forescout installation directory is found.
			configuration_dict = cli.getConfStanza(fsct_defaults.FS_TA_SETUP_CONF_FILE, fsct_defaults.FS_TA_SETUP_CONF_STANZA)
			return configuration_dict
		else:
			raise Error('Error in reading config from ' + fsct_defaults.FS_TA_APP_NAME + '. Could not find the installation directory for this app.')

	def get_fsct_index(self):
		config_dict = self.get_fsct_config()
		fsct_index = config_dict.get(fsct_defaults.FS_TA_INDEX_KEY, '')
		if fsct_index in [None, '']:
			# index is a required field on TA-forescout setup page. If its value is null or empty, raise an exception.
			raise Error('Invalid index value:[' + fsct_index + ']')
		else:
			return fsct_index

	def get_fsct_emip(self):
		config_dict = self.get_fsct_config()
		fsct_emip  = config_dict.get(fsct_defaults.FS_TA_EMIP_KEY, '')
		if fsct_emip in [None, '']:
			# emip is a required field on TA-forescout setup page. If its value is null or empty, raise an exception.
			raise Error('Invalid CounterACT IP Address or Hostname value:[' + fsct_emip + ']')
		else:
			return fsct_emip.split('|')

	def get_fsct_callbackid(self):
		config_dict = self.get_fsct_config()
		fsct_callbackid  = config_dict.get(fsct_defaults.FS_TA_CALLBACKID_KEY, '')
		if fsct_callbackid in [None, '']:
			return []
		else:
			return fsct_callbackid.split('|')

	def get_usessl(self):
		config_dict = self.get_fsct_config()
		usessl = config_dict.get(fsct_defaults.FS_TA_USESSL_KEY, '')
		if usessl in [None, '']:
			raise Error('Invalid usessl value:[' + usessl + ']')
		else:
			return usessl

	def get_verifycert(self):
		config_dict = self.get_fsct_config()
		verifycert = config_dict.get(fsct_defaults.FS_TA_VERIFYCERT_KEY, '')
		if verifycert in [None, '']:
			raise Error('Invalid verifycert value:[' + verifycert + ']')
		else:
			return verifycert

	def getCredentials(self, session_key = None):
		self.logger.debug('Getting credentials configured in app: [' + fsct_defaults.FS_TA_APP_NAME + '].')
		try:
			if session_key is None:
				session_key = SplunkInfraReader.get_shared_instance().session_key

			# list all credentials for TA app
			entities = entity.getEntities(['admin', 'passwords'], count = -1, search = fsct_defaults.FS_TA_APP_NAME, namespace = fsct_defaults.FS_TA_APP_NAME, owner = 'nobody', sessionKey = session_key)

			# return first set of credentials
			emIps = []
			passwords = []
			for key, val in six.iteritems(entities):
				if (str(val['eai:acl']['app'])) == fsct_defaults.FS_TA_APP_NAME:
					username = re.sub(r'_3fs', ':', val['username'])
					password = val['clear_password']
					if (username not in [None, '']) and (password not in [None, '']):
						emIps.append(username)
						passwords.append(password)
						self.logger.info('username: ' + username + ", password: " + password)
					else:
						self.logger.error('Invalid username or password.')
			return emIps, passwords
		except Exception as err:
			raise Error('Could not get credentials configured in ' + fsct_defaults.FS_TA_APP_NAME + '. Error: %s' % (str(err)))

	def getOneCredential(self, session_key = None):
		self.logger.debug('Getting credentials configured in app: [' + fsct_defaults.FS_TA_APP_NAME + '].')
		try:
			if session_key is None:
				session_key = SplunkInfraReader.get_shared_instance().session_key

			# list all credentials for TA app
			entities = entity.getEntities(['admin', 'passwords'], count = -1, search = fsct_defaults.FS_TA_APP_NAME, namespace = fsct_defaults.FS_TA_APP_NAME, owner = 'nobody', sessionKey = session_key)

			# return first set of credentials
			for key, val in six.iteritems(entities):
				if (str(val['eai:acl']['app'])) == fsct_defaults.FS_TA_APP_NAME:
					username = username = re.sub(r'_3fs', ':', val['username'])
					password = val['clear_password']
					if (username not in [None, '']) and (password not in [None, '']):
						self.logger.error('username: ' + username + ", password: " + password)
						return username, password
					else:
						self.logger.error('Invalid username or password.')
		except Exception as err:
			raise Error('Could not get credentials configured in ' + fsct_defaults.FS_TA_APP_NAME + '. Error: %s' % (str(err)))