import requests

import sophos_xml as keys

from xml.etree import ElementTree as ET

status_code = []


class Sophos():

	def __init__(self, logger, host, port, user, password):
		self.host = host
		self.port = port
		self.user = user
		self.password = password
		self.logger = logger


	def response(self, helper, r, action):
		Code = {
		    "200": (True, " operation:finished successfully"),
		    "500": (False, " operation: couldn't be performed"),
		    "529": (False, " operation: failed. Reason: Input request module is invalid"),
		}
		
		resultcontent = ET.fromstring(r.text)
		for child in resultcontent:
			if child.tag == "Login":
				status = child.find('status').text
				if status == "Authentication Successful":
					self.logger.info(status)
				else:
					status = "Login status: %s" % child.find('status').text
					self.logger.error(status)
				status_code.append(status)
			if child.tag in [ "IPHost", "FirewallRule", "FirewallRuleGroup", "User"]:
				Status = child.find('Status')
				try:
					if action:
						msg = " %s" % action + Code[Status.attrib["code"]][1]
					else:
						pass
					if Code[Status.attrib["code"]][0] == "False":
						self.logger.error(msg)
					else:
						self.logger.info(msg)
					status_code.append(msg)
				except KeyError:
					msg_exception = "Message: %s" % Status.text
					self.logger.error(msg_exception)
					continue
			if child.tag == "Status":
				msg = "Error code %s: %s" % (child.attrib['code'], child.text)
				self.logger.error(msg)
		status_ = ','.join([str(elt) for elt in status_code])
		return status_



	def connect_and_apply(self, helper, rule, action = None):
		data = {'reqxml': (None, (keys.Login.format(self.user, self.password, rule)))}
		url = keys.url.format(self.host, self.port)
		r = requests.post( url , data = data, verify = False)
		if action != None:
			s = self.response(helper, r, action)
			return ([r.text, s])
		else:
			return ([r.text])

	def verif_ht_gp_rl(self, helper,rule): 
		r = self.connect_and_apply(helper, rule)[0]
		root = ET.fromstring(r)
		exist_list = []
		for name in root.iter('Name'):
			exist_list.append(name.text)
		print(exist_list)
		return exist_list  
	
	def get_gp_rules(self, helper, rule = None, root = None):
		if rule != None:
			r = self.connect_and_apply(helper, rule)[0]
			root = ET.fromstring(r)
		gp_rules = []
		for name in root.iter('SecurityPolicy'):
			gp_rules.append(name.text)
		return gp_rules

	def get_gp_or_rule_params(self, helper, rule):
		r =self.connect_and_apply(helper, rule)[0]
		root = ET.fromstring(r)
		return (root)

	def verif_host(self, helper,rule):
		r = self.connect_and_apply(helper, rule)[0]
		root = ET.fromstring(r)
		existance = 'Name' in str(r)
		if existance:
			return (root.find('IPHost').find('Name').text)
		else:
			print ("no. of records Zero.")

	






