# Dataminr Pulse for Splunk SOAR

Publisher: Dataminr <br>
Connector Version: 2.1.0 <br>
Product Vendor: Dataminr <br>
Product Name: Dataminr Pulse <br>
Minimum Product Version: 6.4.0

Pulse's AI-powered real-time intelligence integrates into Splunk SOAR workflows for faster detection and response

## Backward Compatibility

**Important Changes in This Version:**

This version of the app includes the following breaking changes that may require updates to existing playbooks and asset configuration:

- **Removed Action:** The "get related alerts" action has been removed from this version.
- **Removed Parameter:** The "query" parameter has been removed from asset configuration please update the on poll action accordingly.
- **Alert Artifacts Enhancement:** Alert artifacts now include all available values from the Alert API response.
- **Updated CEF Types:** The CEF types for URL artifacts and IP artifacts have been updated.

**Action Required:**

- Users must update their existing playbooks accordingly to maintain backward compatibility with these changes.

**NOTE:** If a user is upgrading the API version from v3 to v4, they must run test connectivity before executing any actions, otherwise the actions will fail.

## Explanation of the Asset Configuration Parameters

The asset configuration parameters affect 'test connectivity' and some other actions of the
application. The parameters related to test connectivity action are Client ID and Client Secret.

- **Client ID:** Client ID.
- **Client Secret:** Client Secret.
- **API Version:** API Version [v3 or v4].

## Explanation of the Actions' Parameters

- ### Test Connectivity

  This action will check the status of the Dataminr Pulse API endpoint and test connectivity of
  Splunk SOAR to the Dataminr Pulse instance. It can be used to generate a new token.\
  The action validates the provided asset configuration parameters. Based on the response from the
  API call, the appropriate success and failure message will be displayed when the action gets
  executed.

- ### On Poll

  This polling is to ingest the dynamic alerts of a particular watchlist that is configured on
  this asset. The user can provide the watchlist names to ingest the alerts from, and set the pagesize for polling. The user can also filter the results of the alert
  response, based on alert type.

  - **Manual Polling (POLL NOW)**

    - It will fetch the data when initiated, as per the corresponding asset configuration
      parameters. It does not store the last run context of the fetched data.

  - **Schedule/Interval Polling**

    - **Schedule Polling:** The ingestion action can be triggered at every specified time
      interval.
    - **Interval Polling:** The ingestion action can be triggered at every time range
      interval.
    - It will fetch the data every time, based on the stored context from the previous
      ingestion run. It stores the last run context of the fetched data. It starts fetching
      data based on the combination of the values of stored context for the previous ingestion
      run.
    - **NOTE:** If the user changes the configuration related to 'list names' parameter while the schedule/interval polling is running, then the next polling cycle will start fetching the latest data according to the updated configured parameters.

  <!-- -->

  - **Action Parameter: List names**

    - This parameter accepts comma-seperated names of the watchlist and if it is blank, it will ingest alerts from all the watchlists of the Dataminr Pulse account. Example: Company Cyber Alerts, Supply Chain Partner Cyber Alerts
    - If any one of the list names is invalid in the comma-separated string, the action will
      skip that list name and continue with the valid ones.
    - **NOTE:** The list names asset parameter is case-sensitive and the user must provide the
      exact case match of the watchlist

  - **Action Parameter: Page size for polling**

    - This parameter allows the user to limit the number of alerts in the response. It expects
      a numeric value as an input.
    - The default value is 40 for this parameter. The maximum 100 alerts can be fetched at a time. If the user provides a value greater than 100, then the on poll ingest 100 alerts only in single cycle.

  - **Action Parameter: Alert type**

    - This parameter allows additional filtering above list names. When any of
      "Alert, Urgent, Flash" is selected, it just ingests the alerts with specific alert type
      from the alerts fetched by the API with configured pagesize. If "All" is selected, all
      the types of alerts will be ingested.
    - **NOTE:** The severity of containers, Alert artifacts, and it's cyber artifacts is
      according to the alert type of the first ingested alert. If the alert type is not
      present in the API response of any alert, then by default the severity is set to
      'Alert'. If related alert artifacts are ingested in the same container and have
      different severity, then the higher severity level will be set for the respective
      container and the new Alert artifacts and its cyber artifacts will have the severity of
      it's alert only. Thus, the severity of already ingested container would update only when
      an alert of higher severity than the existing one is ingested in the same container.
    - The priority order of severity levels (high to low): Flash > Urgent > Alert

    ### Addition of Custom Severities on Ingested Data

    - This app needs to add custom severity levels based on alert type. Adding the severity in
      the Splunk SOAR platform is handled by the Dataminr Pulse app on running the Test
      Connectivity.

    - This app requires the proper app-level permissions to do so. Please note, for the
      Dataminr Pulse app to apply these custom severities to the Artifacts ingested via API
      queries using On Poll, you must make sure that the automation user you use has the
      correct permissions.

    - By default, the automation user is selected to run the Dataminr Pulse for Splunk SOAR
      ingestion action. (See **Asset Configuration** > **Asset Settings** > **Advanced** )
      The automation user does **NOT** have access to view or edit **System Settings** , which
      includes the permission to view the custom severities on your instance. This will cause
      your On Poll action to fail since your user cannot add the custom severities (Flash,
      Urgent, and Alert) on your instance.

    - In order to solve this problem, you must create a user of type **Automation** and assign
      this user a Role that has permissions to view or edit **System Settings** (
      **Administration** > **User Management** > **Users** **> + User** button on the top
      right corner). Then, choose this user in your Dataminr Pulse for Splunk SOAR **Asset
      Settings** under **Advanced** and you will be able to successfully apply custom
      severities to your ingested data.

      **Administration** > **User Management** > **Users** **> + User**
      [![](/app_resource/dataminrpulseforsplunksoar_8630b723-b317-4765-b923-5be5229c71d1/img/create_user.png)](/app_resource/dataminrpulseforsplunksoar_8630b723-b317-4765-b923-5be5229c71d1/img/create_user.png)

      **Administration** > **User Management** > **Roles & Permissions** **> + Role**
      [![](/app_resource/dataminrpulseforsplunksoar_8630b723-b317-4765-b923-5be5229c71d1/img/create_role.png)](/app_resource/dataminrpulseforsplunksoar_8630b723-b317-4765-b923-5be5229c71d1/img/create_role.png)

      **Asset Settings** > **Advanced**
      [![](/app_resource/dataminrpulseforsplunksoar_8630b723-b317-4765-b923-5be5229c71d1/img/asset_settings.png)](/app_resource/dataminrpulseforsplunksoar_8630b723-b317-4765-b923-5be5229c71d1/img/asset_settings.png)

      **NOTE:** If an error perists related to severity addition, it would be visible in logs
      while data ingestion. In this case, the user is advised to add the severity manually
      using these steps:

      - On the SOAR platform, navigate to **Administration->Event Settings->Severity**

      - Click on **ADD ITEM** and add severity type 'Flash' and select color as 'Red'. Click
        on **Done** .

      - Click on **ADD ITEM** and add severity type 'Urgent' and select color as 'Orange'.
        Click on **Done** .

      - Click on **ADD ITEM** and add severity type 'Alert' and select color as 'Yellow'.
        Click on **Done** .

      - **NOTE:** The severity types are case-sensitive hence, user is advised to add
        severity in **same case and same order** as mentioned above and as shown in below
        image.

        [![](img/add_severity.png)](img/add_severity.png)

