AWS Web Application Firewall Add-on

Add-on Homepage: https://apps.splunk.com/apps/id/TA-aws_waf

Author: Hurricane Labs

### Description ###
The purpose of this add-on is to provide value to your AWS Web Application Firewall (WAF) logs. This is done by making the logs CIM compliant, adding tagging for Enterprise Security data models, and other knowledge objects to make searching and visualizing this data easy. This add-on also provides a concise guide for how to get your AWS WAF logs into Splunk using AWS Kinesis Firehose (see README for more details).

+Built for Splunk Enterprise 6.x.x and higher
+CIM Compliant (CIM 4.0.0 or higher)
+Ready for Enterprise Security
+Built around JSON format from AWS Kinesis Firehose
++https://docs.splunk.com/Documentation/AddOns/released/Firehose/ConfigureFirehose
++https://docs.aws.amazon.com/waf/latest/developerguide/logging.html

### Useful Information ###
1. This add-on assumes you are using the sourcetype "aws:waf". If you need to use another sourcetype, copy default/props.conf into local/props.conf and change the sourcetype stanza. You could also use a source based stanza if needed.
2. This add-on requires the data be in the JSON format from Kinesis Firehose. This was only tested using AWS Kinesis Firehose sending to Splunk using HEC (best practice).
3. Theoretically you could have WAF stream to Firehose and have Firehose write to an S3 bucket or SQS in JSON format and use the AWS Add-on to pull from there. As long as you have it in the exact same  format, there's no reason this add-on wouldn't work. I'd still recommend using HEC over S3/SQS because it's more efficient and scales better. I have not tested this.
--a. https://splunkbase.splunk.com/app/1876/
4. If you want to save on license at the cost of operational awareness, you can trim out default allowed WAF events
--a. https://aws.amazon.com/blogs/security/trimming-aws-waf-logs-with-amazon-kinesis-firehose-transformations/
5. If you want to map ruleGroupId to a human readable rule name, you can use a lookup table (utilizing an automatic lookup) to do so. This would go on your Search Head(s):

$SPLUNK_HOME/etc/apps/TA-aws_waf/lookups/aws_waf_rule_lookup.csv
rule,ruleGroupList{}.ruleGroupId
rule01_sql_injection_rule_id,16d7c32b-d853-478c-9540-5538167d202b
rule02_auth_token_rule_id,96730828-e43c-4613-98f0-1fee90d092b2


$SPLUNK_HOME/etc/apps/TA-aws_waf/local/transforms.conf
[aws_waf_rule_lookup]
batch_index_query = 0
case_sensitive_match = 1
filename = aws_waf_rule_lookup.csv

$SPLUNK_HOME/etc/apps/TA-aws_waf/local/props.conf
LOOKUP-aws_waf_rule_lookup = aws_waf_rule_lookup "vendor_rule" OUTPUTNEW rule

### INSTALLATION AND CONFIGURATION ###
Search Head: Add-on Always Required (Knowledge Objects)
Heavy Forwarder: Add-on Possibly Required (Data Collection and Event Parsing)
Indexer: Add-on Possibly Required (Data Collection and Event Parsing)
SH & Indexer Clustering: Supported

#### Add-on Installation Instructions ####
1. Install this add-on on the Splunk Enterprise instance that has the HEC inputs/token.
--a. Restart Splunk to ensure the add-on settings (line breaking and timestamp) are in place before proceeding.
2. Install this add-on on your Search Heads where the knowledge objects are required.
--a. A Splunk restart will not be required. If the knowledge objects do not appear, run a debug/refresh.
--b. To increase tagging efficiency, copy default/eventtypes.conf to local/eventtypes.conf and add "index=XYZ" where XYZ is the index you're using.
3. Proceed to follow "Data Ingestion Instructions"

#### Data Ingestion Instructions ####
1. Setup a HEC input and token to be used in AWS. Set the index to whatever you prefer, and set the sourcetype to "aws:waf". Make sure to enable indexer acknowledgement as well. All of this will be in inputs.conf (see example inputs.conf below).
[http://aws_waf]
disabled = 0
index = aws
indexes = aws
sourcetype = aws:waf
useACK = true
token = <HEC_TOKEN_HERE>
--a. Where the token goes is going to vary greatly depending on your environment. Here are some use cases ranked in order of preference:
----1. Best Practice: Use an Indexer Cluster & a third party Load Balancer (this is NOT a Splunk component/feature). Load Balancer should listen on TCP/443 and distribute requests to TCP/8088 on the indexers. HEC token and input should be distributed from your Cluster Master to the indexer peers.
------a. https://docs.splunk.com/Documentation/AddOns/released/Firehose/ConfigureanELB
----2. Single Indexer: If you have a standalone indexer (not clustered), have your indexer listen on TCP/8088. Setup the HEC inputs and token locally, or use your Deployment Server.
----3. Heavy Forwarder: A Heavy Forwarder is required if you can't setup an external load balancer in front of your indexer cluster. Have your Heavy Forwarder listen on TCP/8088. Setup the HEC inputs and token locally, or use your Deployment Server.
2. Configure WAF to stream to Kinesis Firehose: https://docs.aws.amazon.com/waf/latest/developerguide/logging.html
--a. Keep in mind your end goal is to keep these events separated logically and in JSON format containing all the fields listed from above. If you do something that deviates, you may need to adjust some regex in local/props.conf.
3. Configure Kinesis Firehose to send data into Splunk over HEC (HTTPS): https://docs.splunk.com/Documentation/AddOns/released/Firehose/ConfigureFirehose
--a. If you're using an external load balancer, your endpoint will be the load balancer. Otherwise, it will be the Splunk instance you're sending directly to.
--b. You should choose "event" as the endpoint type.
--c. This is the step where your HEC token will be used.
--d. You do NOT need this add-on installed. It's only linked here for the helpful documentation.
4. Verify data is coming in and you are seeing the proper field extractions by searching the data:
--a. Example Search: index=* sourcetype=aws:waf

### New features

### Fixed issues

### Known issues

### Third-party software attributions

### DEV SUPPORT
Contact: splunk-app@hurricanelabs.com
