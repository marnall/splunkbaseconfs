# Flashpoint Add-on for Splunk

## This is an add-on powered by the Splunk Add-on Builder

## OVERVIEW

Flashpoint Splunk Addon is a Splunk Addon which captures, indexes, and correlates real-time data in a searchable repository from which it can generate graphs, reports, alerts, dashboards, and visualizations. The data is collected using Flashpoint REST APIs.

- Author - Flashpoint
- Version - 2.4.1
- Build - 1

## Compatibility Matrix
* Browser: Google Chrome, Mozilla Firefox
* OS: Linux, Windows
* Splunk Enterprise version: 10.0.x, 9.4.x, 9.3.x and 9.2.x
* Supported Splunk Deployment: Splunk Cluster, Splunk Standalone, and Distributed Deployment

## Recommended System Configuration

- Standard Splunk configuration of Search Head, Indexer, and Forwarder.
- This application should be installed on Forwarder and Search Head, but no need to configure it on the Search Head i.e. installation is required on Forwarder and Search Head, but the configuration is only required on Forwarder.

## Installation

This TA can be installed through UI using the following steps.

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click the `install app from file`.
3. Click `Choose File` and select the TA-flashpoint installation file.
4. Click on `Upload`.

Once the installation is complete, restart Splunk.

## Release Notes

### Version: 2.4.1
- Hotfix: Enforced minimum interval of 3600 seconds and increased API Poll Offset 5400 seconds to handle data caching mechanism for Indicators input.

### Version: 2.4.0
- Added support to collect enrichment data in Ransomware events.
- Updated help text to point towards new URL.

### Version: 2.3.1
- Fixed an issue with Compromised Credentials filters.

### Version: 2.3.0
- The API for "Indicators" input type has been upgraded to version v2.
- Upgraded AOB to v4.5.1
- Resolved the checkpoint issue of "CVE" input type.

### Version: 2.2.0
- Added additional filters for compromised credentials input type.
- Improved handling of plain text passwords for Compromised Credentials input type.

### Version: 2.1.1
- Updated the user-agent header to include the current TA version.

### Version: 2.1.0
- Updated the Splunk SDK version.

### Version: 2.0.0
- Updated the endpoints to ignite version.
- Removed 'Exploit' data support.
- Updated the CIM Mappings.

### Version: 1.4.0

- Upgraded to AOB v4.2.0

### Version: 1.3.0

- Upgraded AOB to v4.1.3

### Version: 1.2.0

- Upgraded AOB to v4.0.0
- Added scroll API support for data collection of types "Indicators" and "Mentions"
- Added data collection of types "Compromised Credentials", "Ransomware" and "Alerts"
- Added correlation searches for Compromised Credentials and Alerts
- Disabled fields named "Type" and "Start Date" on an edit of existing Input.

## Upgradation

### Upgrading to version 2.4.1

- No additional steps are required after the upgrade.
- Note: After upgrading, any Indicators input with an interval less than 3600 seconds will need to be updated to meet the new minimum requirement.

### Upgrading to version 2.4.0

- No additional steps are required after the upgrade.

### Upgrading to version 2.3.1

- No additional steps are required after the upgrade.

### Upgrading to version 2.3.0

- No additional steps are required after the upgrade.

### Upgrading to version 2.2.0

- No additional steps are required after the upgrade.

### Upgrading to version 2.1.1

- No additional steps are required after the upgrade.

### Upgrading to version 2.1.0

- No additional steps are required after the upgrade.

### Upgrading to version 2.0.0

- Disable and delete the exploit input before upgrading as it is no longer supported in v2.1.0.
- Make sure that the account that you are using supports Ignite version or else new account needs to be configured.

### Upgrading to version 1.4.0

- No additional steps are required after the upgrade.

### Upgrading to version 1.3.0

- No additional steps are required after the upgrade.

### Upgrading to version 1.2.0

- No additional steps are required after the upgrade.

### Upgrading to version 1.1.2

Follow the below steps to upgrade the Add-on from v1.1.1 to v1.1.2

1. Go to the `Inputs` page and disable all the inputs.
2. Go to Apps > Manage Apps and click the `install app from file`.
3. Click `Choose File` and select the TA-flashpoint installation file.
4. Check the `Upgrade app` checkbox and click on `Upload`.
5. After a successful restart, go to the apps list and open `Flashpoint Intelligence`.
6. Go to the `Inputs` page and enable all the inputs.

