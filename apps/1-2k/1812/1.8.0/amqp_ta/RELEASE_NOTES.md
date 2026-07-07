# Splunk AMQP Messaging Modular Input

1.8.0
-----
* just a version bump for Splunkbase requirements 

1.7.9
-----
* updated the Java SDK

1.7.8
-----
* updated the Java SDK

1.7.7
-----
* in order to support huge modular input configuration xml strings when users want to run a very large number of inputs on 1 single instance of this app , we had to change the way that the child java process is invoked. Previously the xml string was passed as a program argument which could break the max argument size in the Linux kernel. Now we changed the logic to pass the xml string to the java process via the STDIN pipe.

* The app performs periodic socket pings to the splunkd management port to determine if splunkd is still alive and if splunkd is not responding , usually because it has exited or is not network reachable, then the app self exits it's running java process.The default timeout is now 300 seconds. You can change this timeout value in bin/amqp.py by setting the `SPLUNKD_TIMEOUT_SECS` variable. 

* upgraded internal logging libraries to Log4j2 v2.17.2

1.7.6
-----
* added some more verbose informational logging
* made some performance improvements around threading and general usage of AMQP resources

1.7.5
-----
* fixed a bug in getting credentials from storage/passwords

1.7.4
-----
* upgraded internal logging libraries to Log4j2 v2.17.0

1.7.3
-----
* upgraded internal logging libraries to Log4j2 v2.16.0

1.7.2
-----
* upgraded internal logging libraries to Log4j2 v2.15.0

1.7.1
-----
* minor tweak to acking/auto acking logic

1.7.0
-----
* general updates to meet latest Cloud Vetting requirements
* moved password out of inputs.conf , browse to the `Setup Credentials` menu tab and enter any usernames/passwords you require.
* activation key is now setup globally via a menu tab
* removed the HEC output option, default is now stdout

1.6.3
-----
* upgraded the AMQP java client library to version 5.12.0

1.6.2
-----
* upgraded logging functionality

1.6.1
-----
* docs update

1.6
-----
* enforced python3 for execution of the modular input script.If you require Python2.7 , then download a prior version (such as 1.5).
* added a custom setup page for encryption of credentials

1.5
----
* Python 2.7 and 3+ compatibility

1.4
----
* added JAXB dependencies for JRE 9+
* fixed Splunk 8 compatibility for manager.xml file

1.3.3
-----
* cosmetic fixes

1.3.2
-----
* updated docs

1.3.1
-----
* added trial key functionality

1.3
-----
* docs updated

1.2
-----
* minor manager xml ui tweak for 7.1

1.1
-----
* Added an activation key requirement , visit http://www.baboonbones.com/#activation  to obtain a non-expiring key
* Docs updated
* Splunk 7.1 compatible

1.0
---
* Minor HEC tweaks

0.9
---

* Adjusted pre fetch logic

0.8
---
* Added support to optional output to Splunk via a HEC (HTTP Event Collector) endpoint

0.7
---
* Enabled TLS1.2 support by default.
* Made the  core Modular Input Framework compatible with latest Splunk Java SDK
* Please use a Java Runtime version 7+
* If you need to use SSLv3 , you can turn this on in bin/mq.py  


0.6
----
* Added configurable basic qos parameter

0.5
-----
* Initial beta release


