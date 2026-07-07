#!/usr/bin/python

import cStringIO
import merger
import subprocess
from CorvilApiStreamingClient import *
from config_util import *
import sys      ## For appending the library path
import os
sys.path.append('%s/pexpect-2.3' % os.path.dirname(__file__))
import pexpect
import urllib

PASSWORD_MASK = "**********"

def get_pcap(sessions, start, end, SrcIP, SrcPort, DstIP, DstPort, host, config, logger):

    protocolUsed, client = get_client(host, int(config.port), config.username, config.password, int(config.encrypted), corvil_api_mtom_client=True)
    logger.info("Connection with host %s is established using %s mode" % (host, protocolUsed))

    # Try to get all the channels
    sc = client.getSudsClient()
    summary = sc.service.getSummary("", client.createObject("ns0:ReportingPeriod")['1-hour'])
    channels = summary.channel
    mps = set()

    for session in sessions:
        for channel in channels:
            channel_name = urllib.unquote(channel._name)
            session_name = "//"+ session
            if channel_name.endswith(session_name):
                mps.add(channel._name)
                break

    logger.info("Exporting channels: " + ",".join(mps))

    # Now the pcaps
    pcap = None
    for mp in mps:
        logger.info("now pcap..." + SrcIP + DstIP)
        mpReq = client.createMeasurementPointRequest(mp)
        mpFilt = client.createObject("ns0:FilterDefinition")
        trafficRule = client.createObject("ns0:TrafficFilterRule")
        trafficRule._match = "show-if-is"
        trafficRule._destinationIp = SrcIP
        trafficRule._sourceIp = DstIP
        trafficRule._sourcePort = DstPort
        trafficRule._destinationPort = SrcPort
        mpFilt.trafficFilterSequence.trafficFilterRule.append(trafficRule)
        mpFilt.trafficFilterSequence._allOtherTraffic = "hide"
        timeRange = client.createTimeRangeNs(start, end)
        params = {'bothDirections': "true"}
        dataGen = client.getPcapInBlocks(mpReq, timeRange, mpFilt, params=params)
        data = "".join(dataGen)
        # now merge
        if not pcap:
            pcap = data
        else:
            merged = merger.PcapMerger(cStringIO.StringIO(pcap), cStringIO.StringIO(data))
            pcap = merged.data

    return pcap

def get_flow_data(host, start, end, DstIP, SrcIP, filter, config, logger):

    protocolUsed, client  = get_client(host, int(config.port), config.username, config.password, int(config.encrypted))
    logger.info("Connection with host %s is established using %s mode" % (host, protocolUsed))

    query = "ip.src == " + SrcIP  # default filter by src

    if (filter == "SrcIP"):
        query = "ip.src == " + SrcIP
    elif (filter == "DstIP"):
        query = "ip.dst == " + DstIP

    aggregation = ['talkers']
    summariesOnly = False

    dataGen = client.get_flow_index(start, end, aggregation=aggregation, query=query, summariesOnly=summariesOnly)
    data = "".join(dataGen)
    return data

def create_session(username, password, cne_host, suspicious_session, session_config, logger):
    def validateUser():
        result = child.expect(['[Pp]assword:', expect])
        if result == 0:
            child.sendline(password)

    # unsetting 'LD_LIBRARY_PATH' to avoid `OPENSSL_1.0.0 not found (required by ssh)' error.
    if 'LD_LIBRARY_PATH' in os.environ.keys():
            LD_LIBRARY_PATH = os.environ['LD_LIBRARY_PATH']
            os.environ['LD_LIBRARY_PATH'] = ""

    errorMessage = "Error: "
    expect = ".*\$ "
    try:
        child = pexpect.spawn('ssh %s@%s' % (username, cne_host))
        result = child.expect(['.*Are you sure you want to continue connecting (yes/no)?.*', '[Pp]assword:', pexpect.EOF, pexpect.TIMEOUT], timeout=180)
        if result == 0:
            child.sendline("yes")
            child.expect('[Pp]assword:')
            child.sendline(password)
        elif result == 1:
            child.sendline(password)
        elif result == 2:
            logger.error(child.before.strip('\n'))
            return False
        elif result == 3:
            logger.error("Cannot establish connection with host %s" % cne_host)
            return False

        result = child.expect([".*More.*", ".*User is not allowed command line access.*", pexpect.TIMEOUT])
        if result == 0:
            child.sendline('\003')
            child.expect(expect)
        elif result == 1:
            logger.info("Admin user should be configured in connector config for session creation.")
            return False
        child.expect(expect)

        logger.info("Session config: %s" % session_config)

        for command in session_config.split("\n"):
            #Do not create subnet-group if it is already present
            if ("subnet " in command) and ("Created: subnet-group" not in child.after):
                continue

            child.sendline(command)
            child.expect(expect)
            if errorMessage in child.after:
                logger.error('Error occurred while executing command: %s' % command)
                raise Exception('Error occurred while executing command: %s' % command)

        logger.info("Session '%s' created successfully on Corvil Appliance '%s'." % \
                    (suspicious_session, cne_host))
        return True
    except Exception, e:
        logger.error(str(e))
        #Running rollback command
        child.sendline("no session %s" % suspicious_session)
        validateUser()
        child.sendline("no subnet-group %s" % suspicious_session)
        validateUser()

        return  False
    finally:
        #updating 'LD_LIBRARY_PATH' once session is created using ssh
        if 'LD_LIBRARY_PATH' in os.environ.keys():
            os.environ['LD_LIBRARY_PATH'] = LD_LIBRARY_PATH

def retrieve_authentication_details(auth_script, use_auth_script):
    if (not int(use_auth_script)):
        raise Exception("Cannot use Authentication script to retrieve details.")

    process = subprocess.Popen(['sh', auth_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    returncode = process.wait() # Wait for process to complete.

    credentials = process.stdout.readlines()
    errors = process.stderr.readline()

    if returncode != 0:
        raise Exception("Unable to retrieve authentication details. Script '%s' returned error: '%s' Exit value: %s." % (auth_script, errors.rstrip("\n"), returncode))
    elif credentials:
        if len(credentials)==2:
            username = credentials[0].rstrip("\n")
            password = credentials[1].rstrip("\n")
            return (username, password)
        else: #Auth Script returns credentials in incorrect format
            raise Exception("Unable to retrieve authentication details. Output from Authorization script should be two lines, username followed by password.")
    else:
        raise Exception("Unable to retrieve authentication details.")

def fetch_valid_credentials(username, password, auth_script, use_auth_script, host, session_key=None):
    if username is None and password is None:
        return retrieve_authentication_details(auth_script, use_auth_script)
    elif password == PASSWORD_MASK:
        user = "%s@%s" % (username, host)
        return (username, PasswordsConfig.get_password(user, session_key=session_key))
    else:
        return (username, password)

def get_client(host, port, username, password, encrypted, corvil_api_mtom_client=False):
    try:
        if encrypted:
            protocolUsed = "https"
            if corvil_api_mtom_client:
                return protocolUsed, CorvilApiMtomClient(host, port=port, password=password, username=username, cne=None, useHttps=True)
            else:
                return protocolUsed, MtomTool(host, port=port, password=password, username=username, cne=None, useHttps=True)
        else:
            protocolUsed = "http"
            if corvil_api_mtom_client:
                return protocolUsed, CorvilApiMtomClient(host, port=port, password=password, username=username, cne=None)
            else:
                return protocolUsed, MtomTool(host, port=port, password=password, username=username, cne=None)
    except Exception , ex:
        raise Exception("Cannot connect with host %s: %s" % (host, str(ex)))
