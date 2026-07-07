# Splunk JMS Modular Input v2.2.9

## IMPORTANT

The Python code in this App is dual 2.7/3 compatible.
This version of the App enforces Python 3 for execution of the modular input script when running on Splunk 8+ in order to satisfy Splunkbase AppInspect requirements.
If running this App on Splunk versions prior to 8 , then Python 2.7 will get executed.


## Overview

This is a Splunk modular input add-on for polling message queues and topics via the JMS interface.

It implements the  <a href="http://docs.splunk.com/Documentation/Splunk/latest/AdvancedDev/ModInputsIntro">Splunk Modular Inputs Framework</a>


## Why JMS ?

JMS is simply a messaging API and is a convenient means by which to write 1 modular input that can talk to several different underlying messaging
providers :  MQSeries(Websphere MQ), ActiveMQ, TibcoEMS, HornetQ, RabbitMQ,Native JMS, Weblogic JMS, Sonic MQ etc..
The modular input code is generic because it is programmed to the JMS interface.
You can then supply messaging provider specific jar files at runtime.
<a href="http://en.wikipedia.org/wiki/Java_Message_Service">More details on JMS at Wikipedia</a>

## Dependencies

* Splunk 7.0+
* Java Runtime 1.8+
* Supported on all Splunk platforms

## Binary File Declaration

This App contains a custom modular input written in Java

As such , the following binary JAR archives are required

* bin/lib/commons-logging-1.2.jar
* bin/lib/jaxb-runtime-2.3.2.jar
* bin/lib/json.jar
* bin/lib/jms.jar
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
* bin/lib/jmsmodinput.jar
* bin/lib/jaxb-core-2.3.0.1.jar
* bin/lib/httpasyncclient-cache-4.1.jar
* bin/lib/httpclient-cache-4.4.1.jar
* bin/lib/httpcore-4.4.1.jar

## Setup

* Optionally set your JAVA_HOME environment variable to the root directory of you JRE installation.If you don't set this , the input will look for a default installed java executable on the path.
* Untar the release to your $SPLUNK_HOME/etc/apps directory
* Restart Splunk
* Browse to the App's landing page.
* Browse to the `Setup Credentials` menu tab and setup any JNDI and Destination username(s)/password(s).
* Encrypted credentials are saved to `$SPLUNK_HOME/etc/apps/jms_ta/local/passwords.conf`
* Enter your Activation Key , see below
* Browse to the `Data Inputs` menu tab and setup your JMS Inputs.

## Activation Key

* You require an activation key to use this App. Visit http://www.baboonbones.com/#activation to obtain a non-expiring key
* Browse to the `Activation Key` menu tab and enter your key.

##JNDI vs Local mode

For the most part you will setup your JMS connectivity using JNDI to obtain the remote JMS objects.
However, you can bypass JNDI if you wish and use local instantiation.
To this you must code an implementation of the com.splunk.modinput.jms.LocalJMSResourceFactory interface.
You can then bundle the classes in a jar file and place them in `$SPLUNK_HOME/etc/apps/jms_ta/bin/lib`
The configuration screen for creating a new JMS input allows you to choose local or jndi as the instantiation mode.
So choose local , and then you can specify the name of implementation class, as well as any declarative paramaters you want to pass in.

## Logging

Modular Input logs will get written to `$SPLUNK_HOME/var/log/splunk/jmsmodinput_app_modularinput.log`

These logs are rotated after a max size of 5MB with a backup limit of 5.

Setup logs will get written to `$SPLUNK_HOME/var/log/splunk/jmsmodinput_app_setuphandler.log`

These logs are rotated daily with a backup limit of 5.

The Modular Input logging level can be specified in the input stanza you setup. The default level is `INFO`.

You can search for these log sources in the `_internal` index or browse to the `Logs` menu item on the App's navigation bar.

Any Splunk internal errors can also be searched like : `index=_internal jms.py ERROR`

## Third party jars

If you require specific JMS provider or JNDI Context implementation jars, then you can simply copy these to `$SPLUNK_HOME/etc/apps/jms_ta/bin/lib`

They will be automatically picked up upon restart 

##JVM Heap Size

The default heap maximum is 64MB.
If you require a larger heap, then you can alter this in `$SPLUNK_HOME/etc/apps/jms_ta/bin/jms.py`

##JVM System Properties

You can declare custom JVM System Properties when setting up new input stanzas.
Note : these JVM System Properties will apply to the entire JVM context and all stanzas you have setup

## Customized Message Handling

The way in which the Modular Input processes the received messages is enitrely pluggable with custom implementations should you wish.

To do this you code an implementation of the `com.splunk.modinput.jms.AbstractMessageHandler` class and jar it up.

Ensure that the necessary jars are in the `$SPLUNK_HOME/etc/apps/jms_ta/bin/lib` directory.

If you don't need a custom handler then the default handler `com.splunk.modinput.jms.DefaultMessageHandler` will be used.

This handler simply trys to convert the received JMS Message into a textual string for indexing in Splunk.

## App Object Permissions

Everyone's Splunk environment and Users/Roles/Permissions setup are different.

By default this App ships with all of it's objects globally shared (in `metadata/default.meta` )

So if you need to limit access to functionality within the App , such as who can see the setup page , then you should browse to  `Apps -> Manage Apps -> JMS Messaging Modular Input -> View Objects` , and adjust the permissions accordingly for your specific Splunk environment.

## Troubleshooting

* JAVA_HOME environment variable is set or "java" is on the PATH for the user's environment you are running Splunk as
* You are using Splunk 7+
* You are using a 1.8+ Java Runtime
* Any 3rd party jar dependencies are present in `$SPLUNK_HOME/etc/apps/jms_ta/bin/lib`
* Run this command as the same user that you are running Splunk as and observe console output : `$SPLUNK_HOME/bin/splunk cmd python ../etc/apps/jms_ta/bin/jms.py --scheme`
* Your configuration parameters are correct for your JMS connection (check for typos, correct credentials, correct JNDI names etc...)
* Your DNS resolution for hostnames is correctly configured

## Support

[BaboonBones.com](http://www.baboonbones.com#support) offer commercial support for implementing and any questions pertaining to this App.

