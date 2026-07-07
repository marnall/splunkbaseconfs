#!/usr/bin/env python

import os
import csv
import sys
import ast
import time
import json
import logging
import logging.handlers
import requests
import datetime

from xml.etree import ElementTree
from ConfigParser import ConfigParser
import splunk.entity as entity

LOG_LEVEL = logging.DEBUG

logger = object()

domains = []
ips     = []

def getAuth():
    app = 'TA-themediatrust'
    global sessionKey
    sessionKey=sys.stdin.readline().strip()
    if len(sessionKey)==0:
	logger.error("we do not have a good session key")
	sys.exit()
    logger.debug("we have a good session key")
    global auth
	
    try:
        entities = entity.getEntities(['admin', 'passwords'], namespace='TA-themediatrust', owner='nobody', sessionKey=sessionKey)

    except Exception, e:
        logger.debug(e)
        raise Exception("Could not get credentials from splunk. ERROR: %s" % e) 
        sys.exit()

    auth = {}

    for i, c in entities.items():
        if c['username'] != 'license_key':
            auth['user'] = c['username']
            auth['pw'] = c['clear_password']
            thislogger.info("user:"+auth['user'])
            return auth

def setup_logging(parser):
    global SPLUNK_HOME, LOG_LEVEL, LOG_FILE_NAME, logger
    if 'SPLUNK_HOME' in os.environ:
        SPLUNK_HOME = os.environ['SPLUNK_HOME']
    else:
        SPLUNK_HOME = parser.get('config','SPLUNK_HOME')

    LOG_FILE_NAME = os.path.join(SPLUNK_HOME,'var','log','splunk',parser.get('config','LOG_FILE_NAME'))

    if os.path.isfile(LOG_FILE_NAME):
	os.remove(LOG_FILE_NAME)

    log_format = "%(asctime)s %(levelname)-s\t%(module)s[%(process)d]:%(lineno)d - %(message)s"
    logger = logging.getLogger('v')

    logLevel = parser.get('config','LOG_LEVEL')

    if logLevel == 'DEBUG':
        LOG_LEVEL = logging.DEBUG
    elif logLevel == 'INFO':
        LOG_LEVEL = logging.INFO
    elif logLevel == 'WARNING':
        LOG_LEVEL = logging.WARNING
    elif logLevel == 'ERROR':
        LOG_LEVEL = logging.ERROR
    elif logLevel == 'CRITICAL':
        LOG_LEVEL = logging.CRITICAL
    else:
        LOG_LEVEL = logging.DEBUG

    logger.setLevel(LOG_LEVEL)

    l = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, LOG_FILE_NAME), mode='a', maxBytes = 1000000, backupCount=2)
    l.setFormatter(logging.Formatter(log_format))
    logger.addHandler(l)

    logger.propagate = False


def config():
    parser = ConfigParser()
    SPLUNK_HOME=os.environ.get('SPLUNK_HOME')
    parser.read(os.path.join(SPLUNK_HOME,'etc','apps','TA-themediatrust','samples','queries.conf'))
    setup_logging(parser)

    return parser


def splCall(host, parser, section_name, spl):

    logger.debug('splCall - query')

    uid = auth['user'] 
    pwd = auth['pw']

    #
    # Submit the search job and get its jobid
    #
    uri = 'https://' + host + ':8089/services/search/jobs'
    logger.debug('spl job search uri:' + uri)

    params = {'search': spl}

    response = requests.post(uri, data=params, verify=False, auth=(uid, pwd))
    tree = ElementTree.fromstring(str(response.text))
    node = tree.find('sid')
    if node is None:
        logger.debug(str(response.text))
        return
    else:
        jobid = node.text

    logger.debug('spl search: ' +str(response.text))

    #
    # Query the jobid to get the status
    #
    uri = 'https://' + host + ':8089/services/search/jobs/' + jobid
    logger.debug('spl job id uri:' + uri)

    isNotDone = True
    while isNotDone:
        response = requests.post(uri, verify=False, auth=(uid, pwd))
        tree = ElementTree.fromstring(str(response.text))
        node = tree.find('.//*[@name="isDone"]')
        status = node.text

        if status == '1':
            isNotDone = False
        else:
            time.sleep(1)
            logger.debug('spl job processing, retrying')

    logger.debug('spl job: ' +str(response.text))

    #
    # Submit the search job and get its jobid
    #
    uri = 'https://' + host + ':8089/services/search/jobs/' + jobid + '/results?output_mode=' + parser.get(section_name, 'outputType')
    logger.debug('spl job response uri:' + uri)

    response = requests.get(uri, verify=False, auth=(uid, pwd))
    logger.debug('spl results: ' + str(response.text))

    data = str(response.text).replace("\"","")

    if section_name == 'domain':
        global domains
        domains = data.splitlines()

    if section_name == 'ip':
        global ips
        ips = data.splitlines()

def main(parser):

    for section_name in parser.sections():
        logger.debug('query processing:' + section_name)

        if section_name == 'config':
            continue

	section_file=os.path.join(SPLUNK_HOME,'etc','apps','TA-themediatrust','samples',section_name + '.spl')

	with open(section_file, 'r') as splFile:
            spl = splFile.read().replace('\n', '')

	queryServer = parser.get('config', 'QUERY_SERVER')
	splCall(queryServer, parser, section_name, spl)


if __name__ == '__main__':

    parser = config()

    getAuth()

    logger.debug('**** Start of Run ****')

    outputFile = os.path.join(SPLUNK_HOME,'etc','apps','TA-themediatrust','samples',parser.get('config','OUTPUT_FILE'))

    if os.path.isfile(outputFile):
        os.remove(outputFile)
    
    main(parser)

    template_file=os.path.join(SPLUNK_HOME,'etc','apps','TA-themediatrust','samples','template.log')
    with open(template_file, 'r') as templateFile:
        template = templateFile.read()

    del ips[0]
    del domains[0]

    for ip, domain in zip(ips, domains):
        event = template
        event = event.replace("<DATETIME01>", datetime.datetime.now().strftime("%b  %e %H:%M:%S"))
        event = event.replace("<DATETIME02>", datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
        event = event.replace("<IP>", ip)
        event = event.replace("<DOMAIN>", domain)

        with open(outputFile, "a") as myfile:
            myfile.writelines(event + "\n")

    logger.debug('**** End of Run ****')

    sys.exit()

