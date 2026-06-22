This is an add-on powered by the Splunk Add-on Builder.

# Send dashboard PDF

## Overview
This TA includes a custom alert action that implements a dashboard PDF send over email functionality of any dashboard.
It is work in progress but it should work for classic simpleXML and Dashboard Studio.

## Usage
- Download the TA and install it on the Splunk instance.
- Create the alert that should trigger the send dashboard event.
- Select the Send dashboard PDF alert action and configure it.
	- App (required): the app where the dashboard lives.
	- Dashboard (required): the dashboard internal name as it appears in the URL.
	- Owner (required): the dashboard owner.
	- Tokens (required): it is a JSON string that maps the token names in the dashboard with the fields in the search that triggers the alert.
	- Mail to (required): email destination.
	- Mail cc (optional): email cc.
	- Mail subject (required): email subject.
	- Splunk URL (required): the URL and port of the Splunk server. Leave it as default.

## Tokens
Since the Splunk PDF export doesnt apply token values to the dashboard before exporting we need to map and apply the token values manually.
For this purpose we implemented a parameter that accepts a JSON string that it is used to map the token values with the fields in the alert search that contains those values.

### Example
Lets say we have a dashboard that uses a token for selecting users and other token for selecting a time range.
Lets call the tokens `tk_user` and `tk_time`. Now the alert search should return those values in the result fields so we can map the tokens with the field values.
Since we used the timepicker input we have to map the `tk_time.earliest` and the `tk_time.latest` as those are the tokens that will be used in the dashboard.
The Tokens parameter should be configured like this: `{"tk_user":"user", "tk_time.earliest":"info_min_time","tk_time.latest":"info_max_time"}`

## Release notes
- 1.0.2: Better icon and a4 papersize
- 1.0.1: Added Mail cc and Dashboard Studio support.
- 1.0.0: First release.

# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-send-dashboard-alert-action/bin/ta_send_dashboard_alert_action/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-send-dashboard-alert-action/bin/ta_send_dashboard_alert_action/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
