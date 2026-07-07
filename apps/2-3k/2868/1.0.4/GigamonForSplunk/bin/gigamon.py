import sys, xml.dom.minidom, xml.sax.saxutils, logging, urllib2, ConfigParser, base64, json, os, platform, os.path, sched, time, pickle, urllib
from datetime import date, timedelta, datetime
import json, requests
from datetime import datetime, timedelta
from GigamonAPI import GigamonAPI
from credential import credential

_MI_APP_NAME = 'Gigamon For Splunk Modular Input'
_SPLUNK_HOME = os.getenv("SPLUNK_HOME")
_SOURCETYPE = None
_SOURCE = None
_HOSTNAME = None
_DOPRINT_DEBUG = True
_SERVICE_CHECKPOINTS = ["audit", "event", "stats", "traffic"]

if _SPLUNK_HOME == None:
    _SPLUNK_HOME = os.getenv("SPLUNKHOME")
if _SPLUNK_HOME == None:
    _SPLUNK_HOME = "/opt/splunk"

_OPERATING_SYSTEM = platform.system()
_APP_NAME = "GigamonForSplunk"
_APP_HOME = os.path.join(_SPLUNK_HOME, "etc", "apps", _APP_NAME)
_CRED_HOME = os.path.join(_APP_HOME, "local")
_IS_WINDOWS = False

import splunk.Intersplunk
import splunk.entity as entity
import logging as logger
import ast

outputFileName = 'gigamon.py-modularinput.log'
outputFileLog = os.path.join(os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk',
                             outputFileName)
logger.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                   filename=outputFileLog,
                   filemode='a+',
                   level=logger.INFO,
                   datefmt='%Y-%m-%d %H:%M:%S %z')
logger.Formatter.converter = time.gmtime


class Unbuffered:
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        self.stream.write(data)
        self.stream.flush()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)

#SYSTEM EXIT CODES
_SYS_EXIT_FAILED_VALIDATION = 7
_SYS_EXIT_FAILED_GET_CREDENTIALS = 6

SCHEME = """<scheme>
    <title>Gigamon For Splunk</title>
    <description>Gigamon For Splunk queries and consumes the API information from a GigamonVUE-FM node.</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <endpoint>
        <args>
            <arg name="hostname">
                <title>GigamonVUE-FM Hostname</title>
                <description>The host GigamonVUE-FM to query for information. A corresponding credential must be stored.</description>
            </arg>
	    <arg name="username">
		<title>GigamonVUE-FM Username</title>
		<description>The username that has access to the API</description>
	    </arg>
            <arg name="services">
                <title>Services</title>
                <description>Each service goes further down the Rabbit Hole. Can impact licensing! "domain" is required. Valid Additional values: node, port, stats,audit,event,users,traffic. Separate each with a colon ":". </description>
            </arg>
	    <arg name="api">
		<title>API Version</title>
		<description>The API Version compatible with your GigamonVUE-FM. Valid: v1.1, v1.2, v1.3.</description>
	    </arg>
        </args>
    </endpoint>
</scheme>
"""

#SPLUNK SPECIFIC Modular Input Functions


def do_scheme():
    doPrint(SCHEME)
    # prints XML error data to be consumed by Splunk


def escape(s):
    return xml.sax.saxutils.escape(s)


def print_error(s):
    global _SOURCETYPE, _SOURCE, _HOSTNAME
    logger.error("host=%s sourcetype=%s source=%s %s" %
                 (_HOSTNAME, _SOURCETYPE, _SOURCE, s))
    do_event(s)


def catch_error(e):
    """ Catch Error and format into a JSON error object """
    global _SOURCETYPE
    myJson = {}
    myJson["timestamp"] = gen_date_string()
    myJson["log_level"] = "ERROR"
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    myJson["errors"] = [{
        "msg": str((e)),
        "exception_type": "%s" % type(e).__name__,
        "exception_arguments": "%s" % e,
        "filename": fname,
        "line": exc_tb.tb_lineno
    }]
    oldst = _SOURCETYPE
    _SOURCETYPE = "GigamonForSplunk:error"
    print_error("%s" % json.dumps(myJson))
    do_event("%s" % (json.dumps(myJson)))
    _SOURCETYPE = oldst


def buildCHKFilename(fmhost, service):
    return "%s_%s" % (fmhost, service)


