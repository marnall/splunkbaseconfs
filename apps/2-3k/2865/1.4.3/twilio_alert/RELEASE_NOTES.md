# Splunk Twilio SMS Alerting

1.4.3
-----
* just a version bump for Splunkbase requirements 

1.4.2
-----
* Updated the Twilio Python module

1.4.1
-----
* Twilio updated their certificates , so we had to update the local cacert.pem with their latest certificates

1.4.0
-----
* general updates to meet latest Cloud Vetting requirements
* moved authtoken out of alert_actions.conf , browse to the `Setup` menu tab and enter any authtoken(s)/accountsid(s) you require.
* activation key is now setup globally via a menu tab

1.3.6
-----
* removed setup.xml because since Splunk 8.1 it does not seem to work (although it is permitted for Modular Alerts to have a setup.xml file), it just endlessly loops back on itself and writes no configuration settings, hence the App can't escape a "not yet configured" state. Replaced with a custom HTML setup form.

1.3.5
-----
* upgraded logging functionality

1.3.4
-----
* docs update

1.3.3
-----
* added a setup page to encrypt any credentials you require in your configuration

1.3.2
-----
* enforced python3 for execution of the alert script.If you require Python2.7 , then download a prior version (such as 1.3.1).

1.3.1
-----
* general appinspect tidy ups

1.3
-----
* Python 2.7 and 3+ compatibility

1.2
-----
* logging updates

1.1
-----
* fixed Splunk 8 compatibility for manager.xml file

1.0
-----
* added trial key functionality

0.9
---
* docs updates

0.8
----
* prevent dereferencing of message variable

0.7
-----
* Added an activation key requirement , visit http://www.baboonbones.com/#activation to obtain a non-expiring key
* Docs updated
* Splunk 7.1 compatible

0.6
-----
* Comma delimited list of TO numbers

0.5
-----
* Initial beta release
