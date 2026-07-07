# Splunk COAP (Constrained Application Protocol) Modular Input

1.5.0
-----
* just a version bump for Splunkbase requirements 

1.4.9
-----
* updated the Java SDK

1.4.8
-----
* updated the Java SDK

1.4.7
-----
* in order to support huge modular input configuration xml strings when users want to run a very large number of inputs on 1 single instance of this app , we had to change the way that the child java process is invoked. Previously the xml string was passed as a program argument which could break the max argument size in the Linux kernel. Now we changed the logic to pass the xml string to the java process via the STDIN pipe.

* The app performs periodic socket pings to the splunkd management port to determine if splunkd is still alive and if splunkd is not responding , usually because it has exited or is not network reachable, then the app self exits it's running java process.The default timeout is now 300 seconds. You can change this timeout value in bin/coap.py by setting the `SPLUNKD_TIMEOUT_SECS` variable. 

* upgraded internal logging libraries to Log4j2 v2.17.2

1.4.6
-----
* upgraded internal logging libraries to Log4j2 v2.17.0

1.4.5
-----
* upgraded internal logging libraries to Log4j2 v2.16.0

1.4.4
-----
* upgraded internal logging libraries to Log4j2 v2.15.0

1.4.3
-----
* upgraded logging functionality

1.4.2
-----
* docs update

1.4.1
-----
* added a setup page to encrypt any credentials you require in your configuration

1.4
-----
* enforced python3 for execution of the modular input script.If you require Python2.7 , then download a prior version (such as 1.3).

1.3
----
* Python 2.7 and 3+ compatibility

1.2
----
* added JAXB dependencies for JRE 9+
* fixed Splunk 8 compatibility for manager.xml file

1.1.2
-----
* cosmetic fixes

1.1.1
-----
* updated docs

1.1
-----
* added trial key functionality

1.0
-----
* docs updated

0.9
-----
* minor manager xml ui tweak for 7.1

0.8
-----
* Added an activation key requirement , visit http://www.baboonbones.com/#activation  to obtain a non-expiring key
* Docs updated
* Splunk 7.1 compatible

0.7
---
* Minor HEC tweaks

0.6
---
* Added support to optional output to Splunk via a HEC (HTTP Event Collector) endpoint

0.5
-----
* Initial beta release