def buildCheckpoints(hostname, services):
    svcs = {}
    for x in services:
        svcs[x] = buildCHKFilename(hostname, x)
    return svcs


def get_encoded_file_path(config, filename):
    return os.path.join(config["checkpoint_dir"], "giga_%s" % filename)


def save_checkpoint(config, filename):
    chk_file = get_encoded_file_path(config, filename)
    chk_time = (datetime.utcnow() - datetime.utcfromtimestamp(0)
                ).total_seconds()
    # just create an empty file name
    print_info("action=checkpointing status=save file=%s time=%d" %
               (chk_file, chk_time))
    f = open(chk_file, "w")
    f.write("%d" % chk_time)
    f.close()


def load_checkpoint(config, filename):
    chk_file = get_encoded_file_path(config, filename)
    # try to open this file
    try:
        f = open(chk_file, "r")
        chk_time = "%s" % (f.read().strip())
        f.close()
    except:
        # assume that this means the checkpoint is not there
        # Let's Default to 15 minutes ago. Just to start pulling data.
        wibbly_wobbly_timey_wimey = datetime.utcnow() - timedelta(minutes=15)
        default_time = (wibbly_wobbly_timey_wimey -
                        datetime.utcfromtimestamp(0)).total_seconds()
        print_info("action=default_checkpoint time=%d" % default_time)
        return default_time
    print_info("action=checkpoint status=load file=%s time=%s" %
               (chk_file, chk_time))
    return float(chk_time)


def validate_conf(config, key):
    if key not in config:
        raise Exception, "Invalid configuration received from Splunk: key '%s' is missing." % key


def print_debug(s):
    global _SOURCETYPE, _SOURCE, _HOSTNAME
    myStr = "app=%s source=%s sourcetype=%s host=%s %s" % (
        _APP_NAME, _SOURCE, _SOURCETYPE, _HOSTNAME, s)
    logger.debug(myStr)
    doPrint("DEBUG %s" % myStr, True)


def print_info(s):
    global _SOURCETYPE, _SOURCE, _HOSTNAME
    myStr = "app=%s source=%s sourcetype=%s host=%s %s" % (
        _APP_NAME, _SOURCE, _SOURCETYPE, _HOSTNAME, s)
    logger.info(myStr)
    doPrint("INFO %s" % myStr, True)


#read XML configuration passed from splunkd
def get_config():
    config = {}
    try:
        # read everything from stdin
        config_str = sys.stdin.read()
        # parse the config XML
        doc = xml.dom.minidom.parseString(config_str)
        root = doc.documentElement
        chkpointdir = root.getElementsByTagName(
            "checkpoint_dir")[0].firstChild.data
        config["checkpoint_dir"] = chkpointdir
        sessionkey = root.getElementsByTagName(
            "session_key")[0].firstChild.data
        config["session_key"] = sessionkey
        logger.debug("XML: found checkpoint_dir: %s" % chkpointdir)
        conf_node = root.getElementsByTagName("configuration")[0]
        if conf_node:
            logger.debug("XML: found configuration")
            logger.debug("%s" % conf_node)
            stanza = conf_node.getElementsByTagName("stanza")[0]
            if stanza:
                stanza_name = stanza.getAttribute("name")
                if stanza_name:
                    logger.debug("XML: found stanza " + stanza_name)
                    config["name"] = stanza_name
                    params = stanza.getElementsByTagName("param")
                    for param in params:
                        param_name = param.getAttribute("name")
                        logger.debug("XML: found param '%s'" % param_name)
                        if param_name and param.firstChild and \
                           param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                            data = param.firstChild.data
                            config[param_name] = data
                            logger.debug("XML: '%s' -> '%s'" %
                                         (param_name, data))

        if not config:
            raise Exception, "Invalid configuration received from Splunk."

        # just some validation: make sure these keys are present (required)
        validate_conf(config, "hostname")
        validate_conf(config, "username")
        validate_conf(config, "services")
        validate_conf(config, "api")
    except Exception, e:
        raise Exception, "Error getting Splunk configuration via STDIN: %s" % str(
            e)

    return config


