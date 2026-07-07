# ==============================================================================
# Copyright 2012-2019 Scianta Analytics LLC All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import six.moves.urllib.request, six.moves.urllib.parse, six.moves.urllib.error
import fnmatch
import os
import platform
import time
import re
import csv
import sys
from time import sleep
from xml.dom import minidom
import json
import xmltodict
import splunk.Intersplunk as si
from xml.dom.minidom import parseString
import splunk.rest
import logging as logger
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','victorops_search.log'),
     filemode='a')

def getSettings(input_buf):

    settings = {}
    # get the header info
    input_buf = sys.stdin
    # until we get a blank line, read "attr:val" lines, setting the values in 'settings'
    attr = last_attr = None
    while True:
        line = input_buf.readline()
        line = line[:-1] # remove lastcharacter(newline)
        if len(line) == 0:
            break

        colon = line.find(':')
        if colon < 0:
            if last_attr:
               settings[attr] = settings[attr] + '\n' + six.moves.urllib.parse.unquote(line)
            else:
               continue

        # extract it and set value in settings
        last_attr = attr = line[:colon]
        val  = six.moves.urllib.parse.unquote(line[colon+1:])
        settings[attr] = val

    return(settings)

if __name__ == '__main__':
    try:
        type = ''
        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                type = arg.lower()
        else:
            raise Exception('victorops_search-F-001: Usage: |vosearch INCIDENTS|USERS|ONCALL|TEAMS')

        # get user
        settings = getSettings(sys.stdin)
        #logger.info("settings")
        #logger.info(settings)
        authString = settings['authString'];
        p = re.compile('<username>(.*)\<\/username>')
        user= p.search(authString).group(1)

        # retrieve earliest and latest
        infoPath= settings['infoPath']
        f_obj = open(infoPath, "r")
        reader = csv.reader(f_obj, quoting=csv.QUOTE_NONE)
        header = next(reader)
        logger.info(header)

        et_idx = -1
        lt_idx = -1
        earliest = "0"
        latest = "now"
        for idx,col in enumerate(header):
            #test = header[idx]
            #logger.info("test="+test)
            if col  == '"_search_et"' :
                logger.info("Found ET at idx: " + str(idx))
                et_idx = idx
            elif col == '"_search_lt"' :
                logger.info("Found LT at idx: " + str(idx))
                lt_idx = idx

        row = next(reader)
        logger.info(row)

        if et_idx != -1:
            earliest = six.moves.urllib.parse.unquote(row[et_idx])
        if lt_idx != -1:
            latest = six.moves.urllib.parse.unquote(row[lt_idx])
        logger.info("earliest=" + earliest)
        logger.info("latest=" + latest)

        f_obj.close();

        sourcetype = ''
        index = ''
        if type == 'incidents':
            endpoint = '/servicesNS/nobody/TA-splunk-add-on-for-victorops/ta_victorops_victorops_incidents'
            response, content = splunk.rest.simpleRequest(endpoint, method='GET', sessionKey=settings['sessionKey'], raiseAllErrors=False)
            doc = minidom.parseString(content)
            keys=doc.getElementsByTagName('s:key')
            for n in keys:
                if n.getAttribute('name') == 'index':
                    index = n.childNodes[0].nodeValue
                elif n.getAttribute('name') == 'sourcetype':
                    sourcetype= n.childNodes[0].nodeValue

        elif type == 'oncall':
            endpoint = '/servicesNS/nobody/TA-splunk-add-on-for-victorops/ta_victorops_victorops_oncall'
            response, content = splunk.rest.simpleRequest(endpoint, method='GET', sessionKey=settings['sessionKey'], raiseAllErrors=False)
            doc = minidom.parseString(content)
            keys=doc.getElementsByTagName('s:key')
            for n in keys:
                if n.getAttribute('name') == 'index':
                    index = n.childNodes[0].nodeValue
                elif n.getAttribute('name') == 'sourcetype':
                    sourcetype= n.childNodes[0].nodeValue
        elif type == 'teams':
            endpoint = '/servicesNS/nobody/TA-splunk-add-on-for-victorops/ta_victorops_victorops_teams'
            response, content = splunk.rest.simpleRequest(endpoint, method='GET', sessionKey=settings['sessionKey'], raiseAllErrors=False)
            doc = minidom.parseString(content)
            keys=doc.getElementsByTagName('s:key')
            for n in keys:
                if n.getAttribute('name') == 'index':
                    index = n.childNodes[0].nodeValue
                elif n.getAttribute('name') == 'sourcetype':
                    sourcetype= n.childNodes[0].nodeValue
        elif type == 'users':
            endpoint = '/servicesNS/nobody/TA-splunk-add-on-for-victorops/ta_victorops_victorops_user'
            response, content = splunk.rest.simpleRequest(endpoint, method='GET', sessionKey=settings['sessionKey'], raiseAllErrors=False)
            doc = minidom.parseString(content)
            keys=doc.getElementsByTagName('s:key')
            for n in keys:
                if n.getAttribute('name') == 'index':
                    index = n.childNodes[0].nodeValue
                elif n.getAttribute('name') == 'sourcetype':
                    sourcetype= n.childNodes[0].nodeValue
        else:
            raise Exception('victorops_search-F-001: Usage: |vosearch INCIDENTS|USERS|ONCALL|TEAMS')

        searchString = "search index="+index+" sourcetype="+sourcetype+" earliest="+earliest+" latest="+latest
        logger.info("searchString="+searchString)

        endpoint = '/services/search/v2/jobs'
        postArgs = {'search':searchString}
        response, content = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=settings['sessionKey'], raiseAllErrors=False, postargs=postArgs)
        logger.info(response)
        logger.info(content)

        sid = minidom.parseString(content).getElementsByTagName('sid')[0].childNodes[0].nodeValue
        if response.status != 201:
            logger.info('victorops_search - (' + type + ') FAILURE retrieving events')
        else:
            logger.info('victorops_search - sid=' + sid)
            endpoint = '/services/search/v2/jobs/%s' % sid
            notDone = True
            while notDone:
                response, content = splunk.rest.simpleRequest(endpoint, method='GET', sessionKey=settings['sessionKey'], raiseAllErrors=False)
                notDoneStatus = re.compile(b'isDone">(0|1)')
                notDoneStatus = notDoneStatus.search(content).groups()[0]
                logger.info('victorops_search - notDoneStatus=' + str(notDoneStatus))
                if notDoneStatus == b'1' :
                    notDone = False

            logger.info('victorops_search - (' + type + ') Search Finished')
            sleep(1)

            #endpoint = '/services/search/jobs/%s/results' % sid
            endpoint = '/services/search/v2/jobs/%s/results?output_mode=json' % sid
            response, content = splunk.rest.simpleRequest(endpoint, method='GET', sessionKey=settings['sessionKey'], raiseAllErrors=False)
            logger.info('victorops_search - response=' + str(response))
            logger.info(content)

            results,dummy,settings = splunk.Intersplunk.getOrganizedResults()
            #logger.info(results)
            searchResults = json.loads(content)
            for result in searchResults['results']: 
                logger.info("PROCESS ROW")
                row = {}
                for item in result:
                    logger.info("PROCESS TOP LEVEL FIELD")
                    logger.info(item + ': %s' % result[item])
                    if item in row:
                        logger.info("ALREADY EXISTS IN DICT")
                        row[item] = result[item]+"\n"+row[item]
                    else:
                        row[item] = result[item]
                        #tmp = str(result[item]) + '\r' + str(result[item])
                        #tmp = [result[item],result[item]]
                        #row.update({item : tmp})
                        #row[item] = {result[item],result[item]}

                        #row[item] = []
                        #row[item].append(result[item])
                        #row[item].append(result[item])
                        #row[item] = str(result[item]) + '\r' + str(result[item])

                        #tmp = [result[item]]
                        #tmp.append(result[item])
                        #row[item] = tmp
                        #row[item].append(result[item])
                    #logger.info("row["+item+"]: " + row[item])
                    logger.info(row[item])

                    if item == "_raw":
                        logger.info("PROCESS RAW")
                        tmp = json.loads(result[item])
                        for field in tmp:
                            logger.info("PROCESS RAW FIELD")
                            logger.info(field + ': %s' % tmp[field])
                            #if field in row:
                            #    logger.info("ALREADY EXISTS!!!")
                            #    row[field] = row[field]+"\n"+ tmp[field]
                            #else:
                            #    row[field] = tmp[field]
                    
                logger.info(row)
                results.append(row)

            splunk.Intersplunk.outputResults(results)

    except Exception as e:
        si.generateErrorResults(e)

