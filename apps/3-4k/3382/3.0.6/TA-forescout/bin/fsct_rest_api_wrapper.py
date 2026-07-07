from __future__ import absolute_import
from builtins import object
import six.moves.urllib.request, six.moves.urllib.parse, six.moves.urllib.error
import six.moves.urllib.request, six.moves.urllib.error, six.moves.urllib.parse
import re

from fsct_exception import Error
import fsct_defaults
import ipv6utils
class FSSplunkRestApiWrapper(object):

	def __init__(self, logger, local_server, session_key):
		self.logger       = logger
		self.local_server = local_server
		self.session_key  = session_key

	def updateStoragePasswords(self, request_type, username, password):
		if (request_type == 'DELETE'):
			self.logger.info('Deleting credentials for CounterACT IP: %s', username)
			# Need to escape the ipv6 address because in splunk, colon is used for passing
			# info and IPv6 contains colon itself which will cause 404 on splunk server
			if ipv6utils.is_valid_ipv6_address(username):
				username = re.escape(username)
			self.logger.debug('CounterACT IP sent to delete: %s', username)
			request = six.moves.urllib.request.Request(self.local_server + '/servicesNS/nobody/' + fsct_defaults.FS_TA_APP_NAME + '/storage/passwords/:' + username + ':', headers={'Authorization': ('Splunk %s' % self.session_key)})
			request.get_method = lambda: 'DELETE'
			self.sendRestApiRequest(request)
		elif (request_type == 'POST'):
			# store the new credentials in '/storage/passwords' endpoint
			self.logger.info('Storing credentials for CounterACT IP: %s', username)
			request = six.moves.urllib.request.Request(self.local_server + '/servicesNS/nobody/' + fsct_defaults.FS_TA_APP_NAME + '/storage/passwords', data=six.moves.urllib.parse.urlencode({'name': username, 'password': password}).encode('utf-8'), headers={'Authorization': ('Splunk %s' % self.session_key)})
			self.sendRestApiRequest(request)
		else:
			raise Error('Invalid request type while updating /storage/passwords endpoint')

	def sendRestApiRequest(self, request):
		try:
			response = six.moves.urllib.request.urlopen(request)
		except six.moves.urllib.error.HTTPError as err:
			raise Error('HTTPError: error code: [%d]' % err.code)
		except six.moves.urllib.error.URLError as err:
			raise Error('URLError: error reason: [%s]' % err.reason)
		except:
			raise Error('REST API request went wrong.')
		else:
			self.logger.debug('REST API request succeeded')
			return response
