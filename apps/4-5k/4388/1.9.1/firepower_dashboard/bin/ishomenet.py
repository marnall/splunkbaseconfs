#!/usr/bin/env python
# coding=utf-8
#
# Copyright © 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, unicode_literals

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from splunk.clilib import cli_common as cli
import sys
import time
import json
import resources.investigate as investigate
from splunklib import six
from splunklib.six.moves import range


@Configuration()
class IsLocalCommand(GeneratingCommand):

	src_ip = Option(require=True)
	dest_ip = Option(require=True)

	def is_rfc_1918(self, ip):

		#ip=IPNetwork(ip)
		
		if "10.0.0.0/8" == ip or "172.16.0.0/12"==ip in "192.168.0.0/16" ==ip:
			return True
		else:
			return False

	def generate(self):

			src_ip = self.src_ip
			dest_ip = self.dest_ip

			match = "traffic direction"
			if self.is_rfc_1918(self.src_ip) and self.is_rfc_1918(self.dest_ip):
				trafficDirection =  "inside to inside"
			elif self.is_rfc_1918(self.src_ip) and not self.is_rfc_1918(self.dest_ip):
				trafficDirection = "inside to outside"
			else :
				trafficDirection = "outside to inside"	
			
			yield {'_time': time.time(), 'direction' : trafficDirection}


dispatch(IsLocalCommand, sys.argv, sys.stdin, sys.stdout, __name__)
