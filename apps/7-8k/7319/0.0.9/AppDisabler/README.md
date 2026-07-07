## Introduction

The purpose of this application is to disable an application

## Installation
Install this into any forwarder, indexer, search head or search head cluster where you would like an application disabled
In general this is useful for default applications that you would like to disable in an automated fashion

## Why was this application built?

The splunk_secure_gateway app in Splunk 9.1.3 has a poorly written report, and since the application is not in use on most non-search head instances it can be safely disabled. 
Since this is a built-in Splunk application it takes a little bit more work to ensure it's disabled on all cluster managers, monitoring consoles, search heads and indexers. Therefore this application was created

## How do I use this application?
Configure your inputs.conf to disable the required app. You can optionally configure a disabled status

```
[app_disabler://splunk_secure_gateway]
app = splunk_secure_gateway
interval = -1
```

This is the same as:
```
[app_disabler://splunk_secure_gateway]
app = splunk_secure_gateway
app_disabled = True
interval = -1
```

However if you would like to enable an app you can do:
```
[app_disabler://splunk_secure_gateway]
app = splunk_secure_gateway
app_disabled = False
interval = -1
```

Or perhaps you do not require the python readiness check:
```
[app_disabler://python_upgrade_readiness_app]
app = python_upgrade_readiness_app
interval = -1
```

Note that in my testing the splunk_assist app *cannot* be disabled by a REST-based call, however this should work for most applications

## Are there alternatives?
In a search head cluster this is easily disabled via the UI, however using the UI of a search head cluster disables the app on a single member.
To disable on all members you can login to each one, or use this app. It's similar with heavy forwarders or indexers...

If this were a non-default Splunk app you could simply override the disabled flag via app.conf

## Troubleshooting
### SSL validation errors
If you see an error such as:
`Caused by SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self signed certificate in certificate chain (_ssl.c:1106)')))`

Or the entry in the logs of:
`failed due to SSLError, you may need to set verify=False`

This simply means that the port 8089 is running an SSL certificate that is not trusted by the default certificate store in use by Splunk's python
You can change `verify=True` to `verify=False` in the bin/app_disabler.py file and this will bypass SSL validation of your local Splunk instance on port 8089 (note that this comes with a minor security risk)

## Feedback?
Feel free to open an issue on github or use the contact author on the [SplunkBase link](https://splunkbase.splunk.com/app/7319) and I will try to get back to you when possible, thanks!

## Other
Icons by Bing CoPilot

## Release Notes
### 0.0.9
Adding python.required in `inputs.conf` as requested by splunkbase, this is supported in 10.2 and above. Harmless warning messages may occur on older Splunk versions.

Updated Splunk python SDK to 2.1.1

### 0.0.8
Removed from splunkbase, typo in the python.required setting (and this was the only update), replaced by 0.0.8

### 0.0.7
Corrected inputs.conf.spec file to have `debug_mode`
Removed inputs.conf entry for python_upgrade_readiness app this can be done via a `local/inputs.conf` file 

### 0.0.6
Updated `app_disabler.py` to correctly use the schema (no functional changes, UI input will have correct description text now)

### 0.0.5
Added debug option to enable debug logs

### 0.0.4
Updated Splunk python SDK from 2.0.2 to 2.1.0 as per Splunk cloud compatibility requirements

### 0.0.3
Updated splunk python SDK from 2.0.1 to 2.0.2 as per Splunk cloud compatability requirements

### 0.0.2
Removed SHC check as app.conf is not replicated in an SHC by default, this should therefore run per-SH cluster member

### 0.0.1
Initial version