def get_validation_data():
    val_data = {}
    # read everything from stdin
    val_str = sys.stdin.read()
    # parse the validation XML
    doc = xml.dom.minidom.parseString(val_str)
    root = doc.documentElement
    logger.debug("XML: found items")
    item_node = root.getElementsByTagName("item")[0]
    if item_node:
        logger.debug("XML: found item")
        name = item_node.getAttribute("name")
        val_data["stanza"] = name
        params_node = item_node.getElementsByTagName("param")
        for param in params_node:
            name = param.getAttribute("name")
            logger.debug("Found param %s" % name)
            if name and param.firstChild and \
               param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                val_data[name] = param.firstChild.data
    return val_data


def validate_arguments():
    _available_services = ["domain", "node", "port", "stats", "users", "audit",
                           "event", "neighbors", "traffic"]
    _valid_apis = ["v1", "v1.1", "v1.2", "v1.3"]
    val_data = get_validation_data()
    try:
        services = val_data["services"].split(':')
        if "domain" not in services:
            raise Exception, "Domain service not set. Please add it."
        for service in services:
            print_info("operation=validating_input service=%s" % (service))
            if service not in _available_services:
                print_error(
                    "operation=validate_arguments error=invalid_service service=%s"
                    % service)
                raise Exception, "Invalid Service set. Failed excuse was %s " % service
        api = val_data["api"]
        if api not in _valid_apis:
            raise Exception, "API Version not valid. Failed excuse was %s " % api
    except Exception, e:
        print_error("Invalid configuration specified: %s" % str(e))
        sys.exit(_SYS_EXIT_FAILED_VALIDATION)


def gen_date_string():
    st = time.localtime()
    tm = time.mktime(st)
    return time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime(tm))


def doPrint(stringIn, ISDEBUG=False):
    global _DOPRINT_DEBUG
    if (_DOPRINT_DEBUG and ISDEBUG):
        print stringIn
    if (not ISDEBUG):
        print stringIn


def init_stream():
    doPrint("<stream>")
    logger.debug("printed start of stream")


def end_stream():
    doPrint("</stream>")
    logger.debug("printed end of stream")


def do_event(event_data):
    global _SOURCETYPE, _SOURCE, _HOSTNAME
    if len(event_data) < 1:
        event_data = ""
    eventxml = "<event><data>%s</data><sourcetype>%s</sourcetype><source>%s</source><host>%s</host></event>\n" % (
        escape(event_data), escape(_SOURCETYPE), escape(_SOURCE),
        escape(_HOSTNAME))
    doPrint(eventxml)
    logger.debug("printed an event")


def do_done_event():
    global _SOURCETYPE, _SOURCE, _HOSTNAME
    eventxml = "<event><data></data><sourcetype>%s</sourcetype><source>%s</source><host>%s</host><done/></event>\n" % (
        escape(_SOURCETYPE), escape(_SOURCE), escape(_HOSTNAME))
    doPrint(eventxml)
    logger.debug("printed a done event")


def getCredentials(sK, realm, username):
    try:
        return credential(_APP_NAME, realm, username).getPassword(sK)
    except Exception, e:
        print_error("Getting Credentials Failed: %s" % e)
        sys.exit(_SYS_EXIT_FAILED_GET_CREDENTIALS)


def do_json_event(events):
    for evt in events:
        if "timestamp" not in evt:
            evt["timestamp"] = gen_date_string()
        do_event(json.dumps(evt))


def checkAPI(func, obj):
    myFunc = getattr(obj, func, None)
    if (callable(myFunc)):
        return True
    print_error("function=%s version=%s error=not_callable" %
                (func, obj.get_version()))
    return False


def processTimeSeries(obj, metric, cluster):
    for trend in obj["timeSeries"]["series"]:
        context = trend["context"]
        myCtx = {}
        for ctx in context:
            myCtx[ctx["name"]] = ctx["value"]
            print_debug("load stats context: %s" % myCtx)
        for dp in trend["dataPoints"]:
            dp["clusterId"] = cluster["clusterId"]
            try:
                dp["deviceIp"] = myCtx["host"]
            except:
                pass
            dp["timestamp"] = time.strftime("%a, %d %b %Y %H:%M:%S +0000",
                                            time.gmtime(dp["tsUtc"] / 1000))
            try:
                dp["portId"] = "%s/%s" % (myCtx["box"], myCtx["boxPort"])
            except:
                pass
            try:
                dp["mapName"] = myCtx["mapName"]
            except:
                pass
            dp["context"] = myCtx
            dp["metric"] = metric
            do_event(json.dumps(dp))


