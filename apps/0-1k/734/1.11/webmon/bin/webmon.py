# Copyright (C) 2005-2008 Splunk Inc.  All Rights Reserved.  Version 3.0
import getopt, sys, imaplib, os, urllib2, urlparse, httplib, gzip, hashlib, \
        cStringIO, time, signal
from time import gmtime, strftime
import splunk.clilib.cli_common as comm
import threading
from threading import Thread



PINGEE_CONFIGURATION_OPTIONS = (
    ('userAgent', 'Splunk webmon bundle', 'User-Agent header to use when making requests'),
    ('indexResults', False, 'Dump page contents'),
    ('indexMD5', True, 'Create an MD5 of URL contents'),
    ('timeout', 10, 'Network timeout'),
    ('sleep', 10, 'Time between calss'),
    ('setSourceType', True, 'Force the sourcetype wto webping'),
    ('username', "", 'Basic auth'),
    ('password', "", 'Basic auth password'),
)


splunk_home = os.getenv('SPLUNK_HOME')
if not splunk_home:
    raise ConfigError('Environment variable SPLUNK_HOME must be set')

# path to the confguration conf file
scriptDir = sys.path[0] # find it relative to getimap.py file
configDefaultFileName = os.path.join(scriptDir,'..','default','urls.conf')
configLocalFileName = os.path.join(scriptDir,'..','local','urls.conf')

VERSION = 1.11

print_rlock = threading.RLock()



def handler(signum, frame):
    print 'Signal handler called with signal', signum
    raise IOError("Couldn't open device!")


class Pingee(Thread):

    def __init__(self, name, url):
        Thread.__init__(self)
        self.name = name
        self.url = url
        self.config = {}
        self.result = {}
        self.done = False

    def run(self):
        while not self.done:
            if urlparse.urlparse(self.url)[0] not in ('http', 'https'):
                self.result['status'] = 'non-HTTP URLs not supported'
                self.done = True

            request = urllib2.Request(self.url)

            request.add_header('User-Agent', self.config['userAgent'])
            request.add_header('Accept-Encoding', 'gzip')

#            if etag:
#                    headers.append(('If-None-Match', etag))
#            if lastmodified:
#                    headers.append(('If-Modified-Since', lastmodified))

 



            # Begin timing
            startTime = time.time()

            try:
                if self.config['username'] != "" and self.config['password'] != "":
                    password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
                    password_mgr.add_password(None, self.url, self.config['username'], self.config['password'])
                    handler = urllib2.HTTPBasicAuthHandler(password_mgr)
                    opener = urllib2.build_opener(handler)
                else:
                    opener = urllib2.build_opener(SmartRedirectHandler(), DefaultErrorHandler())
                fp = opener.open(request)
            except urllib2.URLError, e:
                self.result['status'] = 'Connection failed while trying to ping URL - %s' % e  
                time.sleep(self.config['sleep']) 
                continue

            self.result['data'] = fp.read()

            # End timing and calculate time in ms
            endTime = time.time()
            totalTime = (endTime - startTime)*1000
            self.result['pingTime'] = int(totalTime)
 
            if hasattr(fp, 'headers'):
                    self.result['etag'] = fp.headers.get('ETag')
                    self.result['lastmodified'] = fp.headers.get('Last-Modified')
                    if fp.headers.get('Content-Encoding', '') == 'gzip':
                            # data came back gzip-compressed, decompress it
                            # corrected call to StringIO - Jimmy J - 08/14/2008
                            self.result['data'] = gzip.GzipFile(fileobj=cStringIO.StringIO(self.result['data'])).read()

            if hasattr(fp, 'status'):
                self.result['status'] = fp.status
            else:
                self.result['status'] = '200'

            fp.close()
            
            with print_rlock:
                self.printOutput()

            time.sleep(self.config['sleep']) 


    def printOutput(self):
         if self.url:

            if self.config['setSourceType']:
                print "***SPLUNK*** source="+self.url
                print "WebMonProcessor"

            print strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime()) + '  ping_name ="' + self.name + '"'
            print "ping_url =", self.url

            if self.result.has_key('pingTime'):
                #print "time_in_ms =", self.result.get('pingTime')
                print "time_in_sec =", self.result.get('pingTime')/1000.0
            if self.result.has_key('data'):
                print "size_in_bytes =", len(self.result.get('data'))
            print "status_code =", self.result.get('status')

            if (self.config['indexMD5'] and self.result.has_key('data')):
                s = self.result.get('data')
                #checksum = md5.new(s).hexdigest()
                checksum = hashlib.sha224(s).hexdigest()
                print 'ping_md5 =', checksum

            if (self.config['indexResults'] and self.result.has_key('data')):
                s = self.result.get('data')
                print 'contents =\n', s

            print "WebMonProcessor"



