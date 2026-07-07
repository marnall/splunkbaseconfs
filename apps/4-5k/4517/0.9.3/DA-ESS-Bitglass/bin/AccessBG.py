#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import urllib2
import sys
import time
import datetime
import socket
import optparse
import Queue
import threading
import logging
import re
from collections import Mapping, Set, Sequence
import requests
import json
import base64
import signal
try:
    import splunk.entity as entity
    from splunk.clilib import cli_common as cli
    undersplunk = True
except ImportError:
    undersplunk = False

COLLECTOR_VERSION = '1.0.1'
ENVIRONMENT = 'trial'  # production (bitglass.com) or trial (us.bitglass.net)
STARTTIME='2017-01-01T00:00:00Z'
#STARTTIME = '2019-01-01T00:00:00Z'
# STARTTIME='2019-02-11'
#SYSLOGHEADERRE=re.compile(r'^"?<\d+>\d (?P<dt>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(.\d{6})?Z) api.bitglass.com', re.U)
SYSLOGHEADERRE = re.compile(
    r'^"?<\d+>\d (?P<dt1>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?P<dt2>.\d{6})?(?P<dt3>Z) api.bitglass.com',
    re.U)

# https://portal.bitglass.com/api/bitglassapi/logs/v1
url = 'https://portal.%s/api/bitglassapi/logs/v1' % (
    'bitglass.com' if ENVIRONMENT == 'production' else 'us.bitglass.net')  # do not edit

# access the credentials in /servicesNS/nobody/<YourApp>/storage/passwords
def getCredentials(sessionKey, opts):
    myapp = 'DA-ESS-Bitglass'
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
            user = c['username']
            passw = c['clear_password']
    except BaseException:
        user = opts.user
        passw = opts.password
    return((user, passw))

# Use Splunk api, Returns (url, logtype, customer, version)
def getApiDetails(opts):
    myapp = 'DA-ESS-Bitglass'
    try:
        cfg = cli.getConfStanza('appsetup', 'bitglass_config')
        url = cfg.get('url')
        version = cfg.get('version')
        lt = cfg.get('logtype')
        customer = cfg.get('customer')
    except NameError:
        url = opts.url
        version = opts.version
        lt = opts.logtype
        customer = opts.customer
    except Exception as e:
        raise Exception("%s: Could not get api details from splunk. Error: %s"
                        % (myapp, str(e)))
    return((url, lt, customer, version))


def SplunkFieldName(key):
    # a-z, A-Z, _ -
    key = u''.join([c for c in key if ord(c) in range(97, 123)
                    or ord(c) in range(65, 91) or ord(c) in (45, 95)])
    # strip leading underbars
    key = key.lstrip('_')
    return(key)

# Should be all unicode strings in d
# Potential time stamp: _time
# Cleans keys according Splunk fieldname syntax
# Returns unicode string in kv-format
def MarshalSplunk(d):
    # Single out special keys: _time
    try:
        strFormat = u'{0:s}'.format(d['_time'])
        d.pop('_time', None)
    except KeyError:
        strFormat = u''
    FixBrokenFields(d)
    for k, v in d.iteritems():
        # remaining fields
        # Remove empty fields
        if v is None or v == '':
            continue
        sv = u'{0}'.format(v)
        # We rely on splunks default KV_MODE detection, based on key=value,
        # so need to take pre-caution for values containing = and/or ,
        if ',' in sv or '=' in sv and sv[0] != '\"':
            # Surround value by " if required, and remove any newlines -
            # questionable practice....
            sv = u'\"{}\"'.format(sv)
        # Delete newlines from values - questionable practice really - we
        # should not tamper with any content....
        sv = sv.replace('\n', u'')
        strFormat += u',{0}={1}'.format(SplunkFieldName(k), sv)
    strFormat += u',\n'
    return(strFormat.encode('utf-8', 'replace'))

