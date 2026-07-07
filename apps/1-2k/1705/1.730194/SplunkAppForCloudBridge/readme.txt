Splunk App for CloudBridge Release Notes


The Splunk App for CloudBridge requires CloudBridge 7.2.0 or later release.

This is a reference AppFlow collector application for Citrix CloudBridge.


Implementation Notes:

All data sets must be enabled in the CloudBridge AppFlow configuration when sending data to the SplunkAppForCloudbridge application. 

Real time searches (real-time options in the time selection field) are not supported. 

Report accuracy for calculated values and time based graphs may suffer as the report duration approaches (or drops below) the update interval from Cloudbridge.  These effects are usually only noticeable if the report duration is less than one hour. 

Example: If CloudBridge is updating every minute then rate calculations for the last 15 minutes could be off by 1/15 since we may only receive 14 updates within a 15 minute window.  

Example: For a timechart spanning 15 minutes the default "bucket" size is 10 seconds.  Given a 1 minute CloudBridge update interval the resulting chart may look uneven with mostly zero values and spikes every minute.  

Splunk App for CloudBridge can be modified to meet your needs. See the AppFlow Developer Guide for details.

See http://docs.splunk.com/Documentation/Splunk/latest/Deploy/Deploymenttoplogies for Splunk deployment guidelines.
