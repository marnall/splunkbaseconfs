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
