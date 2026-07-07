#!/usr/bin/python

# Copyright (c) 2011, Corvil Limited. All rights reserved.
# THIS SOURCE CODE IS A TRADE SECRET OF CORVIL AND SHOULD NOT BE TRANSFERRED
# OR DISCLOSED TO ANY THIRD PARTY WITHOUT CORVIL'S PERMISSION. THIS SOURCE
# CODE IS LICENSED "AS IS", SOLELY FOR ILLUSTRATION PURPOSES, ONLY WITHIN
# THE LIMITED, SPECIFIC CONTEXT AND PARAMETERS INDICATED IN THE APPLICABLE
# CORVIL INSTRUCTIONS AND DOCUMENTATION, AND SUBJECT TO THE TERMS AND
# CONDITIONS OF THE CORVIL STANDARD SOFTWARE LICENSE AGREEMENT, INCLUDING
# WITHOUT LIMITATION THE LIABILITY LIMITATIONS SET FORTH THEREIN.

# NB: this was developed against Python v2.5.4 and Suds v0.4

# $Revision: 189600 $

"""
Corvil XML API example tool for streamed processing of MTOM attachments

Version: TRUNK_VERSION

Usage: CorvilApiStreamingClient.py [<options>] <command> <args> ...

Commands + Arguments:
    version
Prints client version

    pcap            <host> <mp> <start_time> <end_time>
Get PCAP data

    gap-csv         <host> <mp> <start_time> <end_time>
Get message-gap CSV

    message-csv     <host> <mp> <start_time> <end_time>
Get message CSV

    packet-csv      <host> <mp> <start_time> <end_time>
Get packet CSV

    multihop-csv    <host> <mp> <packet_timestamp> <packet_id> <message_index>
Get multihop CSV

    lens-csv        <host> <period> [<view>]
Get Lens CSV

    mp-list         <host>
Show measurement points

    flow-index      <host> <start_time> <end_time> <aggregations>
Get flow-index table CSV

    clock-tracking  <host> <start_time> <end_time>
Get clock tracking log

Arguments:
    host            CNE or CMC to use when requesting data, can specify port: host:port
    mp              Fully qualified measurement point name, e.g.
                    "channel//local-cne///PortA". Use mp-list command for
                    full list of available measurement points
    start_time      Period start time (see Time Formats below)
    end_time        Period end time (see Time Formats below)
    period          Reporting period name, e.g. "Last 1 hour", "Business Day".
    view            Name of Corvil Lens view. Views can be configured using
                    Corvil Lens GUI. Default is 'Default'.
    aggregations    Optional aggregations for flow-index command; Available aggregations:
                    conversations, talkers, listeners, ports, vports, applications,
                    time-seconds, time-minutes, time-hours;
                    These can be specified as a list separated by comma as the last command line
                    argument for the flow-index command. for example: "talkers,listeners,applications"

  Options:
    -n <username>           Specify username, default: admin
    -p <password>           Specify password, default: admin
    -x <cne>                Specify CNE for requests sent to CMC
    -L <local-cne-name>     Specify the local CNE name, default: local-cne (clock-tracking)
    -b                      Request bidirectional export (pcap, gap-csv, message-csv, packet-csv)
    -c                      Request correlation analysis (message-csv)
    -C                      Request correlation IDs (message-csv)
    -a                      Request summaries (flow-index)
    -w                      Request watch list metadata (flow-index)
    -m                      Request additional measurement points (pcap)
    -s                      Request measurement points in the flow-index response (flow-index)
    -q <query>              Optional filter which utilizes Corvil Query Language (CQL) (flow-index)
    -l <columns>            Comma-separated list of columns to return (message-csv, packet-csv)
    -t <filter type>        CQL, Wireshark or BPF
    -f <filter text>        Single line filter expression
    -z                      Use https to access the CNE
    -T <timeout-seconds>    Request timeout in seconds, default value: 3600


  Time Formats:
    YYYY-MM-DD HH:MM:SS
    <epoch_sec>
    <epoch_nsec>
"""

import base64
import errno
import logging
import os
import suds
try:
    import ssl
    if hasattr(ssl, '_create_unverified_context'):
        ssl._create_default_https_context = ssl._create_unverified_context