Follow the below steps to upgrade the Add-on from versions prior to v1.1.1 to v1.1.2

1. Go to the `Inputs` page and disable all the inputs.
2. Delete all the inputs.
3. Go to Apps > Manage Apps and click the `install app from file`.
4. Click `Choose File` and select the TA-flashpoint installation file.
5. Check the `Upgrade app` checkbox and click on `Upload`.
6. After a successful restart, go to the apps list and open `Flashpoint Intelligence`.
7. From the `Inputs` page, click on `Create New Input` to create new inputs with the required fields.

## Application Setup

### Inputs

After Installation

1. Go to the apps list and open Flashpoint Intelligence. From the inputs screen, click on `Create New Input`.
2. Enter all required values.

| Input Parameter             | Mandatory or Optional | Description                                                                                                                                                                                                                                                                                               |
| --------------------------- | --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Name                        | Mandatory             | Give a Unique name to each input to identify |
| Type                        | Mandatory             | Select the Type of data you want to fetch. Example Reports, Indicators, CVE, Mentions, Compromised Credentials, Ransomware, Alerts.|
| Account Name                | Mandatory             | Select your account among the list|
| Collect Plain Text Password | Optional              | Should the password field be collected for Compromised Credential events?|
| Is Fresh | Optional              | To collect The credential that is fresh(recently exposed or observed)|
| Password Complexity Has Lowercase | Optional              | To collect passwords that include at least one lowercase letter |
| Password Complexity Has Uppercase | Optional              | To collect passwords that include at least one uppercase letter |
| Password Complexity Has Number | Optional              | To collect passwords that include at least one numeric digit |
| Password Complexity Has Symbol | Optional              | To collect passwords that include at least one special character (e.g., @, #, $, etc.)|
| Password Complexity Length | Optional              | To collect password with this minimum length |
| Interval                    | Mandatory             | Interval in seconds. The input will be triggered at every interval amount of time for all the inputs. For Indicators input type, the minimum interval is 3600 seconds (1 hour). For CVE the interval is fixed which is 1 hour, but, it will pull the data only at a specific time i.e. 8 PM UTC for CVEs except for the first run. |
| Start Date                  | Mandatory             | Date and time from which you want to fetch events. Enter the value in 'YYYY-MM-DDThh:mm:ss' format e.g. 2013-04-17T09:12:36. UTC TimeZone will be considered.|
| Index                       | Mandatory             | Index to which you want to send data. It refers to the index name in indexes.conf.                                                                                                                                                                                                                        |

### Note:

- Note that the Add-on will consider the UTC timezone for all the data collection
- Number of inputs of type "Ransomware", "Alert" and "Mention" should not exceed more than five as all of them are using scroll API which has a limit of max 5 scroll sessions at a time.

### Configurations

1. Click on the `Configuration` tab next to the `Inputs` tab.

2. If you want to add proxy settings, select the `Proxy` option.
3. Enter your proxy credentials and click `Save`. Note that if multiple inputs are created with the same `Type` and same `Account Name`, there will be duplicate events in Splunk.

| Proxy Parameter       | Mandatory or Optional | Description                                                                                     |
| --------------------- | --------------------- | ----------------------------------------------------------------------------------------------- |
| Enable                | Optional              | Checkbox to enable or disable proxy support                                                     |
| Proxy Type            | Mandatory             | Select the proxy type that you want to use from the dropdown. The TA supports the `http` proxy. |
| Host                  | Mandatory             | Host or IP of the proxy server                                                                  |
| Port                  | Mandatory             | Port for proxy server                                                                           |
| Username              | Optional              | Username of the proxy server. It is mandatory in the case when the user has entered `Password`  |
| Password              | Optional              | Password of the proxy server. It is mandatory in the case when the user has entered `Username`  |
| Remote DNS resolution | Optional              | Check this checkbox if you want to do DNS resolution for the `Host`                             |

1. To create an account, select the `Account` option.
2. Enter your Account Name and Flashpoint Intelligence API Key and click on the `Add` button.

| Input Parameter | Mandatory or Optional | Description                          |
| --------------- | --------------------- | ------------------------------------ |
| Account Name    | Mandatory             | Give Unique name to account          |
| API key         | Mandatory             | API key from Flashpoint Intelligence |

1. To configure logging, Select `Logging`.
2. Select the desired log level from the dropdown and click on `Save`.

## Search

To see data logged by `Flashpoint`, select the `Search` tab and click on `Data Summary`. Follow the given sourcetypes for data searching.

| Data Type               | Sourcetype                                        |
| ----------------------- | ------------------------------------------------- |
| Indicators              | `flashpoint_intelligence`                         |
| Reports                 | `flashpoint_intelligence:reports`                 |
| CVEs                    | `flashpoint_intelligence:cve`                     |
| Mentions                | `flashpoint_intelligence:mentions`                |
| Alerts                  | `flashpoint_intelligence:alerts`                  |
| Ransomware              | `flashpoint_intelligence:ransomware`              |
| Compromised Credentials | `flashpoint_intelligence:compromised_credentials` |

You can also enter search parameters in the search box to filter events.

## CIM Visualisation

To create CIM visualizations, go to `Settings -> Data models`. Select the model you want to create visualizations for. Click on the `Pivot` button at the top right corner. Select the data model from the category. Once you are in the `New Pivot` page, select a chart from the left pane. The Flashpoint TA sourcetype `flashpoint_intelligence` is compliant to `Malware`, `Intrusion Detection` and `Vulnerabilities` Data Model.

## Saved Searches

- This Application contains the following Saved Searches.

| Saved Searches Name                                    | Description                                                                       | Interval | Default Status |
| ------------------------------------------------------ | --------------------------------------------------------------------------------- | -------- | -------------- |
| `Identity - Flashpoint Compromised Credentials - Rule` | Generate Notable Events for new Flashpoint Compromised Credentials data in Splunk | 30 mins  | Disabled       |
| `Threat - Flashpoint Alerts - Rule`                    | Generate Notable Events for new Flashpoint Alerts data in Splunk                  | 30 mins  | Disabled       |

## Macros

### `flashpoint_index`

- It is used for searching flashpoint events from the index.
- By default, it will search from all index
- To improve the performance of searches using this macro, update this macro to only search in indices where flashpoint data is collected. Follow the below steps for updating macro.

* Steps to update the macro

1. Go to `Settings` -> `Advanced Searches` -> `Search macros`
2. Select `Flashpoint Intelligence` in `App`, `Any` in `Owner`, and `Created in App` in the last dropdown
3. Click on the macro which you want to edit
4. Update macro search and click on save

## Enterprise Security - Correction Savedsearch Configuration

### To change the configuration of Correction Savedsearch

1. Open `Enterprise Security` App
2. Go to `Configure` -> `Content` -> `Content Management` Dashboard
3. Select `Flashpoint Intelligence` in the `App` dropdown.
4. To Enable/Disable the Correlation savedsearches, Click on the respective button in the `Actions` column of the table.
5. To change the detailed configuration of a specific correlation search, click on the name of the Savesearch for which you want to change the configuration
6. In edit form, the `Time Range` section
   - Updating `Cron Schedule` changes how frequently savedsearch should run.
   - Updating `Earliest Time` changes how far to look for events in past for matching.
7. In edit form, the `Throttling` section
   - Updating `Window duration` will prevent creating notable again in provided window duration, if the same type of event matches. This will help in changing the suppression feature.

Note: 
- `Earliest Time` should have a larger time range than the `Cron Schedule` interval to avoid missing any Splunk events.
- Any update to correlation savedsearch will clear the suppression data for existing notables so notables can be duplicated for provided `Earliest Time`.

### To add new fields in the `Additional Fields` section when a Notable event is expanded in the `Incident Review` Dashboard of ES

Steps:
1. Open Splunk ES, click Configure -> Incident Management -> Incident Review Settings
2. Scroll down and go to section `Incident Review - Event Attributes`
3. Click on the `Add new entry` button at the end.
4. Form will pop up with fields `Label` and `Field`. The value of `Field` can be any field coming in a notable event that you want to show in the `Additional Fields` section.
5. Click on `Done`. The added field will start showing in the `Additional Fields` section of notables in the `Incident Review` dashboard, which has the given field.

#### Recommended Fields that can be added in `Additional Fields`

* Identity - Flashpoint Compromised Credentials - Rule

| Label                   | Field                                                 |
| ----------------------- | ----------------------------------------------------- |
| Timestamp               | event_timestamp                                       |
| Domain                  | source.domain                                         |
| Email                   | source.email                                          |
| Password                | source.password                                       |
| Is Fresh                | source.is_fresh                                       |
| Customer ID             | source.customer_id                                    |
| Breach Type             | source.breach.breach_type                             |
| Password Hash Algorithm | source.password_complexity.probable_hash_algorithms{} |

* Threat - Flashpoint Alerts - Rule

| Label        | Field                  |
| ------------ | ---------------------- |
| Timestamp    | event_timestamp        |
| BaseTypes    | resource.basetypes{}   |
| Keyword Text | reason.text            |
| Body         | highlight_text         |

Note: If the user sees extremely large content in field `highlight_text`, avoid adding it into `Additional Fields`

For more details, refer to the Splunk blog post https://www.splunk.com/en_us/blog/security/modifying-the-incident-review-page.html

## Troubleshooting

- To troubleshoot Flashpoint Intelligence Addon, check \$SPLUNK_HOME/var/log/splunk/**ta_flashpoint_intelligence_flashpoint_intelligence.log** file.

- Users can also search for ERROR logs in the Splunk using this query `index="_internal" source=**ta_flashpoint_intelligence_flashpoint_intelligence.log** ERROR`

- As the input configuration settings have been changed in the newer version of the Add-on, if a user has enabled any inputs which were created in the older version of Flashpoint App(versions before 1.1.1), then the app will throw an error in the Splunk Message box as:
  `"Found an unsupported input <input_name> from the older version of Flashpoint. Please recreate this input with the new configurations to continue fetching data."`
  To resolve this error, the user would have to delete all the inputs that were created before 1.1.1 and create them again in the latest version to start fetching the data.

- User can also search for the same error in the Splunk using this query
  `index="_internal" source=**ta_flashpoint_intelligence_flashpoint_intelligence.log** ERROR Found an unsupported input`

- In the log, the error message `Too many scroll sessions` with 429 status code indicates that data collections are exhausting the scroll session limit of 5. A number of inputs of type "Ransomware", "Alert" and "Mention" should not exceed more than five as all of them are using scroll API which has a limit of max 5 scroll sessions at a time.

- It is a known issue if you get a 5xx status code error for Inputs of type "Ransomware", "Alert" and "Mention" and will be fixed in future releases. Data won't be missed because of this error and data collection will continue where it left off. Data duplication can happen due to these errors.

- Duplication of a few events can occur when data collection is in progress and Splunk is restarted, Input disabled, or in case of any kind of error from API.

## UNINSTALL & CLEANUP STEPS
* Remove $SPLUNK_HOME/etc/apps/TA-flashpoint-intelligence
* Remove $SPLUNK_HOME/var/log/splunk/ta_flashpoint_intelligence_*.log*.
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

## Binary File Declaration
* _yaml.cpython-37m-x86_64-linux-gnu.so - This is a binary file.

## External Libraries used

| Library(Python) | Version | Repository link                       | License                                                               |
| --------------- | ------- | ------------------------------------- | --------------------------------------------------------------------- |
| Jinja2          | 2.10.1  | https://pypi.org/project/Jinja2/      | https://www.cgl.ucsf.edu/chimerax/docs/licenses/Jinja2-LICENSE.txt    |
| Munch           | 2.0.4   | https://pypi.org/project/munch/       | https://github.com/crazyhitty/Munch/blob/master/LICENSE.md            |
| ply             | 3.9     | https://pypi.org/project/ply/         | https://github.com/dabeaz/ply                                         |
| markupsafe      | 1.0     | https://pypi.org/project/MarkupSafe/  | https://github.com/pallets/markupsafe/blob/master/LICENSE.rst         |
| jsonpath_rw     | 1.3.0   | https://pypi.org/project/jsonpath-rw/ | https://github.com/kennknowles/python-jsonpath-rw/blob/master/LICENSE |
| jsonschema      | 2.5.1   | https://pypi.org/project/jsonschema/  | https://github.com/justinrainbow/json-schema/blob/master/LICENSE      |
| jsl             | 0.2.4   | https://pypi.org/project/jsl/         | https://github.com/aromanovich/jsl/blob/master/LICENSE                |
| functools32     | 0.2.4   | https://pypi.org/project/functools32/ | https://github.com/michilu/python-functools32/blob/master/LICENSE     |

## Contact

Contact Information: https://www.flashpoint-intel.com/contact-us

## Copyright

- (c) Flashpoint 2025
