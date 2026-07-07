##Enosys Add-on for Forcepoint Email Security version 1.0.2
######
##This Application is published and maintained  by Enosys and all the transformation codes
######
##The Enosys Add-on for Forcepoint Email Security version 1.0.0 works only when Forcepoint Email Security syslog logs are forwarded to Splunk Enterprise or Splunk Cloud via Splunk Forwarder.
######

#Version 1.0.2 of the Enosys Add-on for Forcepoint Email Security is compatible with:

| Splunk Enterprise versions |  7.3, 7.2, 7.1, 7.0 |
| --- | --- |
| CIM | 4.10, 4.11, 4.12, 4.13 |
| Platforms | Platform independent |
| Vendor Products | Forcepoint |

#### The version 1.0.2 of the Enosys Add-on for Forcepoint Email Security has the following known issues:

- The event "Audit Log" logs are not tagged
- Action base lookup should be updated as required (field "act")
- Field "x-mailer" require further work sanitising quotation marks

#### Recommendations
This product should be installed on search heads and indexers.
