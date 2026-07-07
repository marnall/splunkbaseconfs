#!/usr/bin/env python 

import os
import urllib
import urllib2
import sys
import time
import datetime
import base64
import json
import optparse
try:
    import splunk.entity as entity
    from splunk.clilib import cli_common as cli
    undersplunk=True
except ImportError:
    undersplunk=False

#%Y-%m-%d HH:MM
EARLIESTDATE = '2017-01-31 00:00'
HOST         = 'beeclear'
MAPPINGS     = {'verbl':'POWERLT', 'verb':'POWER'}

# access the credentials in /servicesNS/nobody/<YourApp>/storage/passwords
def getCredentials(sessionKey, opts):
    myapp = 'BeeClear'
    try:
        # list all credentials
        entities = entity.getEntities(['admin', 'passwords'], namespace=myapp, 
                                      owner='nobody', sessionKey=sessionKey) 
    except NameError:
        # Not under Splunk
        pass
    except Exception as e:
        raise Exception("Could not get %s credentials from splunk. Error: %s" 
                        % (myapp, str(e)))

    # return LAST set of credentials
    try:
        for i, c in entities.items(): 
            #sys.stderr.write('Credentials: {} -- {}\n'.format(repr(i), repr(c)))
            user=c['username']
            passw=c['clear_password']
            return((user,passw))
    except:
        user   = opts.user
        passw  = opts.password
    return((user,passw))

def getApiDetails(opts):
   myapp = 'BeeClear'
   try:
       cfg       = cli.getConfStanza('beeclearsetup','beeclear_config')
       host      = cfg.get('host')
       country   = cfg.get('country')
   except NameError:
       host      = opts.host
       country   = opts.country
   except Exception as e:
      raise Exception("%s: Could not get details from splunk. Error: %s"
                     % (myapp, str(e)))
   return((host, country))

class beeclear:

    def __init__( self, hostname, user, passwd ):
        self.hostname = hostname
        self.user     = user
        self.passwd   = passwd
        self.cookie   = None;

    def connect( self ):
        post_args   = urllib.urlencode( { 'username': base64.b64encode(self.user), 'password': base64.b64encode(self.passwd) } )
        url         = 'http://' + self.hostname + '/bc_login?' + post_args;
        req1        = urllib2.Request(url)
        response    = urllib2.urlopen(req1)
        self.cookie = response.headers.get('Set-Cookie')

    # lParams is list of tuples
    def send( self, command, lParams):
        url = 'http://%(host)s/%(command)s?%(params)s' %{'host':self.hostname,'command':command, 'params':urllib.urlencode(lParams) }
        req = urllib2.Request(url)
        req.add_header('cookie', self.cookie)
        f = urllib2.urlopen(req)
        dReturn = json.load(f)
        f.close()
        return dReturn

    # Collect per day from start till end day
    # Returns last send day
    def CollectAndSend(self, strType, startTime, endTime, fp) :
        returnDate=None
        while startTime.date() < endTime.date() :
            lParams=[('date', int(time.mktime(startTime.timetuple()))),('duration', 'day'), ('period', 'day'), ('type', strType)]
            x= self.send('bc_getVal', lParams)

            self.ChangeTime(x, ['time','start','end'])
            self.MapKeys(x, MAPPINGS)
            l=self.FindKey(x,'val')
            if l == None:
                startTime=startTime+datetime.timedelta(days=1)
                continue
            for p in l:
                theDate=datetime.datetime.strptime(p['time'], '%Y-%m-%d %H:%M:%S')
                if theDate.date() == startTime.date():
                    returnDate=startTime
                    p.pop('time')
                    indexTime = theDate.strftime('%m/%d/%Y %H:%M:%S')
                    strFormat='{0:s} '.format(indexTime)
                    strFormat += ','.join("{!s}={!r}".format(k.upper(),v/1000) for (k,v) in p.items())
                    fp.write(strFormat+'\n')
            startTime=startTime+datetime.timedelta(days=1)
        return returnDate

    # Change the time representation in the returned json style dict from unix time to readable format
    # obj is the iterable object, lookup_keys is the list of key values to look for
    def ChangeTime(self, obj, lookup_keys):
        if isinstance(obj, dict):
            for k, v in obj.iteritems():
                if k in lookup_keys:
                    obj[k]=datetime.datetime.fromtimestamp(int(v)).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    self.ChangeTime(v, lookup_keys)
        elif isinstance(obj, list):
            for item in obj:
                self.ChangeTime(item, lookup_keys)
        else :
            pass

    # Map keys to new values
    # obj is the iterable object, dMap is the dict with key mappings
    def MapKeys(self, obj, dMap):
        if isinstance(obj, dict):
            for k, v in obj.iteritems():
                if k in dMap:
                    obj[dMap[k]]=obj[k]
                    obj.pop(k)
                else:
                    self.MapKeys(v, dMap)
        elif isinstance(obj, list):
            for item in obj:
                self.MapKeys(item, dMap)
        else :
            pass

    # obj is an iterable object: dict or list, retValue is return Value in case there is a match, initially None
    def FindKey(self, obj, lookup_key, retValue=None):
        if isinstance(obj, dict):
            for k, v in obj.iteritems():
                if k==lookup_key:
                    return(v)
                else:
                    ret= self.FindKey(v, lookup_key, None)
                    if ret != None:
                        return ret
        elif isinstance(obj, list):
            for item in obj:
                ret=self.FindKey(item, lookup_key, None)
                if ret != None:
                    return ret
        else :
            if obj==lookup_key :
                return retValue

