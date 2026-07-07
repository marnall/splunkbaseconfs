# OVERVIEW

The Cisco DMP/APP App for Splunk collects alerts from Cisco Domain Protection and Cisco Advanced Phishing Protection products and allows you to view and query them from within your Splunk instance. These real-time alerts include Threat Spikes, Brand Spoofing, Authentication Spikes, Infrastructure Alerts, DMARC and SPF Record Changes, New Sender notifications, and Attack Trends.



# REQUIREMENTS

* Cisco DMP/APP Add-On for Splunk
* Splunk version 8.X.X 
* This application should be installed on Search Head.

# Release Notes

## Version: 1.0.0

## Version: 1.0.1
- Minor update in query.

## Version: 1.0.2
- Minor update for JQuery.


# RECOMMENDED SYSTEM CONFIGURATION

* Standard Splunk configuration of Search Head.

# Test your Install
The main app dashboard can take some time before the data is returned which will populate some of the panels. A good test is to run following query

```search `macro_main_cisco` ```

If you don't see the data yet available after few minutes,try running below query to see if there are any errors.

```index="_internal"```

# Support
Additional support for this application is available at the following URL:
https://agari.zendesk.com/hc/en-us/articles/115001959803

