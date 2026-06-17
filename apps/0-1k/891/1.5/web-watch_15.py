# Copyright (C) 2005-2008 Splunk Inc.  All Rights Reserved.  Version 3.0
import getopt, sys, imaplib, os, urllib2, urlparse, httplib, gzip, md5, \
        cStringIO, time
import splunk.clilib.cli_common as comm



PINGEE_CONFIGURATION_OPTIONS = (
    ('userAgent', 'Splunk webping bundle', 'User-Agent header to use when making requests'),
    ('indexResults', False, 'Dump page contents'),
    ('indexMD5', True, 'Create an MD5 of URL contents'),
    ('timeout', 10, 'Network timeout'),
)


splunk_home = os.getenv('SPLUNK_HOME')
if not splunk_home:
    raise ConfigError('Environment variable SPLUNK_HOME must be set')

# path to the confguration conf file
scriptDir = sys.path[0] # find it relative to getimap.py file
configDefaultFileName = os.path.join(scriptDir,'..','default','urls.conf')
configLocalFileName = os.path.join(scriptDir,'..','local','urls.conf')

VERSION = 1.4

class Pingee(object):

    def __init__(self, name, url):
        self.name = name
        self.url = url
        self.config = {}
        self.result = {}



class WebPingProcessor(object):
    confStanzas = ""
    URLs = []
    setSourceType = True

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
               self.ping(u)

    def printOutput(self):
        for u in self.URLs:
         #Jimmy J - 08/14/2008 - ignore empty urls
         if u.url:

            if self.setSourceType:
                print "***SPLUNK*** source="+u.url
                print "WebPingProcessor"

            print 'ping_name =', u.name
            print "ping_url =", u.url
            
            if u.result.has_key('pingTime'):
                print "time_in_ms =", u.result.get('pingTime')
            if u.result.has_key('data'):
                print "size_in_bytes =", len(u.result.get('data'))
            print "status_code =", u.result.get('status')

            if (u.config['indexMD5'] and u.result.has_key('data')):
                s = u.result.get('data')
                checksum = md5.new(s).hexdigest()
                print 'ping_md5 =', checksum

            if (u.config['indexResults'] and u.result.has_key('data')):
                s = u.result.get('data')
                print 'contents =\n', s
        
            print "WebPingProcessor"

    def ping(self, u):  
        result = {}
        u.result = result
        if urlparse.urlparse(u.url)[0] not in ('http', 'https'):
            result['status'] = 'non-HTTP URLs not supported'
            return

        request = urllib2.Request(u.url)

        request.add_header('User-Agent', u.config['userAgent'])
        request.add_header('Accept-Encoding', 'gzip')

#            if etag:
#                    headers.append(('If-None-Match', etag))
#            if lastmodified:
#                    headers.append(('If-Modified-Since', lastmodified))

        # Begin timing
        startTime = time.time()

        try:
            opener = urllib2.build_opener(SmartRedirectHandler(),
                    DefaultErrorHandler())
            fp = opener.open(request)
        except urllib2.URLError, e:
            result['status'] = 'Connection failed while trying to ping URL'
            return

        result['data'] = fp.read()

        # End timing and calculate time in ms
        endTime = time.time()
        totalTime = (endTime - startTime)*1000
        result['pingTime'] = int(totalTime)

        if hasattr(fp, 'headers'):
                result['etag'] = fp.headers.get('ETag')
                result['lastmodified'] = fp.headers.get('Last-Modified')
                if fp.headers.get('Content-Encoding', '') == 'gzip':
                        # data came back gzip-compressed, decompress it
                        # corrected call to StringIO - Jimmy J - 08/14/2008
                        result['data'] = gzip.GzipFile(fileobj=cStringIO.StringIO(result['data'])).read()

        if hasattr(fp, 'status'):
            result['status'] = fp.status
        else:
            result['status'] = '200'

        fp.close()
        


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
            print "Webping version: ", VERSION

    if debug:
        print "config =", config

    pinger = WebPingProcessor()
    pinger.rollPings()
    pinger.printOutput()

if __name__ == '__main__':
    main()
