Table of Contents
OVERVIEW

About the TA for Nutanix Prism
Release notes
Support and resources

INSTALLATION AND CONFIGURATION

Hardware and software requirements
Installation steps
Deploy to single server instance
Deploy to distributed deployment
Deploy to distributed deployment with Search Head Pooling
Deploy to distributed deployment with Search Head Clustering
Deploy to Splunk Cloud
Configure TA for Nutanix Prism


OVERVIEW
About the TA for Nutanix Prism

Author: Nutanix
App Version: 1.3
Has index-time operations: true, this add-on must be placed on indexers
Create an index: true
Implements summarization: false


The Nutanix Prism TA for Splunk Enterprise allows customers using Splunk to collect, ingest, and index data about their virtual environments and their hosts managed by Nutanix Prism. 


Release notes

About this release

Version 1.3 of the TA for Nutanix Prism is compatible with:

Splunk Enterprise versions: 7.x, 6.x
Platforms: Platform independent
Lookup file changes: None

Third-party software attributions

Version 1.0 of the TA for Nutanix Prism incorporates the following third-party software or libraries.

Requests, http://www.apache.org/licenses/LICENSE-2.0

Support and resources

Questions and Answers Access questions and answers about the TA for Nutanix Prism at ENTER LINK TO SPLUNKBASE

Support

Support URL: 
Toll-Free US Support: 
Email: nutanixready@nutanix.com
For other international support phone numbers: 
Support hours: 24/7
Response: all cases submitted will be confirmed via email
Support cases can be tracked on 

INSTALLATION AND CONFIGURATION
Hardware and software requirements
Hardware requirements

TA for Nutanix Prism supports the following server platforms in the versions supported by Splunk Enterprise:

Linux
Windows
Solaris

Software requirements

To function properly, TA for Nutanix Prism requires the following software:

Nutanix Prism Console

Splunk Enterprise system requirements

Because this add-on runs on Splunk Enterprise, all of the Splunk Enterprise system requirements apply.
Download

Download the TA for Nutanix Prism at ENTER DOWNLOAD LOCATION.
Installation steps

To install and configure this app on your supported platform, follow these steps:

Download and Deploy the add-on to either a single Splunk Enterprise server or a distributed deployment.
Configure your inputs to get your Nutanix Prism's API data into Splunk Enterprise.


Deploying the TA for Nutanix Prism

Using the Web Interface: 

Download from Splunk Apps.
- In Splunk Web, click Apps > Manage Apps.
- Click Install app from file.
- Locate the downloaded file and click Upload.
- Verify that the add-on appears in the list of apps and add-ons. You can also find it on the server at $SPLUNK_HOME/etc/apps/TA-nutanix.

Using the configuration files: 
- Upload the TA-nutanix folder to the forwarder and put into the $SPLUNK_HOME/etc/apps directory.
- Restart Splunk


Deploy to single server instance
Install the TA for Nutanix Prism on the single server using one of the methods described above.



Deploy to distributed deployment
In a distributed deployment, the TA for Nutanix Prism should be installed on the following:
- Heavy Forwarder: The inputs contained within the TA should be configured on the Heavy Forwarder. 
- Indexer:         The inputs does not need to be configured on the indexer unless there is only one indexer in the deployment and no Heavy Forwarder. The TA contains index time conifgurations and should be installed on the Indexer.
- Search Head:    The inputs does not need to be configured on the Search Head. The TA does contain search time configurations and should be installed on the Search Heads.


Configure Nutanix Prism API Inputs: There are two ways to configure the inputs for this app.

Using the Web Interface: 
On you Splunk Enterprise Instance, navigate over to Settings —> Data Inputs —> And select the Nutanix Prism API endpoints you want to ingest into Splunk. For each input you want to add select the endpoint, then select new —> and fill out the required form. 
Input Form: The input form requires the following information from users:

name : Description of the input username: The username for the Nutanix Prism API Console. The format should resemble: username@nutanixbd.local 
password:The password for the Nutanix Prism API Console. 
ip: The ip or hostname of the Nutanix Prism API Console. 
port: The Nutanix Prism API Console port. This defaults to 9440. 
start_time: This number should be in seconds. This signifies how far back for the current time you would like to retrieve data. By default the time is either 900 seconds or 3600 seconds depending on the input.

After successfully completing the input form, ensure to enable the input by navigating over to Settings —> Data Inputs —> Select the Input you added —> Under Status —> Select Enable.By default, the host, source, index and sourcetype fields are configured. 

Using the configuration files:
- Download the TA from Splunkbase : ENTER DOWNLOAD LOCATION
- Add the TA to your Splunk App directory typically found under: $SPLUNK_HOME/etc/apps
- Create a local directory under $SPLUNK_HOME/etc/apps/TA-nutanix and add an inputs.conf file in the local directory. Using the inputs.conf.spec file located in the README Directory as    a guide, add the ip, username, and password of Nutanix Prism Console to each input. Please note, the username should be in the following format: username@nutanixbd.local. In addition,     there are default time intervals, port numbers, and start_times set.  To override the default of any of these stanzas, create a new entry for each in local directory's copy of inputs.conf. Also, each input is disbled by default. To enable an input, add disabled = 0 under each input in the local directory's copy of inputs.conf.