- ### Get Lists

  Retrieves all the watchlists of user's account.\
  The action has no parameters.

- ### Get Alerts

  Fetch the details of the alerts from the Dataminr platform for the given List ID or query.

  - **Action Parameter: List ID**

    - This parameter accepts comma-seperated ids of the watchlist and it is required if we do
      not use the query parameter. Example: 1234567,1234568
    - If any one of the List IDs is invalid in the comma-separated string, the action will
      skip that List ID and continue with the valid ones.
    - Users can get the list ID by executing the "get lists" action.

  - **Action Parameter: Use asset configured lists**

    - This parameter is the optional boolean parameter. On marking it as true, the list id
      will be considered the one which is configured in the asset parameter.
    - If the user provides a list id and marks this boolean parameter as true, then priority
      will be given to list ids.

  - **Action Parameter: Query**

    - This parameter accepts the search value for all the watchlists and it is required if we
      do not use the query parameter. Example: ("Test" AND "Application") OR ("text" AND
      "json")
    - The query parameter is case-insensitive.
    - **Note:** If the user provides a list id and query both, then the action will return
      queried alerts from that particular watchlist only.

    **Note:** User need to provide either 'list id' in action parameter or valid 'list names' in
    asset configuration parameter or 'query' to fetch alerts.

  - **Action Parameter: Max Alerts**

    - This parameter allows the user to limit the number of alerts in the response. It expects
      a numeric value as an input.
    - The default value is 40 for this parameter.

  - **Action Parameter: From**

    - This parameter points to a cursor that you want any alerts after.

  - **Action Parameter: To**

    - This parameter points to a cursor that you want any alerts before.

    **Note:** Only one of "from" or "to" parameter can be included at a time.

  - **Examples:**

    - List the alert details with the List ID '1234567,1234568' and the query ("Test" AND
      "Application") OR ("text" AND "json") with max alerts as 10:
      - List ID = 1234567,1234568
      - Query = ("Test" AND "Application") OR ("text" AND "json")
      - Max Alerts = 10

- ### Get Alert Details

  Fetch the details of an alert from the Dataminr platform using either the Alert ID or an already ingested alert's Artifact ID. The fetched details are displayed in a custom view/UI.

  - **Action Parameter: Alert ID**

    - Accepts the ID of the Dataminr alert.
    - Required if the Artifact ID parameter is not provided.

  - **Action Parameter: Artifact ID**

    - Accepts the ID of the ingested artifact.
    - Required if the Alert ID parameter is not provided.
    - If both Alert ID and Artifact ID are provided, **Alert ID takes priority**.

  **Note:** You must provide either a valid Alert ID or Artifact ID to fetch alert details.

  - If using **Alert ID**, the connector makes an API call to fetch the alert details from Dataminr.
  - If using **Artifact ID**, the connector fetches the alert details from the already ingested data.

## Known Issues

> **Note:** The following issues occur only in the custom UI output when the get_alert_details action is executed with the Alert ID parameter and do not occur when using the Artifact ID parameter.

1. **Outdated or Missing IntelAgents and LiveBrief Content**:
   The IntelAgents and LiveBrief fields contain AI-generated content that can change over time as new alerts are ingested or as updates occur in Dataminr. When alert details are retrieved using the Alert ID, the information in these fields may appear outdated or missing. This behavior occurs because the Alert ID retrieves a snapshot that may not reflect the most recent updates. In contrast, using the Artifact ID returns the latest AI-generated content as stored in the Splunk SOAR environment, ensuring accuracy and consistency with current data.

