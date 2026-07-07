# Mantisnet App Community Version v1.0
* January 2020
* Developed by BaboonBones, Ltd. ( www.baboonbones.com ) for Mantisnet ( www.mantisnet.com )

## Overview

Community edition App for monitoring data received from Mantisnet Probes

## Mandatory Dependencies

* Splunk 7.0+ , https://www.splunk.com/en_us/download/splunk-enterprise.html
* Supported on all Splunk platforms
* Java Runtime 1.8+ : https://openjdk.java.net

## Optional Dependencies

* URL Toolbox App installed and permission visible to the Mantisnet App/User ,  https://splunkbase.splunk.com/app/2734/

## Network Calls

### Inbound

* If TCP data input enabled , Raw TCP streams on whatever port you configure
* If HTTP Event Collector enabled , HTTPs POST on port 8088 (default)

### Outbound

* Kafka client consuming records from a remote Kafka broker(s) on whatever port you configure
* HTTPS calls made by lookup scripts

## Installation

* Untar the App release to your `SPLUNK_HOME/etc/apps` directory
* Restart Splunk and Login

## Binary File Declaration

This App contains a custom modular input written in Java for consuming records from Kafka

As such , the following binary JAR archives are required in `mantisnet_app/bin/lib`

* activation-1.1.1.jar
* commons-codec-1.9.jar
* commons-logging-1.2.jar
* httpasyncclient-4.1.jar
* httpasyncclient-cache-4.1.jar
* httpclient-4.4.1.jar
* httpclient-cache-4.4.1.jar
* httpcore-4.4.1.jar
* httpcore-nio-4.4.1.jar
* istack-commons-runtime-3.0.10.jar
* jaxb-api-2.3.0.jar
* jaxb-core-2.3.0.1.jar
* jaxb-runtime-2.3.2.jar
* json.jar
* kafka-clients-2.3.0.jar
* kafkamodinput.jar
* log4j-1.2.17.jar
* lz4-java-1.6.0.jar
* slf4j-api-1.7.26.jar
* snappy-java-1.1.7.3.jar
* splunk_tlsv12.jar
* zstd-jni-1.4.0-1.jar

## Distributed Installation

In a distributed Splunk installation you will typically install the App components across Heavy Forwarders and Search Heads.

As this App requires that you have access to the App's Setup page in order to configure the environment , you will have to use a Heavy Forwarder(HF) rather than a Universal Forwarder if you want to split out the data collection logic to a forwarder tier.

The App's setup page will only automatically enable the Kafka stanzas if this App is running on a Splunk instance that is an Indexer or Forwarder server role.

Your HF will forward data into your indexer cluster as per standard Splunk administration of `outputs.conf` configurations.

The Search Heads will then only require the UI,Knowledge Object and components of the App release.

The App release ships with an `app.manifest` file , so you can utilise Splunk's Packaging Toolkit (http://dev.splunk.com/view/packaging-toolkit/SP-CAAAE9V) to build the Search Head App bundle.

## Setup

When you first install the App you will be redirected to the App's setup page. 

Upon saving the setup screen , the Kafka inputs will automatically enable and start polling for data if the Splunk instance is an Indexer or Forwarder server role only.

If you have opted to use TCP or HTTP Event Collector instead for receiving your probe data , then the Kafka inputs will not enable.

Any scripted inputs used for lookup data will also enable automatically.

Check that the  data is being received by browsing to the `Indexed Data -> Data Sources` dashboard.

The setup page can be browsed to at any time for configuration edits via the App's navigation menu.

## Data Sources

### Kafka

The default and preferred means to get data into the App is via Kafka. The default Kafka configuration and what you specify on the setup page should be satisfactory. However if you need to customise any settings then you can browse to `Data Inputs -> Kafka Topics` via the App's navigation menu.

All of the Kafka stanzas will run multithreaed in a single JVM process.

If you need to scale Kafka consumer polling , then you can simply clone an existing Kafka stanza.These stanzas will then run as individual threads.

The main constraint to be aware of with adding more stanzas/threads is the amount of JVM heap memory that you have allocated.

