Cisco CWS Add-on for Splunk version 1.0
Copyright (C) 2015 Cisco Systems. All Rights Reserved.
 
The Cisco CWS Add-on for Splunk allows a Splunk Enterprise administrator to ingest Cisco Cloud Web Security (CWS) log files from Amazon S3 servers. You can use Splunk Enterprise to analyze these logs directly or use them as a contextual data source to correlate with other communication and authentication data in Splunk Enterprise.


---------------------------------
Setting up the CWS TA Data Inputs
---------------------------------
Pre-requisite:
1. Ensure that the device where Splunk is installed can connect to the S3 cloud
2. The Cisco_CWS_TA app is present at $SPLUNK_HOME/etc/apps directory.

Steps:
1. Navigate to Settings -> Data Inputs.
2. Under Local inputs, click on "Cisco CWS Logs".
3. Configure the entry to match the AWS S3 account, where:
   -> client_id/CWS Client ID is the S3 bucket name, 
   -> S3 Key and S3 Secret for your Amazon S3 account and Click Save.
4. Click Enable on the Status column.
5. Sync should begin in a few minutes as the cron job runs in the background and ingests the CWS log data.

NOTE: By default, the sync begins for log data that is 4 hours from the current time.
