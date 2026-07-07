#!/usr/bin/env python
# coding=utf-8

import sys,os

splunkhome = os.environ['SPLUNK_HOME']
# sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'TA-base64', 'lib'))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from splunklib.six.moves import range
import math

#
# v1.01 20231201
# Improved input sanity handling
#
# v1.00 20231116
# Initial version

@Configuration()
class dissectbitfield(StreamingCommand):
	"""
	dissectbitfield is a custom search commands which returns the digits of the bits that are set to 1 in the input field.
	The LSB is digit 0. 

	Example: 'eval bitfield=23 | dissectbitfield bitfield=bitfield' returns 0,1,2,4 because 2^0+2ˆ1+2ˆ2+2ˆ4 = 23
	The input can be a positive decimal or hexadecimal number (prefixed with 0x). Input which can not be parsed as such a number is ignored. 

	Usage: dissectbitfield [bitfield=bitfield] [bitfield_result=bitfield_result]
	"""
	bitfield  = Option(name='bitfield', require=False, default='bitfield')
	result = Option(name='result', require=False, default='bitfield_result')
	suppress_error = Option(name='suppress_error', require=False, default=True, validate=validators.Boolean())


	def stream(self, events):
		for event in events:
			
			if not (self.bitfield in event):
				continue

			try:
				res = []
				if isinstance(event[self.bitfield], str):
					val = event[self.bitfield].encode('utf-8')
					try:
						if val.startswith(b'0x'):
							val = int(val,16)
						else:
							val = int(val,10)
					except:
						val = 0
				else:
					val = event[self.bitfield]

				# We can only handle positive numbers
				if val > 0:
	
					for i in range(1+int(math.ceil(math.log(val,2)))):
						if val & 1 == 1:
							res.append(i)
						val = val >> 1

				event[self.result] = res

			except Exception as e:
				if not self.suppress_error :
					raise e

			yield event

dispatch(dissectbitfield, sys.argv, sys.stdin, sys.stdout, __name__)

