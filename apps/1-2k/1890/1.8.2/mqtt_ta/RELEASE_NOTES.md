# Splunk MQTT Modular Input

1.8.2
-----
* just a version bump for Splunkbase requirements 

1.8.1
-----
* added a new custom response handler for indexing the raw polled data only, com.splunk.modinput.mqtt.RawDataOnlyMessageHandler

1.8.0
-----
* updated the Java SDK

1.7.9
-----
* updated the Java SDK

1.7.8
-----
* added support for custom MQTT URLs

* upgraded internal logging libraries to Log4j2 v2.17.2

1.7.7
-----
* added Websockets support

* The app performs periodic socket pings to the splunkd management port to determine if splunkd is still alive and if splunkd is not responding , usually because it has exited or is not network reachable, then the app self exits it's running java process.The default timeout is now 300 seconds. You can change this timeout value in bin/mqtt.py by setting the `SPLUNKD_TIMEOUT_SECS` variable. 

1.7.6
-----
* this version was skipped due to some Splunkbase upload issues.

1.7.5
-----
* in order to support huge modular input configuration xml strings when users want to run a very large number of inputs on 1 single instance of the MQTT Modular Input , we had to change the way that mqtt.py invokes it's child java process. Previously the xml string was passed as a program argument which could break the max argument size in the Linux kernel. Now we changed the logic to pass the xml string to the java process via the STDIN pipe.

1.7.4
-----
* fixed a bug in getting credentials from storage/passwords

1.7.3
-----
* upgraded internal logging libraries to Log4j2 v2.17.0

1.7.2
-----
* upgraded internal logging libraries to Log4j2 v2.16.0

1.7.1
-----
* upgraded internal logging libraries to Log4j2 v2.15.0

1.7.0
-----
* general updates to meet latest Cloud Vetting requirements
* moved password out of inputs.conf , browse to the `Setup Credentials` menu tab and enter any MQTT usernames/passwords you require.
* activation key is now setup globally via a menu tab
* removed the HEC output option, default is now stdout

1.6.3
-----
* upgraded logging functionality

1.6.2
-----
* docs update

1.6.1
-----
* added a setup page to encrypt any credentials you require in your configuration

1.6
-----
* enforced python3 for execution of the modular input script.If you require Python2.7 , then download a prior version (such as 1.5).

1.5
-----
* Python 2.7 and 3+ compatibility

1.4
-----
* added support for HTTP Event Collector raw endpoint and using a host other than the default localhost

1.3
-----
* added JAXB dependencies for JRE 9+
* fixed Splunk 8 compatibility for manager.xml file

1.2.3
-----
* cosmetic fixes

1.2.2
-----
* updated docs

1.2.1
-----
* added trial key functionality

1.2
-----
* docs updated

1.1
-----
* minor manager xml ui tweak for 7.1

1.0
-----
* Added an activation key requirement , visit http://www.baboonbones.com/#activation  to obtain a non-expiring key
* Docs updated
* Splunk 7.1 compatible

0.9.1
---
* Fixed subscription loop

0.9
---
* Minor HEC tweaks

0.8
---
* Added support to optional output to Splunk via a HEC (HTTP Event Collector) endpoint

0.7
---
* Added a message handler (BodyOnlyMessageHandler) that just outputs the mqtt body

0.6
----
* Enabled TLS1.2 support by default.
* Made the  core Modular Input Framework compatible with latest Splunk Java SDK
* Please use a Java Runtime version 7+
* If you need to use SSLv3 , you can turn this on in bin/mqtt.py   

0.5
-----
* Initial beta release
