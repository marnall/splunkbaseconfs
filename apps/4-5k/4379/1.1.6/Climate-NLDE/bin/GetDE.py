#!/usr/bin/env python3
# Erik de Bueger

import os
import re
import sys
import csv
import time
import datetime
from ftplib import FTP
import zipfile
import threading
import queue
import io
import optparse
try:
    import splunk.entity as entity
    from splunk.clilib import cli_common as cli
except ImportError:
    pass

# IP and HOST FTP Server
IP   = '141.38.3.186'
HOST = 'ftp-cdc.dwd.de'
HOST = 'opendata.dwd.de'

# Directory on FTP-Server
FILEDIR           = '/climate_environment/CDC/observations_germany/climate/daily/kl/recent/'
FILEDIRHISTORICAL = '/pub/CDC/observations_germany/climate/daily/kl/historical/'
# Station information
STATIONS_FILE     = 'KL_Tageswerte_Beschreibung_Stationen.txt'
FILE_SELECTOR     = re.compile('produkt_klima_tag_([0-9]{8})_([0-9]{8})_([0-9]+)\.txt')
ARCHIV_MEMBER     = 'produkt_klima_Tageswerte'
ENCODING          = 'iso-8859-1'
#YYYMMDD
EARLIESTDATE      = '20000101'
NUMFTPTHREADS     = 4

#Stations_id von_datum bis_datum Stationshoehe geoBreite geoLaenge Stationsname Bundesland
#----------- --------- --------- ------------- --------- --------- ----------------------------------------- ----------
#00001 19370101 19860630            478     47.8413    8.8493 Aach                                     Baden-Wurttemberg                                                                                 
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
       url     = HOST
       country = opts.country
   except Exception as e:
      raise Exception("%s: Could not get host,url,country from splunk. Error: %s"
                     % (myapp, str(e)))
   return((host,url, country))

# Returns dict with key=station name and value= dict with station info, and last known event date added to dict
def ReadStations(fp, dLastEvents) :
    # First two lines are header lines
    dStations={}
    lKeys=[]
    i=0
    for strLine in fp:
        # Turn strLine into unicode to support extended ascii
        strLine=strLine.decode(encoding='iso-8859-1')
        if i == 0 :
            # Header line
            i+=1
            lKeys=strLine.rstrip('\n').split()
            continue
        elif i ==1 :
            i+=1
            continue
        l=strLine.rstrip('\n').split()
        data=l[:6]
        land=l[-1]
        stationName=' '.join(l[6:-1])
        dStations[stationName]= dict(list(zip(lKeys, l)))
        # Insert Country field
        dStations[stationName]['Country']='DE'
        try :
            dStations[stationName]['LastDate'] = dLastEvents[int(l[0])]
        except:
            dStations[stationName]['LastDate'] = datetime.datetime.strptime(EARLIESTDATE, '%Y%m%d').date()
        dStations[int(l[0])]=dStations[stationName]
    return(dStations)

# For debugging purposes
def WriteStations(d, fp) :
    # write types
    for k,v in d.items() :
        fp.write('Type of key: {!r}\n'.format(k))
        for x,y in v.items() :
            fp.write('Type of value: {!r}\n'.format(y))
    for k,v in d.items() :
        strFormat = ','.join('{}={}'.format(x,y) for (x,y) in list(v.items()))+'\n'
        fp.write(strFormat.encode(encoding='iso-8859-1'))
        fp.write(strFormat.encode(encoding='utf-8'))
        # qOut.put((strFormat+'\n', int(v['Stations_id']), None))
    qOut.put(('STOP', -1,{}))

# Open file containing the last event timestamps per station
def GetLastEvents(strFile) :
    dLastEvents={}
    if os.path.isfile(strFile):
        try:
            fp = open(strFile,'r')
            for strLine in fp:
                k,v = strLine.rstrip().split(',')
                dLastEvents[int(k)]=datetime.datetime.strptime(v, '%Y%m%d').date()
            fp.close()
        except Exception as e:
            sys.stderr.write(str(e)+'\n')
            sys.stderr.write('Error: failed to read or understand last_eventid file, ' + strFile + '\n')
            sys.exit(2)
    else:
        sys.stderr.write('Error: {} not found! Starting from {}. \n'.format(strFile, EARLIESTDATE))
    return(dLastEvents)

