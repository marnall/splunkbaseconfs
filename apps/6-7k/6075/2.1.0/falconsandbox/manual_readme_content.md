
##### Usage

Should you not be using hybrid-analysis.com as the application server, but a private cloud or on
premise instance, please E-Mail support@crowdstrike.com for help on enabling the Phantom integration
on your instance.

##### Testing connectivity

After creating the Falcon Sandbox asset, we recommended to test the application server connectivity.
That way, you make sure that the provided base URL and API credentials are working correctly.

Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Okta server. Below are the default
ports used by Splunk SOAR.

|         Service Name | Transport Protocol | Port |
|----------------------|--------------------|------|
|         http         | tcp                | 80   |
|         https        | tcp                | 443  |