# Open file containing the last event timestamps per command
# Customername,LogType,dataformat,version,token, lastdate
def GetLastEvents(strFile):
    dLastTokens = {}
    dLastDates = {}
    if os.path.isfile(strFile):
        fp = open(strFile, 'r')
        for strLine in fp:
            l = strLine.rstrip().split(',')
            # {(customer,logtype/command,dataformat,version):token}
            assert (len(l) >= 6), 'Invalid lastbitglassevents format'
            dLastTokens[(l[0], l[1], l[2], l[3])] = l[4]
            dLastDates[(l[0], l[1], l[2], l[3])] = datetime.datetime.strptime(
                l[5], '%Y%m%dT%H:%M:%S')
        fp.close()
    else:
        pass
    return(dLastTokens, dLastDates)

# dCommands: {(customer,'cloudloggging','json','1.0.1'):token}
# dDates: {(customer,'cloudloggging','json','1.0.1'):date}
def WriteLastEvents(strFile, dCommands, dDates):
    if len(dCommands) == 0:
        return
    try:
        fp = open(strFile, 'w')
        for k, v in dCommands.iteritems():
            fp.write(
                '{0},{1},{2},{3},{4},{5}\n'.format(
                    k[0],
                    k[1],
                    k[2],
                    k[3],
                    v,
                    dDates[k].strftime('%Y%m%dT%H:%M:%S')))
        fp.close()
    except Exception as e:
        sys.stderr.write(str(e) + '\n')
        sys.stderr.write(
            'Error writing last_eventid to file: ' +
            strFile +
            '\n')

# Class for writing events to destination, either Splunk or Elastic.
# Overwrites possible for alternate destinations
class EventWriter(object):
    def __init__(self, **kwargs):
        self.host = kwargs.get('host', "localhost")
        self.port = kwargs.get('port', 9200)
        self.customer = kwargs.get('customer', 'bitglass')
        self.marshal = kwargs.get('mfunc', None)
        self.logger = kwargs.get('logger', None)

    # Send a kv-formatted message to stdout
    # message is json dict
    def send(self, message):
        if self.marshal is not None:
            data = self.marshal(message)
        else:
            data = json.dumps(message).encode('utf-8', 'replace')
        sys.stdout.write(data)

    # expects unicode strings
    def report(self, message, nEvents):
        data = message.format(nEvents)
        sys.stdout.write(data.encode('utf-8', 'replace'))


class EventWriterSocket(EventWriter):
    def __init__(self, **kwargs):
        self.host = kwargs.get('host', "localhost")
        self.port = kwargs.get('port', 9200)
        self.customer = kwargs.get('customer', 'bitglass')
        self.marshal = kwargs.get('mfunc', None)
        self.logger = kwargs.get('logger', None)
        try:
            sys.stderr.write(
                'Create TCP socket to host {0:s} and port {1:d}\n'.format(
                    self.host, self.port))
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
        except Exception as e:
            sys.stderr.write(str(e) + ' 1')
            self.socket = None

    # message is json dict
    def send(self, message):
        if self.marshal is not None:
            data = self.marshal(message)
        else:
            data = json.dumps(message).encode('utf-8', 'replace')
        self.socket.sendall(data)

    def report(self, message, nEvents):
        data = message.format(nEvents)
        self.socket.sendall(data.encode('utf-8', 'replace'))


# dual python 2/3 compatability, inspired by the "six" library
string_types = (str, unicode) if str is bytes else (str, bytes)

