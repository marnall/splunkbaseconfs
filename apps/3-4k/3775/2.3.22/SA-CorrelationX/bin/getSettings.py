#!/usr/bin/python

import json
import sys,csv,splunk.Intersplunk,splunk.saved,string,re,os,platform
import splunk.entity
import requests
import globals
import ConfigParser


def main():
	results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()

	authString = settings.get("authString", None)
	if authString == None:
		exit

	start = authString.find('<username>') + 10
	stop = authString.find('</username>')
	user = authString[start:stop]

	start = authString.find('<authToken>') + 11
	stop = authString.find('</authToken>')
	authToken = authString[start:stop]

	output = csv.writer(sys.stdout)
	output.writerow([
		"ProxyIp",
		"ProxyPort",
		"ProxyUser",
		"ProxyPassword",
		"DefaultSharingForDataModel",
	])

	try:
		config = ConfigParser.RawConfigParser()
		config.read('../local/proxy.conf')

		proxy_ip = config.get('corx', 'proxy_ip')
		proxy_port = config.get('corx', 'proxy_port')
		proxy_user = config.get('corx', 'proxy_user')
		proxy_password = ""
		defaultSharingForDataModel = 0 if config.get('corx', 'install_datamodels_globally') == 'True' else 1

		try:
			password = splunk.entity.getEntity("storage/passwords", "proxy_password", namespace="SA-CorrelationX", owner=user, sessionKey=authToken)
			proxy_password = password["encr_password"]
		except:
			pass

		output.writerow([
			proxy_ip,
			proxy_port,
			proxy_user,
			proxy_password,
			defaultSharingForDataModel,
		])

	except Exception as e:
		output.writerow([
			'',
			'',
			'',
            '',
            0,
		])


main()
