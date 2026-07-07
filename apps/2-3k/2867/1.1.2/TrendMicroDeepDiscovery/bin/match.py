import csv
import sys
import splunk.Intersplunk as si
import logging as logger
import string
import os
import time
import re
import hashlib
import datetime
from sets import Set
from logging import handlers

import logging.config
logging.config.fileConfig(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "default", "log.ini"))
logger = logging.getLogger('deepdiscovery')


def search_url(url, port, cclist_ip, cclist_domain, pat):
    if pat.match(url):
        if url in cclist_ip:
            if port in cclist_ip.get(url):
                return url
    else:
        if url in cclist_domain:
            if port in cclist_domain.get(url):
                return url

def parseTodict(line):
    L = []
    L = line.split(",")
    ip = L[0]
    domain = L[1]
    ports = L[2:]
    return ip,domain,ports

def match(proxylog, settings):
    try:
        keywords, argvals = si.getKeywordsAndOptions()
        me = os.path.dirname(os.path.realpath(__file__))
        f = open(os.path.join(me, "..", "lookups", "CCList"), "r")

        cclist_domain = {}
        cclist_ip = {}
        while 1:
            line = f.readline()
            logger.debug("line:%s", line)
            if not line: # i.e. line == EOF
                break
            else:
                ip,domain,ports = parseTodict(line.rstrip())
                if ip != '':
                    cclist_ip.update({ip:Set(ports)})
                if domain != '':
                    cclist_domain.update({domain:Set(ports)})
        f.close()

        local_domain = {}
        local_ip = {}
        f = open(os.path.join(me, "..", "lookups", "local_CCList.csv"), "r")
        while 1:
            line = f.readline()
            logger.debug("line:%s", line)
            if not line: # i.e. line == EOF
                break
            else:
                ip,domain,ports = parseTodict(line.rstrip())
                if ip != '':
                    local_ip.update({ip:Set(ports)})
                if domain != '':
                    local_domain.update({domain:Set(ports)})
        f.close()


        results = []
        pat = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")

        for r in proxylog:
            if 'dest_port' in r.keys():
                p = search_url(hashlib.sha1(r['dest']).hexdigest(), hashlib.sha1(r['dest_port']).hexdigest(), cclist_ip, cclist_domain, pat)
                if p is not None:
                    r.update({'CnC_source':'Global C&C List', 'Correlated':datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 'port':r['dest_port']})
                    results.append(r)
                else:
                    p2 = search_url(r['dest'], r['dest_port'], local_ip, local_domain, pat)
                    if p2 is not None:
                        r.update({'CnC_source':'Virtual Analyzer', 'Correlated':datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 'port':r['dest_port']})
                        results.append(r)

            else:
                dest = r['dest'].split(":")
                p = search_url(hashlib.sha1(dest[0]).hexdigest(), hashlib.sha1(dest[1]).hexdigest() if len(dest)==2 else hashlib.sha1('80').hexdigest(), cclist_ip, cclist_domain, pat)
                if p is not None:
                    r.update({'CnC_source':'Global C&C List', 'Correlated':datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 'port':dest[1] if len(dest)==2 else '80'})
                    results.append(r)
                else:
                    p2 = search_url(dest[0], dest[1] if len(dest)==2 else '80', local_ip, local_domain, pat)
                    if p2 is not None:
                        r.update({'CnC_source':'Virtual Analyzer', 'Correlated':datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 'port':dest[1] if len(dest)==2 else '80'})
                        results.append(r)


    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        results = si.generateErrorResults(str(e) + ". Traceback: " + str(stack))
        logger.error(str(e) + ". Traceback: " + str(stack))
    return results

if __name__ == '__main__':
    results, dummyresults, settings = si.getOrganizedResults()
    join_results = match(results, settings)
    si.outputResults(join_results)

