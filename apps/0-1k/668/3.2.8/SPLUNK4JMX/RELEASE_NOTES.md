# Monitoring of Java Virtual Machines with JMX

3.2.8
-----
* just a version bump for Splunkbase requirements 

3.2.7
-----
* updated the Java SDK

3.2.6
-----
* updated the Java SDK

3.2.5
-----
* in order to support huge modular input configuration xml strings when users want to run a very large number of inputs on 1 single instance of this app , we had to change the way that the child java process is invoked. Previously the xml string was passed as a program argument which could break the max argument size in the Linux kernel. Now we changed the logic to pass the xml string to the java process via the STDIN pipe.

* The app performs periodic socket pings to the splunkd management port to determine if splunkd is still alive and if splunkd is not responding , usually because it has exited or is not network reachable, then the app self exits it's running java process.The default timeout is now 300 seconds. You can change this timeout value in bin/jmx.py by setting the `SPLUNKD_TIMEOUT_SECS` variable. 

* upgraded internal logging libraries to Log4j2 v2.17.2

3.2.4
-----
* upgraded internal logging libraries to Log4j2 v2.17.0

3.2.3
-----
* upgraded internal logging libraries to Log4j2 v2.16.0

3.2.2
-----
* upgraded internal logging libraries to Log4j2 v2.15.0

3.2.1
-----
* added a JSON Event formatter. See bin/config/examples/tomcat.xml

3.2.0
-----
* general updates to meet latest Cloud Vetting requirements
* browse to the `Setup Credentials` menu tab and enter any JMX usernames/passwords you require.
* activation key is now setup globally via a menu tab
* removed the HEC output option, default is now stdout

3.1.2
-----
* upgraded logging functionality

3.1.1
-----
* docs update

3.1
-----
* added a setup page to encrypt the JMX Password in your configuration

3.0
-----
* enforced python3 for execution of the modular input script.If you require Python2.7 , then download a prior version (such as 2.8).
* updated all of the dashboards to be compatible with Splunk 8
* removed the default 'jmx' index , 'main' is the new default index

2.8
----
* Python 2.7 and 3+ compatibility

2.7
----
* added JAXB dependencies for JRE 9+
* fixed Splunk 8 compatibility for manager.xml file

2.6.4
-----
* correcting some minor docs errors

2.6.3
-----
* cosmetic fixes

2.6.2
-----
* updated docs

2.6.1
-----
* added trial key functionality

2.6
-----
* docs updated

2.5
-----
* Added an activation key requirement , visit http://www.baboonbones.com/#activation  to obtain a non-expiring key
* Docs updated
* Splunk 7.1 compatible

2.4
---
* Minor HEC tweaks

2.3
---
* Added support to optional output to Splunk via a HEC (HTTP Event Collector) endpoint

2.2.2
-----
* Fixed docs link in nav menu

2.2.1
-----
* Fixed minor typos

2.2
----
* Enabled TLS1.2 support by default.
* Made the  core Modular Input Framework compatible with latest Splunk Java SDK
* Please use a Java Runtime version 7+
* If you need to use SSLv3 , you can turn this on in bin/jmx.py   

2.1
----
Config file dynamically reloaded if it changes
PID File contents read in on each poller execution
PID Command execution on each poller execution
PID Command can also return JVM Descriptions

2.0.4
-----
Minor change so that when using "dumpAllAttributes" , only READABLE attributes will be polled.