except:
    pass
import socket
import sys
import time
import getopt
import httplib
import inspect
from xml.dom import minidom

VERSION='TRUNK_VERSION'

logging.basicConfig(level=logging.INFO)
#logging.getLogger('suds.transport').setLevel(logging.DEBUG)

class SudsParameterPlugin(suds.plugin.MessagePlugin):
    """suds plugin to specify extra method parameters"""
    def __init__(self):
        self.attrs = {}
    def setAttrs(self, attrs):
        self.attrs = attrs
    def marshalled(self, context):
        body = context.envelope.getChild('Body')
        fnTag = body[0]
        for k,v in self.attrs.items():
            fnTag.set(k, v)

class SudsGrabberPlugin(suds.plugin.MessagePlugin):
    """Plugin to grab the XML from a request"""
    def __init__(self):
        self.grab = False
        self.data = None
    def sending(self, context):
        grab = self.grab
        self.grab = False
        if grab:
            self.data = context.envelope

class CorvilApiMtomClient():
    READ_BLOCK_SIZE = 256 * 1024
    MAX_XML_SIZE = 64 * 1024
    SOCKET_TIMEOUT_SECONDS = 3600

    def __init__(self, host, port = 5101, username = 'admin', password = '', cne=None, useHttps=False, timeout=SOCKET_TIMEOUT_SECONDS):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.cne = cne
        self.url = "http://%s:%s/ws/stats-v2?WSDL" % (host, port)
        self.mtomUrl = "http://%s:%s/ws/statsMTOM-v2?wsdl" % (host, port)
        self.useHttps = useHttps
        if self.useHttps:
            self.url = "https://%s/api/ws/stats-v2?WSDL" % (host)
            self.mtomUrl = "https://%s/api/ws/statsMTOM-v2?wsdl" % (host)

        # suds plugins
        self.versionPlugin = SudsParameterPlugin()
        self.versionPlugin.setAttrs({'version' : '2'})
        self.paramPlugin = SudsParameterPlugin()
        self.grabber = SudsGrabberPlugin()

        self.client = suds.client.Client(self.url, username = self.username,
                                         cache = None, password = self.password, plugins=[
                self.versionPlugin, self.paramPlugin, self.grabber],
                                         timeout = CorvilApiMtomClient.SOCKET_TIMEOUT_SECONDS)

        self.hostIsLmc = (hasattr(self.client.service, "getCnes") and
                          callable(self.client.service.getCnes))

    # Various helper methods
    def getSudsClient(self):
        """Return the suds client"""
        return self.client

    def createObject(self, type):
        """Create the specified suds object type"""
        return self.client.factory.create(type)

    def createMeasurementPointRequest(self, mpname):
        """Create a MeasurementPointRequest object"""
        mpReq = self.createObject("ns0:MeasurementPointRequest")
        mpReq._name = mpname
        return mpReq

    def createMeasurementPoints(self, mpname):
        """Create a MeasurementPointRequest object"""
        mp = self.createObject("ns0:MeasurementPointsRequest")
        mp.measurementPoint = self.createMeasurementPointRequest(mpname)
        return mp

    def createTimeRangeNs(self, fromNs, toNs):
        """Create a TimeRangeNs object"""
        timeRange = self.client.factory.create('ns0:TimeRangeNs')
        timeRange._fromNs = fromNs
        timeRange._toNs = toNs
        return timeRange

    def createDefinitionPoints(self, points = None):
        number_of_points = self.client.factory.create('ns0:NumberOfPoints')
        number_of_points._points = points
        return number_of_points

    def createDefinition(self, stat = [], statEventData = [], configurableStat = [],
                         configurableStatThreshold = [], configurableStatEventData = [], points=None):
        """ Create definition object to be used by getAnalytics call"""
        definition = self.client.factory.create('ns0:DefinitionWithPoints')
        definition._points = points
        definition.stat = stat
        definition.statEventData = statEventData
        definition.configurableStat = configurableStat
        definition.configurableStatThreshold = configurableStatThreshold
        definition.configurableStatEventData = configurableStatEventData
        return definition

    def createStat(self, statistic=None):
        """ Create stat object to be used by getAnalytics call"""
        s = self.client.factory.create('ns0:Stat')
        s._name = statistic["name"]
        s._requestedPercentiles = statistic["percentiles"]
        return s

    def createNamedReportingPeriod(self, rpName):
        """Create a NamedReportingPeriod object"""
        rp = self.client.factory.create('ns0:NamedReportingPeriod')
        rp._name = rpName 
        return rp

    def createMessageId(self,packetId,timestamp,messageIndex):
        messageId = self.client.factory.create('ns0:MessageId')
        messageId._packetTs = timestamp
        messageId._packetId = packetId
        messageId._messageIndex = messageIndex
        return messageId

    def createLensView(self, viewName):
        """Create a LensView object"""
        view = self.client.factory.create('ns0:LensView')
        view._name = viewName 
        return view

    def getXmlMtomResponseInBlocks(self, requestXml):
        """
           Sent the specified request in a POST request, and return
           a python generator that streams back the response
        """

        def patch_http_response_read(func):
            def inner(*args):
                try:
                    return func(*args)
                except httplib.IncompleteRead, e:
                    return e.partial

            return inner

        def readSock(sock, nbytes):
            """Handle EINTR in read"""
            while True:
                try:
                    data = sock.read(nbytes)
                except socket.error, e:
                    if e.args[0] == errno.EINTR:
                        continue
                    raise
                return data

        def getLine(resp, maxlen = self.MAX_XML_SIZE, allowPartial = False):
            """Read a line character by character from a response"""
            line = ""
            while len(line) < maxlen and (len(line) < 2 or line[-2:] != "\r\n"):
                c = readSock(resp, 1)
                if not c:
                    if allowPartial:
                        return (False, line)
                    raise Exception, "getLine failed line=`%s'" % line
                line += c
            if len(line) >= maxlen:
                raise Exception, "line `%s' too long" % line
            line = line[:-2]
            if allowPartial:
                return (True, line)
            return line

        headers = {
            'Accept' : 'application/xop+xml',
            'Content-Type' : 'text/xml; charset=utf-8',
            'Authorization' : "Basic %s" % base64.encodestring('%s:%s' %
                (self.username, self.password))[:-1],
        }

        try:
            lib_args = inspect.getargspec(httplib.HTTPConnection.__init__)
            if "timeout" in lib_args[0]:
                if self.useHttps:
                    conn = httplib.HTTPSConnection(self.host, timeout=CorvilApiMtomClient.SOCKET_TIMEOUT_SECONDS)
                else:
                    conn = httplib.HTTPConnection(self.host, self.port,
                                                  timeout=CorvilApiMtomClient.SOCKET_TIMEOUT_SECONDS)
            else:
                if self.useHttps:
                    conn = httplib.HTTPSConnection(self.host)
                else:
                    conn = httplib.HTTPConnection(self.host, self.port)
        except Exception, e:
            #failed to determine timeout support in httplib
            sys.stderr.write("Warning. failed to determine httplib timeout support `%s'\n" %
                             str(e))
            if self.useHttps:
                conn = httplib.HTTPSConnection(self.host)
            else:
                conn = httplib.HTTPConnection(self.host, self.port)

        conn.request("POST", self.mtomUrl, body = requestXml, headers = headers)
        resp = conn.getresponse()

        original_read = httplib.HTTPResponse.read
        httplib.HTTPResponse.read = patch_http_response_read(httplib.HTTPResponse.read)

        try:
            # Read the UUID, XML + headers
            uuid = getLine(resp)
            xml = ""
            while True:
                (ok, l) = getLine(resp, allowPartial = True)
                if not ok:
                    # Handle error responses
                    if l == "%s--" % uuid:
                        errHdrEndPos = xml.find("\n\n")
                        if errHdrEndPos >= 0:
                            xml = xml[errHdrEndPos + 2:]
                        try:
                            xml = minidom.parseString(xml).toprettyxml(indent="  ")
                        except Exception, e:
                            pass
                        raise Exception, xml
                    raise Exception, "getLine failed"
                if l == uuid:
                    break
                xml += l + "\n"
                if len(xml) > self.MAX_XML_SIZE:
                    raise Exception, "xml `%s' too large" % xml
            while True:
                l = getLine(resp)
                if l == "":
                    break

            # Now stream back the data, checking for the UUID end marker
            endMarker = "\r\n%s--" % uuid
            dat = ""
            while True:
                newDat = readSock(resp, self.READ_BLOCK_SIZE)
                if not newDat or len(dat) + len(newDat) < len(endMarker):
                    raise Exception, "Missing end marker"
                dat += newDat
                if len(dat) > len(endMarker):
                    yield dat[:-len(endMarker)]
                dat = dat[-len(endMarker):]
                if dat == endMarker:
                    break
        finally:
            httplib.HTTPResponse.read = original_read

    def wrapMtomCall(self, reqFn):
        """
           Make a suds call without MTOm support, which will fail, but
           intercept the request data and then perform it via MTOM streaming
           reqFn must be a function that makes a call on self.client
        """

        # Make the call, expecting it to fail
        oldLev = logging.getLevelName(logging.getLogger("suds").
                                      getEffectiveLevel())
        logging.root.setLevel(logging.FATAL)
        self.grabber.grab = True
        self.grabber.data = None
        self.versionPlugin.setAttrs({})
        self.client.set_options(port = 'StatsMtomPort')
        try:
            reqFn(self.client)
        except Exception, e:
            if self.grabber.data == None:
                raise e
        finally:
            logging.root.setLevel(oldLev)
            self.client.set_options(port = 'StatsPort')
        if self.grabber.data == None:
            raise Exception, "failed to extract XML request"
        reqXml = self.grabber.data
        self.grabber.data = None

        # Now do it with MTOM streaming
        return self.getXmlMtomResponseInBlocks(reqXml)

    def getPcapInBlocks(self, mpReq, timeRange, filters, extraMps = [], params = {}):
        def sudsFn(client):
            client.service.getPcap(mpReq, timeRange, filters, extraMps)
        self.paramPlugin.setAttrs(params)
        return self.wrapMtomCall(sudsFn)

    def getMessageGapCsvInBlocks(self, mpReq, timeRange, filters, params = {}):
        def sudsFn(client):
            client.service.getMessageGapCsv(mpReq, timeRange, filters)
        self.paramPlugin.setAttrs(params)
        return self.wrapMtomCall(sudsFn)

    def getMultihopCsvInBlocks(self, mpReq, messageId,params={}):
        def sudsFn(client):
            client.service.getMessageMultiHopCsv(mpReq, messageId,params = {})
        self.paramPlugin.setAttrs(params)
        return self.wrapMtomCall(sudsFn)

    def getMessageCsvInBlocks(self, mpReq, timeRange, filters, params = {}):
        def sudsFn(client):
            client.service.getMessageCsv(mpReq, timeRange, filters)
        self.paramPlugin.setAttrs(params)
        return self.wrapMtomCall(sudsFn)

    def getPacketCsvInBlocks(self, mpReq, timeRange, filters, params = {}):
        def sudsFn(client):
            client.service.getPacketCsv(mpReq, timeRange, filters)
        self.paramPlugin.setAttrs(params)
        return self.wrapMtomCall(sudsFn)

    def getLensCsvInBlocks(self, rp, view):
        def sudsFn(client):
            client.service.getLensCsv(rp, view)
        return self.wrapMtomCall(sudsFn)

    def getFlowTableCsvInBlocks(self, timeRange, query, aggregation,
                                summariesOnly, params = {}):
        def sudsFn(client):
            client.service.getFlowTableCsv(timeRange, query, aggregation,
                                           summariesOnly)
        self.paramPlugin.setAttrs(params)
        return self.wrapMtomCall(sudsFn)