# Read objects and send over to destination host
# Expects unicode string objects
def OutputThread(eventwriter, qOutput, opts, logger):
    logger.debug('Start outputthread with EPS limit: {0:d}'.format(opts.eps))
    nCounter = 0
    nSend = 0

    # Keep collecting objects from queue, untill we are told to stop.
    # Potential objects collected can be:
    #     -Strings: STOP, or REPORT
    #     -Dict: expected to be compatible with created eventwriter
    #     -Other: something is seriously wrong.......
    while True:
        try:
            message = qOutput.get(True)
            logger.info(
                'Outputthread retrieves job from queue: {}'.format(
                    type(message).__name__))
        except BaseException:
            logger.warning('Outputthread failed to get job from queue')
            return
        # Check the command they want us to do
        if isinstance(message, string_types) and message == u'STOP':
            # Terminate
            logger.debug('Outputthread received STOP command, terminating')

            # End the thread
            return
        if isinstance(message, string_types) and message.startswith(u'REPORT'):
            try:
                eventwriter.report(message[len('REPORT '):], nSend)
            except Exception as e:
                logger.warning(
                    'Outputthread encountered exception: {0}'.format(
                        str(e)))
                logger.warning('Message data: {0}'.format(message))
        else:
            # must be dict object
            try:
                eventwriter.send(message)
                nCounter += 1
                nSend += 1
            except Exception as e:
                logger.warning(
                    'Outputthread encountered exception: {0}'.format(
                        str(e)))
                logger.warning('Message data: {0}'.format(message))

        # Apply Throttling if requested
        if opts.eps > 0 and nCounter >= opts.eps:
            nCounter = 0
            time.sleep(1)

# Use list as a container to allow duplicate keys
def lflatten(obj, path=()):
    l = []
    if isinstance(obj, Mapping):
        for k, v in obj.iteritems():
            l = l + lflatten(v, path + (k,))
        return(l)
    elif isinstance(obj, (Sequence, Set)) and not isinstance(obj, string_types):
        for x in obj:
            l = l + lflatten(x, path)
        return(l)
    else:
        if isinstance(obj, unicode):
            l.append((u'_'.join(map(unicode, path)), obj))
        elif isinstance(obj, str):
            l.append((u'_'.join(map(unicode, path)), obj.decode('utf-8')))
        else:
            l.append((u'_'.join(map(unicode, path)), unicode(obj)))
        return(l)


def lFlat(obj):
    l = lflatten(obj)
    d = {}
    for t in l:
        if t[0] in d:
            d[t[0]] = d[t[0]] + ';' + t[1]
        else:
            d[t[0]] = t[1]
    return(d)


def sighandler(signum, frame):
    # Stop everything
    qOutput = signalhelper[2]
    logger = signalhelper[3]
    OThread = signalhelper[4]
    qOutput.put(u'STOP')
    OThread.join()
    logger.info('Script exiting....')
    sys.exit()


# Check validity of returned next page token
# '{"log_id": "c8750ab4-f862-4f86-be7e-72c48ba23cd5", "datetime": "2019-03-21T14:23:42.018395Z"}'
def CheckAPIToken(token, logger):
    if token is None:
        return(False)
    try:
        d = json.loads(base64.b64decode(token))
        assert('log_id' in d), 'No log_id in encoded returned token'
        assert('datetime' in d), 'No datetime in encoded returned token'
        return(True)
    except Exception as e:
        logger.warning('Invalid token returned:{0}'.format(token))
        logger.warning('Exception:{0}'.format(e))
        return(False)


BROKENFIELDS = ('patterns',)


def FixBrokenFields(d):
    # patterns, multifield but components contain comma's
    # put in an attempt to separate into multi-value fields
    if 'patterns' not in d or d['patterns'] == '':
        return(d)
    # Ugly Ugly Ugly
    s = ''
    bReplace = True
    for i, c in enumerate(d['patterns']):
        if c == ',' and bReplace:
            s += ';'
        else:
            s += c
        if c == '(':
            bReplace = False
        if c == ')':
            bReplace = True
    d['patterns'] = s
    return(d)

