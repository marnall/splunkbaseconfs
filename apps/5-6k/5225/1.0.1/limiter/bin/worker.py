#!/usr/bin/env python
from __future__ import print_function
import sys
import splunk.rest as rest
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta

def get_entries(session_key, endpoint):
    (response, content) = rest.simpleRequest(endpoint + '?output_mode=json', session_key)
    return json.loads(content)['entry']

def get_first_entry(session_key, endpoint):
    return get_entries(session_key, endpoint)[0]

def get_first_content(session_key, endpoint):
    return get_first_entry(session_key, endpoint)['content']

def get_license_usage(entry):
    usage = 0
    varLogDir = os.environ['SPLUNK_HOME'] + '/var/log/splunk/'
    linePattern = re.compile(r'(?P<datetime>.{19}).*\sidx="(?P<index>[^"]*)".*\sb=(?P<bytes>\d+)')
    minTime = datetime.now()
    if int(entry['content']['snapping']):
        hours = int(entry['content']['hours'])
        minTime = minTime.replace(hour=(minTime.hour // hours) * hours, minute=0, second=0, microsecond=0)
    else:
        minTime -= timedelta(hours=int(entry['content']['hours']))

    fileNr = 0
    while True:
        usageFile = varLogDir + 'license_usage.log'
        if fileNr > 0:
            usageFile += '.' + str(fileNr)
        if not os.path.isfile(usageFile):
            break
        
        usedFirstLine = True
        f = open(usageFile, 'rt')
        for line in f:
            match = linePattern.match(line)
            if not match:
                continue
            linetime = datetime.strptime(match.group('datetime'), '%m-%d-%Y %H:%M:%S')
            if linetime < minTime:
                usedFirstLine = False
                continue
            if entry['name'] != match.group('index'):
                continue
            usage += int(match.group('bytes'))
        if not usedFirstLine:
            break
        fileNr += 1
    return usage

def post_properties(session_key, endpoint, data):
    (response, content) = rest.simpleRequest(endpoint + '?output_mode=json', sessionKey=session_key, method='POST', postargs=data)

def delete_entry(session_key, endpoint):
    (response, content) = rest.simpleRequest(endpoint + '?output_mode=json', sessionKey=session_key, method='DELETE')

def do_the_work():
    session_key = sys.stdin.read()

    limiterStanza = get_first_content(session_key, '/servicesNS/nobody/limiter/configs/conf-app/limiter')
    createAliases = int(limiterStanza['create_aliases'])
    aliasSuffix = limiterStanza['alias_suffix']

    indexNames = set()
    limiterEntries = get_entries(session_key, '/servicesNS/nobody/limiter/configs/conf-limiter')
    for entry in limiterEntries:
        indexNames.add(entry['name'])
        usage = get_license_usage(entry)
        post_properties(session_key, '/servicesNS/nobody/limiter/configs/conf-limiter/' + entry['name'], {'used': usage})

        index = get_first_entry(session_key, '/servicesNS/nobody/-/data/indexes/' + entry['name'])
        indexDisabled = index['content']['disabled']

        limit = int(entry['content']['bytes'])
        if (not indexDisabled) and usage > limit:
            logInfo = 'Disabling index "' + entry['name'] + '"! (limit: ' + str(limit) + ', used: ' + str(usage) + ')'
            logging.info(logInfo)
            post_properties(session_key, index['links']['disable'], {})
            if createAliases:
                post_properties(session_key, '/servicesNS/nobody/limiter/data/indexes/' + entry['name'] + aliasSuffix + '/enable', {})
            post_properties(session_key, '/servicesNS/nobody/-/messages', {'name': 'limiter-disabled-' + entry['name'], 'value': logInfo, 'severity': 'info'})
        
        if indexDisabled and usage <= limit:
            logInfo = 'Enabling index "' + entry['name'] + '"! (limit: ' + str(limit) + ', used: ' + str(usage) + ')'
            logging.info(logInfo)
            if createAliases:
                post_properties(session_key, '/servicesNS/nobody/limiter/data/indexes/' + entry['name'] + aliasSuffix + '/disable', {})
            post_properties(session_key, index['links']['enable'], {})
            post_properties(session_key, '/servicesNS/nobody/-/messages', {'name': 'limiter-enabled-' + entry['name'], 'value': logInfo, 'severity': 'info'})
    
    messages = get_entries(session_key, '/servicesNS/nobody/-/messages')
    for message in messages:
        if message['name'][:21] != 'INDEXER_MISSING_INDEX':
            continue
        if message['name'][22:] not in indexNames:
            continue
        delete_entry(session_key, message['links']['remove'])


if __name__ == '__main__':
    # set up logger to send message to stderr so it will end up in splunkd.log
    sh = logging.StreamHandler()
    # the following line is to make sure the log event looks the same as any other splunkd.log
    sh.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    l = logging.getLogger()
    l.setLevel(logging.INFO)
    l.addHandler(sh)

    #logging.info('HI!')
    try:
        do_the_work()
    except:
        logging.error('Couldn\'t apply index limits!')
        raise
