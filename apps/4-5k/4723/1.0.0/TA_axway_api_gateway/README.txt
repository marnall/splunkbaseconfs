# Axway® API Gateway Add-on for Splunk®


Axway API Gateway Add-on for Splunk provides lightweight field extractions for your Axway API Gateway data.

It is meant to be used with the Axway API Gateway App for Splunk.


# Version 1.0.0


# Release Notes


1.0.0: October 2019

- Initial release


# Axway API Gateway data (open logging)


Traffic logs are JSON structured data which schema is documented here: https://docs.axway.com/bundle/APIGateway_762_AdministratorGuide_allOS_en_HTML5/page/Content/AdminGuideTopics/schema.html


# Collect Axway API Gateway data from your Gateway

Open logging should be enabled. Please refer to the following documentation: https://docs.axway.com/bundle/APIGateway_762_AdministratorGuide_allOS_en_HTML5/page/Content/AdminGuideTopics/admin_open_logging.htm

In our AWS setup, open logging data - group-2_instance-1_traffic.log - is monitored by a CloudWatch agent and pulled to a CloudWatch Log Group then pushed to Splunk HTTP Event Collector via Kinesis Firehose.

This Add-on should however work with more simple architectures and ingestion methods depending on your constraints (i.e. monitoring open logging directory with Splunk Universal Forwarder).


# Add-on deployment


Install the Add-on on your Splunk platform.

For distributed environments, the Add-on needs to be deployed on the Search Head as well as on Indexer(s) or Heavy Forwarder depending on the ingress instance as it includes parsing configuration parameters.


# Index Axway API Gateway open logging data


Open logging data should be indexed under the sourcetype 'axway:apigateway:traffic:json'

If the data is ingested via HTTP Event Collector, you need to configure an HEC input:

 [http://<input name>]
 index = <index>
 indexes = <index>
 sourcetype = axway:apigateway:traffic:json
 token = <token>
 useACK = 1

If the data is monitored using a Splunk Universal Forwarder, you need to configure a monitoring stanza:

 [monitor:///<INSTALL_DIR>/apigateway/logs/group-*_instance-*_traffic.log]
 sourcetype = axway:apigateway:traffic:json
 index = <index>


# Log Sample


Do not hesitate to check provided log sample to make sure your indexed data matches data used to build this Add-on.


# Additional notes


This Add-on does not yet include field extractions or directions to ingest payload data.


# For any help or suggestion on this App, contact d2si-spk [at] protonmail.com