In `mantisnet_app/bin/mantisnet_kafka.py` this is set to a maximum of 512 MB (line 99) , but you can increase this if you need to.

If running multiple threads in a single JVM instance is still not acheiving the desired data collection scale , then you can deploy (n) Mantisnet Apps out horizontally across (n) Splunk Heavy Forwarders that will all run in parallel and forward the collected data into your Splunk Index Cluster. In essence , by utilising Splunk distributed architectures in this fashion , your scale is only going to be limited by your ability to push out more Heavy Forwarders.


### HTTP Event Collector

Via the App's navigation menu , browse to  `Data Inputs -> HTTP Event Collector` to setup your data input.

Be sure to specify the correct `sourcetype` listed below for the probe data being sent to Splunk.

Also , select the `index` that you specified in the App setup screen.


### Raw TCP

Via the App's navigation menu , browse to  `Data Inputs -> TCP` to setup your data input.

Be sure to specify the correct `sourcetype` listed below for the probe data being sent to Splunk.

Also , select the `index` that you specified in the App setup screen.


## Event Index

This App does not create any indexes by default.If you want to change the default index (`main`), ensure you also change the global index used for searches in `mantisnet_app/default/macros.conf` in the 'mantisnet_index' stanza. This is done for you automatically if you change the index via the App's setup page.

You will also need to update any index values in `mantisnet_app/default/inputs.conf` on your Splunk Forwarders.

## Sourcetypes

Please ensure that you use these sourcetypes for your indexed probe data.

DNS Probes : **mantisnet_dns**

## Eventtypes

Please ensure that you use these eventtypes for your probe searches.

DNS Probes : **mantisnet_dns_probe**

## Saved Searches / Alerts

Via the App's navigation menu , browse to  `Additional Config -> Saved Searches / Alerts` to setup your searches.

For convenience , the dashboards in the App are annotated with the underlying Splunk Search to make it easier for you to create your saved searches to drive alerts , Phantom integration etc..

## Phantom Integration

Via the App's navigation menu , browse to  `Additional Config -> Phantom Integration` for more information.

## VictorOps Integration

Via the App's navigation menu , browse to  `Additional Config -> VictorOps Integration` for more information.

## Permissions

By default ,this App is set to be Globally accessible by all users and apps.

## Lookups

The following CSV file lookups are included in this App (note : other 3rd party Apps may also ship their own lookups also)

### l4protocol_lookup

Used to resolve protocol codes to names.

### rrtype_lookup

Used to resolved rrtype codes to names.

### FP_entropy_domains

Used to eliminate false positives in Shannon entropy searches.

### public_dns_lookup

Used to lookup known public DNS Server IPs.
Note : this lookup file is asynchronously written by the `mantisnet_app/bin/public_dns_lookup.py` scripted input.


## Logging and Errors

Logs get written to `SPLUNK_HOME/var/log/splunk/mantisnet_app*.log`

* `mantisnet_app_kafka_modinput.log` : Kafka modular input script
* `mantisnet_app_lookup_public_dns.log` : Scripted Input for Public DNS Data
* `mantisnet_app_setuphandler.log` : Custom setup handler script

These log files are rotated daily and then timestamped.

You can set the logging level globally for the Kafka modular input via the App's setup page.

Also , you can override this global level on a per Kafka stanza basis so that each stanza has it's own logging level.

You can then easily search for logs in Splunk : `index=_internal source=*mantisnet_app*.log ERROR`

Also , via the App's navigation bar you have convenient access to dashboards for displaying the logs.


## Troubleshooting

* You are using Splunk 7+
* Look for any errors as detailed in the "Logging and Errors" section
* Any firewalls blocking outgoing / incoming network calls ?
* Are your proxy settings correct if required on your network ?
* Are there any error logs at the target Kafka broker(s) ?
* Are your URL's correct ?
* Is your authentication setup correctly ?
* If you are running on a Universal Forwarder , is Python installed on the OS system path ?
* Can you see requests being made on the wire ? ie: using Wireshark or another wire capture utility


## Contact

This App was developed by BaboonBones, Ltd. for Mantisnet ( www.mantisnet.com )
* www.baboonbones.com
* info@baboonbones.com