def WriteLastEvents(strFile, dStations):
    try:
        fp = open(strFile,'w')
        # stations dict has keys as strings and keys as ints (station ID), go for the ints
        for k,v in dStations.items() :
            if type(k) == type(2) :
                fp.write('{},{}\n'.format(k,v['LastDate'].strftime('%Y%m%d')))
        fp.close()
    except Exception as e:
        sys.stderr.write(str(e)+'\n')
        sys.stderr.write('Error writing last_eventid to file: ' + strFile + '\n')

#Stations_id von_datum bis_datum Stationshoehe geoBreite geoLaenge Stationsname Bundesland
#STATIONS_ID;MESS_DATUM;QN_3;  FX;  FM;QN_4; RSK;RSKF; SDK;SHK_TAG;  NM; VPM;  PM; TMK; UPM; TXK; TNK; TGK;eor
#         44;20160104;-999;-999;-999;    3;   0.5;   4;    0.000;   1;  -999;   3.8;    -999;   -5.4;   91.54;   -4.0;   -6.0;   -5.8;eor
def WriteToSplunk(qOut, lEvents, dStation):
    if lEvents==None:
        return
    try:
        lastDate=dStation['LastDate']
    except:
        lastDate = datetime.datetime.strptime(EARLIESTDATE, '%Y%m%d').date()
    for x in lEvents:
        theDate=datetime.datetime.strptime(x['MESS_DATUM'], '%Y%m%d').date()
        if theDate > lastDate:
            lastDate=theDate
            # Sanitize kv pairs, ignore values -999
            for k,v in list(x.items()):
                if v.lstrip()=='-999':
                    x.pop(k)
            # Insert station name as well as other station fields, since we have it anyway
            x.update(dStation)
            x.pop('LastDate')
            indexTime = theDate.strftime('%m/%d/%Y %H:%M:%S')
            strFormat='{0:s} '.format(indexTime)
            strFormat += ','.join('{}={}'.format(k.lstrip(),v.lstrip()) for (k,v) in list(x.items()))
            qOut.put((strFormat+'\n', int(dStation['Stations_id']), lastDate))

def OutputThread(fp, qOut, dStations) :
    # Get work
    while True:
        try:
            s, nStation, lastDate = qOut.get(True)
        except Exception as e:
            sys.stderr.write(str(e)+'\n')
            sys.stderr.write('Outputthread failed to get job from queue\n')
            return
        if s=='STOP' :
            return
        try:
            fp.write(s)
        except Exception as e:
            sys.stderr.write(str(e)+'\n')
            sys.stderr.write('Outputthread failed to write event for station {0:d}\n'.format(nStation))
            continue
        dStations[nStation]['LastDate']=lastDate

def FTPThread(strHost, qFTP, qOut) :
    try:
        session = FTP(strHost, timeout=60)
        # Anonymous login
        session.login()
    except Exception as e:
        sys.stderr.write(str(e)+'\n')
        sys.stderr.write('FTP connect error to host:\'{0}\'\n'.format(strHost))
        qOut.put(('STOP', -1,{}))
        return
    # Get work
    while True:
        try:
            (strDir, strFile, dStations) = qFTP.get(True)
        except Exception as e:
            sys.stderr.write(str(e)+'\n')
            sys.stderr.write('FTPthread failed to get job from queue for host:{0}\n'.format(strHost))
            session.close()
            qOut.put(('STOP', -1,{}))
            return
        # Check the command they want us to execute
        if strDir == 'STOP' :
            # End the thread
            session.close()
            qOut.put(('STOP', -1,{}))
            return
        # Must be a regular tuple
        # Change Directory and extract zip archive
        session.cwd(strDir)
        fp=io.BytesIO()
        try:
            session.retrbinary('RETR ' + strFile, fp.write)
        except Exception as e:
            sys.stderr.write(str(e)+'\n')
            sys.stderr.write('FTP failed for file {0}\n'.format(strFile))
            session.close()
            qOut.put(('STOP', -1,{}))
            return

        # we now have one zipped archive, and are really interested in the products file only
        nStation, l=ReadZipArchive(fp)
        try:
            WriteToSplunk(qOut, l, dStations[nStation])
        except Exception as e:
            sys.stderr.write(str(e)+'\n')
            sys.stderr.write('Could not write events for file {0}\n'.format(strFile))
    return

