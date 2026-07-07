Table of Contents

1. OVERVIEW
- About the TA for Nimble Storage
- Release notes
- Support and resources

2. INSTALLATION AND CONFIGURATION
- Hardware and software requirements
- Installation steps
- Deploy to single server instance
- Deploy to distributed deployment
- Deploy to distributed deployment with Search Head Pooling
- Deploy to distributed deployment with Search Head Clustering
- Deploy to Splunk Cloud
- Configure TA for Nimble Storage

---

1. OVERVIEW

1.1 About the TA for Nimble Storage

- Author: Nimble Storage
- App Version: 1.0.4
- Vendor Products: Nimble OS 2.3.4 and above
- Has index-time operations: true, this add-on must be placed on indexers
- Create an index: false
- Implements summarization: false

The Nimble Storage Adaptive Flash platform provides a single storage consolidation architecture for enterprise applications.  Nimble Storage systems provide the ability to efficiently scale performance and capacity non-disruptively from small to extremely large environments, and dramatically simplify management of the storage infrastructure.

The Nimble Storage TA for Splunk Enterprise allows customers to pull information from a Nimble Storage array as a stateful event stream. This data can be used to enrich other data inputs and to display the configuration and state of health of a Nimble Storage array.

1.1.1 Scripts and binaries

- nimble_rest.py - REST Modular Input
- nimble_snmp.py - SNMP Modular Input

1.2 Release notes

1.2.1 About this release

Version 1.0.4 of the TA for Nimble Storage is compatible with:

- Splunk Enterprise versions: 6.2, 6.1
- Platforms: Platform independent
- Vendor Products: Nimble Storage OS 2.3.4 and above
- Lookup file changes: None

Issues addressed in this release:
- REST calls to Nimble Array require SSL verification
- Icons added to meet splunk certification
- Permissions updated for read-only files

1.2.2 Third-party software attributions

Version 1.0.4 of the TA for Nimble Storage incorporates the following third-party software or libraries.

- ASN.1 for Python, http://pyasn1.sourceforge.net/license.html
- PySNMP, http://pysnmp.sourceforge.net/license.html
- Requests, http://www.apache.org/licenses/LICENSE-2.0


1.2.3 Support and resources

**Questions and Answers**
Access questions and answers about the TA for Nimble Storage at http://answers.splunk.com/answers/app/2840

**Support**

- Support URL: http://www.nimblestorage.com/support/overview/
- Toll-Free US Support: 1-877-3NIMBLE (877-364-6253), extension 2
- Email: support@nimblestorage.com
- For other international support phone numbers: http://www.nimblestorage.com/support/overview/
- Support hours: 24/7
- Response: all cases submitted will be confirmed via email
- Support cases can be tracked on infosight.nimblestorage.com


2. INSTALLATION AND CONFIGURATION

2.1 Hardware and software requirements

2.1.1 Hardware requirements

TA for Nimble Storage supports the following server platforms in the versions supported by Splunk Enterprise:

- Linux
- Windows
- Solaris

2.1.2 Software requirements

To function properly, TA for Nimble Storage requires the following software:

- Nimble Storage OS 2.3.4.0 and above

2.1.3 Splunk Enterprise system requirements

Because this add-on runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

2.2 Download

Download the TA for Nimble Storage at https://apps.splunk.com/app/2840/.

2.3 Installation steps

To install and configure this app on your supported platform, follow these steps:

  1) Download and Deploy the add-on to either a single Splunk Enterprise server or a distributed deployment.
  2) Configure your Nimble Storage server to export data to your single instance or your forwarder.
  3) Configure your inputs to get your Nimble Storage data into Splunk Enterprise.

2.3.1 Deploy to single server instance

Follow these steps to install the app in a single server instance of Splunk Enterprise:

  1) Download from Splunk Apps.
  2) In Splunk Web, click Apps > Manage Apps.
  3) Click Install app from file.
  4) Locate the downloaded file and click Upload.
  5) Verify that the add-on appears in the list of apps and add-ons. You can also find it on the server at $SPLUNK_HOME/etc/apps/TA-nimble.

2.3.2 Deploy to distributed deployment

**Install to forwarders**
1. Upload the TA-nimble folder to the forwarder and put into the $SPLUNK_HOME/etc/apps directory
1. Restart Splunk

2.4 Configure TA for Nimble Storage

**Configure REST Inputs**

There are two ways to configure the inputs for this app.

***Using the Web Interface***
  1. Go to Settings->Data Inputs
  2. Click Add New next to either Nimble Array Rest API or Nimble Array SNMP Counters depending on which one you want to add
  3. If you are configuring an SNMP counter input you will need the Array name, the SNMP port, and the community name. You will be able to get that information from the admin interface of the array.
  4. If you are configuring a REST API input, you will need the REST URL for the array and admin login and password.
  5. You can set index name, interval, and sourcetype as well for either inputs under "More settings"

***Using the configuration files***
  1. In the app directory create an inputs.conf in the local directory.
  1. Use the fields in README/inputs.conf.spec folder to make sure all fields are specified
  1. Restart Splunk

**Configure CA Certificates **

Once the input configuration is complete , we need to add the CA cert from the Nimble Array to the cacert file within the appli
cation.  

 1. Use a web browser to connect to the Nimble Array admin.
 2. Inspect and save the array's CA certificate as a PEM file; the server certificate is not needed.
 3. Navigate to the following folder: <splunk-home>/etc/apps/TA-nimble/certs
 4. Ensure there's a nimble_cacert.pem file in there
 4. Concatenate the downloaded PEM file to the nimble_cacert.pem file ( i.e. cat ~/Downloads/local_nimble_array_ca.pem >> nimble_cacert.pem )
 5. Restart Splunk

**Configure Syslog Input**

This is a two part process.

On the Splunk side:
  1. Go to TA-nimble/default
  1. Copy inputs.conf to TA-nimble/local
  1. Edit the inputs.conf file. Change disabled to 0 and 99999 in the stanza name to an open port on your system.
  1. Restart Splunk

On the Nimble Storage side:
  1. Log into the administrator console
  1. Go to Administration -> Alerts & Monitoring -> Syslog
  1. Click on Enable
  1. In the syslog server field put your Splunk Server that you installed the TA on and the port you configured above

