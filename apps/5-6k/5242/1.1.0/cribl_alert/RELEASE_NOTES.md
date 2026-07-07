# Cribl Modular Alert

1.1.0
-----
* just a version bump for Splunkbase requirements

1.0.9
-----
* just a version bump to satisfy Splunkbase's new archiving requirements

1.0.8
-----
* general updates to meet latest Cloud Vetting requirements

1.0.7
-----
* removed setup.xml because since Splunk 8.1 it does not seem to work (although it is permitted for Modular Alerts to have a setup.xml file), it just endlessly loops back on itself and writes no configuration settings, hence the App can't escape a "not yet configured" state. Replaced with a custom HTML setup form.

1.0.6
-----
* added urllib3 package for older versions of Splunk

1.0.5
-----
* updated logos

1.0.4
-----
* upgraded logging functionality

1.0.3
-----
* upgraded logging functionality

1.0.2
-----
* disabled some annoying log warning messages

1.0.1
-----
* chunking of HTTP POSTs.Default of 100 events sent per POST , but can be overridden
* can declare a custom list of fields to POST to Cribl instead of the defaults

1.0.0
-----
* initial release