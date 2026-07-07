#!/usr/bin/python

import json
import sys,csv,splunk.Intersplunk,string,re,os,platform
import requests
import globals
import splunk.search


def getUserInfo(token, proxies):
	try:
		result = requests.get(globals.API_HOST + '/api/account', headers = {
			'Accept': 'application/json',
			'Authorization': 'Bearer ' + token
		}, proxies = proxies, verify = not '.smartru.com' in globals.API_HOST).json()
		if result['displayName'] != None:
			return result
	except:
		return

def main():
	results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
	(isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
	if len(sys.argv) < 2:
		splunk.Intersplunk.parseError("No arguments provided")
		sys.exit(0)

	output = csv.writer(sys.stdout)
	token = sys.argv[1].strip()

	result = getUserInfo(token, globals.getProxies(settings))

	output.writerow(["DisplayName", "Email"])
	output.writerow([result['displayName'], result['email']])


main()
