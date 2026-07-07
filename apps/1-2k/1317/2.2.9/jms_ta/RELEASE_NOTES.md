# Splunk JMS Modular Input

2.2.9
-----
* just a version bump for Splunkbase requirements 

2.2.8
-----
* updated the Java SDK

2.2.7
-----
* updated the Java SDK
* added support for duplicate usernames

2.2.6
-----
* upgraded internal logging libraries to Log4j2 v2.17.2

2.2.5
-----
* in order to support huge modular input configuration xml strings when users want to run a very large number of inputs on 1 single instance of this app , we had to change the way that the child java process is invoked. Previously the xml string was passed as a program argument which could break the max argument size in the Linux kernel. Now we changed the logic to pass the xml string to the java process via the STDIN pipe.

* The app performs periodic socket pings to the splunkd management port to determine if splunkd is still alive and if splunkd is not responding , usually because it has exited or is not network reachable, then the app self exits it's running java process.The default timeout is now 300 seconds. You can change this timeout value in bin/jms.py by setting the `SPLUNKD_TIMEOUT_SECS` variable. 

2.2.4
-----
* fixed a bug in getting credentials from storage/passwords

2.2.3
-----
* upgraded internal logging libraries to Log4j2 v2.17.0

2.2.2
-----
* upgraded internal logging libraries to Log4j2 v2.16.0

2.2.1
-----
* upgraded internal logging libraries to Log4j2 v2.15.0

2.2.0
-----
* general updates to meet latest Cloud Vetting requirements
* moved jndi_pass and destination_pass out of inputs.conf , browse to the `Setup Credentials` menu tab and enter any passwords you require.
* activation key is now setup globally via a menu tab
* removed the HEC output option, default is now stdout

2.1.2
-----
* upgraded logging functionality

2.1.1
-----
* docs update

2.1
-----
* added a setup page to encrypt any credentials you require in your configuration

2.0
-----
* enforced python3 for execution of the modular input script.If you require Python2.7 , then download a prior version (such as 1.9).

1.9
----
* Python 2.7 and 3+ compatibility

1.8
----
* added JAXB dependencies for JRE 9+
* fixed Splunk 8 compatibility for manager.xml file

1.7.2
-----
* updated docs

1.7.1
-----
* added trial key functionality

1.7
-----
* docs updated

1.6.1
-----
* minor manager xml ui tweak for 7.1

1.6
-----
* Added an activation key requirement , visit http://www.baboonbones.com/#activation  to obtain a non-expiring key
* Docs updated
* Splunk 7.1 compatible

1.5.1
-----
* Added a new message handler that just dumps the message body :   
com.splunk.modinput.jms.custom.handler.BodyOnlyMessageHandler

1.5
---
* Minor HEC tweaks

1.4
---
* Added support to optional output to Splunk via a HEC (HTTP Event Collector) endpoint

1.3.9
-----
* Added more verbose INFO level logging

1.3.8
-----
* Enabled TLS1.2 support by default.
* Made the  core Modular Input Framework compatible with latest Splunk Java SDK
* Please use a Java Runtime version 7+
* If you need to use SSLv3 , you can turn this on in bin/mq.py  

1.3.7
-----
* Changed the point in the code where client ID is set for durable topic subscriptions

1.3.6
-----
* Added a LocalConnectionFactory for ActiveMQ

1.3.5
-----
* Added the ability to declare custom JVM System Properties in your stanzas
