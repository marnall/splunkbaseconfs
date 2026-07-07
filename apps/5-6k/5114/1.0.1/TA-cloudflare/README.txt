Cloudflare Technology Add-on for Splunk® by Cloudflare Inc.
==========
For support, please e-mail analytics@cloudflare.com


## Description ############################

The Cloudflare Technology Add-on for Splunk provides index-time configurations for line breaking and time stamping of Cloudflare JSON logs collected from AWS S3 using the Splunk Add-on for AWS.

The Cloudflare Technology Add-on for Splunk is compatible will all Splunk Enterprise 7.x and 8.0 releases.

## Application Requirements ############################

1. Splunk Enterprise version 7.x or 8.0
2. Cloudflare logs are expected to be in JSON format with a sourcetype of cloudflare:json

## Cloudflare Logs Data Onboarding Notes ############################

1. For documentation on the available methods for collecting Cloudflare logs please refer to the Cloudflare Log
Docs website here: https://developers.cloudflare.com/logs/about/

2. For ease of onboarding and integration, it is recommended to use Cloudflare’s Logpush Service to push logs
to Amazon S3 which can then be pulled into Splunk using the Splunk Add-on for AWS. Instructions on how
to install the Splunk Add-on for AWS and configure inputs can be found here: https://docs.splunk.com/Documentation/AddOns/latest/AWS/Description
– this link also contains details on where to install the Splunk Add-on for AWS as it is dependent on the type of deployment you have.

## Application Installation Instructions ############################

The Cloudflare Technology Add-on for Splunk is easy to install and configure. Please follow the steps below to install and configure
the application within your Splunk environment.

1. Ensure the Application Requirements documented above are met.

2. Obtain the Technology Add-on from Cloudflare or download from Splunkbase, if available.

3. Install the application, using standard deployment methods, on the Splunk instance where the Splunk Add-on for AWS is installed and collecting Cloudflare JSON logs.
Information on installing applications on Splunk can be found in the Splunk documentation here:
https://docs.splunk.com/Documentation/Splunk/latest/Admin/Deployappsandadd-ons

4. The Technology Add-on is now installed. Enjoy!

