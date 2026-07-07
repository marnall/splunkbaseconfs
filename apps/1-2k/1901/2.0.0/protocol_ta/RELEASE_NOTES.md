# Protocol Data Inputs

2.0.0
-----
* just a version bump for Splunkbase requirements 

1.9.9
-----
* updated the Java SDK

1.9.8
-----
* updated the Java SDK
* removed unused Spring Jars

1.9.7
-----
* in order to support huge modular input configuration xml strings when users want to run a very large number of inputs on 1 single instance of this app , we had to change the way that the child java process is invoked. Previously the xml string was passed as a program argument which could break the max argument size in the Linux kernel. Now we changed the logic to pass the xml string to the java process via the STDIN pipe.

* The app performs periodic socket pings to the splunkd management port to determine if splunkd is still alive and if splunkd is not responding , usually because it has exited or is not network reachable, then the app self exits it's running java process.The default timeout is now 300 seconds. You can change this timeout value in bin/protocol.py by setting the `SPLUNKD_TIMEOUT_SECS` variable. 

* upgraded internal logging libraries to Log4j2 v2.17.2

1.9.6
-----
* upgraded internal logging libraries to Log4j2 v2.17.0

1.9.5
-----
* upgraded internal logging libraries to Log4j2 v2.16.0

1.9.4
-----
* upgraded internal logging libraries to Log4j2 v2.15.0

1.9.3
-----
* upgraded logging functionality

1.9.2
-----
* docs update

1.9.1
-----
* added a setup page to encrypt any credentials you require in your configuration

1.9
-----
* enforced python3 for execution of the modular input script.If you require Python2.7 , then download a prior version (such as 1.8).

1.8
-----
* Python 2.7 and 3+ compatibility

1.7
-----
* added JAXB dependencies for JRE 9+
* fixed Splunk 8 compatibility for manager.xml file

1.6.5
-----
* search/replace example handler added 

1.6.4
-----
* cosmetic fixes

1.6.3
-----
* cosmetic fixes

1.6.2
-----
* updated docs

1.6.1
-----
* added trial key functionality

1.6
-----
* docs updated

1.5.1
-----
* minor manager xml ui tweak for 7.1

1.5
-----
* Added an activation key requirement , visit http://www.baboonbones.com/#activation  to obtain a non-expiring key
* Docs updated
* Splunk 7.1 compatible

1.4
---
* Updated some jars.
* Added CORS supported to HTTP protocol.

1.3
---
* Added the latest jython jar to the main classpath because the jython language module that is dynamically installed is missing some useful jython modules ie:json


1.2
---
* Added an example handler for decompressing gzip content  
com.splunk.modinput.protocol.handlerverticle.GZipHandler

1.1
---
* Minor HEC tweaks

1.0
---
* Added support for output to be sent via the HTTP Event Collector

0.7
----
* Enabled TLS1.2 support by default.
* Made the  core Modular Input Framework compatible with latest Splunk Java SDK
* Please use a Java Runtime version 7+
* If you need to use SSLv3 , you can turn this on in bin/protocol.py   

0.6
-----
* Abstracted the output transport logic out into verticles.  
So you can choose from STDOUT (default for Modular Inputs) or bypass this and output
data to Splunk over other transports ie: TCP.  
This also makes it easy to add other output transports  in the future.  
Futhermore , this makes the implementation of custom data handlers much cleaner as you don't have worry about output transport logic or formatting Modular Input Stream XML for STDOUT transports.  

0.5
-----
* Initial beta release
