Welcome to InsightFinder!

## Overview
Leverage InsightFinder's predictive analytics services to extract insights from your Splunk data (and other sources) and improve the uptime/availability of your critical services and reduce your MTTR when incidents occur!

InsightFinder provides the industry's best multivariate anomaly detection, automatic root cause analysis, stream-based free-from text log analysis (identifying rare/bursty events, classifying similar events in one group) based on our patent-pending unsupervised statistical machine learning and signal processing technologies. Our product has been tested in some of the largest and most challenging IT environments, from the world's largest technology companies (including Google -- our first customer!), Fortune 50 financial institutions, major telecommunications carriers, and some of the largest healthcare institutions in the world. 

Using InsightFinder’s Splunk integration, customers will see over 95% reduction of false alerts, 80-90% storage cost savings through lossless log compression, true visibility into the causal relationships of your IT infrastructure to predict services outages, and intuitive capacity planning.

InsightFinder is the industry's best AIOps engine, delivering insights and analytics in real time and at scale.

InsightFinder is free for small accounts and priced affordably for others.


## Getting Started with InsightFinder's App for Splunk

### Sign up for an account with InsightFinder
- Go to [InsightFinder Sign-up](https://app.insightfinder.com/signup)

### Register a Splunk project in InsightFinder
- Sign in to [InsightFinder](https://app.insightfinder.com/) with your user credentials
- Go to [Settings](https://app.insightfinder.com/settings) and add a new project (Top icon on the left side of your screen)
- Give your project a name and, optionally a description.
- Select "Insight Agent" as on the Data source page.
- On the Configure page, select,
  - "Private Cloud" for Instance Type.
  - "Metric" or "Log" as the Data Type, depending on your input.
  - "Custom" as the Agent Type if a Metric project, "File Replay" or “Live Streaming” as appropriate otherwise.
  - If the Data Type is Metric, enter a Sampling Interval corresponding to the sampling interval of your metric data.
- Go to Account Info (Note: click on your user ID in the top right corner of the screen) and note your license key number

### Installation
**Single Instance**
- Download the installation file by clicking "Download" on the [InsightFinder Splunkbase Page](https://splunkbase.splunk.com/app/3281/), or obtain a copy from us if you are using an on-prem install that requires non-https connection.
- In Splunk’s web interface, go to Manage Apps > Install app from file. Restart Splunk when prompted to.
- After restarting, the setup screen should appear. Enter your Username and License Key as displayed in the [Account Info](https://app.insightfinder.com/account-info) section of the InsightFinder application. This is your only chance to set up the app; otherwise, you will need to do a full uninstall and reinstall.

**Cluster**
- Download the installation file by clicking "Download" on the [InsightFinder Splunkbase Page](https://splunkbase.splunk.com/app/3281/), or obtain a copy from us if you are using an on-prem install that requires non-https connection.
- On the Search Head Cluster Deployer’s web interface, go to Manage Apps > Install app from file. Restart Splunk when prompted to.
- After restarting, the setup screen should appear. Enter your Username and License Key as displayed in the [Account Info](https://app.insightfinder.com/account-info) section of the InsightFinder application. This is your only chance to set up the app; otherwise, you will need to do a full uninstall and reinstall.
- Copy the app to the shcluster folder:
&emsp;&emsp; `cp -r $SPLUNK_HOME/etc/apps/insightfinderapp $SPLUNK_HOME/etc/shcluster/apps/`
- Distribute the app with `$SPLUNK_HOME/bin/splunk apply shcluster-bundle ...`
Note that the app does not need to be installed on any indexer/search peer.

### Upgrade
Do a full uninstall of the application (see below), then install using the latest app file. 

### Query Requirements
To start sending data to InsightFinder, navigate to the Search page within the app. Make sure that you have projects set up as appropriate for the type of data and streaming method that you plan to use. If not, please review the steps outlined above.

### General parameters
- `projectName`: The name of the project you created in InsightFinder
- `systemName`: The name of the system you are sending data from
- `mode`: The mode of data transmission. Options are `LogStreaming`, `LogReplay`, `MetricStreaming`, and `MetricReplay`
- `instanceType`: The type of instance you are sending data to. Options are `PrivateCloud` and `Splunk`, default is `Splunk`.
- `insightAgentType`: The type of Insight Agent you are sending data to. Options are `Custom`, `containerStreaming`, and `ContainerCustom`, default is `Custom`.

For log streaming analysis, append the following to any query that would return data you’d like to push to InsightFinder:
```
| sort _time 
| reportmetrics projectName=YOUR_PROJECT_NAME systemName=YOUR_SYSTEM_NAME mode=LogStreaming serverUrl=INSIGHTFINDER_APP_SERVER userName=USER_NAME timeout=10 chunkSize=300
```

By default, the app sends processed event_message data. If needed, switching from processed data to raw data can be done as demonstrated below. If you do not have a specific use case for sending raw data, you should not set this parameter.

For sending raw data, append `sendRaw=True` to the end of your query:
```
| sort _time 
| reportmetrics projectName=YOUR_PROJECT_NAME systemName=YOUR_SYSTEM_NAME mode=LogStreaming serverUrl=INSIGHTFINDER_APP_SERVER userName=USER_NAME timeout=10 sendRaw=True
```

The INSIGHTFINDER_APP_SERVER parameter denotes the address of Insightfinder application server(If not an on-prem installation use https://app.insightfinder.com) . The CHUNKSIZE parameter is optional and denotes the size (in KB) of each data block transmitted from your Splunk App to the InsightFinder app server. The default value is 200. Please make sure the chunk size is allowed by your local network configuration and within the jetty configuration limitation on InsightFinder app server. https://app.insightfinder.com currently can accept the chunk size below 500KB.

To continually send data, please refer to Splunk’s documentation on scheduling searches.

For log replay analysis, the same command is appended, except the mode is set to `LogReplay`:
```
| sort _time 
| reportmetrics projectName=YOUR_PROJECT_NAME systemName=YOUR_SYSTEM_NAME mode=LogReplay serverUrl=INSIGHTFINDER_APP_SERVER userName=USER_NAME timeout=10
```

For metrics analysis, both streaming and replay, please make sure timestamp is named as `_time` and the host name is named as `host`. You can use the `rename` command to meet the naming requirements, as demonstrated below.

For metrics streaming analysis, you should append the following to your query:
```
| eval _time = strptime('YOUR_TIMESTAMP_NAME', 'stftime_fmt') 
| rename YOUR_HOST_NAME as host 
| table _time host LIST_OF_METRICS 
| reportmetrics projectName=YOUR_PROJECT_NAME systemName=YOUR_SYSTEM_NAME mode=MetricStreaming serverUrl=INSIGHTFINDER_APP_SERVER userName=USER_NAME timeout=10
```

Simply denote which metrics you wish to send within the table command in place of `LIST_OF_METRICS`; for example, if your field names are `cpu.usage`, `cpu.idle`, `mem_used`, `network_tx`, and `network_rx`, you could use `cpu* mem_used network*` as your LIST_OF_METRICS.

For metrics replay analysis, the command is the same, except the mode is set to `MetricReplay`:
```
| eval _time = strptime('YOUR_TIMESTAMP_NAME', 'stftime_fmt') 
| rename YOUR_HOST_NAME as host 
| table _time host LIST_OF_METRICS 
| reportmetrics projectName=YOUR_PROJECT_NAME systemName=YOUR_SYSTEM_NAME mode=MetricReplay serverUrl=INSIGHTFINDER_APP_SERVER userName=USER_NAME timeout=10
```

If you have column(s) that holds a value (ie an aggregated count) and another columns(s) which holds that value field's potential metric names (ie error code types), you can specify those fields by appending the following parameters:
```
metricValCols="valCol1;valCol2"
metricNameCols="nameCol1a,nameCol1b;nameCol2a,nameCol2b"
```
For each nth `metricValCol`, the columns that contain that value's name are in the nth `metricNameCol`. For example, if `metricValCol="count"` and `metricNameCol="error_code,status_code"`, then the metric reported will be named the value in either `error_code` or `status_code` (whichever column is found first), with a value equal to the value in `count`.

For support, please email support@insightfinder.com

### Uninstall
**Single Instance**
Delete the insightfinderapp folder in `$SPLUNK_HOME/etc/apps/` and any insightfinderapp folders in user directories under `$SPLUNK_HOME/etc/users`, then restart Splunk: `$SPLUNK_HOME/bin/splunk restart`

**Cluster**
Delete the insightfinderapp folder in `$SPLUNK_HOME/etc/shcluster/apps/` and distribute with `$SPLUNK_HOME/bin/splunk apply shcluster-bundle ... -force true`