def run():
    global _SOURCETYPE, _SOURCE, _HOSTNAME, _SERVICE_CHECKPOINTS
    sys.stdout = Unbuffered(sys.stdout)
    print_info("app=%s os=\"%s\" app_home=\"%s\" " %
               (_APP_NAME, _OPERATING_SYSTEM, _APP_HOME))
    config = get_config()
    stanza = config["name"]
    hostname = config["hostname"]
    username = config["username"]
    services = config["services"].split(':')
    apiVersion = config["api"]
    _SOURCE = "gigamon:%s" % hostname
    _BASE_ST = "gigamon:api:service"
    _SOURCETYPE = _BASE_ST
    _HOSTNAME = hostname
    ### Build Checkpoint Files for checkpoint enabled services in _SERVICE_CHECKPOINTS
    _SERVICE_CHECKPOINTS = buildCheckpoints(_HOSTNAME, _SERVICE_CHECKPOINTS)
    print_debug("Built Checkpoints: %s" % _SERVICE_CHECKPOINTS)
    ### ST Set by Service Name
    print_info("set sourcetype to " + _SOURCETYPE)
    print_info("set source to " + _SOURCE)
    init_stream()
    print_info("key=modular_input status=start gkey=%s" % _HOSTNAME)
    try:
        gigaAPI = GigamonAPI(
            apiVersion,
            hostname=hostname,
            username=username,
            password=getCredentials(config["session_key"], hostname, username),
            useJson=True)
        ## Always output Licensing Information. It's small, but important.
        _SOURCETYPE = "%s:license" % _BASE_ST
        try:
            if (checkAPI("get_licensing", gigaAPI)):
                do_event(json.dumps(gigaAPI.get_licensing()))
        except:
            pass
        try:
            do_event(json.dumps(gigaAPI.get_system_info()))
        except:
            pass
        # If set, let's do Audit Logs

        if "audit" in services:
            try:
                _SOURCETYPE = "%s:audit" % _BASE_ST
                #LOAD CHECKPOINT
                audit_chkpoint = load_checkpoint(config,
                                                 _SERVICE_CHECKPOINTS["audit"])
                print_debug("audit checkpoint loaded: %s" % audit_chkpoint)
                #PULL EVENTS
                if (checkAPI("get_audit_logs", gigaAPI)):
                    evts = [x for x in gigaAPI.get_audit_logs((audit_chkpoint
                                                ))["auditLogEntries"]]
                    for evt in evts:
                        evt["timestamp"] = evt["ts"]
                    do_json_event(evts)
                #SAVE CHECKPOINT
                save_checkpoint(config, _SERVICE_CHECKPOINTS["audit"])
            except Exception, e:
                catch_error(e)
        if "event" in services:
            try:
                # If set, let's do Event Logs
                _SOURCETYPE = "%s:event" % _BASE_ST
                evt_chkpoint = load_checkpoint(config,
                                               _SERVICE_CHECKPOINTS["event"])
                print_debug("event checkpoint loaded: %s" % evt_chkpoint)
                if (checkAPI("get_fm_events", gigaAPI)):
                    evts = [
                        x
                        for x in gigaAPI.get_fm_events(evt_chkpoint)["events"]
                    ]
                    for evt in evts:
                        evt["timestamp"] = evt["ts"]
                    do_json_event(evts)
                save_checkpoint(config, _SERVICE_CHECKPOINTS["event"])
            except Exception, e:
                catch_error(e)
        if "traffic" in services:
            try:
                # LET's ANALYZE TRAFFIC!
                _SOURCETYPE = "%s:traffic" % _BASE_ST
                print_debug("checking API fr trafficAnalyzer")
                if (checkAPI("get_trafficAnalyzer", gigaAPI)):
                    for edpt in ["conversations", "apps", "protocols",
                                 "endpoints"]:
                        print_debug("starting trafficAnalyzer for %s" % edpt)
                        rst = gigaAPI.get_trafficAnalyzer(endpoint=edpt,
                                                          since="7-day")
                        context = {}
                        top = []
                        for it in rst:
                            if ("context" in rst[it]):
                                context = rst[it]["context"]
                                context["type"] = rst[it]["type"]
                                top = rst[it]["top"]
                                break
                        context["timestamp"] = gen_date_string()
                        print_debug("found %s items in top url: %s" %
                                    (len(top), gigaAPI.get_last_url()))
                        for evt in top:
                            evt["timestamp"] = context["timestamp"]
                            evt["start_time"] = context["startTime"]
                            evt["end_time"] = context["endTime"]
                            evt["type"] = context["type"]
                            print_debug("%s" % json.dumps(evt))
                        do_json_event(top)
            except Exception, e:
                catch_error(e)

        ## Domain Operations are required for all other calls.
        _SOURCETYPE = "%s:domain" % _BASE_ST
        domain = gigaAPI.get_nodes(flat=False)
        domain["timestamp"] = gen_date_string()
        for cluster in domain["clusters"]:
            if "clusterId" not in cluster and "clusterName" in cluster:
                cluster["clusterId"] = cluster["clusterName"]
            _SOURCETYPE = "%s:node" % _BASE_ST
            print_debug("starting cluster: %s" % cluster["clusterId"])
            cluster["timestamp"] = gen_date_string()
            do_event(json.dumps(cluster))
            if ("node" in services or "stats" in services or "port" in services
                or "neighbors" in services):
                print_debug("found node or stats or port in services")
                for member in cluster["members"]:
                    print_debug("member=%s" % member)
                    for device in member["deviceIps"]:
                        print_debug("device=%s" % device)
                        try:
                            if "users" in services:
                                _SOURCETYPE = "%s:users" % _BASE_ST
                                if (checkAPI("get_system_users", gigaAPI)):
                                    do_json_event(gigaAPI.get_system_users(
                                        cluster["clusterId"])["localUsers"])
                                do_json_event(gigaAPI.get_node_credentials(
                                )["devCredsList"])
                        except Exception, e:
                            catch_error(e)
                        try:
                            print_debug("loading inventory")
                            _SOURCETYPE = "%s:node" % _BASE_ST
                            inventory = gigaAPI.get_chassis_inventory(cluster["clusterId"])
                            print_debug("setting timestamp")
                            inventory["timestamp"] = gen_date_string()
                            print_debug("setting clustername: %s" % cluster)
                            inventory["clusterId"] = cluster["clusterId"]
                            print_debug("setting hostname: %s" % hostname)
                            inventory["hostName"] = hostname
                            print_debug("clearing ports")
                            if (len(inventory["chassisList"]) > 0):
                                if ("port" in services):
                                    ports = inventory["chassisList"][0]["ports"]
                                    #tunneled_ports = gigaAPI.get_tunneled_ports(device)
                                    #### Associate Tunneled Ports and Gigasmart Groups to Port information.
                                    _SOURCETYPE = "%s:port" % _BASE_ST
                                    for port in ports:
                                        port["timestamp"] = gen_date_string()
                                        port["clusterId"] = cluster["clusterId"
                                     ]
                                        port["deviceIp"] = device
                                        port["interfaceType"] = "port"
                                        do_event(json.dumps(port))
                                    _SOURCETYPE = "%s:maps" % _BASE_ST
                                    maps = gigaAPI.get_maps(cluster["clusterId"])["maps"]
                                    for mp in maps:
                                        mp["timestamp"] = gen_date_string()
                                        mp["clusterId"] = cluster["clusterId"]
                                        mp["deviceIp"] = device
                                        do_event(json.dumps(mp))
                                inventory["chassisList"][0]["ports"] = {}

                                if ("cards" in inventory["chassisList"][0]):
                                    for card in inventory["chassisList"][0][
                                        "cards"
                                    ]:
                                        _SOURCETYPE = "%s:port" % _BASE_ST
                                        card["timestamp"] = gen_date_string()
                                        card["clusterId"] = cluster["clusterId"
                                     ]
                                        card["deviceIp"] = device
                                        card["interfaceType"] = "card"
                                        do_event(json.dumps(card))
                            _SOURCETYPE = "%s:node" % _BASE_ST
                            do_event(json.dumps(inventory))
                            print_debug("starting gigasmart gsops call")
                            gsops = gigaAPI.get_gigasmart_ops(cluster["clusterId"])
                            print_info("count=%s item=gsops" %
                                       gsops["context"]["totalItems"])
                            if (gsops["context"]["totalItems"] > 0):
                                for gsop in gsops["gsops"]:
                                    gsop["timestamp"] = gen_date_string()
                                    gsop["interfaceType"] = "gsop"
                                    do_event(json.dumps(gsop))

                            print_debug("starting gigasmart gsGroups call")
                            gsPGs = gigaAPI.get_gigasmart_portgroups(cluster["clusterId"])
                            print_info("count=%s item=gsGroups" %
                                       gsPGs["context"]["totalItems"])
                            if (gsPGs["context"]["totalItems"] > 0):
                                for gsGroup in gsPGs["gsGroups"]:
                                    gsGroup["timestamp"] = gen_date_string()
                                    gsGroup["interfaceType"] = "gsGroup"
                                    do_event(json.dumps(gsGroup))

                        except Exception, e:
                            catch_error(e)
                        finally:
                            if ("stats" in services and checkAPI(
                                "get_port_stats", gigaAPI)):
                                try:
                                    _SOURCETYPE = "%s:stats" % _BASE_ST
                                    device_chkpoint = "%s_%s" % (
                                        _SERVICE_CHECKPOINTS["stats"], device)
                                    stats_chkpoint = load_checkpoint(
                                        config, device_chkpoint)
                                    print_debug(
                                        "trying to load stats for device %s" %
                                        device)
                                    #def get_port_stats(self, clusterId,startTime,metric,port="*"):
                                    for metric in gigaAPI.get_port_metrics():
                                        stats = gigaAPI.get_port_stats(
                                            cluster["clusterId"], stats_chkpoint, "now",
                                            metric)
                                        print_debug("load stats: %s" % stats)
                                        processTimeSeries(stats, metric,
                                                          cluster)
                                    #do_event(json.dumps(stats))
                                    print_debug("loading map stats")
                                    for metric in gigaAPI.get_map_metrics():
                                        stats = gigaAPI.get_map_stats(
                                            device, stats_chkpoint, "now",
                                            metric)
                                        print_debug(
                                            "loading map metrics for %s" %
                                            metric)
                                        processTimeSeries(stats, metric,
                                                          cluster)
                                    print_debug("loading gsops")
                                    for metric in gigaAPI.get_gigasmart_op_metrics(
                                    ):
                                        stats = gigaAPI.get_gigasmart_op_stats(
                                            device, stats_chkpoint, "now",
                                            metric)
                                        print_debug("loading gsop stats for %s"
                                                    % metric)
                                        processTimeSeries(stats, metric,
                                                          cluster)
                                    print_debug("loading gsGroups")
                                    for metric in gigaAPI.get_gigasmart_portgroup_metrics(
                                    ):
                                        stats = gigaAPI.get_gigasmart_portgroup_stats(
                                            device, stats_chkpoint, "now",
                                            metric)
                                        print_debug("loading gsGroups for %s" %
                                                    metric)
                                        processTimeSeries(stats, metric,
                                                          cluster)

                                    save_checkpoint(config, device_chkpoint)
                                except Exception, e:
                                    print_debug("last url call: %s" %
                                                gigaAPI.get_last_url())
                                    catch_error(e)
                            if ("neighbors" in services):
                                try:
                                    _SOURCETYPE = "%s:neighbors" % _BASE_ST
                                    nbrs = gigaAPI.get_port_neighbors(device)
                                    for port in nbrs["portNeighbors"]:
                                        for nbr in port["neighbors"]:
                                            nbr["dst_port"] = port["portId"]
                                            nbr["gigamon_clusterId"
              ] = cluster["clusterId"]
                                            nbr["gigamon_deviceIp"] = device
                                            nbr["timestamp"] = gen_date_string(
                                            )
                                            do_event(json.dumps(nbr))
                                except Exception, e:
                                    print_debug("last url call: %s" %
                                                gigaAPI.get_last_url())
                                    catch_error(e)
    except Exception, e:
        catch_error(e)
    do_done_event()
    print_debug("Ending Stream")
    end_stream()
    _SOURCETYPE = "%s:service" % _BASE_ST
    print_info("key=modular_input status=stop gkey=%s" % _HOSTNAME)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            validate_arguments()
        elif sys.argv[1] == "--test":
            print 'No tests for the scheme present'
        else:
            print 'You giveth weird arguments'
    else:
        run()

    sys.exit(0)
