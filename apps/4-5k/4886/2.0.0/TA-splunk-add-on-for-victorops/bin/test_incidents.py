import os
import sys
import time
import datetime
import json
import requests
import time
import hashlib


def getIncidents(orgHead):
    t = time.clock()
    req = requests.get(
        'https://api.victorops.com/api-public/v1/incidents', headers=orgHead)
    # RATE LIMITS
    while req.status_code == 403:
        # wait until minute has passed
        print('waiting ', str(t + 60 - time.clock()), 'seconds. . .')
        time.sleep(t + 60 - time.clock())
        # reset timer to current time
        t = time.clock()
        # retry
        req = requests.get(
            'https://api.victorops.com/api-public/v1/incidents', headers=orgHead)

    if req.status_code == 200:
        # IF SUCCESS, GET LAST ALERT RAW ALERT
        incidents = json.loads(req.text)
        for i in incidents['incidents']:
            i['lastAlert'] = getAlert(orgHead, i['lastAlertId'])
        return incidents


def getAlert(orgHead, uuid):
    t = time.clock()
    url = "https://api.victorops.com/api-public/v1/alerts/" + uuid
    req = requests.get(url, headers=orgHead)
    # RATE LIMITS
    while req.status_code == 403:
        # wait until minute has passed
        print('waiting ', str(t + 60 - time.clock()), 'seconds. . .')
        time.sleep(t + 60 - time.clock())
        # reset timer to current time
        t = time.clock()
        # retry
        req = requests.get(url, headers=orgHead)
    if req.status_code == 200:
        return json.loads(req.text)


def main():

    orgHead = {
        'Content-Type': 'application/json',
        'Accept': "application/json",
        'X-VO-Api-Id': "<>",
        'X-VO-Api-Key': "<>"
    }

    incidents = getIncidents(orgHead)
    for i in incidents['incidents']:
        print(json.dumps(i, indent=2))


if __name__ == '__main__':
    main()
