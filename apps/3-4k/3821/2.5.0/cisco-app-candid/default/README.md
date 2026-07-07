# ABOUT CISCO CANDID
Cisco Candid is an intent assurance appliance for ACI (Application Centric Infrastructure) which raises issues or concerns as Smart Events against the Intent in ACI and providing information on what could be affecting the underlying infrastructure configurations, helping mitigate direct impact on daily business services. 
This rich information is discovered through RESTful interfaces provided by Cisco Candid to index in Splunk.
The Cisco Candid App for Splunk Enterprise offers interactive and insightful dashboards to Candid users to:
 1.) Track Smart Events over epochs,
 2.) View event changes across epochs reported by Candid Intent Assurance software,
 3.) Correlate event information across different Splunk applications(for ex. Cisco ACI app for Splunk) for useful insights into the events,
 4.) 

# ABOUT THIS APP


# REQUIREMENTS

* Splunk version supported 6.5 and 6.6, 7.0
* This main App requires "Cisco Candid Add-on for Splunk Enterprise" version 1.0

# Recommended System configuration

* Splunk search head system should have minimum 8 GB of RAM and a octa-core CPU to run this app smoothly.


# Topology and Setting up Splunk Environment
  
 1)  Install main app (Cisco Candid for Splunk Enterprise) and Add-on app (Cisco Candid Add-on for Splunk Enterprise) on a single machine.
* Here both the app resides on a single machine.
* Main app uses the data collected by Add-on app and builds dashboard on it
 2) Install the main app (Cisco Candid for Splunk Enterprise) on Search Head and Add-on app (Cisco Candid Add-on for Splunk Enterprise) on Indexer/Forwarder
 * Here both the app resides on a different machines.
 * Main app uses the data collected by Add-on app and builds dashboard on it. Ensure that the index '<defaults to "main">' is searchable by the Search Head


* This app can be installed through UI using "Manage Apps" or extract zip file directly into /opt/splunk/etc/apps/ folder.
* Restart Splunk.
* Login to Splunk: http://<your_splunk_host:port>
* Open browser: http://<your_splunk_host:port>/en-US/debug/refresh. Click "Refresh"
* Open browser: http://<your_splunk_host:port>/en-US/_bump 
    (To pull all updated web resources from the server to the browser, to modify the cached items such as js, cookies, images etc..)
* Restart Splunk

# Installation of Add-on
* This Add-on app can be installed through UI using "Manage Apps" or extract zip file directly into /opt/splunk/etc/apps/ folder.
* Ref documentation provided by "Cisco Candid Add-on for Splunk Enterprise" for Configuration of Add-on


# TEST YOUR INSTALL

* Once  Add-on app  is configured to receive data from Candid, The main app dashboard can take some time before the data is populated in all panels. A good test to see that you are receiving all of the data is to run this search after several minutes:

    index="<your index>" | stats count by sourcetype

In particular, you should see the sourcetype:
* cisco:candid:events

If you don't see these sourcetypes, have a look at the messages output by the scripted input: collect.py. Here is a sample search that will show them:

  index=_internal component="ExecProcessor" collectCandid.py "Candid Error:" | table _time host log_level message


# ABOUT THE DATA

Below are two sample event records. First one gives health detail for tenant with name "common" and the other one gives a fault detail for the same tenant.

1)

2014-04-25 00:38:07     dn=uni/tn-common/health status=created,modified updTs=2014-04-25T04:52:32.274+00:00     chng=0  cur=100 maxSev=cleared  modTs=never     twScore=100     rn=health       prev=100        childAction=    dn=uni/tn-common        lcOwn=local     ownerKey=       name=common     descr=  status=created,modified monPolDn=uni/tn-common/monepg-default   modTs=2014-04-23T22:14:01.702+00:00     ownerTag=       uid=0   rn=tn-common    childAction=    component=fvTenant

2)

2014-04-25 00:38:08     status=created,modified domain=tenant   code=F1228      occur=1 subject=contract        severity=minor  descr=Contract default configuration failed due to filter-not-present   origSeverity=minor      rn=fault-F1228  childAction=    type=config     dn=uni/tn-common/oobbrc-default/fault-F1228     prevSeverity=minor      modTs=never     highestSeverity=minor   lc=raised       changeSet=      created=2014-04-23T22:24:37.274+00:00   ack=no  cause=configuration-failed      rule=vz-abrcp-configuration-failed      lastTransition=2014-04-23T22:26:57.046+00:00    dn=uni/tn-common        lcOwn=local     ownerKey=       name=common descr=  status=created,modified monPolDn=uni/tn-common/monepg-default   modTs=2014-04-23T22:14:01.702+00:00     ownerTag=       uid=0   rn=tn-common    childAction=    component=fvTenant


# Support

* This app is supported by Cisco Systems.
* Email support during weekday business hours. Please ask question or send an email to nilaysh@cisco.com



