# Protocol Data Inputs v2.0.0

## IMPORTANT

The Python code in this App is dual 2.7/3 compatible.
This version of the App enforces Python 3 for execution of the modular input script when running on Splunk 8+ in order to satisfy Splunkbase AppInspect requirements.
If running this App on Splunk versions prior to 8 , then Python 2.7 will get executed.


## Overview

This is a Splunk Add-On for receiving data via a number of different data protocols.

## Protocols

* TCP
* TCP w/ TLS , optional client certificate authentication
* UDP (unicast and multicast)
* HTTP (PUT and POST methods only , data in request body & file uploads)
* HTTPS (PUT and POST methods only , data in request body  & file uploads) , optional client certificate authentication
* Websockets
* SockJS

## But we already have TCP/UDP natively in Splunk

Yes we do. And by all means use those. But if you want to perform some custom data handling and pre-processing of the received data before it gets indexed (above and beyond what you can accomplish using Splunk conf files) , then this Modular Input presents another option for you.

Furthermore , this Modular Input also implements several other protocols for sending data to Splunk.


## Implementation

This Modular Input utilizes VERTX.IO version 2.1.4 under the hood.http://vertx.io/vertx2/manual.html#what-is-vertx.

This framework provides for an implementation that is :

* asynchronous
* event driven (reactive)
* polyglot (code custom data handlers in java , javascript , groovy , scala , clojure , ruby , python , any JVM lang with a vertx module)
* non blocking IO
* scales over all your available cores
* can serve high volumes of concurrent client connections

## Polyglot Custom Data Handling / Pre Processing 

The way in which the Modular Input processes the received raw data is entirely pluggable with custom implementations should you wish. 

This allows you to :

* pre process the raw data before indexing 
* transform the data into a more optimum state for Splunk
* perform custom computations on the data that the Splunk Search language is not the best fit for
* decode binary data (encrypted , compressed , images , proprietary protocols , EBCDIC etc....)
* enforce CIM compliance on the data you feed into the Splunk indexing pipeline
* basically do anything programmatic to the raw byte data you want

To do this you code a Vertx "Verticle" to handle the received data. http://vertx.io/vertx2/manual.html#verticle

These data handlers can be written in numerous JVM languages. http://vertx.io/vertx2/manual.html#polyglot

You then place the handler in the `$SPLUNK_HOME/etc/apps/protocol_ta/bin/datahandlers` directory.

On the Splunk config screen for the Modular Input there is a field where you can then specify the name of this handler to be applied.

If you don't need a custom handler then the default handler com.splunk.modinput.protocolverticle.DefaultHandlerVerticle will be used.

To get started , you can refer to the  default handler examples in the datahandlers directory.

## Supported languages and file extensions

* Javascript .js 
* CoffeeScript .coffee
* Ruby .rb
* Python .py
* Groovy .groovy
* Java .java (compiled to .class)
* Scala .scala
* Clojure .clj
* PHP .php
* Ceylon .ceylon

Note : experimental Nashorn support is included for js and coffee (requires Java 8). To use the Nashorn JS/Coffee engine rather than the default Rhino engine , then edit `protocol_ta/bin/vertx_conf/langs.properties`

## SSL / TLS

This is provisioned using your own Java Keystore that you can create using the keytool utility that is part of the JDK.

Refer to `http://vertx.io/vertx2/core_manual_java.html#ssl-servers`

## Authentication

Client certificate based authentication can be enabled for the TLS/SSL channels you setup.

## VERTX Modules and Repositorys

Any required Vertx modules , such as various language modules for the polyglot functionality (JS , Scala , Groovy etc...) will be dynamically downloaded from online repositorys and installed in your `protocol_ta/bin/vertx_modules` directory.

You can edit your repository locations in `protocol_ta/bin/vertx_conf/repos.txt`

## Performance tuning tips

Due to the nature of the async/event driven/non blocking architecture , the out of the box default settings may just well suffice for you.

But there are some other parameters that you can tune to take more advantage of your underlying computing resource(ie: cpu cores) available to you.

These are the `server_verticle_instances` and `handler_verticle_instances` params.

Refer to `http://vertx.io/vertx2/core_manual_java.html#specifying-number-of-instances` for an explanation of how increasing the number of instances may help you.

You can also tune the TCP accept queue settings (also requires OS tweaks) , particularly if you are receiving lots of connections within a short time span.

Refer to http://vertx.io/vertx2/manual.html#improving-connection-time

## Data Output

By default data will be output to STDOUT in Modular Input Stream XML format.

However you can bypass this if you wish and declare that data is output to a Splunk TCP port or via Splunk's HTTP Event Collector.

## Dependencies

* Splunk 5.0+
* Java Runtime 1.7+
* Supported on Windows, Linux, MacOS, Solaris, FreeBSD, HP-UX, AIX