class WebMonProcessor(object):
    confStanzas = ""
    URLs = []
    done = False

    #--------------------------------------------------------------
    def __init__(self):
        self.readConfig()

    #--------------------------------------------------------------
    def readConfig(self):

        if os.path.exists(configLocalFileName):
            path = configLocalFileName
        elif os.path.exists(configDefaultFileName):
            path = configDefaultFileName
        else:
            return

        self.confStanzas = comm.readConfFile(path)
        for stanzaName, stanzaContents in self.confStanzas.items():
            u = Pingee(stanzaName, stanzaContents.get('url'))

            for option in PINGEE_CONFIGURATION_OPTIONS:
                optionName = option[0]
                defaultOptionValue = option[1]
                optionValue = stanzaContents.get(optionName, defaultOptionValue)

                if not type(optionValue) is type(defaultOptionValue):
                    # Convert to int
                    if type(defaultOptionValue) is int:
                        optionValue = int(optionValue)

                    # Convert to boolean
                    elif type(defaultOptionValue) is bool:
                        optionValue = optionValue.lower()
                        if optionValue in ('true', '1', 't', 'on', 'yes'):
                            optionValue = True
                        else:
                            optionValue = False

                u.config[optionName] = optionValue
            self.URLs.append(u)

    def rollPings(self):
        for u in self.URLs:
            # fix to ignore the default empty url - Jimmy J - 08/14/2008 
            if u.url:
               u.start()

        #for u in self.URLs:
        #    # print "Joining url : ", u.url
        #    if u.url:
        #       u.join()
        #       print "completed joining : ", u.url
 
        while not self.done and len(self.URLs) > 0:
            try:
                # Join all threads using a timeout so it doesn't block
                # Filter out threads which have been joined or are None
                self.URLs = [t.join(1) for t in self.URLs if t is not None and t.isAlive()]
            except KeyboardInterrupt:
                print "Ctrl-c received! Sending kill to threads..."
                for t in self.URLs:
                    t.done = True
                self.done = True



class SmartRedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_301(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_301(
            self, req, fp, code, msg, headers)
        result.status = code
        return result

    def http_error_302(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_302(
            self, req, fp, code, msg, headers)
        result.status = code
        return result

#--------------------------------------------------------------
class DefaultErrorHandler(urllib2.HTTPDefaultErrorHandler):
    def http_error_default(self, req, fp, code, msg, headers):
        result = urllib2.HTTPError(
            req.get_full_url(), code, msg, headers, fp)
        result.status = code
        return result


#--------------------------------------------------------------
def main():
    try:
        optlist, args = getopt.getopt(sys.argv[1:], '?',
                ['config=', 'debug', 'version'])
    except getopt.error, val:
        sys.stderr.write('Error parsing configuration: %s' % val)
        sys.exit(1)

    config = ""
    debug = False

    for o, a in optlist:
        if o == "--debug":
            debug = True
        elif o == "--version":
            print "Webmon version: ", VERSION

    if debug:
        print "config =", config

    #signal.signal(signal.SIGINT, handler)


    pinger = WebMonProcessor()
    pinger.rollPings()

if __name__ == '__main__':
    main()
