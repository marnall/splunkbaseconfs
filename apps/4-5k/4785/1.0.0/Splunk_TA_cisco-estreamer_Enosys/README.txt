##Enosys Add-on for Cisco Firepower eStreamer version 1.0.0
#
# Full credit to the Cisco Security team for their work and maintenance (https://splunkbase.splunk.com/app/3662/#/details)
# This is intended to update field extraction issues and for deployment on Search Heads in Splunk Cloud and as such removed binaries and additional tagging to ensure full CIM compliance is met.
# This effort should not detract from that of the original project and this TA is intended as a companion.
######
##This Application is published and maintained  by Enosys and all the transformation codes
######
##The Enosys Add-on for Cisco Firepower eStreamer works only when Cisco Firepower and eStreamer logs are forwarded to Splunk Enterprise or Splunk Cloud via Splunk Heavy Forwarder with an installed Cisco eStreamer eNcore Add-on for Splunk version 3.6.8.
######

#Version 1.0 of the Enosys Add-on for Cisco Firepower eStreamer is compatible with:

| Splunk Enterprise versions |  7.3, 7.2, 7.1, 7.0 |
| --- | --- |
| CIM | 4.10, 4.11, 4.12, 4.13 |
| Platforms | Platform independent |
| Vendor Products | Cisco |

#### The version 1.0.0 of the Cisco Firepower eStreamer has the following known issues:

- The firepower logs are not tagged
 


#### The new Add-on version 1.0.0 addresses the following issues detected on Cisco eStreamer eNcore Add-on for Splunk version 3.6.8

- Log type tagging


#### Recommendations

This product should be installed on search heads and indexers.
