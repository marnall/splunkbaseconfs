#!/usr/bin/env python
# coding=utf-8

import sys,os

splunkhome = os.environ['SPLUNK_HOME']
# sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'TA-base64', 'lib'))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from splunklib.six.moves import range
from enum import Enum

# 20231201 v1.0.1
# Improved input sanity checking
#
# 20121116 v1.0.0
# Initial version

@Configuration()
class binops(StreamingCommand):
	"""
	binops is an custom search commands which implements bitwise AND, XOR, OR, NOT on the provided input fields.
	This operation is only available from SPL v2 onwards otherwise.

	Usage: binops [binop_in1=binop_in1] [binop_in2=binop_in2] op=AND|XOR|OR [binop_result=binop_result]
	"""
	binop_in1  = Option(name='binop_in1', require=False, default='binop_in1')
	binop_in2  = Option(name='binop_in2', require=False, default='binop_in2')
	action = Option(name='op', require=False, default="AND", validate=validators.Set('XOR', 'AND', 'OR'))
	result = Option(name='binop_result', require=False, default='binop_' + str(action).lower())
	suppress_error = Option(name='suppress_error', require=False, default=False, validate=validators.Boolean())

	#if action not in ["XOR", "OR", "AND"]:
	#	raise Exception("Action must be 'XOR', 'OR' or 'AND'")
		

	def stream(self, events):
		for event in events:
			
			if not (self.binop_in1 in event and self.binop_in2 in event):
				continue

			try:
				args = {}
				for idx, in_field in enumerate([self.binop_in1, self.binop_in2]):
					if isinstance(event[in_field], str):
						val = event[in_field].encode('utf-8')
						try:
							if val.startswith(b"0x"):
								args["a"+str(idx+1)] = int(val,16)
							else:
								args["a"+str(idx+1)] = int(val,10)
						except:
							args["a"+str(idx+1)] = -1
					else:
						args["a"+str(idx+1)]  = event[in_field]
				if args["a1"] > 0 and args["a2"] > 0:
					if self.action == 'AND':
						result = args["a1"] & args["a2"]
					elif self.action == "OR":
						result = args["a1"] | args["a2"]
					elif self.action == "XOR":
						result = args["a1"] ^ args["a2"]
					else:
						result = ""
				else:
					result = ""

				event[self.result] = result 

			except Exception as e:
				if not self.suppress_error :
					raise e

			yield event

dispatch(binops, sys.argv, sys.stdin, sys.stdout, __name__)

