# ABOUT THIS APP

The Aporeto Application for Splunk builds dashboards on indexed data provided by CSV-based Universal Forwarder data. Aporeto uses identity context, vulnerability data, threat monitoring and behavior analysis to build and enforce authentication, authorization and encryption policies for applications. With Aporeto, enterprises implement a uniform security policy decoupled from the underlying infrastructure, enabling workload isolation, API access control and application identity management across public, private or hybrid cloud.

# REQUIREMENTS

* Splunk version 6.4.x, 6.5.x, 6.6.x, 7.0.x and 7.1.x
* The use of the app requires an application which queries the Aporeto REST-based API and is available at aporeto.com.  Please check the aporeto.com help documentation for further details.

# RECOMMENDED SYSTEM CONFIGURATION

* Splunk forwarder system should have 12 GB of RAM and a six-core CPU to run this Technology Add-on smoothly.

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

* This app has been distributed in one part.

  1)  Main app, which receives indexed data directly from the Universal Forwarder which provides dashboards based on CSV submitted data.  The CSV data is based on JSON returned data which is queried directly from the Aporeto console/API.  


# INSTALLATION OF APP

* The Aporeto app is installed through UI using "Manage Apps" or you may download a copy of the application from the Aporeto support website where you may extract the contents of zip file directly into the  $SPLUNK_HOME/etc/apps/ folder.


# SUPPORT
* Support Offered: Yes
* Support Email: support@aporeto.com

### Copyright 2018 Aporeto, Inc.