class MtomTool(CorvilApiMtomClient):
    def __init__(self, host="localhost", port=5101, username='admin', password='LOCAL:', cne=None, useHttps=False, commandLine=False):
        self.msgBlock = ""
        self.msgSize = 0
        if commandLine == False:
            self.client = CorvilApiMtomClient(host, port=port,
                password = password, username=username,cne=cne, useHttps=useHttps)
            if self.client.hostIsLmc and cne is not None:
                self.baseParams = {'cne':cne}
            else:
                self.baseParams = {}
    
    def help(self, message=None, exitcode=2):
        if message:
            sys.stdout.write(message)
        sys.stdout.write(__doc__) # doc string from top of file
        sys.exit(exitcode)

    def version(self):
        print VERSION
        sys.exit(0)

    def parseTime(self, str):
        try:
            if isinstance(str, basestring):
                t = time.strptime(str, "%Y-%m-%d %H:%M:%S")
                return long(time.mktime(t)) * long(1e9)
        except ValueError, e:
            pass
        try:
            ns = long(str)
        except Exception, e:
            sys.stderr.write("Invalid time `%s'" % str)
            sys.exit(1)
        if ns < 0x7fffffff:
            return ns * long(1e9)
        return ns
        
    def decodeMessage(self, msg):
        print len(msg)
        
    def processBlock(self, block):
        self.msgBlock += block
        while True:
            if self.msgSize == 0:
                # waiting for size
                if len(self.msgBlock) > 2:
                    self.msgSize = ord(self.msgBlock[0])*256 + ord(self.msgBlock[1])
                    self.msgBlock = self.msgBlock[2:]
            if self.msgSize > 0:
                if len(self.msgBlock) >= self.msgSize:
                    msgToDecode = self.msgBlock[0:self.msgSize-1]
                    self.decodeMessage(msgToDecode)
                    self.msgBlock = self.msgBlock[self.msgSize:]
                    self.msgSize = 0
                else:
                    break

    def parseHost(self, host):
        parts = host.split(':', 2)
        if len(parts) == 2:
            return (parts[0], parts[1])
        else:
            return (host, 5101)

    def get_mp_list(self):
        sc = self.client.getSudsClient()
        try:
            summary = sc.service.getSummary("", self.client.createObject("ns0:ReportingPeriod")['1-hour'])
        except AttributeError, e:
            # This error is thrown when password is incorrect and
            # Python v2.7 is used to run the script
            if e.message == "'NoneType' object has no attribute 'read'":
                sys.stderr.write("Authentication failed (incorrect password?).\n")
                sys.exit(1)
            raise
        if hasattr(summary, "channel"):
            for chan in summary.channel:
                print "Channel %s:" % chan._displayName
                print "  %s" % chan._name
                for cls in chan.cls:
                    print "    %s" % cls._name
        if hasattr(summary, "interface"):
            for iface in summary.interface:
                print "Interface %s:" % iface._displayName
                print "  %s" % iface._name
                for cls in iface.cls:
                    print "    %s" % cls._name
        sys.exit(0)

    def get_lens_csv(self, period, view):
        namedRp = self.client.createNamedReportingPeriod(period)
        lensView = self.client.createLensView(view)
        dataGen = self.client.getLensCsvInBlocks(namedRp, lensView)

        return dataGen

    def get_flow_index(self, startTime, endTime, aggregation = [], watchlistMetadata = None,
                       showMeasurementPoints = None, query = None, summariesOnly = None, params=None):

        aggr = []
        for p in aggregation:
            pTrimmed = p.strip()
            if pTrimmed not in ["conversations", "talkers", "listeners", "ports", "vports",
                                "applications", "time-seconds", "time-minutes", "time-hours"]:
                self.help("Invalid aggregation option:'"+pTrimmed+"'")
            aggr.append(pTrimmed)

        timeRange = self.client.createTimeRangeNs(self.parseTime(startTime), self.parseTime(endTime))
        if params is None:
            params = {}
        if watchlistMetadata:
            params["watchlistMetadata"] = "true"

        if showMeasurementPoints:
            params["showMeasurementPoints"] = "true"

        dataGen = self.client.getFlowTableCsvInBlocks(timeRange, query,
                                                 aggr, summariesOnly, params=params)
        return dataGen

    def get_multihop_csv(self, timestamp,message_id,message_index, mpReq=None, baseParams=None):

        messageId = self.client.createMessageId(message_id,timestamp,message_index)
        mpReq = self.client.createMeasurementPointRequest(mpReq)
        dataGen = self.client.getMultihopCsvInBlocks(mpReq, messageId, params=baseParams)

        return dataGen

    def add_filters(self, filterText = None, filterType = None):
        filter = self.client.createObject("ns0:FilterDefinition")
        if filterText is not None:
            filterObject = self.client.createObject("ns0:ExpressionFilter")
            filterObject._expression = filterText
            if filterType == "CQL":
                filter.corvilPacketFilter = filterObject
            elif filterType == "BPF":
                filter.berkeleyPacketFilter = filterObject
            elif filterType == "Wireshark":
                filter.tsharkDisplayFilter = filterObject
            else:
                sys.stderr.write("Unknown filter type:"+str(filterType)+"\n")
                sys.stderr.write("Supported filter types: CQL, BPF, Wireshark\n")
                sys.exit(1)
            return filter

    def createMessageFilterSequence(self, messageRules):
        """Create a createMessageFilterSequence object"""
        mfs = self.client.createObject("ns0:MessageFilterSequence")
        for rule in messageRules:
            mfr = self.client.createObject("ns0:MessageFilterRule")
            if not 'match' in rule:
                rule['match'] = "show-if-is"
            mfr._match = rule['match']
            if 'messageProtocol' in rule:
                mfr._messageProtocol = rule['messageProtocol']
            if 'messageType' in rule:
                mfr._messageType = rule['messageType']
            if 'messageField' in rule:
                mfr.messageField = rule['messageField']
            if 'messageFieldValue' in rule:
                mfr.messageFieldValue = rule['messageFieldValue']
            if 'regex' in rule:
                mfr.regex = rule['regex']
            mfs.messageFilterRule.append(mfr)
        mfs._name = ""
        mfs._allOtherTraffic = "hide"
        return mfs

    def createTrafficFilterSequence(self, trafficRules):
        """Create a createMessageFilterSequence object"""
        tfs = self.client.createObject("ns0:TrafficFilterSequence")
        for rule in trafficRules:
            tfr = self.client.createObject("ns0:TrafficFilterRule")
            if not rule['match']:
                rule['match'] = "show-if-is"
            tfr._match = rule['match']
            if 'application' in rule:
                tfr.application = rule['application']
            if 'ipProtocol' in rule:
                tfr.ipProtocol = rule['ipProtocol']
            if 'ipProtocolCustom' in rule:
                tfr.ipProtocolCustom = rule['ipProtocolCustom']
            if 'tos' in rule:
                tfr.tos = rule['tos']
            if 'sourceIp' in rule:
                tfr.sourceIp = rule['sourceIp']
            if 'destinationIp' in rule:
                tfr.destinationIp = rule['destinationIp']
            if 'sourcePort' in rule:
                tfr.sourcePort = rule['sourcePort']
            if 'destinationPort' in rule:
                tfr.destinationPort = rule['destinationPort']
            tfs.trafficFilterRule.append(tfr)

        tfs._name = ""
        tfs._allOtherTraffic = "hide"
        return tfs

    def get_pcap(self, bidir, baseParams, mpReq, startTime, endTime, filterText = None, filterType = None, extraMps = None):
        if os.isatty(sys.stdout.fileno()):
            sys.stderr.write("Not sending binary pcap data to STDOUT\n")
            sys.exit(1)
        params = { 'bothDirections' : str(bidir).lower()}
        params.update(baseParams)
        filter = self.add_filters(filterText, filterType)
        mpReq = self.client.createMeasurementPointRequest(mpReq)
        timeRange = self.client.createTimeRangeNs(self.parseTime(startTime), self.parseTime(endTime))
        additionalMps = []
        if extraMps is not None:
            for mpName in extraMps.split(','):
                extraMpReq = self.client.createMeasurementPointRequest(mpName)
                additionalMps.append(extraMpReq)
        
        dataGen = self.client.getPcapInBlocks(mpReq, timeRange, filter, additionalMps,
                params = params)
        # switch to binary mode on windows to prevent corruption of new line characters
        if sys.platform == "win32":
            import msvcrt
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY) # pylint: disable=no-member
        return dataGen

    def get_gap_csv(self, mpReq, startTime, endTime, baseParams, filterText = None, filterType = None):
        mpReq = self.client.createMeasurementPointRequest(mpReq)
        timeRange = self.client.createTimeRangeNs(self.parseTime(startTime), self.parseTime(endTime))
        filter = self.add_filters(filterText, filterType)
        dataGen = self.client.getMessageGapCsvInBlocks(mpReq, timeRange, filter, params=baseParams)

        return dataGen

    def get_message_csv(self, bidir, includeCA, includeCI, columns, baseParams, mpReq, startTime, endTime,
                        filterRules = [], filterSequence = "expressionFilter"):
        params = {'bothDirections' : str(bidir).lower(),
                      'withCorrelation' : str(includeCA).lower()}
        if includeCI:
            params['withCorrelationIds'] = 'true'
        if columns is not None:
            params['columnList'] = columns
        params.update(baseParams)
        filters = self.client.createObject("ns0:FilterDefinition")
        if filterRules:
            if filterSequence == "expressionFilter":
                filters = self.add_filters(filterRules[0]['filterText'], filterRules[0]['filterType'])
            elif filterSequence == "messageFilter":
                filterObject = self.createMessageFilterSequence(filterRules)
                filters.messageFilterSequence = filterObject
            elif filterSequence == "trafficFilter":
                filterObject = self.createTrafficFilterSequence(filterRules)
                filters.trafficFilterSequence = filterObject

        mpReq = self.client.createMeasurementPointRequest(mpReq)
        timeRange = self.client.createTimeRangeNs(self.parseTime(startTime), self.parseTime(endTime))
        dataGen = self.client.getMessageCsvInBlocks(mpReq, timeRange, filters,
                params = params
        )

        return dataGen

    def get_packet_csv(self, bidir, columns, baseParams, mpReq, startTime, endTime, filterText = None, filterType = None):
        params = {'bothDirections' : str(bidir).lower()}
        if columns is not None:
            params['columnList'] = columns
        params.update(baseParams)
        filter = self.add_filters(filterText, filterType)
        mpReq = self.client.createMeasurementPointRequest(mpReq)
        timeRange = self.client.createTimeRangeNs(self.parseTime(startTime), self.parseTime(endTime))
        dataGen = self.client.getPacketCsvInBlocks(mpReq, timeRange, filter,
                params = params
        )

        return dataGen

    def run(self, args):
        opts, args = getopt.gnu_getopt(args, "n:p:x:q:awsbcCzl:m:t:T:f:L:")
        password = 'admin'
        userName = 'admin'
        bidir = False
        includeCA = False
        includeCI = False
        columns = None
        summariesOnly = None
        watchlistMetadata = None
        showMeasurementPoints = None
        query = None
        cne = None
        filterType = "CQL"
        useHttps = False
        filterText = None
        extraMps = None
        localCne = "local-cne"
        timeout = 3600
        for opt, arg in opts:
            if opt == '-n':
                userName = arg
            elif opt == '-p':
                password = arg
            elif opt == '-x':
                cne = arg
            elif opt == '-q':
                query = arg
            elif opt == '-b':
                bidir = True
            elif opt == '-c':
                includeCA = True
            elif opt == '-C':
                includeCI = True
            elif opt == '-z':
                useHttps = True
            elif opt == '-l':
                columns = arg
            elif opt == '-a':
                summariesOnly = True
            elif opt == '-w':
                watchlistMetadata = True
            elif opt == '-s':
                showMeasurementPoints = True
            elif opt == '-t':
                filterType = arg
            elif opt == '-T':
                timeout = arg
            elif opt == '-f':
                filterText = arg
            elif opt == '-m':
                extraMps = arg
            elif opt == '-L':
                localCne = arg

        if len(args) == 1 and args[0] == 'version':
            self.version()
        elif len(args) < 2:
            self.help()
        cmd = args[0]
        if cmd not in ['pcap', 'gap-csv', 'message-csv', 'packet-csv', 'lens-csv', 'multihop-csv', 'mp-list',
                       'flow-index', 'clock-tracking']:
            self.help()

        try:
            timeout = int(timeout);
        except ValueError:
            self.help("Invalid timeout value.\n")

        if (timeout <= 0):
            self.help("Timeout has to be a positive number.\n")

        host, port = self.parseHost(args[1])
        self.client = CorvilApiMtomClient(host, port=port,
            password = password, username=userName,cne=cne, useHttps=useHttps, timeout=timeout)

        if self.client.hostIsLmc and cmd != "lens-csv" and cne is None:
            self.help()

        if self.client.hostIsLmc and cne is not None:
            baseParams = {'cne':cne}
        else:
            baseParams = {}

        if cmd == 'mp-list':
            self.get_mp_list()

        elif cmd == 'lens-csv':
            if len(args) < 3:
                self.help()
            period = args[2]
            view = 'Default'
            if len(args) == 4:
                view = args[3]
            dataGen = self.get_lens_csv(period, view)
            print '#client version: %s' % (VERSION,)
            for block in dataGen:
                sys.stdout.write(block)
            sys.exit(0)

        elif cmd == 'flow-index':
            if len(args) < 4 or len(args) > 5:
                self.help()
            aggr = []
            startTime = args[2]
            endTime = args[3]
            if len(args) >=5:
                aggr = args[4].split(",")
                if len(aggr) == 0:
                    self.help()
            dataGen = self.get_flow_index(startTime, endTime, aggr, watchlistMetadata, showMeasurementPoints,
                                          query, summariesOnly, baseParams)
            for block in dataGen:
                sys.stdout.write(block)
            sys.exit(0)

        elif cmd == 'multihop-csv':
            if len(args) < 6:
                self.help()
            timestamp = args[3]
            message_id = args[4]
            message_index = args[5]
            mpReq = args[2]
            dataGen = self.get_multihop_csv(timestamp,message_id,message_index,mpReq, baseParams)
            print '#client version: %s' % (VERSION,)
            for block in dataGen:
                sys.stdout.write(block)
            sys.exit(0)

        elif cmd == 'pcap':
            if len(args) < 5:
                self.help()
            mpReq = args[2]
            startTime = args[3]
            endTime = args[4]
            dataGen = self.get_pcap(bidir, baseParams, mpReq, startTime, endTime, filterText, filterType, extraMps)
            for block in dataGen:
                sys.stdout.write(block)
            sys.exit(0)

        elif cmd == 'gap-csv':
            if len(args) < 5:
                self.help()
            mpReq = args[2]
            startTime = args[3]
            endTime = args[4]
            dataGen = self.get_gap_csv(mpReq, startTime, endTime, baseParams, filterText, filterType)
            print '#client version: %s' % (VERSION,)
            for block in dataGen:
                sys.stdout.write(block)
            sys.exit(0)

        elif cmd == 'message-csv':
            if len(args) < 5:
                self.help()
            mpReq = args[2]
            startTime = args[3]
            endTime = args[4]
            filters = []
            filterRule = {}
            filterRule['filterText'] = filterText
            filterRule['filterType'] = filterType
            filters.append(filterRule)
            dataGen = self.get_message_csv( bidir, includeCA, includeCI, columns, baseParams, mpReq, startTime, endTime, filters)
            print '#client version: %s' % (VERSION,)
            for block in dataGen:
                sys.stdout.write(block)
            sys.exit(0)

        elif cmd == 'packet-csv':
            if len(args) < 5:
                self.help()
            mpReq = args[2]
            startTime = args[3]
            endTime = args[4]
            dataGen = self.get_packet_csv(bidir, columns, baseParams, mpReq, startTime, endTime, filterText, filterType)
            print '#client version: %s' % (VERSION,)
            for block in dataGen:
                sys.stdout.write(block)
            sys.exit(0)

        elif cmd == 'clock-tracking':
            if len(args) < 4:
                self.help()
            if not localCne:
                self.help("Local CNE name cannot be empty.\n")
            startTime = args[2]
            endTime = args[3]
            mp = "channel//%s///ClockTracking" % (localCne)
            dataGen = self.get_message_csv( False, False, False, None, baseParams, mp, startTime, endTime, [])
            print '#client version: %s' % (VERSION,)
            for block in dataGen:
                sys.stdout.write(block)
            sys.exit(0)


if __name__ == '__main__':
    c = MtomTool(commandLine=True)
    c.run(sys.argv[1:])

