#!/usr/bin/python

import json
import sys,csv,splunk.Intersplunk,string,re,os,platform
import requests
import globals

def main():
    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)

    try:
        items = requests.get(globals.API_HOST + "/api/contentType", headers = {
            "Accept": "application/json"
        }, proxies = globals.getProxies(settings), verify = not '.smartru.com' in globals.API_HOST).json()

        output = csv.writer(sys.stdout)
        output.writerow(["contentTypeId", "name"])

        for item in items:
            output.writerow([item["contentTypeId"], item["name"]])

    except:
        splunk.Intersplunk.parseError("Unable to load Content Types")



main()
