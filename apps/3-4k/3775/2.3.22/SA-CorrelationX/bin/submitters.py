#!/usr/bin/python

import json
import sys,csv,splunk.Intersplunk,string,re,os,platform
import requests
import globals

def main():
    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
    if len(sys.argv) < 2:
        splunk.Intersplunk.parseError("No arguments provided")
        sys.exit(0)

    token = sys.argv[1].strip()

    try:
        items = requests.get(globals.API_HOST + "/api/user/search/", headers = {
            "Accept": "application/json",
            "Authorization": "Bearer " + token
        }, proxies = globals.getProxies(settings), verify = not '.smartru.com' in globals.API_HOST).json()

        output = csv.writer(sys.stdout)
        output.writerow(["id", "displayName"])

        for item in items:
            output.writerow([item["id"], item["displayName"]])

    except:
        splunk.Intersplunk.parseError("Unable to load Submitters")



main()
