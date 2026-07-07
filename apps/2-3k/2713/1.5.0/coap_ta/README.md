# Splunk COAP (Constrained Application Protocol) Modular Input v1.5.0

## IMPORTANT

The Python code in this App is dual 2.7/3 compatible.
This version of the App enforces Python 3 for execution of the modular input script when running on Splunk 8+ in order to satisfy Splunkbase AppInspect requirements.
If running this App on Splunk versions prior to 8 , then Python 2.7 will get executed.


## Overview

This is a Splunk Modular Input Add-On for indexing messages from a COAP Server.

## What is COAP ?

`http://en.wikipedia.org/wiki/Constrained_Application_Protocol`

## COAP and MQTT

http://eclipse.org/community/eclipse_newsletter/2014/february/article2.php

## Implementation

This Modular Input utilizes the Californium Java client library version 1.0 , https://eclipse.org/californium/

## Dependencies

* Splunk 5.0+
* Java Runtime 1.7+
* Supported on Windows, Linux, MacOS, Solaris, FreeBSD, HP-UX, AIX

## Binary File Declaration

This App contains a custom modular input written in Java

As such , the following binary JAR archives are required

* bin/lib/commons-logging-1.2.jar
* bin/lib/jaxb-runtime-2.3.2.jar
* bin/lib/coapmodinput.jar
* bin/lib/json.jar
* bin/lib/httpclient-4.4.1.jar
* bin/lib/activation-1.1.1.jar
* bin/lib/splunk_tlsv12.jar
* bin/lib/log4j-api-2.17.2.jar
* bin/lib/log4j-core-2.17.2.jar
* bin/lib/commons-codec-1.9.jar
* bin/lib/jaxb-api-2.3.0.jar
* bin/lib/istack-commons-runtime-3.0.10.jar
* bin/lib/httpasyncclient-4.1.jar
* bin/lib/httpcore-nio-4.4.1.jar
* bin/lib/jaxb-core-2.3.0.1.jar
* bin/lib/californium-core-1.0.0.jar
* bin/lib/httpasyncclient-cache-4.1.jar
* bin/lib/httpclient-cache-4.4.1.jar
* bin/lib/httpcore-4.4.1.jar
* bin/lib/element-connector-1.0.0-M1.jar

## Setup

* Optionally set your JAVA_HOME environment variable to the root directory of your JRE installation.If you don't set this , the input will look for a default installed java executable on the path.
* Untar the release to your $SPLUNK_HOME/etc/apps directory
* Restart Splunk
* If you are using a Splunk UI Browse to `Settings -> Data Inputs -> COAP` to add a new Input stanza via the UI
* If you are not using a Splunk UI (ie: you are running on a Universal Forwarder) , you need to add a stanza to inputs.conf directly as per the specification in `README/inputs.conf.spec`. The `inputs.conf` file should be placed in a `local` directory under an App or User context.

## Encryption of credentials

If you require an encrypted credential in your configuration , then you can enter it on the  setup page.

Then in your configration stanza refer to it in the format `{encrypted:somekey}`

Where `somekey` is any value you choose to enter on the setup page to refer to your credential.

## Activation Key

You require an activation key to use this App. Visit http://www.baboonbones.com/#activation  to obtain a non-expiring key


## Logging

Modular Input logs will get written to `$SPLUNK_HOME/var/log/splunk/coapmodinput_app_modularinput.log`

These logs are rotated after a max size of 5MB with a backup limit of 5.

Setup logs will get written to `$SPLUNK_HOME/var/log/splunk/coapmodinput_app_setuphandler.log`

These logs are rotated daily with a backup limit of 5.

The Modular Input logging level can be specified in the input stanza you setup. The default level is `INFO`.

You can search for these log sources in the `_internal` index or browse to the `Logs` menu item on the App's navigation bar.

## JVM Heap Size

The default heap maximum is 64MB.
If you require a larger heap, then you can alter this in `$SPLUNK_HOME/etc/apps/coap_ta/bin/coap.py` 

## JVM System Properties

You can declare custom JVM System Properties when setting up new input stanzas.
Note : these JVM System Properties will apply to the entire JVM context and all stanzas you have setup

## Customized Message Handling

The way in which the Modular Input processes the received COAP messages is enitrely pluggable with custom implementations should you wish.

To do this you code an implementation of the com.splunk.modinput.coap.AbstractMessageHandler class and jar it up.

Ensure that the necessary jars are in the `$SPLUNK_HOME/etc/apps/coap_ta/bin/lib` directory.

If you don't need a custom handler then the default handler com.splunk.modinput.coap.DefaultMessageHandler will be used.



## Troubleshooting

* JAVA_HOME environment variable is set or "java" is on the PATH for the user's environment you are running Splunk as
* You are using Splunk 5+
* You are using a 1.7+ Java Runtime
* You are running on a supported operating system
* Run this command as the same user that you are running Splunk as and observe console output : `$SPLUNK_HOME/bin/splunk cmd python ../etc/apps/coap_ta/bin/coap.py --scheme`

## Support

[BaboonBones.com](http://www.baboonbones.com#support) offer commercial support for implementing and any questions pertaining to this App.