def main() :
    # Parse command line options
    p = optparse.OptionParser("usage: %prog [options]")
    p.add_option("-l", "--log", dest="loglevel", default='WARNING', \
                     help = 'loglevel field, defaults to WARNING, options are: CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET')
    p.add_option("-o", "--host", dest="host", default='beeclear', \
                     help = 'hostname or ip address for beeclear host, defaults to beeclear')
    p.add_option("-u", "--user", dest="user", default='beeclear', \
                     help = 'user name, defaults to beeclear')
    p.add_option("-p", "--password", dest="password", default='password', \
                     help = 'beeclear password')
    p.add_option("-c", "--country", dest="country", default='NL', \
                     help = 'NL or DE')
    opts,args = p.parse_args()
    last_eventid_filepath = os.path.join(sys.path[0],'lastbcevent')

    # Open file containing the last event timestamp
    # Format = type,day e.g.: gas,20170119
    dLastEvents={}
    if os.path.isfile(last_eventid_filepath):
        try:
            fp = open(last_eventid_filepath,'r')
            for strLine in fp:
                k,v = strLine.rstrip().split(',')
                dLastEvents[k]=datetime.datetime.strptime(v, '%Y%m%d')
            fp.close()

        except IOError:
            sys.stderr.write('BeeClear Error: failed to read last_eventid file, ' + last_eventid_filepath + '\n')
            sys.exit(2)
    else:
        sys.stderr.write('BeeClear Warning: {} not found! Starting from {}. \n'.format(last_eventid_filepath, EARLIESTDATE))

    try:
        sessionKey = 'hello'
        if undersplunk == True:
            # read session key sent from splunkd
            sessionKey = sys.stdin.readline().strip()

        if len(sessionKey) == 0:
           sys.stderr.write("BeeClear: Did not receive a session key from splunkd. " + 
                            "Please enable passAuth in inputs.conf for this " +
                            "script\n")
           sys.exit(2)

        # now get credentials - might exit if no creds are available 
        user, passwd = getCredentials(sessionKey,opts)
        host,country = getApiDetails(opts)
        bc = beeclear(host, user, passwd)
        bc.connect()
    except Exception as e:
        sys.stderr.write(str(e)+'\n')
        sys.stderr.write('BeeClear Connection Error to host {}!\n'.format(host))
        sys.exit(2)

    # Starting date for event collection for GAS consumption
    try :
        lastEventTime = dLastEvents['gas']
        lastEventTime = lastEventTime+datetime.timedelta(days=1)
        lastEventTime=lastEventTime+datetime.timedelta(hours=23)
        lastEventTime=lastEventTime+datetime.timedelta(minutes=59)
    except:
        lastEventTime = datetime.datetime.strptime(EARLIESTDATE, '%Y-%m-%d %H:%M')
        lastEventTime=lastEventTime+datetime.timedelta(hours=23)
        lastEventTime=lastEventTime+datetime.timedelta(minutes=59)
    endTime= datetime.datetime.now()

    try:
        dt = bc.CollectAndSend('gas', lastEventTime, endTime, sys.stdout)
        if dt:
            dLastEvents['gas'] = dt
    except Exception as e:
        sys.stderr.write(str(e)+'\n')
        sys.stderr.write('BeeClear Collection Error!\n')
        sys.exit(2)

    # Starting date for event collection for power consumption
    try :
        lastEventTime = dLastEvents['power']
        lastEventTime = lastEventTime+datetime.timedelta(days=1)
        lastEventTime=lastEventTime+datetime.timedelta(hours=23)
        lastEventTime=lastEventTime+datetime.timedelta(minutes=59)
    except:
        lastEventTime = datetime.datetime.strptime(EARLIESTDATE, '%Y-%m-%d %H:%M')
        lastEventTime=lastEventTime+datetime.timedelta(hours=23)
        lastEventTime=lastEventTime+datetime.timedelta(minutes=59)
    endTime= datetime.datetime.now()

    try:
        dt = bc.CollectAndSend('elek', lastEventTime, endTime, sys.stdout)
        if dt:
            dLastEvents['power'] = dt
    except Exception as e:
        sys.stderr.write(str(e)+'\n')
        sys.stderr.write('BeeClear Collection Error!\n')
        sys.exit(2)

    # Write new last event timestamps per type
    try:
        fp = open(last_eventid_filepath,'w')
        for k,v in dLastEvents.iteritems() :
            fp.write('{},{}\n'.format(k,v.strftime('%Y%m%d')))
        fp.close()
    except IOError:
        sys.stderr.write('Error writing last_eventid to file: ' + strPath + '\n')
        sys.exit(2)

if __name__ == '__main__':
    main()
