Cisco Umbrella Add-on for Splunk

Add-on Homepage:
Author: Hurricane Labs
Version: 1.0.7

### Description ###
The purpose of this add-on is to provide CIM compliant field extractions for Cisco Umbrella OpenDNS logs AWS S3 bucket logs.

This add-on requires the Splunk Add-on for Amazon Web Services as the means of data on-boarding.

* Built for Splunk Enterprise 6.x.x or higher
* CIM Compliance (CIM 4.0.0 or higher)
* Ready for Enterprise Security
* Requires Splunk Add-on for Amazon Web Services (unless using Cisco Managed S3)
    * https://splunkbase.splunk.com/app/1876/
* Supports Cisco Umbrella Log Management Version 1-5

### INSTALLATION AND CONFIGURATION
Search Head: Required
Heavy Forwarder: Optional
Indexer: Optional
Universal Forwarder: Not Supported
Light Forwarder: Not Supported

Ultimately this add-on needs to be installed on your Search Head and on the AWS Add-on collection point. It is recommended that you setup the AWS inputs on a Heavy Forwarder, and it is recommended that you setup the Cisco Umbrella Add-on on the Heavy Forwarder and Search Head. If you are using your Search Head as the AWS collection point, then this only needs to go on your search head. If your AWS collection point is on your Indexer, then this add-on needs to go on the Indexer and on your Search Head.

#### Setting up AWS Input
Reference Link: https://support.umbrella.com/hc/en-us/articles/230650987-Configuring-Splunk-for-use-with-Cisco-Umbrella-Log-Management-in-AWS-S3
1. Refer to the reference link to configure AWS and set up the account in Splunk, you can follow the rest of the steps in this guide when you reach the "Configuring Data Inputs for Splunk" step.
2. Navigate to the Splunk Add-on for AWS
3. Create a new input (Custom Data Type > Generic S3)
4. Select the appropriate AWS Account/Role/S3 Bucket
5. (Recommended) Do not set a S3 Key Prefix, and change the sourcetype to "opendns:s3".
5. (Optional) If you want more control over the data you bring in, you'll need to do separate inputs using these S3 Key Prefixes "/proxylogs/", "/dnslogs/", "/firewalllogs/", "/auditlogs/" and "/iplogs/". Each of these will use it's own sourcetype: "opendns:dnslogs", "opendns:proxylogs", "opendns:firewalllogs", "opendns:auditlogs", and "opendns:iplogs"

#### Heavy Forwarder & Search Head (RECOMMENDED)
1. Install the add-on on the Heavy Forwarder and Search Head. A Splunk Restart may be required, you may also attempt a debug refresh.
2. Configure the AWS Input to scrape your OpenDNS S3 bucket;
2a. One Input: If you scrape the entire bucket, you NEED to use sourcetype "opendns:s3"
2b. Multiple Inputs: If you want more control over the buckets being scraped, this add-on supports multiple inputs. There are three types of logs sent by Umbrella OpenDNS; "/proxylogs/", "/dnslogs/", "/firewalllogs/", "/auditlogs/" and "/iplogs/". Each input should use exactly one of those prefixes. The respective sourcetypes for those prefixes are as follows; "opendns:dnslogs", "opendns:proxy", "opendns:firewalllogs", "opendns:auditlogs" and "opendns:iplogs".
3. Verify data is coming in and you are seeing the proper field extractions by searching the data.
+ Example Search: index=awsindexyouchose sourcetype=opendns:\* | dedup sourcetype

#### Search Head Only
1. Install the add-on on the Search Head. A Splunk Restart may be required, you may also attempt a debug refresh.
2. Configure the AWS Input to scrape your OpenDNS S3 bucket;
2a. One Input: If you scrape the entire bucket, you NEED to use sourcetype "opendns:s3"
2b. Multiple Inputs: If you want more control over the buckets being scraped, this add-on supports multiple inputs. There are three types of logs sent by Umbrella OpenDNS; "/proxylogs/", "/dnslogs/", "/firewalllogs/", "/auditlogs/" and "/iplogs/". Each input should use exactly one of those prefixes. The respective sourcetypes for those prefixes are as follows; "opendns:dnslogs", "opendns:proxy", "opendns:firewalllogs", "opendns:auditlogs" and "opendns:iplogs".
3. Verify data is coming in and you are seeing the proper field extractions by searching the data.
+ Example Search: index=awsindexyouchose sourcetype=opendns:\* | dedup sourcetype

#### Indexer and Search Head (NOT RECOMMENDED)
1. Install the add-on on the Indexer and Search Head. A Splunk Restart may be required, you may also attempt a debug refresh.
2. Configure the AWS Input to scrape your OpenDNS S3 bucket;
2a. One Input: If you scrape the entire bucket, you NEED to use sourcetype "opendns:s3"
2b. Multiple Inputs: If you want more control over the buckets being scraped, this add-on supports multiple inputs. There are three types of logs sent by Umbrella OpenDNS; "/proxylogs/", "/dnslogs/", "/firewalllogs/", "/auditlogs/" and "/iplogs/". Each input should use exactly one of those prefixes. The respective sourcetypes for those prefixes are as follows; "opendns:dnslogs", "opendns:proxy", "opendns:firewalllogs", "opendns:auditlogs" and "opendns:iplogs".
3. Verify data is coming in and you are seeing the proper field extractions by searching the data.
+ Example Search: index=awsindexyouchose sourcetype=opendns:\* | dedup sourcetype

