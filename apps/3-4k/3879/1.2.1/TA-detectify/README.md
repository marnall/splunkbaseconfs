# TA-detectify

| App version               | 1.2.0            |
|---------------------------|----------------|
| Author                    | Hurricane Labs |
| Supported Splunk versions | 6.5, 6.6, 7.0, 7.1, 7.2, 7.3, 8.0  |

### Installation (all-in-one search head)

Extract tar.gz to $SPLUNK_HOME/etc/apps or install in Splunkweb from the "manage apps" page.

### Installation (distributed environment)

Install app to a forwarder, as well as all search heads. Disable default input in inputs.conf before installation to search head. Follow "Configuration" section on the forwarder.

### Configuration

Once installed, navigate to the "manage apps" page, find the row for TA-detectify and click "Set up" (/en-US/manager/TA-detectify/apps/local/TA-detectify/setup?action=edit). Enter an API key and click save. Input runs hourly, so after configuration data may take up to an hour to be indexed. App outputs events to the "detectify:findings" sourcetype in the default index. If you'd like to specify a different index, specify one in this app's inputs.conf. 

### Troubleshooting

For bug reporting and app questions, contact splunk-app@hurricanelabs.com.
