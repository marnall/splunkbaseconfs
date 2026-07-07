To get started with the Splunk On-Call API to integrate with Phantom, log into the Splunk On-Call
web portal and go to Integrations then API. From here you can retrieve your API ID and have the
opportunity to create your API Keys. Note: Only Splunk On-Call admin users can create API Keys. The
documentation for the Splunk On-Call API allows you to try out the different calls in real time. To
get started read the [API Documentation](https://portal.victorops.com/api-docs/#/) .

Phantom integrates with the Splunk On-Call REST Endpoint to trigger, update, or resolve incidents in
Splunk On-Call. To enable this integration in Splunk On-Call, click on Integrations >> 3rd Party
Integrations API >> REST – Generic. If the REST endpoint integration has not been enabled, click
the blue Enable Integration button to generate your endpoint destination URL.

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Splunk On-Call server. Below are the
default ports used by Splunk SOAR.

|         SERVICE NAME | TRANSPORT PROTOCOL | PORT |
|----------------------|--------------------|------|
|         http | tcp | 80 |
|         https | tcp | 443 |
