#!/usr/bin/env python 

import os
import urllib
import urllib2
import sys
import time
import datetime

strNow= datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d')

URL          = 'http://projects.knmi.nl/klimatologie/daggegevens/getdata_dag.cgi'
FIELDS       = 'TG:TN:TX:TXH:T10N:DDVEC:FG:FHX:FX:FHXH:FHVEC:iFHN:iFXXH:SQ:SP:Q:DR:RH:RHX:RHXH:PG:PX:PN:PNH:UG:UX:UXH'
HEADERLINE   = 170
DATASTART    = 172
#YYYMMDD
EARLIESTDATE = '19720101'

last_eventid_filepath = os.path.join(sys.path[0],'lastnlevent')

# Open file containing the last event timestamps per station
dLastEvents={}
if os.path.isfile(last_eventid_filepath):
    try:
        fp = open(last_eventid_filepath,'r')
        for strLine in fp:
            k,v = strLine.rstrip().split(',')
            dLastEvents[k]=time.strptime(v, '%Y%m%d')
        fp.close()

    except IOError:
        sys.stderr.write('Error: failed to read last_eventid file, ' + last_eventid_filepath + '\n')
        sys.exit(2)
else:
    sys.stderr.write('Error: {} not found! Starting from {}. \n'.format(last_eventid_filepath, EARLIESTDATE))

try:
    data     = urllib.urlencode({'start' : EARLIESTDATE, 'end' : strNow, 'vars': FIELDS, 'stns':'ALL'})
    req      = urllib2.Request(URL, data)
    response = urllib2.urlopen(req)

    dNewLastEvents=dLastEvents.copy()
    line=0
    for strLine in response :
        line=line+1
        # Ignore all header lines
        if line >=DATASTART :
            # Extract date for optimisation for indexing later
            lColumns=strLine.lstrip().rstrip().split(',')
            # Second column contains date, turn into date object
            lineTime=time.strptime(lColumns[1], '%Y%m%d')

            # First column contains the station number
            # Find last known event from that station
            strTheStation = lColumns[0].lstrip().rstrip()
            try :
                lastEventTime = dLastEvents[strTheStation]
            except:
                lastEventTime = time.strptime(EARLIESTDATE, '%Y%m%d')

            # Ignore events before last seen event for the station
            if lineTime > lastEventTime:
                dNewLastEvents[strTheStation]=lineTime
                # timestamp the returned data
                indexTime = time.strftime('%m/%d/%Y %H:%M:%S',lineTime)
                # strip spaces from the received columns
                fCols=[]
                for x in lColumns:
                    fCols.append(x.lstrip().rstrip())
                lFieldNames=['STN','YYYYMMDD']+FIELDS.split(':')
                dFormat=dict(zip(lFieldNames,fCols))
                # Manually add Country field
                dFormat['Country']='NL'
                strFormat='{0:s} '.format(indexTime)
                for x in lFieldNames : strFormat+=',{0:s}={{{1:s}}}'.format(x,x)
                sys.stdout.write(strFormat.format(**dFormat)+'\n')
except Exception,e:
    sys.stderr.write(str(e)+'\n')
    sys.stderr.write('URL Fetch Connection Error!\n')
    sys.exit(2)
    
# Write new last event timestamps per station
try:
    fp = open(last_eventid_filepath,'w')
    for k,v in dNewLastEvents.iteritems() :
        fp.write('{},{}\n'.format(k,time.strftime('%Y%m%d',v)))
    fp.close()
except IOError:
    sys.stderr.write('Error writing last_eventid to file: ' + last_eventid_filepath + '\n')
    sys.exit(2)
