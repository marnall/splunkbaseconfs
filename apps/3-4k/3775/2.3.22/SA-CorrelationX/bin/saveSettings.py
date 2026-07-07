#!/usr/bin/python

import json
import base64
import sys,csv,splunk.Intersplunk,splunk.saved,string,re,os,platform
import splunk.entity
import requests
import globals
import ConfigParser


def main():
	results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
	(isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
	if len(sys.argv) < 6:
		splunk.Intersplunk.parseError("No arguments provided")
		sys.exit(0)

	authString = settings.get("authString", None)
	if authString == None:
		exit

	start = authString.find('<username>') + 10
	stop = authString.find('</username>')
	user = authString[start:stop]

	start = authString.find('<authToken>') + 11
	stop = authString.find('</authToken>')
	authToken = authString[start:stop]

	proxy_ip = sys.argv[1].strip()
	proxy_port = sys.argv[2].strip()
	proxy_user = sys.argv[3].strip()
	proxy_password = sys.argv[4].strip()
	defaultSharingForDataModel = sys.argv[5].strip()

	output = csv.writer(sys.stdout)
	output.writerow([
		"Result",
	])

	try:
		config = ConfigParser.RawConfigParser()

		try:
			config.read('../local/proxy.conf')
		except:
			pass

		try:
			config.add_section('corx')
		except:
			pass

		config.set('corx', 'proxy_ip', proxy_ip)
		config.set('corx', 'proxy_port', proxy_port)
		config.set('corx', 'proxy_user', proxy_user)
		config.set('corx', 'install_datamodels_globally', 'True' if defaultSharingForDataModel == '0' else 'False')

		with open('../local/proxy.conf', 'wb') as configfile:
			config.write(configfile)

		if proxy_password is not None and proxy_password != '':
			try:
				password = splunk.entity.getEntity("storage/passwords", "proxy_password", namespace="SA-CorrelationX", owner=user, sessionKey=authToken)
				password["encr_password"] = None
				password["clear_password"] = None
				password["username"] = None
				if password["encr_password"] != proxy_password:
					password["password"] = proxy_password
			except:
				password = splunk.entity.Entity("storage/passwords", "proxy_password", namespace="SA-CorrelationX", owner=user)
				password["name"] = "proxy_password"
				password["password"] = proxy_password

			splunk.entity.setEntity(password, sessionKey=authToken)
		else:
			try:
				splunk.entity.deleteEntity("storage/passwords", "proxy_password", namespace="SA-CorrelationX", owner=user, sessionKey=authToken)
			except:
				pass

		output.writerow([
			"True"
		])

	except Exception as e:
		output.writerow([
			str(e),
		])


main()
