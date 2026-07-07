'''
Singleton class that is meant to store and retrieve Splunk platform-specific info
'''
from __future__ import absolute_import
from builtins import object
import sys
import splunk

class SplunkInfraReader(object):

	shared_instance = None

	class SplunkInfraReaderHelper(object):

		def __call__(self):
			# If an instance of this class does not exist,
			# create one and assign it to shared_instance.
			if SplunkInfraReader.shared_instance is None :
				new_instance = SplunkInfraReader()
				SplunkInfraReader.shared_instance = new_instance

			return SplunkInfraReader.shared_instance

	# Create a class level method that must be called to get the shared instance
	get_shared_instance = SplunkInfraReaderHelper()

	def __init__(self):
		if SplunkInfraReader.shared_instance is not None:
			raise RuntimeError('Only one instance of SplunkInfraReader is allowed!')
		else:
			self.local_server = self.get_local_server()
			self.session_key  = self.get_session_key()

	def get_session_key(self):
		session_key=''
		for line in sys.stdin:
			session_key = line
			if session_key in [None, '']:
				raise Exception('Invalid session key received from Splunk.')
		return session_key

	def get_local_server(self):
		return splunk.getLocalServerInfo()