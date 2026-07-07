# Tessian Email Security

Tessian Email Security connects the Tessian API to your Splunk instance
so that you can easily ingest Tessian data into your workflows.

## Data Sources

This app connects to the Tessian API and allows you to ingest data from one of our data
streaming endpoints. To do this, the app will require you to input your Tessian
subdomain, API token and region so that it can connect to the API.

## Usage Instructions

To ingest data into your Splunk instance, you will need to first set the app up, then
configure data inputs for the data sources you wish to connect to.

This app requires the use of the Python 3 runtime. 

### Application Setup

After you have installed or updated the app, you will be prompted to set the app up.

It is important to note that we store your API key securely using Splunk's secret
storage module. Because of this, you will need to set the app up while logged in as a
user that has the `list_storage_passwords` capability - this allows the app to read
and write your API token to the secure storage.

Please enter your subdomain, API token and environment. You can find this information
in the following places:

* Your subdomain follows `https://` and preceeds `tessian-app.com` or
  `tessian-platform.com` in your Tessian portal URL, for example in
  https://security.tessian-platform.com, the subdomain would be `security`.
* Your API token can be generated from within the Tessian portal. For instructions on
  how to do this, visit our helpdesk page:
  https://tessian.zendesk.com/hc/en-us/articles/360004824638-How-to-use-the-Tessian-API
* Your environment, which will either be EU or US. If your Tessian portal URL ends in
  `tessian-platform.com`, your environment is EU, otherwise if it is
  `tessian-app.com` it is US.

Once you have entered this information, click 'Submit' and wait to be redirected to
the Search page of the app.

When you update the app, you may be prompted to follow this process again. All of
your settings will be saved, so unless you wish to update them, you can click
'Submit' and continue with the existing values.

If you want to get back to this page without updating, for example if you wish to
rotate an API token, open the 'Tessian' app and click the 'Tessian Security Events
for Splunk Setup Page' link in the navigation bar.

### Setting Up Data Inputs

Once you have set the app up, the next step is to set up data inputs. These connect
Splunk to the Tessian API by calling the API at regular intervals and ingesting
available data into Splunk.

To create a data input, take the following steps: * Open the 'Settings' pane from the
top bar and selecting 'Data Inputs' under the 'Data' category. * Find 'Tessian
Security Events' in the list of data inputs and click 'Add New'. * Enter an input
name, select an endpoint that you wish to ingest data and enter the intervals at which
the data input should run.
    * The name should be a unique identifier that you wish to identify this data
    input by. It cannot
      be changed after creation.
    * Endpoint is the Tessian API that you want this data input to call. We recommend
      that you have a maximum of one data input per endpoint. You can find the
      endpoints in our API documentation here:
      https://developer.tessian.com/documentation/api/index.html.
    * Interval (in seconds) sets how often this data input will run and try to ingest
      data from the Tessian API. We recommend starting with 10-15 minutes, as the
      input will automatically make subsequent requests on each run if there is
      more data available. It will do this until either there is no new data
      available or it hits the rate limit for the API.
* If you need to access the advanced settings, such as the destination index or host
  field value, click the 'Advanced Settings' checkbox to reveal them.
* Once ready, click 'Next' at the top of the screen.

Your data input should start to run and you will see events being ingested into
Splunk. Note that the inputs will ingest data from the oldest event to the newest, so
it may take some time to catch up.

If you want to change the interval or endpoint of one of the data inputs after
creation, you can take the following steps: * Open the 'Settings' pane from the top
bar and selecting 'Data Inputs' under the 'Data' category. * Find 'Tessian Security
Events' in the list of data inputs and on the title link. This should take
  you to a list of your data inputs created for this app.
* Click on the name of the input you wish to edit. * Edit the interval or endpoint as
needed. * Click 'Save'.

### Advanced Settings

On the application setup page, there is an 'Advanced Settings' section. This allows you
to configure additional options for the app. In most cases, you will not need to change
options but we provide them for advanced users who may need to adjust the
configuration of the app.

The options are:

* Max Event Size (default 0, no truncation): This sets the maximum size of an event object that can
  be ingested from the 'Events' data input. If an event exceeds this size, the application will try
  to truncate it to this size without compromising key information. If the event is still too large,
  you may see the event truncated further by Splunk. You might need to use this if your maximum line
  size set by `TRUNCATE` in props.conf is lower than your largest events - a common sign that this is
  the case is if events are being truncated without indication in the search results. Setting this value
  to zero will disable truncation.

## Support

You can find additional instructions on the app setup in our help center:
https://tessian.zendesk.com/hc/en-us/articles/9695706059293-Splunkbase-App

If you have an issue while using this app, please raise a support ticket with Tessian
via the help center.

We may ask you to share log files with us, so that we can investigate your issue.
This app outputs log values to a dedicated file called
`tessian_email_security.log`. You can find this at
$SPLUNK_HOME/var/log/splunk/tessian_email_security.log, where
$SPLUNK_HOME is the directory of your Splunk instance.

## Release Notes

### 1.1.0

- Adds support for truncating some fields of large events.
- New UI for application setup.

### 1.0.9

- Improves error handling for API calls.
- Fixes a unicode handling bug in configuration data.
- Improves error handling on the configuration page.

### 1.0.8

- Removes the deprecated Risk Hub endpoint as a data input.
- Adds support for the Audit endpoint as a data input.

### 1.0.7

- Upgrades third party package versions.

### 1.0.6

- Fixes a bug that prevented events with null timestamps being submitted.
- Upgrades third party package versions.

### 1.0.5

- Fixes a bug that caused checkpoints to be reset when receiving certain error responses
from the server.

### 1.0.4

- Resolves a dependency conflict issue.

### 1.0.3

- Fixes a bug which meant that the environment value might not be saved on initial 
setup.
- Third party package upgrades.

### 1.0.2

- Fixes a bug with environment selection that prevented some environments from
  ingesting data.
- Small description updates across the app.

### 1.0.1

Initial release.