# Extract events via API, and feed to output thread
def RetrieveLogs(td, q, opts, logger, marshalfunc):
    ClientToken = (opts.user + ":" + opts.passwd).encode()
    Base64ClientToken = base64.b64encode(ClientToken)
    bMore = True
    iLen = 0
    maxtime = None
    nexttoken = None

    logger.info(
        'retrieve bitglass logs for logtype {0}, URL:{1}'.format(
            opts.logtype, opts.url))
    # logger.info('user:{0}---passwd:{1}'.format(opts.user,opts.passwd))
    while bMore:
        if isinstance(td, (Sequence)):
            # td is last token
            theurl = '%s?type=%s&responseformat=%s&nextpagetoken=%s&cv=%s' % (
                opts.url, opts.logtype, opts.dataformat, urllib2.quote(td), urllib2.quote(opts.version))
        else:
            # td must be last timestamp
            theurl = '%s?type=%s&responseformat=%s&startdate=%s&cv=%s' % (opts.url, opts.logtype, opts.dataformat,
                                                                          urllib2.quote(td.strftime('%Y-%m-%dT%H:%M:%SZ')),
                                                                          urllib2.quote(opts.version))
        try:
            request = urllib2.Request(theurl)
            request.add_header('Authorization', 'basic %s' % Base64ClientToken)
            logger.info(
                'bitglass api for logtype {0}  url:{1}'.format(
                    opts.logtype, request.get_full_url()))
            response = urllib2.urlopen(request)
        # except requests.RequestException as e:
        except Exception as e:
            logger.warning('Exception:{0}'.format(e))
            logger.warning(
                'API request for logtype {0} failed: {1}'.format(
                    opts.logtype, theurl))
            return(None, None, 0)

        # Result is dict with keys: status, nextpagetoken,response
        logger.info('Decode JSON response for logtype {}'.format(opts.logtype))
        try:
            result = json.loads(response.read())
        except BaseException:
            logger.warning(
                'Could not interpret json response from {0}'.format(theurl))
            logger.warning('Response:{0}'.format(repr(response)))
            logger.warning(
                'Headers: {0}'.format(
                    repr(
                        response.request.headers)))
            logger.warning('Body: {0}'.format(repr(response.request.body)))
            return((None, None, 0))
        try:
            nexttoken = result['nextpagetoken']
            # Check on validity
            if not CheckAPIToken(nexttoken, logger):
                logger.warning(
                    'Invalid new token returned: {} for logtype {}'.format(
                        nexttoken, opts.logtype))
                nexttoken = None
        except KeyError:
            # td remains unchanged
            nexttoken = None
            logger.warning(
                'No new token returned for logtype {}'.format(
                    opts.logtype))

        # Number of objects received
        iLen += len(result['response']['data'])

        # Send objects to Output Queue for forwarding to client
        for x in result['response']['data']:
            # Extract time from events, and inject into dict
            m = SYSLOGHEADERRE.search(x['syslogheader'])
            if m:
                lastTS = m.group('dt1') + m.group('dt3')
                try:
                    # Strip optional milliseconds
                    lastdate = datetime.datetime.strptime(
                        lastTS.split('.')[0], '%Y-%m-%dT%H:%M:%SZ')
                except BaseException:
                    logger.warning(
                        'Error converting date string, string={}, format={}'.format(
                            lastTS, '%Y-%m-%dT%H:%M:%SZ'))
                    logger.warning('Message={}'.format(x))
                    lastdate = datetime.datetime.now()
            # Force three fields: _time, customer and logtype
            x['_time'] = datetime.datetime.strftime(
                lastdate, '%m/%d/%Y %H:%M:%S')
            x[u'customer'] = opts.customer
            x[u'logtype'] = opts.logtype
            q.put(x)

            if maxtime is None:
                maxtime = lastdate
            else:
                if maxtime < lastdate:
                    maxtime = lastdate

        bMore = False
        if nexttoken is not None and nexttoken != td:
            td = nexttoken
            bMore = True
    logger.info(
        'RetrieveLogs returns: token: {} -- timestamp: {} -- number of events: {}'.format(
            nexttoken,
            maxtime,
            iLen))
    return((nexttoken, maxtime, iLen))


