# ABOUT THIS APP

The Technology Add-on for Violin Systems FSP is used to gather data from Violin FSP, do indexing on it and provide the indexed data to "Violin FSP App for Splunk" which runs searches on indexed data and builds dashboards using it.


# REQUIREMENTS

* Splunk version 6.5.x and 6.6.x
* Violin FSP 7000 series.
* If using a forwarder, it must be a UNIVERSAL forwarder on concerto.
* A Heavy forwarder to collect data from Violin FSP platform using REST API. Same heavy forwarder can also be used to receive forwarded logs from universal forwarder and forward them to indexer.

* Appropriate User ID and password for collecting data from Violin Concerto using REST API.

# RECOMMENDED SYSTEM CONFIGURATION

* Splunk forwarder system should have 4 GB of RAM and a quad-core CPU to run this Technology Add-on smoothly.


# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

* This app has been distributed in two parts.

  1) Add-on app, which runs collector scripts and gathers data from Violin FSP, does indexing on it and provides indexed data to Main app.
  2) Main app, which receives indexed data from Add-on app, runs searches on it and builds dashboard using indexed data.

* This App can be set up in two ways:
  1) **Standalone Mode**: Install main app and Add-on app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup

     * Here both the app resides on a single machine.
	 * Add-on needs to be installed on Concerto's Universal forwarder and start forwarding data to standalone splunk server.
     * Main app uses the data collected by Add-on.

   2) **Distributed Environment**: Install main app and Add-on on search head and Add-on on Heavy forwarder (for REST API) and universal forwarder (for log collection).

     * Here also both the app resides on search head machine, but no need to configure Add-on on search head.
     * Only Add-on needs to be installed and configured on Heavy forwarder system and universal forwarder.
     * Execute the following command on Heavy forwarder to forward the collected data to the indexer.
       /opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997
     * On Indexer machine, enable event listening on port 9997 (recommended by Splunk).
     * Main app on search head uses the received data and builds dashboards on it.

# INSTALLATION OF APP

* This app can be installed through UI using "Manage Apps" or extract zip file directly into /opt/splunk/etc/apps/ folder.

# CONFIGURATION OF APP

## REST API Events:
*  After installation, Go to Settings->Data inputs->Violin Systems REST Input Modular. The set up screen will open which will ask for Violin Systems Concerto credentials. Provide host, username, password for Concerto and save them.
*  Splunk REST API will encrypt the password and store it in Add-on's folder itself in encrypted form, REST modular script will fetch these credentials through REST API to connect to the Violin FSP.


## Concerto logs
* On Concerto, user needs to configure log collection and forwarding to Heavy forwarder/Indexer. Since universal forwarder doesn't have front end UI enabled, user needs to first extract TA_violin-fsp.tar.gz at $SPLUNK_HOME/etc/apps.
* Technology Add-on contains settings in inputs.conf.example to monitor the var/log/messages and callhome.log file but it is kept disabled by default.
* Copy inputs.conf.example from TA_violin-fsp/README/ to TA_violin-fsp/local/ folder
      Rename inputs.conf.example file under location TA_violin-fsp/local/ to inputs.conf
      By default these monitor stanzas are disabled, user has to make all disabled = 0
* If user doesn't want to install whole TA on universal forwarder then follow below manual configuration:
      Add inputs.conf with monitoring stanzas at /opt/splunkforwarder/etc/system/local/
      Add below monitoring stanzas in inputs.conf

    [monitor:///var/log/messages]
    sourcetype = violin:fsp:mglogs
    disabled = 0
    
    [monitor:///var/log/acm]
    sourcetype = violin:fsp:acmlogs
    disabled = 0
    
    [monitor:///PRODUCT/concerto/log/callhome/callhome.log]
    sourcetype = violin:fsp:mglogs
    disabled = 0
* Execute the following command on Heavy forwarder to forward the collected data to the indexer/Heavy forwarder.
       /opt/splunk/bin/splunk add forward-server <indexer_ip_address/heavy_forwarder_ip>:9997
	   Depending on the receiver in above command user needs to enable event listening on port 9997 either on heavy forwarder or on Indexer.
* Restart Splunk

# TEST YOUR INSTALL

The main app dashboard can take some time to populate the dashboards, once data collection is started. A good test to see that you are receiving all of the data we expect is to run this search after several minutes:

    search `get_vm_index` | stats count by sourcetype

In particular, you should see these sourcetypes:
* violin:fsp:rest
* violin:fsp:mglogs
* violin:fsp:acmlogs

If you don't see these sourcetypes, have a look at the messages for "violin:fsp:rest" .User can see logs at $SPLUNK_HOME/var/log/violin/violin_fsp.log file.

  
# SAMPLE EVENT GENERATOR

* The TA_violin-fsp, comes with sample data files, which can be used to generate sample data for testing. In order to generate sample data it requires SA-Eventgen application. The TA will generate sample data of rest api calls at an interval of 10 minutes and sample data of log files at an interval of 4 hours. You can update this configuration from eventgen.conf file available under $SPLUNK_HOME/etc/apps/default/.
 
# TROUBLESHOOTING

* Environment variable SPLUNK_HOME must be set
* To troubleshoot Violin FSP application, check $SPLUNK_HOME/var/log/violin/violin_fsp.log file.

# REFERENCES

* We have used external library requests_toolbelt (version: 0.8.0) to manage request with certificate against the hostname.
  http://toolbelt.rtfd.org/
* We have used external library defusedxml(version: 0.5.0) to handle security concerns while parsing untrusted XML data.
  https://pypi.python.org/pypi/defusedxml/0.5.0

# SUPPORT
* Support Offered: Yes
* Support Email: support@vmem.com
* Please visit https://www.violin-systems.com/services/support-services, and ask your question regarding Violin FSP App For Splunk, and your question will be attended to.