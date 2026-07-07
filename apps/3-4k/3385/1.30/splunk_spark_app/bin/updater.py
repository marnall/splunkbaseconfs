#!/usr/bin/python

import sys, json
import urllib2
import urllib
import re
import time
import os, datetime
import pickle


baseUrl = 'https://demo-api.phonebot.io/v1/demo/incident/get'
logData = [[]]
cpath = os.path.dirname(__file__)
parentIndex = os.path.dirname(__file__).index('apps/')


def encodeStr(s, safeChars="~!*()-_'"):
    return urllib.quote_plus(s, safe=safeChars)


def modifyData(resolvedName, message, agents):
    global logData
    
    try:
        for l in logData:
            if l:
                if l[0] == resolvedName:
                    indexTime = time.strftime('%b / %d / %Y %H:%M:%S %p %Z', time.localtime())

                    print '_time={}, alert={}, id={}, trigger_time={}, agents={}, log={}, status={}'.format(indexTime, l[1], l[2], l[3], agents, message, 'resolved')
                    logData.remove(l)

        dbPath = os.path.join(cpath[:parentIndex], 'data')
        pickle.dump(logData, open(dbPath, 'wb'))

    except Exception as e:
        print >> sys.stderr, 'ERROR Failed at indexing data: {}'.format(e)


def checkData(dataToCheck):
    global logData
    newData = [[]]

    for item in dataToCheck:
        try:
            result = urllib2.urlopen(baseUrl + ('?name={}'.format(encodeStr(item))))
            response = result.read().replace('\'', '\\')
            parsedJson = json.loads(response)

            reqResult = 200 <= parsedJson['code'] < 300

            if 'resolvedReason' in parsedJson['data']:
                reason = '[ ' + ''.join(parsedJson['data']['resolvedReason']) + ' ]'
                agents = ', '.join(parsedJson['data']['agents']).replace(', ', ' || ')
                message = reason
                modifyData(item, message, agents)
            else:
                print >> sys.stderr, 'INFO Status is open yet {}'.format(item)
        except Exception as e:
            print >> sys.stderr, 'ERROR Fetch data with error: {}'.format(e)
            continue


def getData():
    global logData
    dbPath = os.path.join(cpath[:parentIndex], 'data')

    if os.path.isfile(dbPath):
        try:
            logData = pickle.load(open(dbPath, 'rb'))
            alerts = set()
            for l in logData:
                if l:
                    if l[4] == 0:
                        alerts.add(l[0])
            if alerts:
                checkData(dataToCheck=alerts)

        except IOError as e:
            print >> sys.stderr, 'ERROR Faild to open the file: {}'.format(e)
            sys.exit(1)
    else:
        print >> sys.stderr, 'ERROR No file was found'
        sys.exit(1)

getData()
