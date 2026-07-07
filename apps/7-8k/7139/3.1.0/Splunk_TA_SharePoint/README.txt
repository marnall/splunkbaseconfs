Splunk Add-on for SharePoint API 
Copyright (c) 2023 omztec LLC. All Right Reserved.
Email: support@omztec.com
Tel: 202-909-0805


Features: 
                                             * Splunk Add-on for SharePoint API requires to be installed in a Linux machine with Splunk HF installed on it.

-Splunk Add-on for SharePoint API is an API based Splunk TA
-This App pulls Files from Office365 SharePoint site or Stand Alone Cloud/On-Prem Servers (Need to select one of them). Please see SECTIONs-(a) and (b) in the config.ini file. 
-These APIs are allowed to pull the Delta (Delta based on time) from the SharePoint site.
-Types of source files should be in json,csv,xml, or/and xlsx formatted in the SharePoint site.
-It only pulls files from the location specified in config.ini file -see # SECTION-(c) in config.ini file.
-All Downloaded files from SharePoint site converted to UTF-8 json formatted files and stored in OUT_DIR location specified SECTION-(d) in config.ini files.

System Requirements for Splunk Add-on for SharePoint API:
-OS 
    -Linux 7 - above
    -Ubuntu 20.x
-python 3.9 or above
-python modules (see requirements.txt for detail list of modules) 
-Linux server (Cloud or OnPrem) with Splunk and HF installed on it

Description of Folders and Files: 
-config.ini: API parameters initialization (see inside of this files for details of it to make any changes in the content of config.ini files)
-requirements.txt: required python modules to execute this SPlunk_TA (these modules need to be installed into the Linux machine to run this Splunk Add-on)
-cert folder: contains 2 certificate files 
     -These 2 files do not require for Stand Alone Cloud or On-Prem Server
     -cert.crt: contains public key and this file need to be uploaded to Office365 SharePoint with require permission
     -Cert.key: Contains private key
-config.py: it calls and initializes API parameters (Should not make any changes)
-json_converter.py: convert all files to UTF-8 json (Should not make any changes)
-s3_utils.py:use to write data into AWS S3 Bucket (Should not make any changes)
-sqs_utils.py:use to write data into AWS SQS (Should not make any changes)
-shrpoint_api_aws.py: executable python file (Should not make any changes)
-default: Contains Splunk props.conf, inputs.conf, and app.conf files

Where to Install:
-Heavy forwarders
   -Supported: Yes
   -Required: Yes
   -Comments: This add-on requires heavy forwarders to execute its functionalities and Splunk ingestion
-Universal forwarders
   -Supported: No
   -Required: No
   -Comments: This add-on requires heavy forwarders.
-Search heads
   -Supported: Yes
   -Required: No
   -Comments: All operation and execution processed can be done in HFs

Splunk Ingestion: 
-Converted json formatted files can be ingested into SPLUNK using the props.conf and inputs.config files included in this app.
OR
-Converted json formatted files can also be written to AWS SQS or/and S3 Bucket- see the SECTIONs-(e),(f), and (g) in the config.ini file. In this case, Splunk AWS Add-on (AWS-TA) needs to be used to ingest that data from AWS SQS/S3 bucket to Splunk.

How to Execute API:
-To automate this process configure a cron job in Linux OS to exectute shrpoint_api_aws.py scripts with require frequencies.

How to get Certificates:
-Use the certificates provided within this Splunk-TA
OR
-Create own certificates
OR
Contact omzTec LLC: support@omztec.com

-



  

 