from __future__ import absolute_import
from __future__ import print_function
import os
import sys
import json
import csv
import gzip
import re
import time
import voUtils
import requests
import socket
from xml.dom import minidom
import xml.etree.ElementTree as ET

useSix = False
try:
    import six.moves.urllib.request, six.moves.urllib.parse, six.moves.urllib.error
    useSix = True
except ImportError:
    #import urllib.quote
    import urllib

try:
    from urllib.request import urlopen, ProxyHandler, HTTPBasicAuthHandler, build_opener, install_opener, Request
except ImportError:
    from urllib2 import urlopen, ProxyHandler, HTTPBasicAuthHandler, build_opener, install_opener, Request
try:
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import HTTPError

from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'victorops_app', 'lib']))

from cim_actions import ModularAction, ModularActionTimer
import splunklib.client as client
import splunk.rest
from splunk.clilib.bundle_paths import make_splunkhome_path

## Retrieve a logging instance from ModularAction
## It is required that this endswith _modalert
logger = ModularAction.setup_logger('victorops_modalert')

myapp = 'victorops_app'
collection_name = 'mycollection'
proxy_collection_name = 'proxyconfig'
active_alerts_collection_name = 'activealerts'
deployment_details_collection_name = 'deployment'
tmp_routing_key = ''

logger.info('PYTHON VERSION: ' + sys.version)
logger.info(sys)
python3 = sys.version_info[0] >= 3

splunkVersion = "unknown"

