##Table of Contents


###OVERVIEW

* About the TA for Nutanix Prism
* Release notes
* Support and resources


###INSTALLATION AND CONFIGURATION

* Hardware and software requirements
* Installation steps
* Deploy to single server instance
* Deploy to distributed deployment
* Deploy to distributed deployment with Search Head Pooling
* Deploy to distributed deployment with Search Head Clustering
* Deploy to Splunk Cloud


####About the Nutanix Prism App for Splunk

* Author: Nutanix
* App Version: 1.0
* Has index-time operations: false
* Create an index: false
* Implements summarization: false


The Nutanix Prism App for Splunk allows customers of Splunk® Enterprise and Nutanix to visualize and view the state of their cluster from Splunk Enterprise. In addition, the app allows users to view log events surrounding all Nutanix processes and search specific Nutanix syslog data within the app.

####Release notes

#####About this release

Version 1.0 of the Nutanix Prism App for Splunk is compatible with:

* Splunk Enterprise versions: 6.3, 6.2
* Platforms: Platform independent
* Lookup file changes: None

#####Support and resources

**Questions and Answers:** Nutanix Prism App for Splunk at INSERT SPLUNK BASE/ANSWERS LINK HERE

######Support
* **Email:** splunkapp@nutanix.com
* **Support hours:** 24/7
* **Response:** All cases submitted will be confirmed via email.


#####INSTALLATION AND CONFIGURATION
######Hardware and software requirements
######Hardware requirements

Nutanix Prism App for Splunk supports the following server platforms in the versions supported by Splunk Enterprise:

* Linux
* Windows
* Solaris

######Software requirements

To function properly, Nutanix Prism App for Splunk requires the following software:

* TA for Nutanix Prism installed and bringing data into the indexers. To ensure that all dashboard panels are populating and reporting, configure all 5 inputs included in the TA for Nutanix Prism. Doing this will on-board the datasets needed to populate the panels. Also, to ensure that the Nutanix Syslog drop-down returns the necessary results, ensure that the syslog data is configure with a sourcetype of nutanix_syslog.

######Splunk Enterprise system requirements

<p>Because this add-on runs on Splunk Enterprise, all of the <a href="http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements">Splunk Enterprise system requirements</a> apply.</p>

######Download

Download the Nutanix Prism App for Splunk at ENTER LOCATION.


####Installation steps

To install and configure this app on your supported platform, follow these steps:

1. Download and Deploy the add-on to either a single Splunk Enterprise server or a distributed deployment.


######Using the Web Interface: 

* In Splunk Web, click Apps > Manage Apps.
* Click Install app from file.
* Locate the downloaded file and click Upload.
* Verify that the add-on appears in the list of apps and add-ons. You can also find it on the server at $SPLUNK_HOME/etc/apps/nutanix.

######Using the configuration files:
* Untar the downloaded app.
* Copy or Move the nutanix folder to the forwarder and put into the $SPLUNK_HOME/etc/apps directory.
* Restart Splunk


**Standalone Splunk Environments and Independent Search Heads**

Install the TA for Nutanix Prism on the single server using one of the methods described above.

**Distributed Environments:**

In distributed environments, the Nutanix Prism App for Splunk Enterprise should be installed on the search heads. 
 












