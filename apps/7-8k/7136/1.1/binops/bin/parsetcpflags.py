#!/usr/bin/env python
# coding=utf-8

import sys,os

splunkhome = os.environ['SPLUNK_HOME']
# sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'TA-base64', 'lib'))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from splunklib.six.moves import range
from enum import Enum

# 20231201: v1.01
# Added additional input sanity checks
# 20231115: v1.00
# Initial version

class TcpFlags(Enum):
	FIN = 1
	SYN = 2
	RST = 4
	PSH = 8
	ACK = 16
	URG = 32

@Configuration()
class parsetcpflags(StreamingCommand):
	"""
	Decodes a bit field of TCP header flags to their alias names (SYN, ACK, FIN, ...)

	| parsetcpflags [infield=mytcpflags]
	"""
	in_field = Option(name='field', require=False, default='tcpflags')
	suppress_error = Option(name='suppress_error', require=False, default=True, validate=validators.Boolean())

	def stream(self, events):
		for event in events:
			if not self.in_field in event:
				continue
			try:
				if isinstance(event[self.in_field], str):
					val = event[self.in_field].encode('utf-8')
					try:
						if val.startswith(b"0x"):
							tcp_flags = int(val,16)
						else:
							tcp_flags = int(val,10)
					except:
						tcp_flags = 0
				else:
					tcp_flags = event[self.in_field]
				flag_set = []
				if int(tcp_flags) > 0:
					for tf in TcpFlags:
						if tcp_flags & tf.value == tf.value:
							flag_set.append(tf.name)
				event[self.in_field+'_parsed'] = flag_set
			except Exception as e:
				if not self.suppress_error :
					raise e

			yield event

dispatch(parsetcpflags, sys.argv, sys.stdin, sys.stdout, __name__)

