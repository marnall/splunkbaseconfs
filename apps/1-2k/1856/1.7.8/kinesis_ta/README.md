# Splunk Amazon Kinesis Modular Input v1.7.8

## IMPORTANT

The Python code in this App is dual 2.7/3 compatible.
This version of the App enforces Python 3 for execution of the modular input script when running on Splunk 8+ in order to satisfy Splunkbase AppInspect requirements.
If running this App on Splunk versions prior to 8 , then Python 2.7 will get executed.


## Overview

This is a Splunk Modular Input Add-On for indexing records from Amazon Kinesis.

## What is Kinesis ?

http://aws.amazon.com/kinesis/

## Dependencies

* Splunk 7.0+ Enterprise or Cloud
* Java Runtime 1.8+
* Supported on all Splunk platforms

## Binary File Declaration

This App contains a custom modular input written in Java

As such , the following binary JAR archives are required

* bin/lib/jackson-core-2.1.1.jar
* bin/lib/jackson-databind-2.1.1.jar
* bin/lib/aws-java-sdk-1.7.13.jar
* bin/lib/commons-logging-1.2.jar
* bin/lib/jaxb-runtime-2.3.2.jar
* bin/lib/json.jar
* bin/lib/httpcore-4.2.jar
* bin/lib/commons-logging-1.1.1.jar
* bin/lib/httpclient-4.4.1.jar
* bin/lib/activation-1.1.1.jar
* bin/lib/splunk_tlsv12.jar
* bin/lib/log4j-api-2.17.2.jar
* bin/lib/log4j-core-2.17.2.jar
* bin/lib/httpclient-4.2.jar
* bin/lib/commons-codec-1.9.jar
* bin/lib/jaxb-api-2.3.0.jar
* bin/lib/amazon-kinesis-client-1.1.0.jar
* bin/lib/kinesismodinput.jar
* bin/lib/joda-time-2.2.jar
* bin/lib/commons-codec-1.3.jar
* bin/lib/istack-commons-runtime-3.0.10.jar
* bin/lib/jackson-annotations-2.1.1.jar
* bin/lib/httpasyncclient-4.1.jar
* bin/lib/httpcore-nio-4.4.1.jar
* bin/lib/jaxb-core-2.3.0.1.jar
* bin/lib/httpasyncclient-cache-4.1.jar
* bin/lib/httpclient-cache-4.4.1.jar
* bin/lib/httpcore-4.4.1.jar

## Setup

* Optionally set your JAVA_HOME environment variable to the root directory of your JRE installation.If you don't set this , the input will look for a default installed java executable on the path.
* Untar the release to your `$SPLUNK_HOME/etc/apps` directory
* Restart Splunk
* Browse to the App's landing page.
* Browse to the `Setup Credentials` menu tab and setup AWS Credentials.
* Encrypted credentials are saved to `$SPLUNK_HOME/etc/apps/kinesis_ta/local/passwords.conf`
* Enter your Activation Key , see below
* Browse to the `Data Inputs` menu tab and setup your Kinesis Inputs.

## Activation Key

* You require an activation key to use this App. Visit http://www.baboonbones.com/#activation to obtain a non-expiring key
* Browse to the `Activation Key` menu tab and enter your key.


## Logging

Modular Input logs will get written to `$SPLUNK_HOME/var/log/splunk/kinesismodinput_app_modularinput.log`

These logs are rotated after a max size of 5MB with a backup limit of 5.

Setup logs will get written to `$SPLUNK_HOME/var/log/splunk/kinesismodinput_app_setuphandler.log`

These logs are rotated daily with a backup limit of 5.

The Modular Input logging level can be specified in the input stanza you setup. The default level is `INFO`.

You can search for these log sources in the `_internal` index or browse to the `Logs` menu item on the App's navigation bar.

Any Splunk internal errors can also be searched like : `index=_internal kinesis.py ERROR`

## JVM Heap Size

The default heap maximum is 64MB.
If you require a larger heap, then you can alter this in `$SPLUNK_HOME/etc/apps/kinesis_ta/bin/kinesis.py`

## JVM System Properties

You can declare custom JVM System Properties when setting up new input stanzas.
Note : these JVM System Properties will apply to the entire JVM context and all stanzas you have setup

## Customized Message Handling

The way in which the Modular Input processes the received Kinesis records is enitrely pluggable with custom implementations should you wish.

To do this you code an implementation of the com.splunk.modinput.kinesis.AbstractMessageHandler class and jar it up.

Ensure that the necessary jars are in the `$SPLUNK_HOME/etc/apps/kinesis_ta/bin/lib` directory.

If you don't need a custom handler then the default handler com.splunk.modinput.kinesis.DefaultMessageHandler will be used.

## App Object Permissions

Everyone's Splunk environment and Users/Roles/Permissions setup are different.

By default this App ships with all of it's objects globally shared (in `metadata/default.meta` )

So if you need to limit access to functionality within the App , such as who can see the setup page , then you should browse to  `Apps -> Manage Apps -> Amazon Kinesis Modular Input -> View Objects` , and adjust the permissions accordingly for your specific Splunk environment.

## Troubleshooting

* JAVA_HOME environment variable is set or "java" is on the PATH for the user's environment you are running Splunk as
* You are using Splunk 7+
* You are using a 1.8+ Java Runtime
* Run this command as the same user that you are running Splunk as and observe console output : `$SPLUNK_HOME/bin/splunk cmd python ../etc/apps/kinesis_ta/bin/kinesis.py --scheme`

## Support

[BaboonBones.com](http://www.baboonbones.com#support) offer commercial support for implementing and any questions pertaining to this App.


