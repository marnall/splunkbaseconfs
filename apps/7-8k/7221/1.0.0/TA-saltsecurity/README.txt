Salt Security Technology Add-on for Splunk® by Salt Security.
==========
For support, please e-mail support@salt.security

## OVERVIEW

Author: Salt Security 
App Version: 1.0.0
Vendor Products: Salt Security Platform


## Description ############################

The Salt Security Technology Add-on for Splunk provides search-time configurations for CIM compliant field extractions as well as index-time configurations for line breaking and time stamping of Salt Security logs collected from Syslog.

The Salt Security Technology Add-on for Splunk is compatible with Splunk Enterprise and Splunk Cloud Platform version 9.x.


## Prerequisites and Requirements ############################

1. Splunk Enterprise or Splunk Cloud Platform version 9.x.

2. Salt Security logs are expected to be received in syslog format and have the originating sourcetype of salt:syslog. 

For documentation on the Salt Security Platform syslog integration, please refer to the Salt Security Platform docs website: https://docs.secured-api.com/docs/syslog



## INSTALLATION

## Installation steps ############################

1. Ensure the Prerequisites and Requirements documented above are met.

2. Download the Salt Security Technology Add-on for Splunk from Splunkbase.

3. The app has index-time sourcetyping operations, so it should be deployed to your search tier as well as the first Splunk platform system to receive your data using standard application deployment methods. Information on installing applications on Splunk platform can be found in the Splunk documentation here: https://docs.splunk.com/Documentation/AddOns/released/Overview/Installingadd-ons

4. The Technology Add-on is now installed. Enjoy!



## Release notes ############################

1.0.0 - First application release