## Binary File Declaration

This App contains a custom modular input written in Java

As such , the following binary JAR archives are required

* bin/lib/commons-logging-1.2.jar
* bin/lib/aspectjweaver.jar
* bin/lib/jaxb-runtime-2.3.2.jar
* bin/lib/json.jar
* bin/lib/vertx-hazelcast-2.1.4.jar
* bin/lib/httpclient-4.4.1.jar
* bin/lib/activation-1.1.1.jar
* bin/lib/commons-logging-1.1.3.jar
* bin/lib/ion-java-1.0.1.jar
* bin/lib/vertx-platform-2.1.4.jar
* bin/lib/splunk_tlsv12.jar
* bin/lib/jackson-databind-2.6.6.jar
* bin/lib/log4j-api-2.17.2.jar
* bin/lib/log4j-core-2.17.2.jar
* bin/lib/jackson-core-2.6.6.jar
* bin/lib/netty-all-4.0.21.Final.jar
* bin/lib/httpclient-4.5.2.jar
* bin/lib/commons-codec-1.9.jar
* bin/lib/javax.mail-api-1.4.6.jar
* bin/lib/vertx-core-2.1.4.jar
* bin/lib/jaxb-api-2.3.0.jar
* bin/lib/hazelcast-3.2.3.jar
* bin/lib/jackson-dataformat-cbor-2.6.6.jar
* bin/lib/istack-commons-runtime-3.0.10.jar
* bin/lib/joda-time-2.8.1.jar
* bin/lib/ImageHandler.jar
* bin/lib/freemarker-2.3.9.jar
* bin/lib/httpasyncclient-4.1.jar
* bin/lib/httpcore-4.4.4.jar
* bin/lib/commons-imaging-1.0-R1401825.jar
* bin/lib/httpcore-nio-4.4.1.jar
* bin/lib/jackson-annotations-2.6.0.jar
* bin/lib/jaxb-core-2.3.0.1.jar
* bin/lib/protocolmodinput.jar
* bin/lib/httpasyncclient-cache-4.1.jar
* bin/lib/httpclient-cache-4.4.1.jar
* bin/lib/httpcore-4.4.1.jar
* bin/lib/jython-standalone-2.7.0.jar
* bin/lib/aspectjrt-1.8.2.jar

## Setup

* Optionally set your JAVA_HOME environment variable to the root directory of your JRE installation.If you don't set this , the input will look for a default installed java executable on the path.
* Untar the release to your $SPLUNK_HOME/etc/apps directory
* Restart Splunk
* If you are using a Splunk UI Browse to `Settings -> Data Inputs -> Protocol Data Inputs` to add a new Input stanza via the UI
* If you are not using a Splunk UI (ie: you are running on a Universal Forwarder) , you need to add a stanza to inputs.conf directly as per the specification in `README/inputs.conf.spec`. The `inputs.conf` file should be placed in a `local` directory under an App or User context.

## Encryption of credentials

If you require an encrypted credential in your configuration , then you can enter it on the  setup page.

Then in your configration stanza refer to it in the format `{encrypted:somekey}`

Where `somekey` is any value you choose to enter on the setup page to refer to your credential.

## Activation Key

You require an activation key to use this App. Visit http://www.baboonbones.com/#activation  to obtain a non-expiring key


## Logging

Modular Input logs will get written to `$SPLUNK_HOME/var/log/splunk/protocolmodinput_app_modularinput.log`

These logs are rotated after a max size of 5MB with a backup limit of 5.

Setup logs will get written to `$SPLUNK_HOME/var/log/splunk/protocolmodinput_app_setuphandler.log`

These logs are rotated daily with a backup limit of 5.

The Modular Input logging level can be specified in the input stanza you setup. The default level is `INFO`.

You can search for these log sources in the `_internal` index or browse to the `Logs` menu item on the App's navigation bar.

## JVM Heap Size

The default heap maximum is 256MB.
If you require a larger heap, then you can alter this in `$SPLUNK_HOME/etc/apps/protocol_ta/bin/protocol.py`

## JVM System Properties

You can declare custom JVM System Properties when setting up new input stanzas.
Note : these JVM System Properties will apply to the entire JVM context and all stanzas you have setup

## Troubleshooting

* JAVA_HOME environment variable is set or "java" is on the PATH for the user's environment you are running Splunk as
* You are using Splunk 5+
* You are using a 1.7+ Java Runtime
* You are running on a supported operating system
* Run this command as the same user that you are running Splunk as and observe console output : `$SPLUNK_HOME/bin/splunk cmd python ../etc/apps/protocol_ta/bin/protocol.py --scheme` 

## Support

[BaboonBones.com](http://www.baboonbones.com#support) offer commercial support for implementing and any questions pertaining to this App.