class VictorOpsModularAction(ModularAction):

    #=========================
    # Modular Action Overrides
    #=========================
    ## This method will initialize VictorOpsModularAction
    def __init__(self, settings, logger, action_name=None):

        ## Call ModularAction.__init__
        super(VictorOpsModularAction, self).__init__(settings, logger, action_name)
        ## Initialize param.limit
        try:
            self.limit = int(self.configuration.get('limit', 1))
            if self.limit<1 or self.limit>30:
                self.limit = 30
        except:
            self.limit = 1

        # Extract and store session key
        self.sessionKey = self.settings.get('session_key')

    def validate(self, result):

        #logger.info('Validate called - configuration: ' + json.dumps(self.configuration))

        if len(self.sessionKey) == 0:
            logger.error ('Did not receive a session key!');
            raise Exception('Missing session_key')

    def dowork(self, result):
        #logger.debug('dowork config: ' + json.dumps(self.configuration));
        #logger.debug('dowork result: ' + json.dumps(result));

        if len(self.sessionKey) == 0:
            logger.error ('Did not receive a session key from splunkd. ');

        # Get web proxy configuration.
        proxyConfig = {}
        try:
            proxyConfig = voUtils.getWebProxyConfig(self.sessionKey,logger);
        except Exception as e:
            logger.error('Exception retrieving webProxy config');
            logger.error(e);

        settings = self.configuration;
        record_id = settings.get('record_id', '');
        key_name = settings.get('name', '');
        #logger.info('Received the record_id parameter: ' + record_id + ', key_name: ' + key_name);

        # get api and routing keys
        [api_key,routing_key] = voUtils.getCredentials(self.sessionKey,record_id,key_name,logger);

        # record_id of -1 indicates api_key is specified in $param.api_key$
        if record_id == '-1':
            for param in result:
                if "param.api_key" in param:
                    if len(result[param]) > 0:
                        api_key = result[param]
                        masked_api_key = voUtils.maskUrl(api_key)
                        logger.info("masked_api_key="+masked_api_key)

                        query=json.dumps({"org_name":"<internal>", "api_key": masked_api_key})
                        #logger.info("query: " + query)
                        service = voUtils.getService(self.sessionKey, myapp, logger);
                        collection = service.kvstore[collection_name]
                        if collection_name in service.kvstore:
                            result2 = None;
                            try:
                                result2 = collection.data.query(query=query);
                                #logger.info(len(result2))
                                if len(result2) > 0:
                                    #logger.info('Found existing api_record: ' + json.dumps(result2) )
                                    record_id = result2[0].get('_key')
                                else:
                                    # Insert new api record.
                                    #logger.info('Inserting new api record') 
                                    record = { 'api_key': masked_api_key, 'org_name': '<internal>', 'routing_key': '', 'is_default': 'false' }
                                    #logger.info(record)
                                    collection.data.insert(json.dumps(record));
                                    result2 = collection.data.query(query=query);
                                    #logger.info("_key after insert: " + result2[0].get('_key'))
                                    record_id = result2[0].get('_key')

                                    endpoint = "/servicesNS/nobody/victorops_app/storage/passwords"
                                    postargs = {"name": record_id, "password": api_key}
                                    response, content = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=self.sessionKey, raiseAllErrors=False, postargs=postargs)
                                    #logger.info('status='+str(response.status))
                                    if response.status != 201:
                                        logger.info("Failure creating storage/password for internal key");
   
                                settings['record_id'] = record_id

                            except Exception as e:
                                logger.error('Error with api key query or insert')
                                logger.error(e)

        if len(api_key) == 0:
            logger.error('API Key Record not found!');
            sys.exit(1);

        if len(routing_key) > 0:
            # Pass provisioned routing key in settings.
            settings['routing_key'] = routing_key;

        routing_key_override = settings.get('routing_key_override')
        if routing_key_override == '-1':
            for param in result:
                if "param.routing_key" in param:
                    if len(result[param]) > 0:
                        #logger.info("dowork: Setting routingKey with param: " + result[param])
                        settings['routing_key'] = result[param];
        elif len(routing_key_override) > 0:
            settings['routing_key'] = routing_key_override

        #logger.info("dowork: final routing_key=" + settings['routing_key'])

        success = self.send_notification(api_key, proxyConfig, result)

    #=================
    # Internal Methods
    #=================

    #
    # Method to add alert to active alerts collection, this is only done when alert recovery is enabled.
    # The purpose is to track active alerts so that alert recovery can clear alerts that are no longer
    # being generated.
    #
    # The data parameter contains information used to send the notification:
    #   data = dict(
    #       message_type=message_type, monitoring_tool=monitoring_tool,
    #       state_message=state_message, entity_id=entity_id,
    #       entity_display_name=entity_display_name, view_report=view_report,
    #       version=appVersion);
    #
    # The api_key_id parameter is the apiKey's _key parameter from collection: mycollection.
    # The endpoint parameter is the base URL of the endpoint to send recovery notification.
    # The api_key parameter is the masked api key associated with the alert.
    #
    def save_active_alert(self,api_key_id,data,endpoint,api_key,routing_key):

        #logger.info('Entering save_active_alert, api_key_id: ' + api_key_id + ', api_key: ' + api_key + ', routing_key: ' + routing_key)
        #logger.info('Entering save_active_alert')
        #logger.info(api_key_id)
        #logger.info(api_key)
        #logger.info(routing_key)

        settings = self.configuration;
        poll_interval = settings.get('poll_interval')
        inactive_polls = settings.get('inactive_polls')
        #logger.info("override poll_interval: " + str(poll_interval))
        #logger.info("override inactive_polls: " + str(inactive_polls))
        if poll_interval == None:
             #logger.info("poll_interval is None");
             poll_interval = ''
        if inactive_polls == None:
             #logger.info("inactive_polls is None");
             inactive_polls = ''

        query=json.dumps({"entityId": data.get('entity_id'), "monitoringTool" : data.get('monitoring_tool') });
        service = voUtils.getService(self.sessionKey, myapp, logger);
        #logger.info('Looking for existing active alert, query: ' + json.dumps(query));
        collection = service.kvstore[active_alerts_collection_name];
        if collection_name in service.kvstore:
            result = None;
            try:
                result = collection.data.query(query=query);
                # The active alerts record for either insert or update below.
                record = { "entityId" : data.get('entity_id'),
                           "messageType": data.get('message_type'),
                           "monitoringTool": data.get('monitoring_tool'),
                           "apiKeyId" : api_key_id,
                           "routingKey" : routing_key,
                           "lastGeneratedTime": str(time.time()),
                           "apiEndpoint": endpoint,
                           "api_key" : api_key,
                           "poll_interval" : poll_interval,
                           "inactive_polls" : inactive_polls};
                if len(result) > 0:
                    # Update lastGenerationTime in existing active alerts record.
                    #logger.info('Found existing active alert, updating, result: ' + json.dumps(result) + ', update record:  ' + json.dumps(record));
                    collection.data.update(result[0].get('_key'), json.dumps(record));
                else:
                    # Insert new active alerts record.
                    #logger.info('Inserting new record into active alerts collection: ' + json.dumps(record));
                    collection.data.insert(json.dumps(record));
            except Exception as e:
                logger.error('Error with active alerts query, insert, or update. Query: ' + json.dumps(query));
                logger.error(e);
        else:
            logger.error('Unexpected error - [' + active_alerts_collection_name + '] collection not found in KV store!');

    def send_notification(self, api_key, proxy, result):

        #logger.info('Entering send notification')

        settings = self.configuration;

        # deployment details, if any
        deploymentDetailsKV = voUtils.getService(self.sessionKey, myapp, logger).kvstore["deployment"]
        deploymentData = deploymentDetailsKV.data.query()

        #routing_key = settings.get('routing_key_override', settings.get('routing_key'))
        routing_key = settings.get('routing_key')

        if routing_key == 'No Routing Keys Found':
            routing_key = ''

        #for param in result:
        #   if "param.routing_key" in param:
        #       if len(result[param]) > 0:
        #           logger.info("send_notification: Setting routingKey with param: " + result[param])
        #           routing_key = result[param]
        #   if "param.api_key" in param:
        #       if len(result[param]) > 0:
        #           logger.info("send_notification: Setting api_key with param: " + voUtils.maskUrl(result[param]))
        #           api_key = result[param]

        message_type = settings.get('message_type')
        state_message = settings.get('state_message')
        view_report = self.settings.get('results_link')
        api_endpoint = "%s/%s" % (settings.get('api_endpoint').rstrip('/'), api_key)
        #logger.info("api_endpoint="+api_endpoint)

        monitoring_tool = settings.get('monitoring_tool', 'Splunk')
        if monitoring_tool == '':
            # monitoring_tool can be present but empty in certain cases.
            #monitoring_tool = 'Splunk';

            if self.app == "SA-ITOA":
                if self.action_mode == "adhoc":
                    monitoring_tool = "splunk-itsi"
                else:
                    monitoring_tool = "splunk"
            elif self.app == "SplunkEnterpriseSecuritySuite":
                if self.action_mode == "adhoc":
                    monitoring_tool = "splunk-es"
                else:
                    monitoring_tool = "splunk"
            else:
                monitoring_tool = "splunk"

        entity_id = settings.get('entity_id');
        if not entity_id:
            if monitoring_tool.lower() == 'splunk-es':
                entity_id = result.get('desc');
                if entity_id == None:
                    # suspect monitoring tool was set incorrectly, lets check search_name
                    entity_id = self.search_name;
                    if entity_id == None:
                        # give up
                        entity_id = "N/A"
            elif monitoring_tool.lower() == 'splunk-itsi':
                entity_id = result.get('itsi_group_id')
            else:
                entity_id = self.search_name;

        entity_display_name = settings.get('entity_display_name')
        if not entity_display_name:
            if monitoring_tool.lower() == 'splunk-es':
                entity_display_name = result.get('desc');
                if entity_display_name == None:
                    entity_display_name = entity_id;
            elif monitoring_tool.lower() == 'splunk-itsi':
                entity_display_name = result.get('itsi_group_title')
            else:
                entity_display_name = entity_id;

        if not state_message:
            if monitoring_tool.lower() == 'splunk-es':
                state_message = result.get('desc');
            elif monitoring_tool.lower() == 'splunk-itsi':
                state_message = result.get('itsi_group_title')

        if routing_key:
            api_endpoint = "%s/%s" % (api_endpoint, routing_key);

        if not api_endpoint.startswith('https'):
            logger.error("VictorOps API Endpoint is insecure");
            return False

        # Flag indicating if alert recovery is disabled by the alert's configuration.
        recovery_enabled_by_alert = settings.get('enable_recovery', '1');
        logger.info('Is recovery enabled by alert: ' + recovery_enabled_by_alert);

        appVersion=voUtils.getAppVersion();
        #logger.debug('Adding app version: ' + appVersion + ' to alert payload!');
        data = dict(
            message_type=message_type,
            monitoring_tool=monitoring_tool,
            state_message=state_message,
            entity_id=entity_id,
            entity_display_name=entity_display_name,
            view_report=view_report,
            victorops_version=appVersion,
            python_version=sys.version,
            splunk_version=splunkVersion
        );

        #logger.info(data)
        # is this a hybrid-action deployment? If so, set "manager_host_url" in the "deployment_details_lookup"
        # It's the only way we know how to include valid ITSI links in the alerts.
        ea_mgr = None
        try:
            ea_mgr = deploymentData[0]["manager_host_url"]
        except Exception as ex:
            logger.info("No hybrid-action deployment config details found.")

        # Add deep-dive link annotation.
        # parse off host/port from view_report
        if monitoring_tool.lower() == 'splunk-itsi':
            logger.info("monitoring_tool is splunk-itsi, adding view_report")
            if view_report != None:
                m = re.match("(.+?)(?=app\/SA-ITOA)", view_report)
                if m:
                    web_url = ea_mgr if ea_mgr else m.group(1)
                    deepdive_report = web_url + '/en-US/app/itsi/itsi_event_management?earliest=-24h&episodeid='+entity_id+'&tabid=impact'
                    deepdive_name = "vo_annotate.u.ITSI Filtered Episode Review"
                    data[deepdive_name]=deepdive_report;
                    episode_review = web_url + '/en-US/app/itsi/itsi_event_management?earliest=-24h'
                    episode_name = "vo_annotate.u.ITSI Episode Review"
                    data[episode_name] = episode_review;
        else:
            # Add alert link annotation.
            data["vo_annotate.u.Alert Link"] = view_report # this doesn't have a sensible destination in ITSI

        if monitoring_tool.lower() == 'splunk-es':
            logger.info("monitoring_tool is splunk-es, adding view_report")
            if view_report != None:
                m = re.match("(.+?)(?=app\/SplunkEnterpriseSecuritySuite)", view_report)
                if m:
                    web_url = m.group(1)
                    event_id = result.get('event_id')
                    if event_id == None:
                        event_id = ''
                    earliest = result.get('_time')
                    if earliest == None:
                        earliest = ''
                    #latest = int(earliest)+1
                    latest = ''
                    #if python3 == True:
                    if useSix == True:
                        incident_review_report = web_url + '/en-US/app/SplunkEnterpriseSecuritySuite/incident_review?earliest='+str(earliest)+'&latest='+str(latest)+'&search=event_id%3D'+six.moves.urllib.parse.quote(event_id)
                    else:
                        incident_review_report = web_url + '/en-US/app/SplunkEnterpriseSecuritySuite/incident_review?earliest='+str(earliest)+'&latest='+str(latest)+'&search=event_id%3D'+urllib.quote(event_id)
                    incident_review_name = "vo_annotate.u.Incident Review for " + entity_display_name
                    data[incident_review_name]=incident_review_report;

                # - Add all result fields that have values and name doesn't start with "_"
                for item in result:
                    if item[0] != "_" and result[item] != '':
                        data[item] = result[item]

        record_id = settings.get('record_id', '');
        endpoint = settings.get('api_endpoint');
        #logger.info("record_id="+record_id);

        payload = self.settings;
        payload.update(data);
        payload.pop("configuration");
        payload.pop("session_key");

        #logger.info("payload: ")
        #logger.info(payload)

        # Send notification.
        voUtils.send_notification(self.sessionKey, api_endpoint, proxy, payload, logger);

        # Persist active alert in support of alert recovery. The is_active flag is set when the alert
        # is generated by a configured alert actions vs. a test alert from the UI. The recovery_enabled_by_alert
        # flag is set by alert configuration.
        # NOTE: splunk-itsi alerts are NOT recovered because ITSI itself implements alert recovery.
        if monitoring_tool != 'splunk-itsi' and result.get('is_active') and recovery_enabled_by_alert == '1':
            # Persist active alert for alert recovery.
            logger.info('Alert recovery is enabled, persisting active alert!');
            self.save_active_alert(record_id,data,endpoint,voUtils.maskUrl(api_key),routing_key);
        else:
            logger.info('Not persisting active alert because sending test alert or alert recovery is disabled globally or by the alert.');

        # If this is an ITSI server, then we want to add an incident link
        if monitoring_tool.lower() == 'splunk-itsi':
            org_slug,api_id,api_key= voUtils.getDataKey(self.sessionKey,'','',logger)
            #logger.info("org_slug="+org_slug)
            #logger.info("api_id="+api_id)
            #logger.info("api_key="+api_key)

            if org_slug == "":
                # Done
                logger.info('Data Key is not configured - skipping!');
            else:
                # give vo time to process
                time.sleep(1.6)

                #logger.info('Retrieved Data Config: ' + json.dumps(dataconfig));

                api_endpoint = 'https://api.victorops.com/api-public/v1/incidents'
                body = ''

                try:
                    # Possible race condition - alert sent to victorops; but, may not be processed yet and can't find incident
                    # Lets make at least 3 trys - with a second delay between them

                    incidentsNotDone = True
                    incidentsNotDoneCount = 0

                    while incidentsNotDone:

                        r=requests.get(api_endpoint, headers={"content-type":"application/json", "X-VO-Api-Id":api_id, "X-VO-Api-Key":api_key})
                        #logger.info(r);
                        d = r.json()
                        #logger.info(d);

                        incidents = d['incidents']
                        foundIncident = 'false'
                        for dic in incidents:
                            incidentNumber = ''
                            entityId = ''
                            for key in dic:
                                if key == 'entityId':
                                    entityId  = dic[key]
                                elif key == 'incidentNumber':
                                    incidentNumber  = dic[key]

                            if entityId != '' and incidentNumber != '' and foundIncident == 'false':

                                logger.info("comparing entityId("+str(entityId)+") with entity_id ("+str(entity_id))
                                if entity_id == entityId:
                                    foundIncident = 'true'
                                    logger.info("FOUND entity ID: " + entityId)

                                    incidentUrl = 'https://portal.victorops.com/ui/'+org_slug+'/incident/'+incidentNumber+'/details'
                                    #logger.info("incidentUrl: " + incidentUrl)


                                    data = {
                                        "is_group" : True,
                                        "name" : "itsi_event_action_link_ticket",
                                        "ids": [entityId],
                                        "parms" : {
                                            "action.itsi_event_action_link_ticket.param.kwargs" : "",
                                            "action.itsi_event_action_link_ticket.param.operation" : "upsert",
                                            "action.itsi_event_action_link_ticket.param.ticket_id" : "Incident " + incidentNumber,
                                            "action.itsi_event_action_link_ticket.param.ticket_system" : "VictorOps",
                                            "action.itsi_event_action_link_ticket.param.ticket_url" : incidentUrl
                                        }
                                    }

                                    # if we're in a hybrid-action environment, we need to change how we do the search
                                    ea_role = None
                                    try:
                                        ea_endpoint = self.settings.get("server_uri") + "/servicesNS/nobody/SA-ITOA/configs/conf-itsi_settings/episode_action_dispatch/"
                                        itsi_resp, itsi_content = splunk.rest.simpleRequest(ea_endpoint, method='GET', sessionKey=self.sessionKey, raiseAllErrors=False)
                                        itsi_root = ET.fromstring(itsi_content)
                                        maybe_content = itsi_root.find(".//{http://www.w3.org/2005/Atom}title[.='episode_action_dispatch']../{http://www.w3.org/2005/Atom}content")
                                        ea_role = maybe_content.find(".//{http://dev.splunk.com/ns/rest}key[@name='role']").text if maybe_content != None else ""
                                    except Exception as e:
                                        logger.info("failed to query for server role")
                                        logger.info(e)

                                    search_remote = '| earemotesearch remote_spl="search `itsi_event_management_group_index`  itsi_group_id="'+entityId+'" | dedup itsi_group_id | fields *  | `itsi_notable_event_actions_temp_state_values` | `itsi_notable_group_lookup` | `itsi_notable_event_actions_coalesce_state_values` |  sendalert "itsi_event_action_link_ticket"  param.ticket_id=\\"Incident #'+incidentNumber+'\\" param.operation="upsert" param.kwargs="" param.ticket_system="VictorOps" param.ticket_url="https://portal.victorops.com/ui/'+org_slug+'/incident/'+incidentNumber+'/details""'
                                    search_local = 'search `itsi_event_management_group_index`  itsi_group_id="'+entityId+'" | dedup itsi_group_id | fields *  | `itsi_notable_event_actions_temp_state_values` | `itsi_notable_group_lookup` | `itsi_notable_event_actions_coalesce_state_values` |  sendalert "itsi_event_action_link_ticket"  param.ticket_id="Incident #'+incidentNumber+'" param.operation="upsert" param.kwargs="" param.ticket_system="VictorOps" param.ticket_url="https://portal.victorops.com/ui/'+org_slug+'/incident/'+incidentNumber+'/details"'
                                    searchString = search_remote if ea_role == "executor" else search_local
                                    #logger.info("searchString="+searchString);
                                    endpoint = '/services/search/jobs'
                                    postArgs = {'search':searchString}
                                    response, content = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=self.sessionKey, raiseAllErrors=False, postargs=postArgs)
                                    #logger.info(content)
                                    sid = minidom.parseString(content).getElementsByTagName('sid')[0].childNodes[0].nodeValue
                                    #logger.info(sid)
                                    if response.status != 201:
                                        logger.info('status='+str(response.status))
                                    else:
                                        endpoint = '/services/search/jobs/%s' % sid
                                        notDone = True
                                        while notDone:
                                            response, content = splunk.rest.simpleRequest(endpoint, method='GET', sessionKey=self.sessionKey, raiseAllErrors=False)
                                            notDoneStatus = re.compile(b'isDone">(0|1)')
                                            notDoneStatus = notDoneStatus.search(content).groups()[0]
                                            #logger.info('notDoneStatus=' + str(notDoneStatus))
                                            if notDoneStatus == b'1' :
                                                notDone = False
                                    break

                        if foundIncident == 'true':
                            incidentsNotDone = False
                        else:
                            logger.info("Incident Not There Yet!")
                            incidentsNotDoneCount = incidentsNotDoneCount + 1
                            if incidentsNotDoneCount > 3:
                                logger.info("Giving Up Looking for Incident Number!")
                                incidentsNotDone = False
                            else:
                                #logger.info("sleeping ...")
                                time.sleep(1.6)

                except HTTPError as e:
                    logger.error("Failure Retrieving incident for Adding Link to Episode - Is Data Key configured?")
                    #raise;

        else:
            #logger.info("Skipping Adding link to episode, message_type="+message_type)
            logger.info("Skipping Adding link to episode")

        #logger.info("Leaving send notification")

        return True;

    def get_incident(self, api_key, proxy, result):
        #logger.info('Entering get_incident')
        settings = self.configuration;

