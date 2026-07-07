# Table of Contents
## End User License Agreement
Installation and use of this app signifies acceptance of the [Gigamon End User License Agreement(EULA)](/static/app/Gigamon_Application_Intelligence/html/Gigamon-EULA.pdf) inclusive of any future updates.
## Quick Start

Navigate to the [Gigamon and Stream Integration](#gsi) section for a step-by-step installation path.

## OVERVIEW

- About Gigamon_Application_Intelligence
- Release notes
- Performance benchmarks
- Support and resources

## INSTALLATION

- Hardware and Software Requirements
- Installation steps 
- Deploy to a Single Server Instance
- Deploy to a Distributed Deployment
- Deploy to a Distributed Deployment with Search Head Clustering
- Deploy to Splunk Cloud


## USER GUIDE

- Data types
- Lookups
- Configure Gigamon_Application_Intelligence
- Troubleshooting
- Upgrade


# OVERVIEW

## About Gigamon Application Intelligence for Splunk

| About | Gigamon Application Intelligence for Splunk |
| --- | --- |
| App Version | 2.0.0 |
| Folder Name | Gigamon_Application_Intelligence |
| Vendor Products | GigaVUE-OS >=5.8 with GigaSMART |
| Splunk Requirements | Splunk Stream >= 7.2.0 |
| Splunk Requirements | URL Toolbox >= 1.6 |
| Splunk Requirements | Python for Scientific Computing (for Linux 64-bit) >= 1.3 |
| Splunk Requirements | TA-IOC Lookup >= 2.0.1 |
| Has index-time operations | true (SEDCMD for ASN.1 Encoded Elements)
| Create an index | false |
| Implements summarization | false |

Gigamon_Application_Intelligence allows a Splunk Admin the ability to configure Splunk Stream for Gigamon Specific elements over IPFIX or CEF.

## Scripts and binaries

There is a script located in /Gigamon_Application_Intelligence/appserver/static/library and called SplunkAppconfiguration.py called SplunkAppconfiguration.py
This script automates setting up Splunk Stream for ingesting IPFIX

## Release notes

These are the improvements packaged as part of version 1.0.0.
* This is the first release for this app

## About this release

Version 2.0.0 of Gigamon Application Intelligence for Splunk is compatible with:

| Item | Value |
| --- | --- |
| Splunk Enterprise versions | 7.3.0, 8.0.x |
| Splunk Stream versions | 7.2.x |
| URL Toolbox | 1.6 |
| CIM | 4.8 |
| Platforms |`<Platform independent>`  |
| Vendor Products | GigaVUE-OS >=5.8 with GigaSMART |

Gigamon Metadata Application For Splunk requires Splunk Stream 7.2.0 or higher to ingest IPFIX data. Splunk Stream is not required to ingest CEF data.

## New features

Gigamon Metadata Application For Splunk includes the following new features:

* Ability to parse Gigamon IANA PEN Elements sent via Netflow v10 (IPFIX) from a GigaSMART.
* Ability to parse CEF data from a GigaSMART.

## Fixed issues

Version 2.0.0 of Gigamon_Application_Intelligence fixes the following issues:

- No Fixed Issues. If you find an error, please contact support.

## Known issues

This version Gigamon_Application_Intelligence has the following known issues:

- When upgrading between Splunk Stream versions:
    - the `splunk_app_stream` vocabulary file will be deleted. This needs restored with the correct version of the vocab.
    - the `splunk_app_stream` stream file will be deleted. This needs restored with the correct version of the stream.
    - the change in streams (`metadata` vs `packet`) requires the deletion and re-addition of the configured netflow stream.
    - follow the instructions listed under  ##### Install into Stream ::install_stream_manual:: to restore correct vocabulary files.
- If the `netflow` stream file is changed, any existing streams using that stream configuration need to be deleted and re-added.

## Support and resources

### Questions and answers

Access questions and answers specific to Gigamon_Application_Intelligence at https://answers.splunk.com.  

### Support

Support Email: apps@gigamon.com or App.Splunk@gigamon.com
Please visit https://answers.splunk.com, and ask your question regarding Gigamon Metadata Application For Splunk. Please tag your question with the correct App Tag, and your question will be attended to.

# INSTALLATION AND CONFIGURATION

## Software requirements

To function properly, Gigamon Metadata Application For Splunk requires the following software:

- Splunk 7.3.x, 8.0.x
- Splunk Stream >= 7.2.0
- URL Toolbox >= 1.6
- GigaVUE-OS >= 5.8

## Splunk Enterprise system requirements

Because this add-on runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

Because this add-on requires Splunk Stream, all of the [Splunk Stream system requirements](https://docs.splunk.com/Documentation/StreamApp/latest/DeployStreamApp/Deploymentrequirements) apply.

## Download

Download Gigamon Metadata Application For Splunk at [Splunkbase](https://splunkbase.splunk.com).


# Installation steps

## Deploy to single server instance

Follow these steps to install the app in a single server instance of Splunk Enterprise:

1. Download the Gigamon Metadata Application For Splunk package from https://splunkbase.splunk.com.
1. Install the App via the recommended installation methods (CLI, Web GUI)
1. Restart Splunk.
1. See the Instructions for [Gigamon and Stream Integration](#gsi).

## Deploy to distributed deployment

### Install to search head

1. Download the Gigamon Metadata Application For Splunk package from https://splunkbase.splunk.com.
1. Install the App via the recommended installation methods (CLI, Web GUI, Deployment Server)
1. See the Instructions for [Gigamon and Stream Integration](#gsi).

### Install to indexers

1. Download the Gigamon Metadata Application For Splunk package from https://splunkbase.splunk.com.
1. See the Instructions for [Gigamon and Stream Integration](#gsi).

### Install to universal forwarders

1. There is no installation to Universal Forwarders.

### Install to Heavy Forwarders

1. Download the Gigamon Metadata Application For Splunk package from https://splunkbase.splunk.com.
1. See the Instructions for [Gigamon and Stream Integration](#gsi).

### Deploy to distributed deployment with Search Head Clustering

1. Place the App into the "deploy_apps" folder on the Deployer Server.
1. Be sure to modify the base event type in `default/eventtypes.conf` prior to deployment!
3. Deploy the App to the Search Head Cluster.
1. See the Instructions for [Gigamon and Stream Integration](#gsi).

### Deploy to Splunk Cloud

1. Instruct the Splunk Cloud Support team to follow the instructions above that matches the Cloud environment.

## Install Splunk App URL Toolbox 
Gigamon Metadata Application For Splunk has dependency on the app “URL Toolbox”. Install the Splunk app “URL Toolbox” using the standard installation procedure. “URL Toolbox” can be found on splunkbase.splunk.com.

### Steps to Ingest CEF Data
1. Edit $SPLUNK_HOME/etc/apps/Gigamon_Application_Intelligence/appserver/static/library/gigamon_cef_inputs.conf to change the receiver port to your local settings (replace PORT).
2. Copy gigamon_cef_inputs.conf to $SPLUNK_HOME/etc/apps/Gigamon_Application_Intelligence/inputs.conf

Here is an example output of inputs.conf file
[udp://10514]
connection_host = ip
sourcetype = cefevents

10514 above is the port number. Change it to whatever the port number desired. Make sure that it matches with port number configuration on GigaSMART device.

## Gigamon and Stream Integration ::gsi::

The Gigamon and Stream integration requires precise adherence to the instructions. Failure to do so may cause Stream to not collect the Gigamon IPFIX data appropriately.

The GSI (Gigamon and Stream Integration) is an advanced configuration technique, designed to extend the protocol decoding abilities of Splunk Stream. As this feature relies on Splunk Stream, Splunk Stream is a requirement and must be installed on your Splunk server(s). Please see the instructions on how to install [Splunk Stream](#ss_install).

### Install Stream ::ss_install::

If you are installing Stream for the first time, the preferred version at this time is `7.2.0`. If you have an existing stream installation, ensure the version number is `7.2.0` (other versions, if available, have not been tested).

- [Splunk Stream Documentation](https://docs.splunk.com/Documentation/StreamApp/latest/DeployStreamApp/InstallSplunkAppforStream)

NOTE: The NIC associated with the Netflow collection should *not* be in promiscuous mode. Stream is being used as a protocol decoder in this configuration only.


### Extend Stream
In order to extend the base installation of Stream, there must be file-level changes made. There are two installation methods, script and manual. The base location of the Gigamon-specific configuration is `$SPLUNK_HOME/etc/apps/Gigamon_Application_Intelligence/appserver/static/library`. `$SPLUNK_HOME` refers to the install location of Splunk. Start in the library folder mentioned, and then proceed to either [Manual Configuration](#install_manual) or [Scripted Installation](#install_script).


#### Manual Configuration ::install_manual::

This configuration method requires the user to edit and copy various files to locations in the `splunk_app_stream` and `Splunk_TA_stream` apps. `$SPLUNK_HOME` refers to the install location of Splunk.

##### Install into Stream ::install_stream_manual::

1. Edit `$SPLUNK_HOME/etc/apps/Gigamon_Application_Intelligence/appserver/static/library/gigamon_streamfwd.conf` to change the reciever IP and Port to your local settings (replace `@@IP` and `@@PORT`).
1. Copy `$SPLUNK_HOME/etc/apps/Gigamon_Application_Intelligence/appserver/static/library/gigamon_streamfwd.conf` to `$SPLUNK_HOME/etc/apps/splunk_app_stream/local/streamfwd.conf` and `$SPLUNK_HOME/etc/apps/Splunk_TA_stream/local/streamfwd.conf`.
1. Copy the Splunk Stream Version-specific vocabulary file (see file names right below) to `$SPLUNK_HOME/etc/apps/splunk_app_stream/default/vocabularies/gigamon.xml` and `$SPLUNK_HOME/etc/apps/Splunk_TA_stream/default/vocabularies/gigamon.xml`.
    1. For Splunk Stream 7.1.3: `gigamon_vocabulary_7.1.3.xml`
    1. For Splunk Stream 7.2.0: `gigamon_vocabulary_7.2.0.xml`

1. Copy `$SPLUNK_HOME/etc/apps/Gigamon_Application_Intelligence/appserver/static/library/gigamon_stream.json` to `$SPLUNK_HOME/etc/apps/splunk_app_stream/default/streams/netflow`.
1. GigaSMART occasionally sends data elements encoded in ASN.1 to Stream. To avoid excessive license usage, apply the following fix.
    1. On the system indexing the Stream data (typically where splunk_app_stream is installed), edit the `$SPLUNK_HOME/etc/apps/splunk_app_stream/local/props.conf` file.
    1. For the stanza `[stream:netflow]`, add this line of configuration: `SEDCMD-remove_nulls_gigamon = s/\\u0000//g`. If the stanza doesn't exist, create it.
    1. This `SEDCMD` will remove any data that cannot be decoded correctly.
1. Restart Splunk.
1. Configure Stream via the steps at [Stream Configuration](#stream_config).

### Stream Configuration ::stream_config::

Full and complete documentation of Stream Configuration is located at [docs.splunk.com](http://docs.splunk.com/Documentation/StreamApp/latest/User/ConfigureStreams). This instructions use Stream 7.2.0 as the basis.

1. On the Splunk Home page, click on the app “Splunk Stream”
1. Use the navigation bar: **Configuration** -> **Configure Streams**
1. In the top right of the dashboard, click **New Stream** -> **Metadata Stream**
    1. ( Full Documentation [here](http://docs.splunk.com/Documentation/StreamApp/latest/User/ConfigureStreams#Create_new_metadata_stream))
1. Basic Info
    1. **Protocol**: *Netflow*
    1. **Name**: *your source name*
    1. Click **Next**
1. Aggregation ( Full documentation [here](http://docs.splunk.com/Documentation/StreamApp/latest/User/ConfigureStreams#Aggregation_types))
    1. Click **Next** to accept the default of `No`
1. Fields ( Full documentation [here](http://docs.splunk.com/Documentation/StreamApp/latest/User/ConfigureStreams#Select_protocol_fields))
    1. Deselect the fields that you do not want to collect
    1. Click **Next**
1. Filters ( Full documentation [here](http://docs.splunk.com/Documentation/StreamApp/latest/User/ConfigureStreams#Create_new_filters))
    1. Create a filter to limit the data that is collected
    1. Click **Next**
1. Settings
    1. Select an index to collect data to
    1. Select the status
    1. Click **Next**
1. Groups
    1. Select a forwarder group (if applicable)
    1. Click **Create Stream**
1. Done
    1. Click **Done**

### Configure GigaSMART

Now that Stream is configured to accept Gigamon Elements, configure the Gigamon appliance that has the GigaSMART card installed. Gigamon provides [documentation](https://www.gigamon.com/products/technology/netflow-and-metadata-generation) to configure netflow and metadata generation, and there is also a third-party step-by-step [tutorial](https://www.plixer.com/blog/ipfix-2/gigamon-ipfix-configuration/) that may help configure the GigaSMART.

NOTE: There is an option within the GigaSMART Exporter configuration to set the `Template Refresh Interval`. This setting should be set to **AT MOST** 2 minutes.  

### Distributed Stream Deployment

If you are pushing `Splunk_TA_stream` to a universal forwarder in a distributed deployment, then you must make the same changes for `Splunk_TA_stream` above in the `deployment-apps` folder

### Stream Upgrade Notes

- When upgrading Stream:
    - the `splunk_app_stream` vocabulary file will be deleted. This needs restored with the correct version of the vocab.
        - Follow Step 3 in the Manual Configuration.
    - the `splunk_app_stream` stream file will be deleted. This needs restored with the correct version of the stream.
        - Follow Step 4 in the Manual Configuration.
    - the change in streams (`metadata` vs `packet`) [Splunk Stream 7.0.1 -> 7.1.x] requires the deletion and re-addition of the configured netflow stream.


- If the `netflow` stream file is changed, any existing streams using that stream configuration need to be deleted and re-added.

#USER GUIDE

## Data types

This app provides the index-time and search-time knowledge for the following types of data:

1. Gigamon IANA PEN Elements as sent via GigaSMART over Netflow IPFIX.

## Lookups

The following lookups are provided as a part of the Gigamon Application Intelligence for Splunk app.

- port_list
    - This lookup provides descriptions for most common port numbers.
- http_status
    - This lookup provides descriptions for most HTTP event codes.
- dns_responses
    - This lookup provides descriptions for DNS reply code ids.
- protocol_numbers
    - This lookup provides descriptions for most common protocol numbers.
- dns_server_list
    - This lookup provides Trusted and Known DNS server IP address. User can edit this file $SPLUNK_HOME/etc/apps/Gigamon_Application_Intelligence/lookups/dns_server_list.csv to add list of DNS servers known to the organization.
- http_standard_ports
    - This lookup provides Standard ports for HTTP and HTTPS. User can edit this file $SPLUNK_HOME/etc/apps/Gigamon_Application_Intelligence/lookups/ http_standard_ports.csv  to add their custom standard HTTP/HTTPS ports.
- dns_standard_ports
    - This lookup provides Standard ports for DNS. User can edit this file $SPLUNK_HOME/etc/apps/Gigamon_Application_Intelligence/lookups/ dns_standard_ports.csv to add their custom standard DNS port other than 53.
If lookup files are edited, reload Splunk to make new changes take effect.

## Event Generator

Gigamon Application Intelligence For Splunk does make use of an event generator. This allows the product to display data, even when there are no inputs configured. Edit `eventgen.conf` for each stanza to "enable" the stanza.

### gigamon_ipfix_http.sample

This generates relevant fields to the IPFIX IANA HTTP elements.

### gigamon_ipfix_ssl.sample

This generates relevant fields to the IPFIX IANA SSL elements.

### gigamon_ipfix_dns.sample

This generates relevant fields to the IPFIX IANA DNS elements.


## Configure Gigamon Application Intelligence For Splunk

- Install the App according to your environment (see steps above)
- Navigate to the App
- Edit the event type to point to the correct data for the netflow.
- Click the `Update Eventtype` button, and the `Save` button.

## Troubleshoot Gigamon Application Intelligence For Splunk

The best place to start troubleshooting Gigamon Application Intelligence For Splunk is to visit the Monitoring Console Health Check. There are 4 specific checks related to the Gigamon Stream configuration. 
Click the "Start" button and then review the results.

If you are still having problems, use the Command line and run this command:

`$SPLUNK_HOME/bin/splunk diag --collect app:Gigamon_Application_Intelligence`

Send the generated diag file to Gigamon Application Intelligence For Splunk support.

## Accelerations

Summary Indexing: None
Data Model Acceleration: None
Report Acceleration: None

## Upgrade Gigamon Application Intelligence For Splunk

Upgrade Gigamon Application Intelligence For Splunk by re-installing into your environment per Splunk Documentation and your environment (see steps above).

## Third-party software attributions

Gigamon Application Intelligence For Splunk incorporates the third-party software or libraries referred at the path $SPLUNK_HOME/etc/apps/Gigamon_Application_Intelligence/appserver/static/html/3pp.md


#Configurability

Each of the use cases supported in this app are shown in their own dashboards. Each of these use cases run Splunk query to get the data, massage that data and then compared that data against configured entries. Many of the use cases in this app are configurable and configuration files for each of these use cases present in <SPLUNK_HOME>/etc/apps/ Gigamon_Application_Intelligence/lookups

##corp_domains.csv
This file contains the domain name of the organization. It’s used to look into all DNS records to collect host address to host name mapping. Edit this file to put your organization domain name. In the example below replace “*.gigamon.com” to say “*.google.com”

Sample domain name:
#### cat corp_domains.csv
domain, valid  
"*.gigamon.com",1

##priv_user.csv
This file contains login id and host name of privilege users of the organization. Network admins, SOC admins and finance admins are considered privilege users. You can customize this file to include your own list of privilege users. This file is used in the use-case High Privilege User Login Activity.
Sample priv_user.csv:
#### cat priv_user.csv
"host_name","login_id"  
"lt-Ptom-mac.gigamon.com",ptom  
"dt-Sdave-mac.gigamon.com",sdave  

##corp_networks.csv
This file contains allowed corporate network subnets. It’s used to validate endpoints of remote connections for the use case Suspicious Remote connections.  Edit this file to put your organization allowed network subnets.

Sample corp_networks.csv  
#### cat corp_networks.csv  
network_prefix,network_type,valid  
10.*,corp,1  
192.*,remote,1  

##server_list.csv
This file contains trusted and known servers allowed in the organization. Servers in this file are used to validate against rogue servers seen in the organization. Currently this file is used to validate DNS and DHCP servers for the use case Rogue Servers. Edit this file to put your own server IP address and server type.

Sample server_list.csv:
#### cat server_list.csv
Server,State,Type  
1.2.3.4,Trusted,DNS  
8.8.8.8,Known,DNS  
4.4.4.4,Known,DNS  
1.2.3.5,Trusted,DHCP