1. **Not Receiving Lists and Topics**:
   When retrieving alert details using the Alert ID, the Lists and Topics fields may not be returned. This is expected behavior, as lists and topics are contextual information associated with the list, not the alert itself

1. **Differences in Alert Type**:
   The alert type (such as Flash, Urgent, or Alert) is determined by the context of the list in which the alert is ingested. When fetching an alert using the Alert ID, it is retrieved as a standalone alert that is not associated with any list; therefore, the alert type may appear as the default Alert. In contrast, alerts ingested via the on-poll mechanism will display the correct alert type based on the list context defined in the Dataminr account.

### Configuration variables

This table lists the configuration variables required to operate Dataminr Pulse for Splunk SOAR. These variables are specified when configuring a Dataminr Pulse asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**client_id** | required | string | Client ID |
**client_secret** | required | password | Client Secret |
**api_version** | required | string | API Version |
**list_names** | optional | string | List Names (comma-seperated values allowed). NOTE: If this field is blank, it will ingest alerts from all the lists of the Dataminr Pulse account |
**alert_type** | optional | string | Alert Type |
**page_size_for_polling** | optional | numeric | Page Size for polling |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[get lists](#action-get-lists) - Retrieve the list of all the watchlists <br>
[get alerts](#action-get-alerts) - Fetch the details of the alerts from the Dataminr platform for the given List ID or query <br>
[get alert details](#action-get-alert-details) - Get alert details from Dataminr using Dataminr Pulse API <br>
[on poll](#action-on-poll) - Ingest alerts from Dataminr using Dataminr Pulse API

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'get lists'

Retrieve the list of all the watchlists

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.companies.\*.id | string | | 0123456f1cdctest28f1a30d123456 |
action_result.data.\*.companies.\*.name | string | | Company name |
action_result.data.\*.description | string | | |
action_result.data.\*.id | numeric | | 123456 |
action_result.data.\*.name | string | | watchlist_name |
action_result.data.\*.properties.watchlistColor | string | | purple |
action_result.data.\*.type | string | | COMPANY |
action_result.summary | string | | 1 |
action_result.summary.total_results | numeric | | 1 |
action_result.message | string | | Total watchlists: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary.total_watchlists | numeric | | |
action_result.data.\*.subType | string | | CYBER_PHYSICAL |

## action: 'get alerts'

Fetch the details of the alerts from the Dataminr platform for the given List ID or query

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**list_id** | optional | List ID (comma-seperated values allowed) | string | `dataminrpulse list id` |
**use_asset_configured_lists** | optional | Use lists as configured in asset parameter | boolean | |
**query** | optional | Query | string | |
**max_alerts** | optional | Maximum number of alerts to fetch (max 100) | numeric | |
**from** | optional | From value | string | `dataminrpulse to cursor value` |
**to** | optional | To value | string | `dataminrpulse from cursor value` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.from | string | `dataminrpulse to cursor value` | testEncodedValue123456 |
action_result.parameter.list_id | string | `dataminrpulse list id` | 0123456 |
action_result.parameter.max_alerts | numeric | | 7 |
action_result.parameter.query | string | | text |
action_result.parameter.to | string | `dataminrpulse from cursor value` | testEncodedValue123456 |
action_result.parameter.use_asset_configured_lists | boolean | | True False |
action_result.data.\*.alerts.\*.alertId | string | | 1234567890-123456789-5 |
action_result.data.\*.alerts.\*.alertType.color | string | | FFBB05 |
action_result.data.\*.alerts.\*.alertType.id | string | | urgent |
action_result.data.\*.alerts.\*.alertType.name | string | | Urgent |
action_result.data.\*.alerts.\*.availableRelatedAlerts | numeric | | 7 |
action_result.data.\*.alerts.\*.caption | string | | Headline in caption |
action_result.data.\*.alerts.\*.categories.\*.id | string | | 124031 |
action_result.data.\*.alerts.\*.categories.\*.idStr | string | | 124031 |
action_result.data.\*.alerts.\*.categories.\*.name | string | | Cybersecurity - Crime and Malicious Activity |
action_result.data.\*.alerts.\*.categories.\*.path | string | | /TOPIC/EXT/CS/123456 |
action_result.data.\*.alerts.\*.categories.\*.requested | string | | true |
action_result.data.\*.alerts.\*.categories.\*.retired | boolean | | True False |
action_result.data.\*.alerts.\*.categories.\*.topicType | string | | category |
action_result.data.\*.alerts.\*.companies | string | | testHash123456 |
action_result.data.\*.alerts.\*.companies.\*.dm_bucket.\*.name | string | | Tech - Software & Services |
action_result.data.\*.alerts.\*.companies.\*.dm_sector.\*.id | string | | testHash123456 |
action_result.data.\*.alerts.\*.companies.\*.dm_sector.\*.name | string | | Software |
action_result.data.\*.alerts.\*.companies.\*.id | string | | testHash123456 |
action_result.data.\*.alerts.\*.companies.\*.idStr | string | | testHash123456 |
action_result.data.\*.alerts.\*.companies.\*.locations.\*.city | string | | City |
action_result.data.\*.alerts.\*.companies.\*.locations.\*.country | string | | COUNTRY |
action_result.data.\*.alerts.\*.companies.\*.locations.\*.postalCode | string | | 012345 |
action_result.data.\*.alerts.\*.companies.\*.locations.\*.state.name | string | | STATE |
action_result.data.\*.alerts.\*.companies.\*.locations.\*.state.symbol | string | | SYMBOL |
action_result.data.\*.alerts.\*.companies.\*.name | string | | COmpany name |
action_result.data.\*.alerts.\*.companies.\*.requested | string | | true |
action_result.data.\*.alerts.\*.companies.\*.retired | boolean | | True False |
action_result.data.\*.alerts.\*.companies.\*.ticker | string | | akam |
action_result.data.\*.alerts.\*.companies.\*.topicType | string | | company |
action_result.data.\*.alerts.\*.eventLocation.coordinates.\* | string | | [71.456, 72.45676] |
action_result.data.\*.alerts.\*.eventLocation.name | string | | Location |
action_result.data.\*.alerts.\*.eventLocation.places.\* | string | | testHash123456 |
action_result.data.\*.alerts.\*.eventLocation.probability | numeric | | 1 |
action_result.data.\*.alerts.\*.eventLocation.radius | numeric | | 123.456 |
action_result.data.\*.alerts.\*.eventMapLargeURL | string | | https://api.domain.com/value/1/map?size=540x124&center=52.132633,5.291265999999999&zoom=9&markers=color:yellow%7Csize:small%7C52.132633,5.291265999999999&key=kh0qvJ4wltQL-LPESkURRYIaE_P6qwD33dBL95Jc&signature=PESTO9XyjAb7pPuEoRQL_T3X_2s= |
action_result.data.\*.alerts.\*.eventMapSmallURL | string | | https://api.domain.com/value/1/map?size=124x124&center=52.132633,5.291265999999999&zoom=9&markers=color:yellow%7Csize:small%7C52.132633,5.291265999999999&key=kh0qvJ4wltQL-LPESkURRYIaE_P6qwD33dBL95Jc&signature=wDeXt1LM_6WtRTS99j5Wbidijxs= |
action_result.data.\*.alerts.\*.eventTime | numeric | | 1234567890123 |
action_result.data.\*.alerts.\*.eventVolume | numeric | | 0 |
action_result.data.\*.alerts.\*.expandAlertURL | string | | https://app.domain.com/#alertDetail/10/testAlert-123456789-3 |
action_result.data.\*.alerts.\*.expandMapURL | string | | https://app.domain.com/#map-popup2/{"search":{"date":{"start":1234567890123,"end":1234567890123,"isRealtime":false},"geo":{"bounds":{"north":53.132633,"east":6.291265999999999,"south":51.132633,"west":4.291265999999999},"center":{"lat":52.132633,"lng":5.291265999999999},"zoom":10}},"map":{"mapType":"ROADMAP","shouldAskDefaultLocation":false,"visited":[]}} |
action_result.data.\*.alerts.\*.headerColor | string | | FFFFAD |
action_result.data.\*.alerts.\*.headerLabel | string | | Urgent |
action_result.data.\*.alerts.\*.metadata.cyber.URLs.\* | string | | https://www.domain.com |
action_result.data.\*.alerts.\*.metadata.cyber.addresses.\*.ip | string | | 8.8.8.8 |
action_result.data.\*.alerts.\*.metadata.cyber.addresses.\*.port | string | | 7120 |
action_result.data.\*.alerts.\*.metadata.cyber.addresses.\*.version | string | | v4 |
action_result.data.\*.alerts.\*.metadata.cyber.asOrgs.\*.asOrg | string | | company |
action_result.data.\*.alerts.\*.metadata.cyber.asOrgs.\*.asn | string | | AS0123 |
action_result.data.\*.alerts.\*.metadata.cyber.asns.\* | string | | AS0123 |
action_result.data.\*.alerts.\*.metadata.cyber.hashValues.\*.type | string | | md5 |
action_result.data.\*.alerts.\*.metadata.cyber.hashValues.\*.value | string | | testHash123456 |
action_result.data.\*.alerts.\*.metadata.cyber.hashes.\* | string | | testHash123456 |
action_result.data.\*.alerts.\*.metadata.cyber.malwares.\* | string | | malware |
action_result.data.\*.alerts.\*.metadata.cyber.orgs.\* | string | | Organization |
action_result.data.\*.alerts.\*.metadata.cyber.products.\* | string | | products |
action_result.data.\*.alerts.\*.metadata.cyber.threats.\* | string | | threat |
action_result.data.\*.alerts.\*.metadata.cyber.vulnerabilities.\*.cvss | string | | 1 |
action_result.data.\*.alerts.\*.metadata.cyber.vulnerabilities.\*.exploitPocLinks.\* | string | | https://www.domain.com |
action_result.data.\*.alerts.\*.metadata.cyber.vulnerabilities.\*.id | string | | CVE-0123-4567 |
action_result.data.\*.alerts.\*.metadata.cyber.vulnerabilities.\*.products.\*.productName | string | | product name |
action_result.data.\*.alerts.\*.metadata.cyber.vulnerabilities.\*.products.\*.productVendor | string | | product vendor |
action_result.data.\*.alerts.\*.metadata.cyber.vulnerabilities.\*.products.\*.productVersion | string | | * |
action_result.data.\*.alerts.\*.parentAlertId | string | | 0123456-0123456789-0 |
action_result.data.\*.alerts.\*.post.languages.\*.lang | string | | en |
action_result.data.\*.alerts.\*.post.languages.\*.position | numeric | | 0 |
action_result.data.\*.alerts.\*.post.link | string | | https://domain.com/event/301329 |
action_result.data.\*.alerts.\*.post.media.\*.description | string | | https://domain.com/user/status/1234567895/photo/1 |
action_result.data.\*.alerts.\*.post.media.\*.display_url | string | | pic.domain.com/Vj0y85hDyn |
action_result.data.\*.alerts.\*.post.media.\*.media_url | string | | http://pbs.domain.com/media/FizHmhBX0AA0kph.jpg |
action_result.data.\*.alerts.\*.post.media.\*.sizes.large.h | numeric | | 847 |
action_result.data.\*.alerts.\*.post.media.\*.sizes.large.resize | string | | fit |
action_result.data.\*.alerts.\*.post.media.\*.sizes.large.w | numeric | | 1920 |
action_result.data.\*.alerts.\*.post.media.\*.sizes.medium.h | numeric | | 529 |
action_result.data.\*.alerts.\*.post.media.\*.sizes.medium.resize | string | | fit |
action_result.data.\*.alerts.\*.post.media.\*.sizes.medium.w | numeric | | 1200 |
action_result.data.\*.alerts.\*.post.media.\*.sizes.small.h | numeric | | 300 |
action_result.data.\*.alerts.\*.post.media.\*.sizes.small.resize | string | | fit |
action_result.data.\*.alerts.\*.post.media.\*.sizes.small.w | numeric | | 680 |
action_result.data.\*.alerts.\*.post.media.\*.sizes.thumb.h | numeric | | 150 |
action_result.data.\*.alerts.\*.post.media.\*.sizes.thumb.resize | string | | crop |
action_result.data.\*.alerts.\*.post.media.\*.sizes.thumb.w | numeric | | 150 |
action_result.data.\*.alerts.\*.post.media.\*.source | string | | source |
action_result.data.\*.alerts.\*.post.media.\*.type | string | | photo |
action_result.data.\*.alerts.\*.post.media.\*.url | string | | http://pbs.domain.com/media/FizHmhBX0AA0kph.jpg |
action_result.data.\*.alerts.\*.post.media.\*.video_info.duration_millis | numeric | | 139067 |
action_result.data.\*.alerts.\*.post.media.\*.video_info.variants.\*.bitrate | numeric | | 288000 |
action_result.data.\*.alerts.\*.post.media.\*.video_info.variants.\*.content_type | string | | video/mp4 |
action_result.data.\*.alerts.\*.post.media.\*.video_info.variants.\*.url | string | | https://video.domain.com/vid/1234567895/vid/480x270/sN94SuRcfAuHCd7E.mp4?tag=16 |
action_result.data.\*.alerts.\*.post.text | string | | https://domain.me/user/23368 |
action_result.data.\*.alerts.\*.post.timestamp | numeric | | 1234567890123 |
action_result.data.\*.alerts.\*.post.translatedText | string | | https://domain.me/user/23368 |
action_result.data.\*.alerts.\*.publisherCategory.color | string | | A24512 |
action_result.data.\*.alerts.\*.publisherCategory.id | string | | chatter |
action_result.data.\*.alerts.\*.publisherCategory.name | string | | Chatter |
action_result.data.\*.alerts.\*.publisherCategory.shortName | string | | CTR |
action_result.data.\*.alerts.\*.relatedTerms.\*.text | string | | akamai |
action_result.data.\*.alerts.\*.relatedTerms.\*.url | string | | https://app.domain.com/search?query=testTerm&location=testLocation |
action_result.data.\*.alerts.\*.relatedTermsQueryURL | string | | https://app.domain.com/search?query=testTerms&location=testLocation |
action_result.data.\*.alerts.\*.sectors.\*.id | string | | testHash123456 |
action_result.data.\*.alerts.\*.sectors.\*.idStr | string | | testHash123456 |
action_result.data.\*.alerts.\*.sectors.\*.name | string | | Software |
action_result.data.\*.alerts.\*.sectors.\*.retired | boolean | | True False |
action_result.data.\*.alerts.\*.sectors.\*.topicType | string | | dm_sector |
action_result.data.\*.alerts.\*.source.displayName | string | | source name |
action_result.data.\*.alerts.\*.source.entityName | string | | entity name |
action_result.data.\*.alerts.\*.source.link | string | | https://audio.domain.com/prod/2023/01/10/1234567890.123456ch0segment1.wav |
action_result.data.\*.alerts.\*.source.verified | boolean | | True False |
action_result.data.\*.alerts.\*.subCaption.bullets.content | string | | IP: 0.0.0.0 ASN: AS0000 ASN HOST: Company COUNTRY: Country CITY: City TAGS: Tag FIRST SEEN: 2018-11-14 |
action_result.data.\*.alerts.\*.subCaption.bullets.media | string | | |
action_result.data.\*.alerts.\*.subCaption.bullets.source | string | | According to grey noise |
action_result.data.\*.alerts.\*.watchlistsMatchedByType.\*.id | string | | 0123456 |
action_result.data.\*.alerts.\*.watchlistsMatchedByType.\*.locationGroups.\*.id | string | | 4019 |
action_result.data.\*.alerts.\*.watchlistsMatchedByType.\*.locationGroups.\*.locations.\*.id | string | | 771347 |
action_result.data.\*.alerts.\*.watchlistsMatchedByType.\*.locationGroups.\*.locations.\*.lat | numeric | | 37.7687302 |
action_result.data.\*.alerts.\*.watchlistsMatchedByType.\*.locationGroups.\*.locations.\*.lng | numeric | | -122.3884732 |
action_result.data.\*.alerts.\*.watchlistsMatchedByType.\*.locationGroups.\*.locations.\*.name | string | | location name |
action_result.data.\*.alerts.\*.watchlistsMatchedByType.\*.locationGroups.\*.name | string | | location name |
action_result.data.\*.alerts.\*.watchlistsMatchedByType.\*.name | string | | watchlist_name |
action_result.data.\*.alerts.\*.watchlistsMatchedByType.\*.type | string | | topics |
action_result.data.\*.alerts.\*.watchlistsMatchedByType.\*.userProperties.omnilist | string | | true |
action_result.data.\*.alerts.\*.watchlistsMatchedByType.\*.userProperties.uiListType | string | | CYBER |
action_result.data.\*.alerts.\*.watchlistsMatchedByType.\*.userProperties.watchlistColor | string | | purple |
action_result.data.\*.from | string | | testEncodedValue123456 |
action_result.data.\*.to | string | | H4sIAAAAAAAAAFWQ3ytDcRyGz7u+rSVJkiRJkiS0JEkSsiVJkiRJVltrpU1z/oCRpAmznTRr7QLx+V6oadygtVwsLZdrzWLNj7QbO5QkY5xbt8/F87y9KqYVDWazydg3Z7KLCy3zBrtoES02q8k4+/BBGAsGOOoPsgR9wsUxGnuRUew7kJj6NUdouP2VmCZ+JqMkHSNMBx4Jvf4vwkxgTUa5VCBo3SHCQPKe0Ll7QZjcVnyVqUOO9o14DhVnL4TWyLnEVK4tju6VIw8runwjNAeXOWqyGcK4b09GafqK0J/d4RhJ3BGm9k8lxoJHHFV+B8dE+IbQ41DidavPHIPORw8TvDKh2unm6Cp8Etrcmxwd10nCcCRKqD1RpjWGFdb0FcmhLKoIhoS2f1dYbVad0SLa7BbDXPHy8bdO85Bf0hdlKK9j3vUnH4T3H4deHY8t6lWCkJBShZDhD0tWiJtPAQAA |
action_result.summary | string | | 1 |
action_result.summary.total_results | numeric | | 1 |
action_result.message | string | | Total related alerts: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.\*.alertId | string | | testAlert-123456789-4 |
action_result.data.\*.\*.headline | string | | Road closed near Jhaverchand Meghani Road and Memco Road in Ahmedabad, India: Sensor via HERE WeGo. |
action_result.data.\*.\*.alertType.name | string | | Alert |
action_result.data.\*.\*.publicPost.href | string | | https://r.dataminr.com/testUrl123456789 |
action_result.data.\*.\*.publicPost.timestamp | string | | 2025-08-13T12:15:30.011Z |
action_result.data.\*.\*.alertTopics.\*.id | string | | 853063 |
action_result.data.\*.\*.alertTopics.\*.name | string | | Transportation - Roadways - Logistics |
action_result.data.\*.\*.listsMatched.\*.id | string | | 4774397 |
action_result.data.\*.\*.listsMatched.\*.name | string | | CDS Sample Cyber Physical |
action_result.data.\*.\*.listsMatched.\*.subType | string | | CYBER_PHYSICAL |
action_result.data.\*.\*.alertTimestamp | string | | 2025-08-13T12:16:31.164Z |
action_result.data.\*.\*.dataminrAlertUrl | string | | https://app.dataminr.com/#alertDetail/5/testAlert-123456789-4 |
action_result.data.\*.\*.estimatedEventLocation.name | string | | Memco Road, Ahmedabad, India |
action_result.data.\*.\*.estimatedEventLocation.probabilityRadius | numeric | | 0.1 |
action_result.data.\*.\*.publicPost.media.\*.href | string | | https://video.twimg.com/amplify_video/1234567895/vid/avc1/640x360/HR9Rg2TWusThIPso.mp4 |
action_result.data.\*.\*.publicPost.media.\*.type | string | | video |
action_result.summary.total_alerts | numeric | | 40 |
action_result.data.\*.\*.metadata.cyber.URL.\*.name | string | | img.shdell.net. |
action_result.data.\*.\*.alertSectors.\*.name | string | | Oil & Gas |
action_result.data.\*.\*.alertCompanies.\*.name | string | | Royal Dutch Shell plc |
action_result.data.\*.\*.metadata.cyber.asOrgs.\*.asn | string | | AS16509 |
action_result.data.\*.\*.metadata.cyber.asOrgs.\*.asOrg | string | | Amazon Technologies Inc. |
action_result.data.\*.\*.metadata.cyber.addresses.\*.ip | string | | 13.248.169.48 |
action_result.data.\*.\*.metadata.cyber.addresses.\*.port | numeric | | 80 |
action_result.data.\*.\*.metadata.cyber.addresses.\*.type | string | | |
action_result.data.\*.\*.metadata.cyber.addresses.\*.version | string | | |
action_result.data.\*.\*.subHeadline.title | string | | Gab |
action_result.data.\*.\*.intelAgents.\*.summary.\*.title | string | | Potential domain impersonations on apex domain ushell[.]com |
action_result.data.\*.\*.intelAgents.\*.version | string | | current |
action_result.data.\*.\*.intelAgents.\*.timestamp | string | | 2025-08-06T00:34:24.085Z |
action_result.data.\*.\*.metadata.cyber.malware.\*.name | string | | keylogger |
action_result.data.\*.\*.intelAgents.\*.discoveredEntities.\*.name | string | | Money Message |
action_result.data.\*.\*.intelAgents.\*.discoveredEntities.\*.type | string | | malware |
action_result.data.\*.\*.intelAgents.\*.discoveredEntities.\*.summary | string | | A new ransomware gang hitting companies in worldwide firstly spotted by Zscaler. |
action_result.data.\*.\*.intelAgents.\*.discoveredEntities.\*.affectedOperatingSystems | string | | win |
action_result.data.\*.alerts.\*.headline | string | | Road closed near Unnamed Road in Ahmedabad, India: Sensor via HERE WeGo. |
action_result.data.\*.alerts.\*.publicPost.href | string | | https://r.dataminr.com/testUrl123456789 |
action_result.data.\*.alerts.\*.publicPost.timestamp | string | | 2025-09-01T11:45:29.259Z |
action_result.data.\*.alerts.\*.alertTopics.\*.id | string | | 853063 |
action_result.data.\*.alerts.\*.alertTopics.\*.name | string | | Transportation - Roadways - Logistics |
action_result.data.\*.alerts.\*.listsMatched.\*.id | string | | 4774397 |
action_result.data.\*.alerts.\*.listsMatched.\*.name | string | | CDS Sample Cyber Physical |
action_result.data.\*.alerts.\*.listsMatched.\*.subType | string | | CYBER_PHYSICAL |
action_result.data.\*.alerts.\*.alertTimestamp | string | | 2025-09-01T11:45:46.008Z |
action_result.data.\*.alerts.\*.dataminrAlertUrl | string | | https://app.dataminr.com/#alertDetail/5/testAlert-123456789-5 |
action_result.data.\*.alerts.\*.alertReferenceTerms.\*.text | string | | road |
action_result.data.\*.alerts.\*.estimatedEventLocation.name | string | | Unnamed Road, Ahmedabad, India |
action_result.data.\*.alerts.\*.estimatedEventLocation.probabilityRadius | numeric | | 0.1 |
action_result.data.\*.nextPage | string | | H4sIAAAAAAAA/2NiMShJTE9PTXHMSS0qKdYtSCwqySzJzM9LTUl48/AjB8Oq5W1sOk+utbFZHOs8yyby7EIbm92cJW1sct9enGHj67rSyhY043wbW8SMZ21sWg+WtLKFTFvaxibT1djOZvRpZRubXsv6Nja3Safa2aT+NLSxWW242samduRLG5tfy+x2No0Z3z5wcN2Z1sYmsWbvGTahEy/a2Wym3PzIwdLz/Swbz5+XbWxKTTvb2VSuAHWY/Prdwhbz7lcrW9yqPW1sUSuetLEFXNvSxubV96KVzeXX/E8cTDO2n2UTO9PRzmbwCugCswfv2tk8Lu39xMHx72Ybm0PbozY2p1VA23yaprSzhZ2Z84mDbcfks2wCCza3sSkwGKEERV5+nmtKZkl+UWZiDs+GCZNqmd6c761lOXfo10VGhlfPptdynZg8sZbtw7IJtRwMDBtuHL+4IA0AhFLw508BAAA= |
action_result.data.\*.previousPage | string | | H4sIAAAAAAAA/2NiMShJTE9PTXHMSS0qKdYtSCwqySzJzM9LTUl48/AjB8Oq5W1sOk+utbFZHOs8yyby7EIbm92cJW1sct9enGHj67rSyhY041kbm9aDJa1sIdOWtrHJdDW2sxl9WtnGpteyvo3NbdKpdjapPw1tbFYbrraxqR350sbm1zK7nU1jxrcPHFx3prWxSazZe4ZN6MSLdjabKTc/crD0fD/LxvPnZRubUtPOdjaVK0AdJr9+t7DFvPvVyha3ak8bW9SKJ21sAde2tLF59b1oZXP5Nf8TB9OM7WfZxM50tLMZvAK6wOzBu3Y2j0t7P3Fw/LvZxuYw4XgbW0TbozY2p1VAK32aprSzhZ2Z84mDbcfks2wCCza3sSkwGKEERV5+nmtKZkl+UWZiDs+GCZNqmd6c761lOXfo10VGhlfPptdynZg8sZbtw7IJtRwMDDPmzd+9IA0AFWwipk8BAAA= |
action_result.summary.api_version_used | string | | v4 |
action_result.data.\*.alerts.\*.post.media.\*.isSafe | boolean | | True False |
action_result.data.\*.alerts.\*.metadata.cyber.URL.\*.name | string | | level.com |
action_result.data.\*.alerts.\*.watchlistsMatchedByType.\*.hasAssetMatches | boolean | | True False |
action_result.data.\*.alerts.\*.metadata.cyber.malware.\*.name | string | | AsyncRAT |
action_result.data.\*.alerts.\*.metadata.cyber.URL.\*.type | string | | |
action_result.data.\*.alerts.\*.metadata.cyber.threatActors.\*.name | string | | NoName05716 |

## action: 'get alert details'

Get alert details from Dataminr using Dataminr Pulse API

Type: **investigate** <br>
Read only: **True**

This action retrieves detailed alert information from Dataminr via the Dataminr Pulse API. You must provide either an Alert ID or an Artifact ID; if both are supplied, the Alert ID takes precedence. The response is returned in a rich, custom view format for better readability. This action is compatible only with API version v4 and will return a clear, user-friendly error message if executed with API version v3.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**alert_id** | optional | Alert ID | string | `dataminrpulse alert id` |
**artifact_id** | optional | Artifact ID | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.alert_id | string | | testAlert-123456789-1 |
action_result.status | string | | success failed |
action_result.message | string | | Alert details fetched successfully |
action_result.data.\*.total_objects | numeric | | 1 |
action_result.data.\*.total_objects_successful | numeric | | 1 |
action_result.data.\*.alerts.\*.id | string | | testAlert-123456789-1 |
action_result.data.\*.alertId | string | | testAlert-123456789-2 |
action_result.data.\*.headline | string | | Protest mentioning Palestinian territories planned for August 22 at 17:00 in Sabarmati, Gujarat, India: Local Source via X. |
action_result.data.\*.publicPost.href | string | | https://r.domain.com/testUrl123456 |
action_result.data.\*.publicPost.media.\*.href | string | | https://pbs.domain.com/media/testImage123456.jpg |
action_result.data.\*.publicPost.media.\*.type | string | | photo |
action_result.data.\*.publicPost.timestamp | string | | 2025-01-01T12:00:00.000Z |
action_result.data.\*.alertTimestamp | string | | 2025-01-01T12:00:00.000Z |
action_result.data.\*.dataminrAlertUrl | string | | https://app.dataminr.com/#alertDetail/5/testAlert-123456789-2 |
action_result.data.\*.estimatedEventLocation.name | string | | Sabarmati, Ahmedabad, Gujarat, India |
action_result.data.\*.estimatedEventLocation.probabilityRadius | numeric | | 2.123456 |
action_result.data.\*.metadata.cyber.vulnerabilities.\*.id | string | | CVE-2025-53779 |
action_result.data.\*.metadata.cyber.vulnerabilities.\*.cvss | numeric | | 7.2 |
action_result.data.\*.metadata.cyber.vulnerabilities.\*.products.\*.productName | string | | windows_10 |
action_result.data.\*.metadata.cyber.vulnerabilities.\*.products.\*.productVendor | string | | microsoft |
action_result.data.\*.metadata.cyber.vulnerabilities.\*.products.\*.productVersion | string | | |
action_result.data.\*.intelAgents.\*.summary.\*.title | string | | Background and Exploit Status |
action_result.data.\*.intelAgents.\*.version | string | | current |
action_result.data.\*.intelAgents.\*.timestamp | string | | 2025-08-13T06:48:48.342Z |
action_result.data.\*.intelAgents.\*.discoveredEntities.\*.cvss | numeric | | 7.2 |
action_result.data.\*.intelAgents.\*.discoveredEntities.\*.name | string | | CVE-2025-53779 |
action_result.data.\*.intelAgents.\*.discoveredEntities.\*.type | string | | vulnerability |
action_result.data.\*.intelAgents.\*.discoveredEntities.\*.summary | string | | Relative path traversal in Windows Kerberos allows an authorized attacker to elevate privileges over a network. |
action_result.data.\*.intelAgents.\*.discoveredEntities.\*.products.\*.productName | string | | windows_server_2025 |
action_result.data.\*.intelAgents.\*.discoveredEntities.\*.products.\*.productVendor | string | | microsoft |
action_result.data.\*.intelAgents.\*.discoveredEntities.\*.epssScore | numeric | | 0.1 |
action_result.data.\*.subHeadline.title | string | | According to Soft Zone |
action_result.data.\*.alertSectors.\*.name | string | | Software |
action_result.data.\*.alertCompanies.\*.name | string | | Microsoft Corporation |
action_result.data.\*.alertType.name | string | | Alert |
action_result.data.\*.alertReferenceTerms.\*.text | string | | road |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary.api_version_used | string | | v4 |
action_result.data.\*.metadata.\*.cyber.URL.\*.name | string | | level.com |
action_result.data.\*.metadata.\*.cyber.threatActors.\*.name | string | | Desolator |
action_result.data.\*.liveBrief.\*.summary | string | | The NSA has said that malicious activity outlined in its advisory partially overlaps with China-affiliated APT Salt Typhoon, with some activities linked to multiple China-based entities. The UK NCSC and international partners have now linked three China-based companies to Salt Typhoon campaigns targeting foreign governments and critical networks. The FBI has said that China-affiliated APT Salt Typhoon compromised at least 200 US organizations and targeted companies in 80 countries. |
action_result.data.\*.liveBrief.\*.version | string | | prior |
action_result.data.\*.liveBrief.\*.timestamp | string | | 2025-08-27T19:57:53.853Z |
action_result.data.\*.intelAgents.\*.discoveredEntities.\*.ttps.\*.tacticName | string | | Resource Development |
action_result.data.\*.intelAgents.\*.discoveredEntities.\*.ttps.\*.techniqueId | string | | T1587.001 |
action_result.data.\*.intelAgents.\*.discoveredEntities.\*.ttps.\*.techniqueName | string | | Malware |
action_result.data.\*.intelAgents.\*.discoveredEntities.\*.ttps.\*.topLevelTechniqueName | string | | Develop Capabilities |
action_result.data.\*.intelAgents.\*.discoveredEntities.\*.countryOfOrigin | string | | CN |
action_result.data.\*.linkedAlerts.\*.count | numeric | | 5 |
action_result.data.\*.linkedAlerts.\*.parentAlertId | string | | testAlert-123456789-6 |
action_result.parameter.artifact_id | string | | |

## action: 'on poll'

Ingest alerts from Dataminr using Dataminr Pulse API

Type: **ingest** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_time** | optional | Parameter Ignored in this app | numeric | |
**end_time** | optional | Parameter Ignored in this app | numeric | |
**container_id** | optional | Parameter Ignored in this app | string | |
**container_count** | optional | Parameter Ignored in this app | numeric | |
**artifact_count** | optional | Parameter Ignored in this app | numeric | |

#### Action Output

No Output

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2026 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