def MainThread(opts, args, qOutput, logger, strLastEvents, marshalfunc):
    logger.info('Starting main thread\n')
    signal.signal(signal.SIGALRM, sighandler)
    signal.signal(signal.SIGTERM, sighandler)
    signal.signal(signal.SIGINT, sighandler)

    try:
        dLastTokens, dLastDates = GetLastEvents(strLastEvents)
    except Exception as e:
        # Exit: force output thread to stop and end this thread
        sys.stderr.write(str(e) + '\n')
        sys.stderr.write(
            'Error: failed to read or understand last_eventid file, ' +
            strLastEvents +
            '\n')
        qOutput.put('STOP')
        return

    # Split logtype into multiple logtypes potentially.....bit of an ugly hack
    # sorry
    l = opts.logtype.split(':')
    for lt in l:
        logger.info('Collecting log type: {}'.format(lt))
        opts.logtype = lt
        # find matching token/date from last run
        try:
            lasttoken = dLastTokens[(
                opts.customer, opts.logtype, opts.dataformat, opts.version)]
            # Check for validity of token
            if not CheckAPIToken(lasttoken, logger):
                lasttoken = None
            lastdate = dLastDates[(
                opts.customer, opts.logtype, opts.dataformat, opts.version)]
        except KeyError:
            lasttoken = None
            lastdate = None
        if lasttoken is None or lastdate is None:
            # No valid token and/or lastdate, revert to starting date
            # This should really only happen the very first run, if it occurs in later situations
            # this will imply duplicate events imported.
            logger.warning(
                'No valid token and/or date from last run for logtype {}, revert to starting date: {}'.format(lt, STARTTIME))
            lastdate = datetime.datetime.strptime(
                STARTTIME, '%Y-%m-%dT%H:%M:%SZ')

        # Run!
        try:
            # if we have a valid token, use it
            if lasttoken is not None:
                token = lasttoken
            else:
                token = lastdate
            lasttoken, lasttime, nEvents = RetrieveLogs(
                token, qOutput, opts, logger, marshalfunc)

            # Update last token and last date
            if lasttime is not None:
                dLastDates[(opts.customer, opts.logtype,
                            opts.dataformat, opts.version)] = lasttime
            if lasttoken is not None:
                dLastTokens[(opts.customer, opts.logtype,
                             opts.dataformat, opts.version)] = lasttoken

            # Have OutputThread generate intermediate report, for tracking and
            # debugging purposes
            t = datetime.datetime.strftime(
                datetime.datetime.now(), '%m/%d/%Y %H:%M:%S')
            qOutput.put(
                u'REPORT {} STATS=True, LogType={}, APIEventsSend={{}}\n'.format(
                    t, opts.logtype))
        except Exception as e:
            logger.warning('Exception:{0} for logtype: {1}'.format(e, lt))
    # Generate final report and stop the output thread
    t = datetime.datetime.strftime(
        datetime.datetime.now(),
        '%m/%d/%Y %H:%M:%S')
    qOutput.put(
        u'REPORT {} STATS=True, Script ending, APIEventsSend={{}}\n'.format(t))
    WriteLastEvents(strLastEvents, dLastTokens, dLastDates)
    qOutput.put(u'STOP')
    return


# Main code
global signalhelper
signalhelper = []