if __name__ == "__main__":

    try:

        if len(sys.argv) > 1 and sys.argv[1] == "--execute":

            ## Retrieve an instanced of VictorOpsModularAction and name it modaction
            ## pass the payload (sys.stdin) and logging instance
            modaction = VictorOpsModularAction(sys.stdin.read(), logger, "VictorOps")
            splunkVersion = voUtils.getSplunkVersion()

            #logger.info('Search Results File: ' + modaction.results_file);

            ## Add a duration message for the "main" component using modaction.start_timer as
            ## the start time
            with ModularActionTimer(modaction, 'main', modaction.start_timer):

                if os.path.exists(modaction.results_file):
                    #logger.info(modaction)
                    logger.info("modaction.app="+modaction.app)
                    logger.info("modaction.search_name="+modaction.search_name)
                    logger.info("modaction.action_mode="+modaction.action_mode)
                    #logger.info(modaction.results_file)
                    # Alert use case, action invoked from a search with results. Process search results and tie
                    # alert to the generating search.
                    #logger.info('Calling modaction.invoke(), from search results.');
                    try:
                        fh = gzip.open(modaction.results_file, "rt")
                    except ValueError:
                        # Workaround for Python 2.7 under Windows
                        fh = gzip.open(modaction.results_file, "r")

                    #with gzip.open(modaction.results_file, 'rt') as fh:
                    if fh != None:
                        ## Iterate the result set using a dictionary reader
                        ## We also use enumerate which provides "num" which
                        ## can be used as the result ID (rid)
                        for num, result in enumerate(csv.DictReader(fh)):
                            #logger.info("num="+str(num))
                            #logger.info(result)
                            ## results limiting
                            if num>=modaction.limit:
                                break;
                            ## Set rid to row # (0->n) if unset
                            result.setdefault('rid', str(num));
                            ## Update the ModularAction instance
                            ## with the current result.  This sets
                            ## orig_sid/rid/orig_rid accordingly.
                            modaction.update(result);
                            ## Generate an invocation message for each result.
                            ## Tells splunkd that we are about to perform the action
                            ## on said result.
                            modaction.invoke();
                            ## Validate the invocation
                            modaction.validate(result);
                            ## Set flag indicating the alert should be made active to enable alert recovery.
                            result.setdefault('is_active', 'yes');
                            ## This is where we do the actual work.  In this case
                            ## we are calling out to an external API and creating
                            ## events based on the information returned
                            #logger.info("calling dowork()")
                            modaction.dowork(result);
                            #logger.info("return from dowork()")
                            ## rate limiting
                            time.sleep(1.6);
                    else:
                        logger.warn('File not opened!');
                else:
                    # Not an alert (i.e. it's a test), search results file does not exist. This
                    # code is invoked when the test link is clicked.
                    #logger.info('Calling modaction.invoke(), w/out processing results file.');
                    modaction.invoke();
                    ## Validate the invocation
                    #logger.info('Calling modaction.validate()');
                    modaction.validate({});
                    ## This is where we do the actual work.  In this case
                    ## we are calling out to an external API and creating
                    ## events based on the information returned
                    #logger.info('Calling modaction.dowork()');
                    modaction.dowork({});
        else:
            logger.error('Unsupported execution mode (expected --execute flag)');
            sys.exit(2);

    except Exception as e:
        ## adding additional logging since adhoc search invocations do not write to stderr
        try:
            modaction.message(e, status='failure', level=logging.CRITICAL);
        except:
            logger.critical(e);
            sys.exit(3);
