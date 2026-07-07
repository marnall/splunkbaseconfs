
# ABOUT THIS APP

Fidelis Cybersecurity Add-on for Splunk will listen for Syslog messages from Fidelis Cybersecurity on specific port and index it into Splunk.


# REQUIREMENTS

* Splunk version >= 6.3
* If using a forwarder, it must be a HEAVY forwarder( we use the HF because the universal forwarder does not include python)
* The forwarder system must have network access (HTTP/HTTPS) to Fidelis Cybersecurity Command post which is to be Splunked.
* Fidelis user ID, password, Command Post URL and Command Post Port Number for collecting data from Fidelis Cybersecurity Commandpost.


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


# Configuration of App

* If you are using index different than "main", please change the index name into inputs.conf and macros.conf files. By default the app will ingest data into main index

*  After installation, go to the Apps->Manage Apps->Set up Technology Add-on for Fidelis Cybersecurity. New setup screen will open which will ask for Fidelis Cybersecurity Command post details. Provide Port to listen for Fidelis Alert traffic, Protocol, Command Post URL, Command Post Port Number, User Name and password for Fidelis Cybersecurity Command post and save them.
*  Splunk REST API will encrypt the password and store it in Add-on's folder itself in encrypted form, REST modular script will fetch these credentials through REST API to connect to the Fidelis Cybersecurity Commandpost.
*  Restart the Splunk

# Upgrade App

* Follow standard steps to upgrade the app.
* The setup form in the new version of the app has an option called "Enable Data Inputs" which is checked by default. If user is upgrading from the previous version and wants to use same Data Inputs, this checkbox should be explicitly unchecked.

# CIM Compatibility

This app is compatible with CIM 4.x >=

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
