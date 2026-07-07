# ABOUT THIS APP

Fidelis Cybersecurity App for Splunk helps in visualizing and monitoring Fidelis Cybersecurity Alerts.

# REQUIREMENTS

* Splunk version >= 6.3

# Recommended System configuration

* Splunk forwarder system should have 4 GB of RAM and a quad-core CPU to run this app smoothly.


# Topology and Setting up Splunk Environment


* This app has been distributed in two parts.

  1) Add-on app, which listens for Syslog messages from Fidelis Cybersecurity.
  2) Main app for visualizing Fidelis Cybersecurity data.

* This App can be set up in two ways:
  1) **Standalone Mode**: Install main app and Add-on app.

     * Here both the app resides on a single machine.
     * Main app uses the data collected by Add-on app and builds dashboard on it

   2) **Distributed Environment**: Install the main app and Add-on app on search head. Add-on app on forwarder and Indexer.

     * Configure Add-on app on forwarder.
     * Main app on search head uses the received data and builds dashboards on it.


# Installation in Splunk Cloud

* In Splunk cloud we recommend, install Add-on app on internal premises forwarder, Splunk cloud indexer, and Splunk cloud search head. But configure only on internal premises forwarder.


# Installation of App

* This app can be installed through UI using "Manage Apps" or extract zip file directly into /opt/splunk/etc/apps/ folder.

# OPEN SOURCE COMPONENTS AND LICENSES

* Some of the components included in Fidelis Cyber Security App for Splunk are licensed under free or open source licenses. We wish to thank the contributors to those projects.

*jQuery 
	version: 2.1.0 
	URL: http://jquery.com/ 
	LICENSE: https://github.com/jquery/jquery/blob/master/LICENSE.txt

*Underscore JS 
	version: 1.6.0 
	URL: http://underscorejs.org 
	LICENSE: https://github.com/jashkenas/underscore/blob/master/LICENSE
*Require JS 
	version: 2.1.15 
	URL: http://github.com/jrburke/requirejs 
	LICENSE: https://github.com/requirejs/requirejs/blob/master/LICENSE
	
*D3 JS 
	version: 3.3.5 
	URL: https://github.com/d3/d3/releases 
	LICENSE: appserver/static/components/d3/LICENSE

*Chart JS 
	version: 1.0.2 
	URL: https://chartjs.org
	LICENSE: https://github.com/nnnick/Chart.js/blob/master/LICENSE.md

# PREREQUISITES
For CIM dashboards to work, it requires Splunk_SA_CIM >=4.6 installed on your Splunk instance.


# Savedsearches

* Below savedsearches are used for generating lookup files
Malware - Lookup Gen
Policy - Lookup Gen
Rule and Policy - Lookup Gen
Rules - Lookup Gen
Sensor - Lookup Gen
Severity - Lookup Gen


# Support
* Fidelis Apps for Splunk are supported by Fidelis.
* Please open case at support@fidelissecurity.com.
* Please include Component Type, Software Version information in the mail.

# TEST YOUR INSTALL

The main app dashboard can take some time before the data is returned which will populate some of the panels. A good test to see that you are receiving all of the data we expect is to run this search after several minutes:

    search `fidelis_get_xps_event` | stats count by sourcetype

In particular, you should see these sourcetypes:
* fidelis:xps
* fidelis:xps:api

If you don't see these sourcetypes, have a look at the log file $SPLUNK_HOME/var/log/TA-Fidelis-Analytics/fidelis.log.
