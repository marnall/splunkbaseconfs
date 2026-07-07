# Splunk Pubnub Modular Alert

1.5.9
-----
* just a version bump for Splunkbase requirements

1.5.8
-----
* just a version bump to satisfy Splunkbase's new archiving requirements

1.5.7
-----
* general updates to meet latest Cloud Vetting requirements

1.5.6
-----
* removed setup.xml because since Splunk 8.1 it does not seem to work (although it is permitted for Modular Alerts to have a setup.xml file), it just endlessly loops back on itself and writes no configuration settings, hence the App can't escape a "not yet configured" state. Replaced with a custom HTML setup form.

1.5.5
-----
* upgraded logging functionality

1.5.4
-----
* docs update

1.5.3
-----
* added a setup page to encrypt any credentials you require in your configuration

1.5.2
-----
* enforced python3 for execution of the modular input script.If you require Python2.7 , then download a prior version (such as 1.5.1).

1.5.1
-----
* general appinspect tidy ups

1.5
-----
* Python 2.7 and 3+ compatibility

1.4
-----
* logging updates

1.3
-----
* Splunk 8 compatibility

1.2.1
-----
* added trial key functionality

1.2
-----
* docs updated

1.1
-----
* Added an activation key requirement , visit http://www.baboonbones.com/#activation to obtain a non-expiring key
* Docs updated
* Splunk 7.1 compatible

1.0
-----
* Initial beta release
