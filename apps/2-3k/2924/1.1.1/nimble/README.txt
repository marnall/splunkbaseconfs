
---
1. OVERVIEW

1.1 About the Nimble Storage App for Splunk

| Author : Nimble Storage |
| App Version : 1.1.1 |
| Vendor Products : Nimble OS 2.3.4 and above |
| Has index-time operations : false |
| Create an index : false |
| Implements summarization : false |

The Nimble Storage Adaptive Flash platform provides a single storage consolidation architecture for enterprise applications.  Nimble Storage systems provide the ability to efficiently scale performance and capacity non-disruptively from small to extremely large environments, and dramatically simplify management of the storage infrastructure.

The Nimble Storage App for Splunk allows a Splunk® Enterprise administrator to customers to pull information from a Nimble Storage array as a stateful event stream. This data can be used to enrich other data inputs and to display the configuration and state of health of a Nimble Storage array.

1.1.1 Scripts and binaries

N/A

1.2 Release notes

1.2.1 About this release

Version 1.1.1 of the Nimble Storage App for Splunk is compatible with:

| Splunk Enterprise versions | 6.1 and above |
| --- | --- |
| CIM | N/A |
| Platforms | Platform independent |
| Vendor Products | Nimble OS 2.3.4 and up |
| Lookup file changes | none |

1.2.2 New features

Nimble Storage App for Splunk includes the following new features:

- Added the following dashboards: Array Inventory, Volume Collections Inventory, Volumes

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

Nimble Storage App for Splunk supports the following server platforms in the versions supported by Splunk Enterprise:

- Platform Independent

2.1.2 Software requirements

To function properly, Nimble Storage App for Splunk requires the following software:

- [TA for Nimble Storage](https://apps.splunk.com/app/2840/) installed and bringing data into the indexers

2.1.3 Splunk Enterprise system requirements

Because this add-on runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

2.2 Download

Download the Nimble Storage App for Splunk at https://splunkbase.splunk.com/app/2924.

2.3 Installation steps

To install and configure this app on your supported platform, follow these steps:

  1) Click on the gear next to Apps
  2) Click on Install App From File
  3) Chose downloaded file and click upload


3. USER GUIDE

3.1 Key concepts for Nimble Storage App for Splunk

When you load the Nimble Storage app you will see a list of all of the arrays that you have configured Modular Inputs for in the TA for Nimble Storage. 

Clicking on an array will give you a list of all of the volumes on that array on the left side and an array status box that will show syslog events from the array.

Clicking on a volume will show you a performance graph for that volume.

