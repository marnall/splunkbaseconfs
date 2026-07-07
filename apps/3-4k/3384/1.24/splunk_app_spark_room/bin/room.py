#!/usr/bin/env python2

import sys, json
import urllib2
import urllib
import time
import os, datetime
import pickle
import random


apiUrl = ''
baseUrl = 'https://demo-api.phonebot.io/v1/demo/incident'
shortenerApi = 'https://www.googleapis.com/urlshortener/v1/url?key=AIzaSyD_JIzr3PS7cQCLxA8y_F9MwgsfZdcRFI8'


def _url(path):
    if apiUrl:
        return apiUrl + path
    else:
        return baseUrl + path


def encodeStr(s, safeChars="~!*()-_'"):
    return urllib.quote_plus(s, safe=safeChars)


def generateID():
    return long(time.time() + random.randint(0, 100))


def storeAlert(data):
    cpath = os.path.dirname(__file__)
    parentIndex = os.path.dirname(__file__).index('apps/')
    dbPath = os.path.join(cpath[:parentIndex], 'data')

    logData = [[]]

    if os.path.isfile(dbPath):
        logData = pickle.load(open(dbPath, 'rb'))

    logData.append(data)
    pickle.dump(logData, open(dbPath, 'wb'))


def logData(settings, event, source, sourcetype):
    header = {'Authorization': 'Splunk %s' % settings.get('session_key')}
    query = [('source', source), ('sourcetype', sourcetype), ('index', 'main'), ('host', settings.get('server_host'))]
    url = '{}/services/receivers/simple?{}'.format(settings.get('server_uri'), urllib.urlencode(query))

    try:
        encoded_body = unicode(event).encode('utf-8')
        req = urllib2.Request(url, encoded_body, header)
        res = urllib2.urlopen(req)

        if 200 <= res.code < 300:
            print >> sys.stderr, 'DEBUG receiver endpoint responded with HTTP status= {}'.format(res.code)
            return True
        else:
            print >> sys.stderr, 'ERROR receiver endpoint responded with HTTP status= {}'.format(res.code)
            return False
    except urllib2.HTTPError, e:
        print >> sys.stderr, 'ERROR Error sending receiver request: {}'.format(e)
    except urllib2.URLError, e:
        print >> sys.stderr, 'ERROR Error sending receiver request: {}'.format(e)
    except Exception as e:
        print >> sys.stderr, 'ERROR Error happened: {}'.format(e)
    return False


def send_incident(settings):
    config = settings.get('configuration')

    header = {}
    apiUrl = config.get('base_url')
    token = config.get('auth_token')

    roomTitle = config.get('subject')
    descData = config.get('desc')
    emails = config.get('agent').replace(' ', '')
    linkToSend = config.get('viewLink')
    linkToSearch = config.get('searchLink')
    alertName = config.get('alertName')
    sid = settings.get('sid')

    incidentId = generateID()

    eventLink = linkToSearch
    urlReq = urllib2.Request(shortenerApi, data=json.dumps({'longUrl': linkToSearch}), headers={'Content-Type': 'application/json'})
    try:
        urlResult = urllib2.urlopen(urlReq).read()
        eventLink = json.loads(urlResult)['id']
    except urllib2.HTTPError, e:
        print >> sys.stderr, 'ERROR Shortener faild: {}'.format(e)


    desc =  encodeStr('{}\nAlert Link: {}'.format(descData, eventLink), "'")
    url = '/report?name={}&incidentId={}&agents={}&description={}'.format(encodeStr(roomTitle), incidentId, encodeStr(emails), desc)
    apiAddr = _url(url)

    indexTime = time.strftime('%b / %d / %Y %H:%M:%S %p %Z', time.localtime())

    req = urllib2.Request(apiAddr, {})
    try:
        result = urllib2.urlopen(req)
        body = result.read()

        reqResult = 200 <= result.code < 300

        if reqResult:
            eventdata = 'alert={}, id={}, trigger_time={}, agents={}, status={}'.format(alertName, incidentId, indexTime, emails.replace(',', ' || '), 'open')
            logSuccess = logData(settings=settings, event=eventdata, source='spark_room', sourcetype='spark_room_log')

            storeAlert([roomTitle, alertName, incidentId, indexTime, 0])

            return logSuccess
        else:
            return False

    except urllib2.HTTPError, e:
        print >> sys.stderr, 'ERROR Error creating room: {}'.format(e)
        return False


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        payload = json.loads(sys.stdin.read())

        success = send_incident(payload)
        if not success:
            print >> sys.stderr, 'FATAL creating room failed'
            sys.exit(1)
        else:
            print >> sys.stderr, 'INFO Job was done!'
            sys.exit(0)