def main():
    # Parse command line options
    p = optparse.OptionParser("usage: %prog [options]")
    p.add_option(
        "-n",
        "--network",
        dest="network",
        action='store_true',
        default=False,
        help='send output messages over TCP socket, by default routed to stdout')
    p.add_option("-v", "--version", dest="version", default='1.0.1',
                 help='api version field, defaults to 1.0.1')
    p.add_option(
        "-d",
        "--dataformat",
        dest="dataformat",
        default='json',
        help='requested api dataformat, json of csv, defaults to json')
    p.add_option(
        "-t",
        "--logtype",
        dest="logtype",
        default='cloudsummary:access:cloudaudit',
        help='logtype field, defaults to cloudsummary:access:cloudaudit')
    p.add_option("-c", "--customer", dest="customer", default='Bitglass',
                 help='customer field, defaults to Bitglass')
    p.add_option(
        "-l",
        "--log",
        dest="loglevel",
        default='WARNING',
        help='loglevel field, defaults to WARNING, options are: CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET')
    p.add_option(
        "-o",
        "--host",
        dest="host",
        default='localhost',
        help='hostname or ip address for splunk host, defaults to localhost')
    p.add_option(
        "-r",
        "--url",
        dest="url",
        default='https://portal.us.bitglass.net/api/bitglassapi/logs/v1',
        help='url for portal access, defaults to https://portal.us.bitglass.net/api/bitglassapi/logs/v1')
    p.add_option("-k", "--pass", dest="passwd", default='nopasswd',
                 help='password for portal access')
    p.add_option("-u", "--user", dest="user", default='anonymous',
                 help='user name for portal access')
    p.add_option("-p", "--port", dest="port", type='int', default=9200,
                 help='TCP or UDP port for splunk host, defaults to 9200')
    p.add_option(
        "-e",
        "--eps",
        dest="eps",
        type='int',
        default=500,
        help='events per second, if set to a value larger then 0 throttling will be applied, defaults to 500')
    p.add_option("-i", "--index", dest="index", default=None,
                 help='Json file with index details, defaults to None')
    opts, args = p.parse_args()

    # Initiate Logging
    numeric_level = getattr(logging, opts.loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % opts.loglevel)

    formatter = logging.Formatter(
        '%(asctime)s,Level=%(levelname)s, ErrorMessage=%(message)s',
        '%m/%d/%Y %H:%M:%S')
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(formatter)

    # Splunk format
    logger = logging.getLogger('Bitglass2Splunk')
    logger.addHandler(sh)
    logger.level = numeric_level

    # By default, send to Splunk, either over stdout or socket
    if opts.network:
        eventwriter = EventWriterSocket(
            host=opts.host,
            port=opts.port,
            customer=opts.customer,
            mfunc=MarshalSplunk)
        # Check if connection was created
        if eventwriter.socket is None:
            logger.warning(
                'Outputthread failed to create connection to host {}'.format(
                    opts.host))
            # End the thread
            sys.exit(-1)
    else:
        # By default its Splunk, over stdout
        eventwriter = EventWriter(customer=opts.customer, mfunc=MarshalSplunk)
        logger.info('Create Splunk standard output')

    marshalfunc = MarshalSplunk
    qOutput = Queue.Queue(0)
    last_eventid_filepath = os.path.join(sys.path[0], 'lastbitglassevents')
    OThread = threading.Thread(
        target=OutputThread, args=(
            eventwriter, qOutput, opts, logger))
    OThread.start()

    if undersplunk:
        # read session key sent from splunkd
        sessionKey = sys.stdin.readline().strip()
    else:
        sessionKey = 'Bitglass'

    # now get credentials
    try:
        user, passwd = getCredentials(sessionKey, opts)
        opts.user = user
        opts.passwd = passwd
    except BaseException:
        logger.info('Could not get credentials....')

    # Get parameters from Splunkd
    try:
        url, logtype, customer, version = getApiDetails(opts)
        opts.url = url
        opts.logtype = logtype
        opts.customer = customer
        opts.version = version
    except BaseException:
        logger.info('Could not get parameters....')

    MainThread(
        opts,
        args,
        qOutput,
        logger,
        os.path.join(
            sys.path[0],
            'lastbitglassevents'),
        marshalfunc)

    # Wait for output thread to be completed
    OThread.join()
    logger.info('Script exiting....')
    sys.exit()


if __name__ == '__main__':
    main()