# Really interested in the products file only, return tuple: station number, list of event dicts
def ReadZipArchive(fp) :
    zFp=zipfile.ZipFile(fp, 'r')
    for strName in zFp.namelist():
        match=FILE_SELECTOR.search(strName)
        if match:
            try:
                nStation=int(match.group(3))
            except Exception as e:
                sys.stderr.write(str(e)+'\n')
                sys.stderr.write('Could not properly match Station for file {0}\n'.format(strName))
                continue

            # we have the file we want, extract and write to splunk
            fpProduct=io.StringIO((zFp.read(strName)).decode('utf-8'))
            dReader=csv.DictReader(fpProduct, delimiter=';')
            l=[]
            for x in dReader:
                d={}
                for k,v in x.items() :
                    if v.lstrip()!='-999':
                        d[k]=v
                l.append(d)
            # We are done, max one file per zip is it
            return((nStation,l))
        else:
            continue
    return((-1,None))

def ReadFTPDirectory(strHost, strDirPath,strStationsFile,  qFTP, qOut, dLastEvents, bStationsOnly) :
    # Connect to FTP server
    try:
        session = FTP(strHost, timeout=60)
        # Anonymous login
        session.login()
        # Change Directory
        session.cwd(strDirPath)
        # Get stations file
        fp=io.BytesIO()
        s='RETR ' + strStationsFile
        session.retrbinary('RETR ' + strStationsFile, fp.write)
    except Exception as e:
        sys.stderr.write(str(e)+'\n')
        sys.stderr.write('FTP Fetch Error to host:\'{0}\' and file:\'{1}\'!\n'.format(strHost, strStationsFile))
        sys.exit(2)

    fp.seek(0)
    dStations=ReadStations(fp, dLastEvents)
    del fp

    if bStationsOnly:
        for x in range(NUMFTPTHREADS) :
            qFTP.put(('STOP', 'STOP', {}))
        return(dStations)

    # Get list of zip files from ftp site, and put worker threads to work
    for strFile in session.nlst('*.zip') :
        qFTP.put((strDirPath, strFile, dStations))
    session.close()
    # Inform all FTP threads that we are done
    for x in range(NUMFTPTHREADS) :
        qFTP.put(('STOP', 'STOP', {}))
    return(dStations)

def main() :
    # Check if we need to retrieve historical data as opposed to recent data
    p = optparse.OptionParser("usage: %prog [-historical]")
    p.add_option("-o", "--old", dest="historic", action='store_true',\
                     help = 'fetch historic data')
    p.add_option("-t", "--stations", dest="stations", action='store_true',\
                     help = 'fetch only station info')
    p.add_option("-z", "--zipfile", dest="zipfile", action='store_true',\
                     help = 'process only one local zipfile, no ftp interaction')
    p.add_option("-s", "--host", dest="host", default=HOST, \
                     help = 'FTP host for german climate  data extraction, defaults to: {}'.format(HOST))
    p.add_option("-c", "--country", dest="country", default='NL', \
                     help = 'Country: NL or DE')
    opts,args = p.parse_args()
    host,url,country = getApiDetails(opts)

    # Debugging option, only process local zipfile
    if opts.zipfile:
        fp=open(args[0], 'r')
        nStation, l = ReadZipArchive(fp)
        if l==None:
            sys.stdout.write('No records found\n')
            sys.exit()
        for x in l:
            strFormat = ','.join('{}={}'.format(k.lstrip(),v.lstrip()) for (k,v) in list(x.items()))
            sys.stdout.write(strFormat+'\n')
        fp.close()
        sys.exit()

    # Queues for thread synchronisations
    qOut                  = queue.Queue(0)
    qFTP                  = queue.Queue(0)
    if opts.historic==True:
        last_eventid_filepath = os.path.join(sys.path[0],'lastolddeevent')
        strPath=FILEDIRHISTORICAL
    else :
        last_eventid_filepath = os.path.join(sys.path[0],'lastdeevent')
        strPath=FILEDIR
    dLastEvents           = GetLastEvents(last_eventid_filepath)
    dStations             = ReadFTPDirectory(host, strPath, STATIONS_FILE, qFTP, qOut, dLastEvents, opts.stations)

    if opts.stations :
        WriteStations(dStations, sys.stdout)

    # Create Threads
    outThread             = threading.Thread(target=OutputThread, args=(sys.stdout, qOut, dStations))
    lFTP                  = []
    # Multiple FTP threads to avoid long execution time
    for x in range(NUMFTPTHREADS) :
        lFTP.append(threading.Thread(target=FTPThread, args=(host, qFTP, qOut)))
    # Start the threads
    for t in lFTP:
        t.start()
    outThread.start()
    # Wait for theats to finish
    for t in lFTP:
        t.join()
    outThread.join()
    # Remember the most recent event times
    WriteLastEvents(last_eventid_filepath, dStations)
    sys.exit()

if __name__ == '__main__':
    main()
