# Google Analytics Reporting for Splunk

Adds a simple modular input for bringing in Google Analytics Report data. The input runs daily 
and the ga:dateHour dimension is automatically added to every report.

## Installation
For distributed Splunk environments, install this app on a forwarder and every search head. 
Configuration only needs to be performed on the forwarder. Create inputs on the forwarder as well.

## Configuration

### App config
1. Create OAuth credentials. Follow step 1
[here](https://developers.google.com/analytics/devguides/reporting/core/v4/quickstart/service-py) 
and note down your client ID and client secret.
2. Open the app. You will be redirected to the setup page automatically.
3. On the setup page, enter your client ID and secret, then click "Get code!"
4. A pop-up should appear. Authorize Splunk to use your Google account, and copy the 
authorization code back into the Splunk setup page.
5. Click "Save code!"

### Input config
1. In SplunkWeb, navigate to Settings->Data Inputs->Google Analytics Input->New
2. Name your input, and then enter comma-separated lists of metrics/dimensions. Available 
metrics/dimensions can be found
[here](https://developers.google.com/analytics/devguides/reporting/core/dimsmets#mode=api&cats=time,user). 
Note that some metrics and dimensions cannot be combined. All inputs have the "ga:dateHour" 
metric automatically applied. Set your amount of backfill days, and select a view.
3. Click save. If you set a backfill, you should begin seeing data shortly. Otherwise you will 
see the latest data at around midnight. 