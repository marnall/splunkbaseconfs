#!/usr/bin/env python3
# Erik de Bueger

import os
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import sys
import time
import datetime
import optparse
try:
    import splunk.entity as entity
    from splunk.clilib import cli_common as cli
except ImportError:
    pass

URL          = 'http://projects.knmi.nl/klimatologie/daggegevens/getdata_dag.cgi'
FIELDS       = 'TG:TN:TX:TXH:T10N:DDVEC:FG:FHX:FX:FHXH:FHVEC:iFHN:iFXXH:SQ:SP:Q:DR:RH:RHX:RHXH:PG:PX:PN:PNH:UG:UX:UXH'
HEADERLINE   = 170
DATASTART    = 172
#YYYMMDD
EARLIESTDATE = '19700101'

# Use Splunk api, Returns (host, url, country)
def getApiDetails(opts):
   myapp = 'Climate'
   try:
       cfg      = cli.getConfStanza('climatesetup','climate_config')
       host     = cfg.get('host')
       url      = cfg.get('url')
       country  = cfg.get('country')
   except NameError:
       host    = opts.host
       url     = opts.url
       country = opts.country
   except Exception as e:
      raise Exception("%s: Could not get host,url,country from splunk. Error: %s"
                     % (myapp, str(e)))
   return((host,url, country))

# Open file containing the last event timestamps per station
def GetLastEvents(strFile) :
    dLastEvents={}
    if os.path.isfile(strFile):
        try:
            fp = open(strFile,'r')
            for strLine in fp:
                k,v = strLine.rstrip().split(',')
                dLastEvents[k]=time.strptime(v, '%Y%m%d')
            fp.close()

        except IOError:
            sys.stderr.write('Error: failed to read last_eventid file, ' + strFile + '\n')
            sys.exit(2)
    else:
        sys.stderr.write('Error: {} not found! Starting from {}. \n'.format(strFile, EARLIESTDATE))
    return(dLastEvents)

# Write new last event timestamps per station
# Dict format: string,date
def WriteLastEvents(strFile, dNewLastEvents):
    try:
        fp = open(strFile,'w')
        for k,v in dNewLastEvents.items() :
            fp.write('{},{}\n'.format(k,time.strftime('%Y%m%d',v)))
        fp.close()
    except IOError:
        sys.stderr.write('Error writing last_eventid to file: ' + strFile + '\n')
        sys.exit(2)

# Main code
def main():
    # Parse command line options
    p = optparse.OptionParser("usage: %prog [options]")
    p.add_option("-t", "--host", dest="host", default='ftp-cdc.dwd.de', \
                     help = 'FTP host for german climate  data extraction, defaults to ftp-cdc.dwd.de')
    p.add_option("-u", "--url", dest="url", default=URL, \
                     help = 'url for dutch KNMI data extraction, defaults to: {}'.format(URL))
    p.add_option("-c", "--country", dest="country", default='NL', \
                     help = 'Country: NL or DE')
    opts,args = p.parse_args()
    host,url,country = getApiDetails(opts)
    #sys.stderr.write('Parameters: host {} -- url {} -- country {}\n'.format(host,url,country))
    strNow= datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d')

    try:
        data     = urllib.parse.urlencode({'start' : EARLIESTDATE, 'end' : strNow, 'vars': FIELDS, 'stns':'ALL'})
        req      = urllib.request.Request(url, data.encode('utf-8'))
        response = urllib.request.urlopen(req)
    except Exception as e:
        sys.stderr.write(str(e)+'\n')
        sys.stderr.write('URL Fetch Connection Error!\n')
        sys.exit(2)

    dLastEvents=GetLastEvents(os.path.join(sys.path[0],'lastnlevent'))
    dNewLastEvents=dLastEvents.copy()
    line=0
    for strLine in response :
        # strLine is bytes type
        line=line+1
        # Ignore all header lines
        if line >=DATASTART :
            # Extract date for optimisation for indexing later
            lColumns=strLine.lstrip().rstrip().split(b',')
            # Second column contains date, turn into date object
            lineTime=time.strptime(lColumns[1].decode('utf-8'), '%Y%m%d')

            # First column contains the station number
            # Find last known event from that station, and make sure strTheStation is string type
            strTheStation = lColumns[0].lstrip().rstrip().decode('utf-8')
            try :
                lastEventTime = dLastEvents[strTheStation]
            except KeyError:
                lastEventTime = time.strptime(EARLIESTDATE, '%Y%m%d')

            # Ignore events before last seen event for the station
            if lineTime > lastEventTime:
                dNewLastEvents[strTheStation]=lineTime
                # timestamp the returned data
                indexTime = time.strftime('%m/%d/%Y %H:%M:%S',lineTime)
                # strip spaces from the received columns
                fCols=[]
                for x in lColumns:
                    fCols.append(x.lstrip().rstrip().decode('utf-8'))
                lFieldNames=['STN','YYYYMMDD']+FIELDS.split(':')
                dFormat=dict(list(zip(lFieldNames,fCols)))
                # Manually add Country field
                dFormat['Country']='NL'
                lFieldNames.append('Country')
                strFormat='{0:s} '.format(indexTime)
                for x in lFieldNames : strFormat+=',{0:s}={{{1:s}}}'.format(x,x)
                sys.stdout.write(strFormat.format(**dFormat)+'\n')
    WriteLastEvents(os.path.join(sys.path[0],'lastnlevent'), dNewLastEvents)

if __name__ == '__main__':
    main()
