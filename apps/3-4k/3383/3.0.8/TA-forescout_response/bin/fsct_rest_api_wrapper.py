from __future__ import absolute_import
from builtins import object
import six.moves.urllib.request, six.moves.urllib.parse, six.moves.urllib.error
import six.moves.urllib.request, six.moves.urllib.error, six.moves.urllib.parse

from fsct_exception import Error
from splunk_infra_reader import SplunkInfraReader
import fsct_defaults

class FSSplunkRestApiWrapper(object):

	def __init__(self, logger):
		self.logger       = logger
		self.local_server = SplunkInfraReader.get_shared_instance().local_server
		self.session_key  = SplunkInfraReader.get_shared_instance().session_key

	def updateIndexMacrosConf(self, index):
		self.logger.info('Updating macros.conf in app: [' + fsct_defaults.FS_TA_RESPONSE_APP_NAME + '] with index: [' + index + ']')
		macrovalue = 'index="' + index + '"'
		request    = six.moves.urllib.request.Request(self.local_server + '/servicesNS/nobody/' + fsct_defaults.FS_TA_RESPONSE_APP_NAME + '/properties/macros/get_index', data=six.moves.urllib.parse.urlencode({ 'definition' : macrovalue }).encode('utf-8'), headers = { 'Authorization' : ('Splunk %s' % self.session_key) })
		self.sendRestApiRequest(request)

	def updateAlertActionsConf(self, action_stanza, action_params):
		self.logger.info('Updating alert_actions.conf in app: [' + fsct_defaults.FS_TA_RESPONSE_APP_NAME + '], action stanza: [' + action_stanza + ']')
		request = six.moves.urllib.request.Request(self.local_server + '/servicesNS/nobody/' + fsct_defaults.FS_TA_RESPONSE_APP_NAME + '/properties/alert_actions/' + action_stanza, data=six.moves.urllib.parse.urlencode(action_params).encode('utf-8'), headers = { 'Authorization' : ('Splunk %s' % self.session_key) })
		self.sendRestApiRequest(request)

	def updateMessages(self, request_type, name, value, severity):
		if request_type is 'POST':
			self.logger.info('Posting new message to bulletin.')
			request = six.moves.urllib.request.Request(self.local_server + '/services/messages', data = six.moves.urllib.parse.urlencode({ 'name' : name, 'value' : value, 'severity' : severity }).encode('utf-8'), headers = { 'Authorization' : ('Splunk %s' % self.session_key) })
			self.sendRestApiRequest(request)
		else:
			self.logger.error('This request type is not yet supported for /services/messages endpoint.')

	def sendRestApiRequest(self, request):
		try:
			response = six.moves.urllib.request.urlopen(request)
		except six.moves.urllib.error.HTTPError as err:
			raise Error('HTTPError: error code: [%d]' % err.code)
		except six.moves.urllib.error.URLError as err:
			raise Error('URLError: error reason: [%s]' % err.reason)
		else:
			self.logger.debug('REST API request succeeded')
			return response