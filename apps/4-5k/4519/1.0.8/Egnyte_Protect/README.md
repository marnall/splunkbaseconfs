# OVERVIEW

Egnyte Secure & Govern App For Splunk provides insights to the enterprises for the overall incidents which are identified and raised by Egnyte Secure & Govern. It would enable Splunk administrators to track the enterprise-wide incidents identified by Egnyte Secure & Govern directly through the Splunk App.

Egnyte Secure & Govern is a SaaS content governance solution that is simple to set up and use. It works across multiple repository types, such as Egnyte Connect, OneDrive for Business and Windows File Servers. It shows you where your sensitive information resides and highlights potential exposures of information.

Egnyte Secure & Govern delivers content classification, identifies issues, sends realtime alerts, enables remediation.



# REQUIREMENTS

* Egnyte Secure & Govern Add-on For Splunk
* Splunk version 7.2.x, 7.3.x , 8.x.x
* This application should be installed on Search Head.

# Release Notes

## Version: 1.0.0
- Initial Relase

## Version: 1.0.6
- Update App name.

## Version: 1.0.7
- Adding Pie charts for Issue Severity
- Updating timechart for Created Issues Over time.

# RECOMMENDED SYSTEM CONFIGURATION

* Standard Splunk configuration of Search Head.

# Test your Install
The main app dashboard can take some time before the data is returned which will populate some of the panels. A good test is to run following query

```search `egnyte_get_index` ```

If you don't see these sourcetypes, run following query to find out if any alert with demisto action was executed.

```index="_internal"```

# Support
Customers can file issues by sending emails to : splunk.support@egnyte.com
