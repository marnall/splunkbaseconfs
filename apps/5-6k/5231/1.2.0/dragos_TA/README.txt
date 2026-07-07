Overview
===================================================================================================
Dragos and Splunk have teamed to provide customers with a convenient way to  load Dragos Worldview 
Threat Intelligence Indicators of Compromise (IoCs) into Splunk for searching stored data.  The 
Dragos Splunk extensions for Worldview  Threat Intelligence are split into two parts.

This application is the the Dragos Technology Add-on and it provides the necessary logic to read
and store Worldview IoCs in a Splunk key value store or index.  Splunk users can craft custom
queries themselves or leverage the Dragos Worldview Threat Intelligence App. This application also
provides underlying components that can be used to ingest alerts from the Dragos Platform using the
syslog events functionality.

The Worldview Threat Intelligence App can be installed in conjunction with this application. The
Worldview Threat Intelligence App searches log data and combines the Dragos IoCs and customer data
to leverage the Splunk Common Information Model (CIM). The App presents the results as a series of
dashboards that are user-customizable to fit individual needs.

The Splunk Add-on and Threat Intelligence app allow users to search log data collected from both
enterprise IT and industrial Operational Technology (OT) networks. This combined view gives users
a unified experience when searching their data for IOCs, providing analysts with improved
situational awareness and decision-making support.

This expands the ICS cybersecurity ecosystem to ensure critical infrastructure and industrial
organizations are equipped with enhanced threat visibility and better analytics, resulting in
better protection of their OT environments regardless of where an adversary may attack. It enables
more effective SOC functions - more effective threat hunts, ability to resolve incidents more
quickly - for organizations concerned about ICS cybersecurity.

Support
===================================================================================================
For support or questions please contact splunk-support@dragos.com

Additional Information
===================================================================================================

### Splunk Validated Architectures

#### Single Server Deployment (S1)
In this deployment architecture a single instance is used for both indexing and searching data. In
this architecture you can deploy the Dragos Add-On for Splunk on this single node. You can then 
configure the Dragos IOC input on this single instance. For single server deployments the Dragos 
IOC input will be configured to use the local search head.

#### Distributed Clustered Deployment + SHC - Single Site (C3)
In this deployment architecture the Dragos Add-On for Splunk should be installed on all instances 
in your Search Tier.  You should then deploy the Dragos Add-On for Splunk to each instance in your 
indexing tier. This ensures that the custom search helpers and data inputs are available to each 
node. 

Note that you should not configure the Dragos IOC input on any member of your search tier or 
indexing tier.

In order to ingest IOCs you should setup a separate heavy forwarder, install the Dragos Add-On for 
Splunk application, and configure the Dragos IOC input to run on the heavy forwarder and send data 
to your remote search head cluster. This ensures that only a single Splunk node contacts the Dragos
API.

### External Data Sources
This application creates a new modular input that can be used to download IoCs from the Dragos 
Worldview Threat Intelligence API (https://intel.dragos.com/api/v1/doc/). It is recommended that
you verify network connectivity from Splunk to this external API before installation.

### Use of Third Party Code Libraries
This application uses the following third party code libraries:
* Splunk Enterprise SDK for Python version 1.6.13
(https://dev.splunk.com/enterprise/docs/devtools/python/sdk-python/)

### Custom Search Commands
This application creates several custom search commands that are used to manage the IoCs that have 
been downloaded into splunk:
* dragosnormalizeindicator: This command can be used to normalize an indicator so that it can
  be properly searched for in the IoCs You can run this command by specifying the input field
  containing the indicator you want to normalize and the name of the new output field that will
  hold the normalized indicator: `| dragosnormalizeindicator input_fieldname=potential_indicator output_fieldname=normalized_indicator`
* dragosresetkvstores: If you ever want to reset the application to its initial state, you can 
  run a special command. In order to do this, you must either delete or disable the current 
  the Dragos IOCs input. After you have done this, you can open a search bar in Splunk and run 
  the following command (the search time frame doesn’t matter). You should run this command
  on the search head where the IoCs are stored. You ran run this command like this: 
   `| dragosresetkvstores | table *`
* dragosmanageiocinactivelist: This command can be used to manage the IoCs that have been
  downloaded into Splunk. It is reccomended that you use the "Manage IoCs" dashboard in the 
  Dragos Worldview Threat Intelligence App to assist with this command.

### Eventgen App
This application supplies an `eventgen.conf` file which can be used with then Eventgen App
(https://splunkbase.splunk.com/app/1924/) to generate fake/sample Dragos alert and network data. 
All sample data will be stored in an index `dragos_sample_data` which you need to create prior to
generating the data.
