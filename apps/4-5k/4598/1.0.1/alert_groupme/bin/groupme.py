#!/usr/bin/python
# -*- coding: utf-8 -*-


#Splunk Custom Alert Action for Groupme 

import os
import sys
import re
import subprocess
import json
import csv
import gzip
import requests
import urllib
import datetime

URL = "https://api.groupme.com/v3/bots/post"

def log(msg):
    f = open(os.path.join(os.environ["SPLUNK_HOME"],  "var", "log", "splunk", "alert_groupme.log"), "a")
    print >> f, str(datetime.datetime.now().isoformat()), msg
    f.close()

#Check args
def main():
    #os.environ['LD_LIBRARY_PATH'] = os.getcwd()
    #get json ouptut from splunk modular alert - See alert_actions.conf.spec
    payload = json.loads(sys.stdin.read())
    config = payload.get('configuration', dict())
    #host = payload.get('host') 
    splunkServer = payload.get('server_host')
    splunkURI = payload.get('server_uri')
    splunkApp = payload.get('app')
    splunkSearch = payload.get('search_name')
    resultsLink = payload.get('results_link')
    #result = payload.get('result')
    botID = config.get('botID')
    message = config.get('message')
    severity = config.get('severity')
    message = "****SPLUNK ALERT MESSAGE***\nSplunk Search: {0} \nSEVERITY: {1} \nMESSAGE: {2} \nResults Link: {3}".format(splunkSearch, severity, message, resultsLink)

    #Format the paramaters and pass them to send_message
    params = {"bot_id" : botID,"text" : message}

            #UNCOMMENT DEBUG
    log("[DEBUG] - Groupme Alert Starting")

    try:
        log("[DEBUG] - Sending Alert Message")
        r = requests.post(URL,  params=params)
        print r.text
        log("[DEBUG] - Alert Message Sent")
    except Exception as e:
        log("[ERROR] - Groupme Alert Failed, check splunkd.log for more details." + str(e))
        log("[ERROR] - " + str(e))
        sys.stderr.write('[Groupme] failed to run command\n')
if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit()

    main()