#### Cisco Managed Buckets Instructions
Reference Links:
https://support.umbrella.com/hc/en-us/articles/360000739983-How-to-Downloading-logs-from-Cisco-Umbrella-Log-Management-using-the-AWS-CLI
https://support.umbrella.com/hc/en-us/articles/360001388406-Configuring-Splunk-with-a-Cisco-managed-S3-Bucket
The AWS Add-on can NOT be used to pull data from Cisco managed S3 buckets. The only way to get this data in is through the use of the awscli tool. This should be setup on a Splunk Enterprise system that is meant for data ingestion (such as a Heavy Forwarder). You need to install this add-on on your Search Heads and the system handling data ingestion. The steps below will ONLY apply to your data ingestion box, NOT your Search Heads. I have only tested this on Ubuntu and we will not provide any further support/guidance on this, these steps are provided as is:

-1. Install awscli via apt-get (apt-get install awscli)

-2. In $SPLUNK\_HOME/etc/apps/TA-cisco\_umbrella/bin create two shell scripts. If you want the shell script write to a different location, make sure you change the paths in both shell scripts!
#pull-umbrella-logs.sh
\#!/bin/sh
unset LD\_LIBRARY_PATH
unset PYTHONPATH

AWS\_ACCESS\_KEY\_ID=<KEY\_HERE> AWS\_SECRET\_ACCESS\_KEY=<KEY_HERE> AWS\_DEFAULT\_REGION=<REGION_HERE> aws s3 sync s3://<CISCO_BUCKET_PATH_HERE> /opt/splunk/etc/apps/TA-cisco_umbrella/data

#delete-old-umbrella-logs.sh
\#!/bin/bash

\#Removes old data depending on the "Retention Duration" configured in the Umbrella dashboard --> Admin --> Log Management:

a) 7 days:

find /opt/splunk/etc/apps/TA-cisco_umbrella/data -type f -name "*.csv.gz" -mmin +11520 -delete 2>&1 >/dev/null

b) 14 days:

find /opt/splunk/etc/apps/TA-cisco_umbrella/data -type f -name "*.csv.gz" -mmin +21600 -delete 2>&1 >/dev/null

c) 30 days:

find /opt/splunk/etc/apps/TA-cisco_umbrella/data -type f -name "*.csv.gz" -mmin +44640 -delete 2>&1 >/dev/null

The suggested values leave a one day buffer for safety.

\#Removes old directories with no data
rmdir /opt/splunk/etc/apps/TA-cisco_umbrella/data/dnslogs/\*

-3. Verify that Splunk is actually able to run the shell scripts without issue by running '$SPLUNK\_HOME/bin/splunk cmd sh $SPLUNK\_HOME/etc/apps/TA-cisco_umbrella/pull-umbrella-logs.sh'. If this does not work, there is a problem with your setup or keys.

-4. If you are using a different path than my example, you will need to create $SPLUNK\_HOME/etc/apps/TA-cisco_umbrella/local/props.conf and alter this stanza to match:
[source::/opt/splunk/etc/apps/TA-cisco_umbrella/data/dnslogs/...]
TRANSFORMS-umbrella-logs\_source = remove\_umbrella\_date\_from_source

-5. In $SPLUNK\_HOME/etc/apps/TA-cisco_umbrella/local/inputs.conf create the following stanzas. Make sure you change the path and index in the monitor stanza if necessary!

[script://./bin/pull-umbrella-logs.sh]
disabled = 0
interval = 300
index = _internal
sourcetype = cisco:umbrella:input
start_by_shell = false

[script://./bin/delete-old-umbrella-logs.sh]
disabled = 0
interval = 600
index = _internal
sourcetype = cisco:umbrella:cleanup
start_by_shell = false

[monitor:///opt/splunk/etc/apps/TA-cisco_umbrella/data/dnslogs/\*/\*.csv.gz]
disabled = 0
index = opendns
sourcetype = opendns:dnslogs

-6. Verify data is coming in and you are seeing the proper field extractions by searching the data.
----Example Search: index=awsindexyouchose sourcetype=opendns:dnslogs
----Note: You can look for script output by searching: index=_internal sourcetype=cisco:umbrella:\*

### New features
+ 1.0.3: Added support for Cisco Managed Bucket
+ 1.0.5: Adds support for logging format version 5 + Firewall Logs
+ 1.0.6: Adds support for Audit Logs
+ 1.0.7: Added additional CIM fields for OpenDNS: query_type, message_type

### Fixed issues
+ 1.0.1: Added timezone setting as logs are requested in UTC by default.
+ 1.0.2: Fixed "category" field as it was being split into "categories" field which broke lookup table functionality. Removed trailing dot at the end of "query" field.
+ 1.0.3: Added vendor_product field, lowered action field for CIM compliance, altered eventtype to account for managed buckets.
+ 1.0.4: Fixes an issue in the README under delete-old-umbrella-logs.sh

### Known issues
+ No support for log format version 6 that adds new Proxy Log fields for SWG/DLP modules. If you have these logs please send us (see Dev Support email) some samples and we will add support to this TA.

### Third-party software attributions
+ opendns_dnslogs_categories.csv from https://api.opendns.com/v3/categories

### DEV SUPPORT
Contact: splunk-app@hurricanelabs.com
