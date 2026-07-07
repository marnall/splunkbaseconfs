# ThousandEyes App For Splunk

## SUMMARY

The ThousandEyes App For Splunk enables organizations to collect and analyze Cloud & Enterprise Agent and Endpoint Agent
test results data, Event and Activity logs, and Network Trace data. Integrated with Splunk, it provides visibility into
the health and performance of IT systems, applications, and network endpoints. The App also offers pre-built dashboards
for easy analysis. This helps operational teams monitor performance, troubleshoot issues, and optimize both
infrastructure and end-user experiences.

## REQUIREMENTS

- Splunk version 9.1.x, 9.2.x, 9.3.x, 9.4.x and 10.4.x (see note below).
- OS Support: Linux (Centos, Ubuntu) and Windows
- Browser Support: Chrome and Firefox
- [Splunk Common Information Model (CIM)](https://splunkbase.splunk.com/app/1621): 6.0.1
- ThousandEyes account credentials

## DETAILS

> **Splunk 10.4 note:** All dashboard scripts have been migrated away from the removed `splunkjs/mvc` module. The OAuth configuration flow, multiselect filter inputs, and table link columns are all fully supported on Splunk 10.4. The Traces dashboard uses Dashboard Studio and is unaffected.

### Version: 0.8.0

* Fix OAuth authorization flow broken on Splunk 10.4 (Enterprise and Cloud) by replacing the removed `splunkjs/mvc` dependency with native `fetch` API calls.
* Fix OAuth proxy requests to respect Splunk's configured web-root prefix when deployed behind a reverse proxy.

### Version: 0.7.0

* Add `python.required = 3.13` to all Python-backed stanzas in `restmap.conf`, `inputs.conf`, and `alert_actions.conf` to restore Splunk Cloud Platform compatibility.

### Version: 0.6.0

* Updated the webhook payload template drill-down URL from the deprecated `cloud-and-enterprise-agents` path to the new `network-app-synthetics/views` path, reflecting the ThousandEyes platform URL restructuring.

### Version: 0.5.0

* Support for Network Endpoint Experience Dynamic Tests in "Tests Stream - Metrics" input and dashboard

### Version: 0.4.0

* Add new "Alerts Stream" input for real-time alert notifications from ThousandEyes
* New alerts dashboard for visualizing received alerts

### Version: 0.2.2

- Default window. Application Dashboard
- Add API test types for "Tests Stream - Traces"

### Version: 0.2.1

- Make app.conf compliant with splunk base check

### Version: 0.2.0

- Add a new Alert Action to support forwarding ITSI events to ThousandEyes

### Version: 0.1.0

- Improve Proxy Settings
- Add ThousandEyes Free Trial activation tab in the configuration page
- Replace old "Activity" input with new "Activity logs Stream" using OpenTelemetry integration
- Activity logs data now collected via stream instead of polling for improved performance
- Remove "all accounts" option for Activity logs Stream input

### Version: 0.0.25

- Add new "Tests Stream - Traces" input for network trace data collection
- Rename existing "Tests Stream" input to "Tests Stream - Metrics"
- Support for page-load and web-transactions trace data collection
- Support Tags for easier test selection
- Add support for the re-authorization users manually if they encountered the issue with the expired token error or the issue with the authorization scope (401 error)

### Version: 0.0.24

- Fix HEC Target URL prefill

### Version: 0.0.23

- Add the "HEC Target URL" field to streams
- Add automatic token refreshing to avoid token expiration issues

### Version: 0.0.22

- Fix bug getting list of HEC tokens

### Version: 0.0.21

- Update API permission scopes from 'endpoint-tests:manage' and 'tests:manage' to 'endpoint-tests:read' and 'tests:read'

### Version: 0.0.20

- Update Network dashboard Agent-to-Agent and Agent-to-Server single value panels to support events without server.address values

### Version: 0.0.19

- Add Input Type in Inputs Table.
- Added HTTPS proxy support.
- Added indication if tests are enabled in the Tests dropdown in Tests Stream configuration.
- Updated line charts in dashboards to have data points continuously connected

### Version: 0.0.18

- Handle the user accounts having the special character +
- Updated the Event Dashboards to add link to the Event on ThousandEyes Platform.

### Version: 0.0.15

- Provided Configuration, Inputs and Dashboards.
- Configuration is used to provide configuring the ThousandEyes with OAuth.
- 3 Data Inputs for Data Collection Tests Stream, Event and Activity
- Provided Inbuilt dashboards to visualize collected streams, Configuration and activity data

## INSTALLATION OF APP

ThousandEyes TA for Splunk can be installed through UI as shown below or extract .spl file directly into $SPLUNK_HOME/etc/apps/ folder.

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click `Install app from file`.
3. Click `Choose file` and select the ThousandEyes TA for Splunk installation file.
4. Click on `Upload`.

### TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

This app can be set up in two ways:

1. Standalone Mode
   - Install the ThousandEyes TA for Splunk.
   - Configure an account and create modular input.
2. Distributed Environment
   - Install the ThousandEyes TA for Splunk on the Search Head and On-Premise IDM/Heavy Forwarder.
   - Configure the modular Inputs only on the Forwarder .
   - Configure macros, savedsearches only on the Search Head.

Note that for the distributed environment, only indexes of the Forwarder would be shown in the input configuration page.

### INSTALLATION IN SPLUNK CLOUD

- Same as an on-premise setup.

## UPGRADE THE APP

You can upgrade the Cisco ThousandEyes App for Splunk using one of the following methods.

### Upgrade from Splunk Web UI (Manual Installation)

- Download the required version from [Cisco ThousandEyes App for Splunk on Splunkbase](https://splunkbase.splunk.com/app/7719).
- In Splunk, go to **Apps** > **Manage Apps**.
- Click **Install app from file**.
- Click **Choose File** and select the Cisco ThousandEyes App for Splunk installation file.
- Select **Upgrade app**, then click **Upload**.
- Restart the Splunk instance if prompted.

### Upgrade from Splunk Web UI (Automated Update)

- In Splunk, go to **Apps** > **Manage Apps**.
- Find **Cisco ThousandEyes App for Splunk** in the list.
- In the **Version** column, click **Update to `<latest_version>`**.
- Accept the terms and conditions, then click **Accept and continue**.
- Enter your credentials if prompted.
- Restart the Splunk instance if prompted.

### Upgrading to version 0.0.18 from 0.0.15

- Before upgrading to version 0.0.18, follow these steps:
  - Navigate to Cisco ThousandEyes App for Splunk > Inputs and delete all the configured inputs
  - Navigate to Cisco ThousandEyes App for Splunk > Inputs and delete the configured Thousandeyes user
- Follow the `UPGRADE THE APP` section.
- Re-configure the Thousandeyes user and Inputs for Cisco ThousandEyes App for Splunk.

## TROUBLESHOOTING

- To troubleshoot Cisco ThousandEyes App for Splunk, check $SPLUNK_HOME/var/log/splunk/_thousandeyes_.log or user can search `index="_internal" sourcetype="ciscoThousandEyes:log"` query to see all the logs on UI. Also, user can use `index="_internal" source="*thousandeyes*.log" ERROR` query to see ERROR logs on the Splunk UI.
- Note that all log files of this App will be generated in `$SPLUNK_HOME/var/log/splunk/` directory.
- If data collection is not working then ensure that the internet is active where a proxy is configured and also ensure that the kvstore is enabled. You can check current kvstore status by running following command `splunk show kvstore-status` from $SPLUNK_HOME/bin. The output should not report any errors and status should be Ready.Alternatively, you should not receive any KVstore related error in the messages section in Splunk menu bar.
- If Stream Input (Metrics, Traces, or Activity logs Stream) is still not working, Navigate to `Settings` > `HTTP Event Collector`. Ensure
  that the token used to configure the Stream input is Enabled. If not, click on the corresponding `Enable` option
  in the Actions Column. If the Enable/Disable button is disabled, Click on Global Settings and select All Tokens to
  Enable.
- While configuring Input in Splunk Enterprise instance if following error message is encountered: `The Server Name, Host Name and Host is not reachable from Cisco Thousandeyes` make sure that the Server Name or Host Name is set correctly. To set these, Navigate to `Settings` > `Server Settings` > `General Settings`. Here set the `Splunk server name` or `Default host name` under Index Settings to correct value as expected in the HEC collector URL. Restart Splunk after this change.
- If configured proxy uses custom certificate, you should add the custom certificate to $SPLUNK_HOME/etc/apps/ta_cisco_thousandeyes/lib/certifi/cacert.pem

## CONTACT

- Support Offered: Yes
- Support Details:
  - Email: support@thousandeyes.com

## CONFIGURATION OF APP

Configure ThousandEyes TA for Splunk:

- Login to Splunk Web UI.
- Navigate to Apps > ThousandEyes TA for Splunk

### Account

To configure the Account

1. Navigate to the `Configuration` > `ThousandEyes User`.
2. Click on `Add` button on the right corner.
3. Click on Authorize and provide the consent.
4. Click on Add button to save the account.

| ThousandEyes Account parameters | Mandatory or Optional | Description                                    |
|---------------------------------|-----------------------|------------------------------------------------|
| Account Name                    | Mandatory             | Unique Name for the Account that is configured |
| Authorize                       | Mandatory             | To authorize and to provide consent            |

To re-authorize the user, follow the below steps:

1. Navigate to the `Configuration` > `ThousandEyes User`.
2. Click on the `Edit` button in the **Actions** column.
3. Click on the `Re-Authorize` button.
4. Click on the **Verify** and provide the consent.
5. Click on the `Update` button to update the account tokens.

### ThousandEyes Free Trial

To configure the ThousandEyes 15-day Free Trial:

1. Navigate to the `Configuration` > `ThousandEyes Free Trial` tab.
2. Follow up the instructions:
   - Submit the ThousandEyes free trial form
   - Wait for an email with the activation link
   - Set your password
   - Create the ThousandEyes test.
3. Click on the `Start 15-day Free Trial` button to start the free trial.

**Note:** For more information on how to create a ThousandEyes test, please refer to the [ThousandEyes Documentation](https://docs.thousandeyes.com/product-documentation/getting-started/getting-started-with-cloud-and-enterprise-agent-tests).

### Proxy

To configure the Proxy

1. Navigate to the `Setup`> `Configuration`.
2. Click on the `Proxy` tab.
3. Provide your Proxy credential and Click on `Save`.

| Proxy Parameters  | Mandatory/Optional | Description                                                                             |
| ----------------- | ------------------ | --------------------------------------------------------------------------------------- |
| Enable            | Optional           | To enable the proxy                                                                     |
| Auth Type         | Mandatory          | Select the auth type from the dropdown `None/Basic`                                     |
| Proxy Username    | Optional           | Username of the proxy server (Mandatory if **Auth Type** is chosen `Basic`)             |
| Proxy Password    | Optional           | Password of the proxy server (Mandatory if **Auth Type** is chosen `Basic`)             |
| Proxy Protocol    | Mandatory          | Select proxy protocol that you want to use from the dropdown (supports HTTP proxy only) |
| Proxy Certificate | Optional           | Add Proxy Certificate in PEM format                                                     |
| Proxy Host        | Mandatory          | Host or IP of the proxy server                                                          |
| Proxy Port        | Mandatory          | Port for proxy server                                                                   |

### Logging

To configure the Logging

1. Navigate to the `Setup`> `Configuration`.
2. Click on the `Logging` tab.
3. Select the log level from the dropdown and click on `Save`.

### To Configure HEC

1. Navigate to `Settings` > `Data inputs` > `HTTP Event Collector`
2. Click on `New Token` button.
3. In the Token configuration page, provide the following details and click `Next`

| Input Parameter       | Mandatory or Optional | Description                                    |
|-----------------------|-----------------------|------------------------------------------------|
| Name                  | Mandatory             | Unique name identify the HEC token created     |
| Source name override? | Mandatory             | Add the value to specify the source of data    |
| Description           | Optional              | Text to provide description for this HEC token |

### Inputs

To configure the Inputs

1. Navigate to the `Setup`> `Inputs`.
2. Click on `Create New Input`, one dropdown will be open with options:
    * `Tests Stream - Metrics`
    * `Tests Stream - Traces`
    * `Event`
    * `Activity logs Stream`
    * `Alerts Stream`
3. Select a option and pop-up will open accordingly.
4. Provide the input related information and click on `Add` to start the data collection.

**Tests Stream - Metrics**
Tests Steam - Metrics input is used for Cloud & Enterprise Agent & Endpoint Agent tests via OTel stream along with
Network Path Data if configured.

Field descriptions are as below:

| Input Parameter               | Mandatory or Optional | Desciption                                                                                                                                                                            |
| ----------------------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Name                          | Mandatory             | Unique name identify Input                                                                                                                                                            |
| ThousandEyes User             | Mandatory             | Choose the user created from configuration step                                                                                                                                       |
| Account Group                 | Mandatory             | Select one account group                                                                                                                                                              |
| Tags                          | Optional              | Select one/multiple tags for easier test selection                                                                                                                                    |
| Cloud & Enterprise Agent Test | Optional              | Select one/multiple tests of Cloud & Enterprise Agent Test                                                                                                                            |
| Endpoint Agent Test           | Optional              | Select one/multiple tests of Endpoint Agent Test                                                                                                                                      |
| HEC Target                    | Mandatory             | HEC Target URL (e.g., https://http-inputs-<host>.splunkcloud.com:443/services/collector/event for Splunk Cloud or https://<host>:8088/services/collector/event for Splunk Enterprise) |
| HEC Token                     | Mandatory             | Token value of Configured Splunk HEC Input                                                                                                                                            |
| Test Index                    | Mandatory             | To get the stream data into particular index                                                                                                                                          |
| ThousandEyes Stream ID        | Optional              | ThousandEyes Stream ID for given Input                                                                                                                                                |
| Include Network Path Data     | Optional              | Fetch Network Path Data if checked                                                                                                                                                    |

if Include Network Path Data Information will be checked then, below fields will be visible.

| Input Parameter            | Mandatory or Optional | Description                                        |
|----------------------------|-----------------------|----------------------------------------------------|
| Network Path Data Index    | Mandatory             | To get the Network Path data into particular index |
| Network Path Data Interval | Mandatory             | Interval to fetch the Network Path Data from API   |


**Tests Stream - Traces**
Tests Stream - Traces input is used for collecting network trace data from Cloud & Enterprise Agent page-load and
web-transactions tests.

Field descriptions are as below:

| Input Parameter   | Mandatory or Optional | Description                                                                                                                                                                           |
| ----------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Name              | Mandatory             | Unique name identify Input                                                                                                                                                            |
| ThousandEyes User | Mandatory             | Choose the user created from configuration step                                                                                                                                       |
| Account Group     | Mandatory             | Select one account group                                                                                                                                                              |
| Tags              | Optional              | Select one/multiple tags for easier test selection                                                                                                                                    |
| CEA Tests         | Optional              | Select one/multiple CEA tests (page-load and web-transactions only)                                                                                                                   |
| HEC Target        | Mandatory             | HEC Target URL (e.g., https://http-inputs-<host>.splunkcloud.com:443/services/collector/event for Splunk Cloud or https://<host>:8088/services/collector/event for Splunk Enterprise) |
| HEC Token         | Mandatory             | Token value of Configured Splunk HEC Input                                                                                                                                            |
| Test Index        | Mandatory             | To get the trace data into particular index                                                                                                                                           |

**Event**

Once the user selects event input, the user will need to provide below fields to create the input. List of events from the selected account group based on time interval.

To configure Event Input, Field descriptions are as below:

| Input Parameter   | Mandatory or Optional | Desciption                                |
|-------------------|-----------------------|-------------------------------------------|
| Name              | Mandatory             | Unique name identify Input                |
| ThousandEyes User | Mandatory             | Choose the user created from earlier step |
| Account Group     | Mandatory             | Select one account groups                 |
| Polling Interval  | Mandatory             | Interval to fetch the event data from API |
| Index             | Mandatory             | Index to ingest data into                 |

**Activity logs Stream**

Activity logs Stream input is used for collecting activity logs data via OpenTelemetry stream integration instead of traditional polling.

Field descriptions are as below:

| Input Parameter     | Mandatory or Optional | Description                                                                                                                                                                           |
| ------------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Name                | Mandatory             | Unique name identify Input                                                                                                                                                            |
| ThousandEyes User   | Mandatory             | Choose the user created from configuration step                                                                                                                                       |
| Account Group       | Mandatory             | Select one account group                                                                                                                                                              |
| HEC Target          | Mandatory             | HEC Target URL (e.g., https://http-inputs-<host>.splunkcloud.com:443/services/collector/event for Splunk Cloud or https://<host>:8088/services/collector/event for Splunk Enterprise) |
| HEC Token           | Mandatory             | Token value of Configured Splunk HEC Input                                                                                                                                            |
| Activity Logs Index | Mandatory             | To get the activity logs data into particular index                                                                                                                                   |

**Alerts Stream**
 
Alerts Stream input is used for collecting real-time alert notifications from ThousandEyes via webhook integration. This input automatically configures ThousandEyes webhook operations and connects them to Splunk HEC for seamless alert delivery.
 
Field descriptions are as below:
 
| Input Parameter      | Mandatory or Optional | Description                                                                                                                                                                           |
|----------------------|-----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Name                 | Mandatory             | Unique name identify Input                                                                                                                                                            |
| ThousandEyes User    | Mandatory             | Choose the user created from configuration step                                                                                                                                       |
| Account Group        | Mandatory             | Select one account group                                                                                                                                                              |
| Alert Rule IDs       | Mandatory             | Select one/multiple alert rules to enable webhook notifications                                                                                                                       |
| Severity Filter      | Optional              | Filter alerts by severity level (info, warning, critical)                                                                                                                             |
| HEC Target           | Mandatory             | HEC Target URL (e.g., https://http-inputs-<host>.splunkcloud.com:443/services/collector/event for Splunk Cloud or https://<host>:8088/services/collector/event for Splunk Enterprise) |
| HEC Token            | Mandatory             | Token value of Configured Splunk HEC Input                                                                                                                                            |
| Alerts Index         | Mandatory             | To get the alerts data into particular index                                                                                                                                          |
| Page Size            | Optional              | Number of records per page for API requests                                                                                                                                           |
| Interval             | Optional              | Frequency of checking for configuration updates                                                                                                                                       |
 
**Note**: When you configure an Alerts Stream input, the system will automatically:
1. Create a webhook operation in ThousandEyes
2. Create a connector for Splunk HEC integration
3. Link the webhook operation to the connector
4. Update the selected alert rules to use the webhook for notifications

## MACROS

The app contains the following macros

1. **summariesonly**: If you want to visualize only accelerated data then change this macro to summariesonly=true. Default value: summariesonly=false.
2. **stream_index**: Kindly update the specific indexes in which Test Stream Metrics data is collected. Default value: index=\*.
3. **path_viz_index**: Kindly update the specific indexes in which Network Path Data is collected. Default value: index=\*.
4. **activity_index**: Kindly update the specific indexes in which Activity data is collected. Default value: index=\*.
5. **event_index**: Kindly update the specific indexes in which Event data is collected. Default value: index=\*.
6. **trace_index**: Kindly update the specific indexes in which Test Stream Traces data is collected. Default value:
   index=*.
7. **alerts_index**: Kindly update the specific indexes in which Alerts Stream data is collected. Default value: index=*.
   index=\*.

**Note** : Please update the above index macros to specific indexes in which the corresponding data is collected. The default value may lead to performance overhead as unrelated indexes will also be searched. For trace data, use the
trace_index macro to specify the index where trace data is collected.
To update Macros,

1. Navigate to Settings > Advanced Search > Search Macros
2. In the App dropdown filter select Cisco ThousandEyes App for Splunk
3. click on the macro in the Name column.
4. Update the Definition as required.
5. click save.

## SAVED SEARCHES

The app contains the following macros

1. **thousandeyes_account_groups_update**: used to maintain account group Id and account group name

## DASHBOARDS

The app contains the following dashboards

1. **Application**: It consists on panels of HTTP Server, Page Load, API and Transaction Test.
2. **Network**: It consists on panels of Agent to Server & Agent to Agent, BGP and DNS Test.
3. **Voice**: It consists on panels of FTP, SIP and RTP Test.
4. **Configuration Status**: An overview of statistics data related to Test Stream input configured within the TA.
5. **Activity Logs**: An Overview of Activity Dashboard show the results of user activities based on input configured for the Activity input.
6. **Alerts**: An Overview of triggered alerts.

## BINARY FILE DECLARATION

- lib/charset_normalizer/md\_\_mypyc.cpython-39-x86_64-linux-gnu.so - This binary file is provided by UCC
- lib/charset_normalizer/md.cpython-39-x86_64-linux-gnu.so - This binary file is provided by UCC

## UNINSTALL & CLEANUP STEPS

- Remove $SPLUNK_HOME/etc/apps/ta_cisco_thousandeyes
- Remove $SPLUNK_HOME/var/log/splunk/_thousandeyes_.log.
- To reflect the cleanup changes in UI, Restart Splunk Enterprise instance
