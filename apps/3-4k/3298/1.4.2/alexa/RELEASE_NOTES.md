# Talk to Splunk with Amazon Alexa

1.4.2
-----
* upgraded logging functionality

1.4.1
-----
* docs update

1.4
-----
* enforced python3 for execution of the modular input script.If you require Python2.7 , then download a prior version (such as 1.3).

1.3
---
* Python 2.7 and 3+ compatibility

1.2
-----
* added JAXB dependencies for JRE 9+
* fixed Splunk 8 compatibility for manager.xml file

1.1.1
-----
* added trial key functionality

1.1
-----
* docs updated

1.0
-----
* Added an activation key requirement , visit http://www.baboonbones.com/#activation  to obtain a non-expiring key
* Docs updated
* Splunk 7.1 compatible

0.8
----
* Trivial bug fix that was messing with my OCD

0.7
----
* Can have time range defaults now if no time slot is passed in with the intent. These can be global  or per search intent.
* Can override the default mod input user (splunk-system-user) , and auth with your own user
* If you specify your own auth user , password can be encrypted
* Can specify the search namespace( aka app context) , global or per intent, saves having to ask App owners to make everything global.
* Multiple search result rows now supported , you don't have to do anything , they are magically handled.

0.6
-----
* Hardwired the SSL port to be 443 as currently the Alexa Cloud service does not support using other ports
* Added support for mapping generating search commands, ie: those starting with a pipe such as "| metadata" , "| tstats" etc..

0.5
-----
* Initial beta release
