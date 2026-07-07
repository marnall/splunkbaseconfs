# Chronicle

Publisher: Splunk \
Connector Version: 2.2.9 \
Product Vendor: Google Cloud \
Product Name: Chronicle \
Minimum Product Version: 6.3.0

This app enables the end-user to search, analyze, and ingest the enterprise security data stored in the Chronicle using investigative, reputation, and ingestion actions

## Explanation of the Asset Configuration Parameters

The asset configuration parameters affect [test connectivity] and all the other actions of the
application. Below are the explanation and usage of all these parameters.

- **Base URL:** The URL used to connect with the Chronicle server. It represents the Chronicle
  platform's API base URL. Example: https://backstory.googleapis.com
  The user should not include the API version in this parameter as it would get overridden with
  the specific API versions for the respective actions. The API versions used for each of the
  actions are specified in [<u>this section</u>](#api-versions-used-in-the-actions) .
- **Contents of Service Account JSON File:** This file contents will be used to authenticate with
  the Google APIs.
- **Scope:** ["https://www.googleapis.com/auth/chronicle-backstory"]
- **Number of Retries:** The value of this parameter defines the number of attempts for which the
  action will keep on retrying if the Chronicle API continuously returns the HTTP 429
  (RESOURCE_EXHAUSTED) error. If the error gets eliminated before the number of retries gets
  exhausted, then, the action execution will continue along its workflow with the next set of API
  calls and if the error is still persistent and all the number of retries are exhausted, then,
  the action will fail with the latest error message being displayed.
- **Retry Wait Period (in seconds):** The value of this parameter defines the waiting period in
  seconds for which to hold the current execution of the action on receiving the HTTP 429
  (RESOURCE_EXHAUSTED) error and then, retry the same API call after the waiting period is
  exhausted. This ensures that the integration provides a mechanism of attempting to overcome the
  HTTP 429 (RESOURCE_EXHAUSTED) error.

## Service account

This app requires a pre-configured service account to operate. Please follow the procedure outlined
at [<u>this link</u>](https://support.google.com/a/answer/7378726?hl=en) to create a service
account. At the end of the creation process, the admin console should ask you to save the config as
a JSON file. Copy the contents of the JSON file in the clipboard and paste it as the value of the
"Contents of Service Account JSON file" asset configuration parameter.
**Or else**
Your Customer Experience Engineer (CEE) will provide you with a [<u>Google Developer Service Account
Credential</u>](https://developers.google.com/identity/protocols/oauth2#serviceaccount) to enable
the Google API client to communicate with the Chronicle API. Copy the contents of the JSON file in
the clipboard and paste it as the value of the "Contents of Service Account JSON file" asset
configuration parameter.

**For more details visit the below-listed links:**

- [<u>Creating a service
  account</u>](https://developers.google.com/identity/protocols/oauth2/service-account#creatinganaccount)
- [<u>Understanding service
  accounts</u>](https://cloud.google.com/iam/docs/understanding-service-accounts)

## API Versions used in the actions

- ### Search API
  - This API uses /v1 endpoint. The actions using this API are as follows:
    - List Alerts
    - List Assets
    - List Events
    - List IoCs
    - List IoC Details
    - Domain Reputation
    - IP Reputation
- ### Detection Engine API
  - This API uses /v2 endpoint. The actions using this API are as follows:
    - List Rules
    - List Detections

## Explanation of the Chronicle Actions' Parameters

- ### Test Connectivity (Action Workflow Details)
  - This action will test the connectivity of the Phantom server to the Chronicle instance by
    making an initial API call to the ListIoCs endpoint using the provided asset configuration
    parameters.

  - The action validates the provided asset configuration parameters. Based on the API call
    response, the appropriate success and failure message will be displayed when the action gets
    executed.

  - **<u>Note:</u>**

    - There are a total of 8 reputation-related asset configuration parameters and 7 on poll
      action-related asset configuration parameters that are not validated while running test
      connectivity for optimum performance and are only validated in their respective actions.
      You can find more details about these parameters in their respective section of the
      action.
- ### List Assets
  - **<u>Action Parameter:</u> Artifact Indicator**

    - The Artifact Indicator parameter enables search by selecting anyone from given artifact
      indicators.

    - Valid Values:

      - Domain Name
      - Destination IP Address
      - MD5 File Hash
      - SHA1 File Hash
      - SHA256 File Hash

  - **<u>Action Parameter:</u> Value**

    - The user can provide artifact value into the Value action parameter.

  - **<u>Action Parameter:</u> Time Range**

    - This parameter will be used for specifying the time range of the search.
    - User can provide time using this '\<digit>\<d/h/m/s>' time format. Here, d = Day, h =
      Hour, m = Minutes, and s = Seconds.
    - **Note:** The Start time and End time will be calculated using the specified time range.
      The end time will be present time and according to the specified time range, the start
      time will be calculated for the search.

  - **<u>Action Parameters:</u> Start Time and End Time**

    - These parameters will be used for specifying the time range of the search.
    - Users can provide time using this 'yyyy-MM-ddTHH:mm:ssZ' time format. Here, y=Year,
      M=Month, d=Day, H=Hour, m=Minutes, s=Seconds.
    - **Note:** The number of returned assets can be reduced over a shorter period using these
      parameters.

  - **<u>Action Parameter:</u> Limit**

    - This parameter is used to limit the number of assets results to return.
    - The user can specify between 1 and 10,000. The default value is 10,000. If the limit is
      not provided, it will fetch by default 10,000 assets results.

  - **<u>Note:</u>**

    - If the user doesn't provide any of the time-related action parameters, the action will
      perform a search for the last three days.
    - If the user provides [Time Range] and other time-related action parameters, the
      priority will be given to the [Time Range] action parameter and the search will be
      performed according to its given value.

  - **Example:**

    - Get a list of assets that accessed the specified domain artifact
      - Artifact Indicator = Domain Name
      - Value = wp.com
      - Start Time = 1970-01-01T00:00:00Z
      - End Time = 1970-01-10T00:00:00Z
    - Fetch assets results for the IP artifact for the last three days (Here, the Present time
      is 2020-01-03T00:00:00Z)
      - Artifact Indicator = Destination IP Address
      - Value = 216.58.217.78
      - Time Range = 3d
    - Filtering assets results based on the specifying time range for the IP artifact
      - Artifact Indicator = Destination IP Address
      - Value = 216.58.217.78
      - Start Time = 1970-01-01T00:00:00Z
      - End Time = 1970-01-05T00:00:00Z
- ### List Alerts
  - **<u>Action Parameter:</u> Time Range**

    - This parameter will be used for specifying the time range of the search.
    - User can provide time using this '\<digit>\<d/h/m/s>' time format. Here, d = Day, h =
      Hour, m = Minutes, and s = Seconds.
    - **Note:** The Start time and End time will be calculated using the specified time range.
      The end time will be present time and according to the specified time range, the start
      time will be calculated for the search.

  - **<u>Action Parameters:</u> Start Time and End Time**

    - These parameters will be used for specifying the time range of the search.
    - Users can provide time using this 'yyyy-MM-ddTHH:mm:ssZ' time format. Here, y=Year,
      M=Month, d=Day, H=Hour, m=Minutes, s=Seconds.
    - **Note:** The number of returned alerts can be reduced over a shorter period using these
      parameters.

  - **<u>Action Parameter:</u> Limit**

    - This parameter is used to limit the number of alerts results to return.
    - The user can specify between 1 and 10,000. The default value is 10,000. If the limit is
      not provided, it will fetch by default 10,000 alerts results.

  - **<u>Action Parameter:</u> Alert Type**

    - This parameter will be used to fetch alerts of a particular type. Its default value is
      'All'.

    - Valid Values:

      - Asset Alerts
      - User Alerts
      - All

  - **<u>Note:</u>**

    - If the user doesn't provide any of the time-related action parameters, the action will
      perform a search for the last three days.
    - If the user provides [Time Range] and other time-related action parameters, the
      priority will be given to the [Time Range] action parameter and the search will be
      performed according to its given value.
    - If the Alert Type is selected to 'All' then, based on the selected type, the limit
      parameter will result in fetching those many (or less if not that many asset alerts
      present) asset alerts as well as those many (or less if not that many user alerts
      present) user alerts in the output. But due to the known API limitation, the results
      returned by the API for the asset and user alerts are not consistent with the provided
      page_size attribute in the API call.
    - Due to the above-mentioned API limitation, the number of asset alerts being returned
      (when the selected Alert Type is 'Asset Alerts' or 'All') and the number of user alerts
      being returned (when the selected Alert Type is 'User Alerts' or 'All') will be
      inconsistent with the Limit action parameter, i.e., the user can receive less or more
      number of alerts than the specified limit.

  - **Example:**

    - Get a list of security alerts for the last three days (Here, the Present time is
      2020-01-03T00:00:00Z)
      - Time Range= 3d
    - Get a list of security alerts for the specified time
      - Start Time= 2019-01-01T00:00:00Z
      - End Time= 2020-01-01T00:00:00Z
    - Get a list of all alerts for the default time range, i.e., last three days
      - Alert Type= All
      - Limit= 50
- ### List Events
  - **<u>Action Parameter:</u> Asset Indicator**

    - The Asset Indicator parameter enables search by selecting anyone from given asset
      indicators.

    - Valid Values:

      - Hostname
      - Asset IP Address
      - MAC Address
      - Product ID

  - **<u>Action Parameter:</u> Value**

    - The user can provide asset value into the Value action parameter.

  - **<u>Action Parameter:</u> Time Range**

    - This parameter will be used for specifying the time range of the search.
    - User can provide time using this '\<digit>\<d/h/m/s>' time format. Here, d = Day, h =
      Hour, m = Minutes, and s = Seconds.
    - **Note:** The Start time and End time will be calculated using the specified time range.
      The end time will be present time and according to the specified time range, the start
      time will be calculated for the search.

  - **<u>Action Parameters:</u> Start Time and End Time**

    - These parameters will be used for specifying the time range of the search. The user
      specifies the time for the asset you are investigating using the reference time action
      parameter
    - Users can provide time using this 'yyyy-MM-ddTHH:mm:ssZ' time format. Here, y=Year,
      M=Month, d=Day, H=Hour, m=Minutes, s=Seconds.
    - **Note:** The number of returned events can be reduced over a shorter period using these
      parameters.

  - **<u>Action Parameter:</u> Limit**

    - This parameter is used to limit the number of events results to return.
    - The user can specify between 1 and 10,000. The default value is 10,000. If the limit is
      not provided, it will fetch by default 10,000 events results.

  - **<u>Note:</u>**

    - If the user doesn't provide any of the time-related action parameters, the action will
      perform a search for the last three days.
    - If the [Reference Time] action parameter is not given, the action will consider the
      start time as reference time. And if the value is given for it, the value will be
      validated and used in the search request.
    - If the user provides [Time Range] and other time-related action parameters, the
      priority will be given to the [Time Range] action parameter and the search will be
      performed according to its given value.

  - **Example:**

    - Get a list of events discovered on the specified Hostname asset
      - Asset Indicator = Hostname
      - Value = franklin-guzman-laptop
      - Start Time = 2019-11-01T20:37:00Z
      - End Time = 2019-11-02T20:37:00Z
      - Reference Time = 2019-11-02T20:37:00Z
    - Filtering events results for the specified Asset IP Address for the last three days
      (Here, the Present time is 2020-01-03T00:00:00Z)
      - Asset Indicator = Asset IP Address
      - Value = 157.122.62.205
      - Time Range = 3d
    - Filtering events results based on the specifying time range for the specified Asset IP
      Address.
      - Asset Indicator = Asset IP Address
      - Value = 157.122.62.205
      - Start Time = 2019-01-01T00:00:00Z
      - End Time = 2020-01-01T00:00:00Z
      - Reference Time = 2020-01-01T00:00:00Z
- ### List IoCs
  - **<u>Action Parameter:</u> Time Range**

    - This parameter will be used for specifying the time range of the search.
    - User can provide time using this '\<digit>\<d/h/m/s>' time format. Here, d = Day, h =
      Hour, m = Minutes, and s = Seconds.
    - **Note:** The Start time and End time will be calculated using the specified time range.
      The end time will be present time and according to the specified time range, the start
      time will be calculated for the search.

  - **<u>Action Parameters:</u> Start Time**

    - This parameter will be used for specifying the start time of the search.
    - Users can provide time using this 'yyyy-MM-ddTHH:mm:ssZ' time format. Here, y=Year,
      M=Month, d=Day, H=Hour, m=Minutes, s=Seconds.
    - **Note:** IoCs returned by this method are the IoCs that were discovered by Chronicle
      within the specified time range in the enterprise environment. There might be IoCs
      within your data that were present prior to their discovery by the Chronicle.

  - **<u>Action Parameter:</u> Limit**

    - This parameter is used to limit the number of IoCs results to return.
    - The user can specify between 1 and 10,000. The default value is 10,000. If the limit is
      not provided, it will fetch by default 10,000 IoCs results.

  - **<u>Note:</u>**

    - If the user doesn't provide any of the time-related action parameters, the action will
      perform a search for the last three days.
    - If the user provides [Time Range] and other time-related action parameters, the
      priority will be given to the [Time Range] action parameter and the search will be
      performed according to its given value.

  - **Example:**

    - Get a list of all of the possible IoC discovered within the enterprise for the last
      three days (Here, the Present time is 2020-01-03T00:00:00Z)
      - Time Range= 3d
    - Get a list of all of the possible IoC discovered within the enterprise starting from the
      specified time.
      - Start Time= 2019-01-01T00:00:00Z
- ### List IoC Details
  - **<u>Action Parameter:</u> Artifact Indicator**

    - The Artifact Indicator parameter enables search by selecting anyone from given artifact
      indicators.

    - Valid Values:

      - Domain Name
      - Destination IP Address

  - **<u>Action Parameter:</u> Value**

    - The user can provide artifact value into the Value action parameter.

  - **Example:**

    - Fetch threat intelligence associated with the specific domain artifact
      - Artifact Indicator = Domain Name
      - Value = wp.com
    - Fetch threat intelligence associated with the specific IP artifact
      - Artifact Indicator = Destination IP Address
      - Value = 45.64.104.167
- ### Domain Reputation
  - **<u>Reputation Decision Algorithm</u>**

    - There is a total of 8 asset configuration parameters that will use in this algorithm.
      These parameter values will be used for deriving anyone of reputation from 'Malicious',
      'Suspicious', and 'Unknown' for the specified artifact. Chronicle provides details about
      the Domain/IP which includes Categories, Severity, and Confidence Score. The reputation
      calculation can be controlled using these 3 properties. Here, 'Malicious' reputation has
      higher priority over 'Suspicious' reputation which means if any of the details of the
      sources of the retrieved domain IoC from search falls under the 'Malicious' criteria,
      then, reputation will be defined as 'Malicious' and won't check for the 'Suspicious'
      criteria. If the retrieved IoC doesn't fall under any one of the criteria configured for
      'Malicious' and 'Suspicious', then, reputation will be derived as 'Unknown'.

  - **<u>Action Parameter:</u> Domain Name**

    - This parameter will be used to specify the value of the domain artifact for search. It
      is a required action parameter.

  - **<u>Asset Configuration Parameters:</u> Malicious categories for reputation, Malicious
    severity for reputation, Malicious Str Confidence score for reputation, and Malicious Int
    Confidence score for reputation**

    - These parameters will be used for deriving the 'Malicious' reputation for the specified
      artifact. Chronicle provides details about the IoC which includes Categories, Severity,
      and Confidence Score. The reputation calculation can be controlled using these 3
      properties. Using the values of these parameters, if any of the details of the sources
      of retrieved domain IoC from search falls under these values, then, reputation will be
      derived as a 'Malicious'. You can identify this in the action output data path as this
      action will set the value of reputation datapath to 'Malicious'.

  - **<u>Asset Configuration Parameters:</u> Suspicious categories for reputation, Suspicious
    severity for reputation, Suspicious Str Confidence score for reputation, and Suspicious Int
    Confidence score for reputation**

    - These parameters will be used for deriving the 'Suspicious' reputation for the specified
      artifact. Chronicle provides details about the IoC which includes Categories, Severity,
      and Confidence Score. The reputation calculation can be controlled using these 3
      properties. Using the values of these parameters, if any of the details of the sources
      of retrieved domain IoC from search falls under these values, then, reputation will be
      derived as a 'Suspicious'. You can identify this in the action output data path as this
      action will set the value of reputation datapath to 'Suspicious'.

  - **<u>Note:</u>**

    - Using the values of asset configuration parameters, if retrieved IoC from search does
      not fall under any of the values, then, reputation will be derived as an 'Unknown'. You
      can identify this in the action output data path as this action will set the value of
      reputation datapath to 'Unknown'.
    - If the user doesn't configure any values for these asset configuration parameters,
      reputation will be derived as an 'Unknown'.
    - If the search will not retrieve any of the sources for a specified domain artifact,
      then, reputation will be derived as an 'Unknown'.
    - Here, 'Malicious' reputation has higher priority over 'Suspicious' reputation which
      means if any of the details of the sources of the retrieved domain IoC from search falls
      under the 'Malicious' criteria, then, reputation will be defined as 'Malicious' and
      won't check for the 'Suspicious' criteria.

  - **Example:**

    - Derive reputation of threat intelligence associated with the specific domain artifact
      - Domain Name = wp.com (Action parameter)

      - Malicious severity for reputation = ["High", "Medium"] (Asset configuration
        parameter)

      - **Sample response for this search:**

        ```json
        {
            "sources": [
                {
                    "sourceUrl": "........",
                    "confidenceScore": {
                        "strRawConfidenceScore": "30"
                    },
                    "rawSeverity": "Medium",
                    "category": ".......",
                    "addresses": [......],
                    .....
                }
            ]
        }
        ```

      - Reputation will be defined as 'Malicious' as retrieved IoC from search has 'Medium'
        rawSeverity in its sources.
- ### IP Reputation
  - **<u>Reputation Decision Algorithm</u>**

    - There is a total of 8 asset configuration parameters that will use in this algorithm.
      These parameter values will be used for deriving anyone of reputation from 'Malicious',
      'Suspicious', and 'Unknown' for the specified artifact. Chronicle provides details about
      the Domain/IP which includes Categories, Severity, and Confidence Score. The reputation
      calculation can be controlled using these 3 properties. Here, 'Malicious' reputation has
      higher priority over 'Suspicious' reputation which means if any of the details of the
      sources of the retrieved IP IoC from search falls under the 'Malicious' criteria, then,
      reputation will be defined as 'Malicious' and won't check for the 'Suspicious' criteria.
      If the retrieved IoC doesn't fall under any one of the criteria configured for
      'Malicious' and 'Suspicious', then, reputation will be derived as 'Unknown'.

  - **<u>Action Parameter:</u> Destination IP Address**

    - This parameter will be used to specify the value of the IP artifact for search. It is a
      required action parameter.

  - **<u>Asset Configuration Parameters:</u> Malicious categories for reputation, Malicious
    severity for reputation, Malicious Str Confidence score for reputation, and Malicious Int
    Confidence score for reputation**

    - These parameters will be used for deriving the 'Malicious' reputation for the specified
      artifact. Chronicle provides details about the IoC which includes Categories, Severity,
      and Confidence Score. The reputation calculation can be controlled using these 3
      properties. Using the values of these parameters, if any of the details of the sources
      of retrieved IP IoC from search falls under these values, then, reputation will be
      derived as a 'Malicious'. You can identify this in the action output data path as this
      action will set the value of reputation datapath to 'Malicious'.

  - **<u>Asset Configuration Parameters:</u> Suspicious categories for reputation, Suspicious
    severity for reputation, Suspicious Str Confidence score for reputation, and Suspicious Int
    Confidence score for reputation**

    - These parameters will be used for deriving the 'Suspicious' reputation for the specified
      artifact. Chronicle provides details about the IoC which includes Categories, Severity,
      and Confidence Score. The reputation calculation can be controlled using these 3
      properties. Using the values of these parameters, if any of the details of the sources
      of retrieved IP IoC from search falls under these values, then, reputation will be
      derived as a 'Suspicious'. You can identify this in the action output data path as this
      action will set the value of reputation datapath to 'Suspicious'.

  - **<u>Note:</u>**

    - Using the values of asset configuration parameters, if retrieved IoC from search does
      not fall under any of the values, then, reputation will be derived as an 'Unknown'. You
      can identify this in the action output data path as this action will set the value of
      reputation datapath to 'Unknown'.
    - If the user doesn't configure any values for these asset configuration parameters,
      reputation will be derived as an 'Unknown'.
    - If the search will not retrieve any of the sources for specified IP artifact, then,
      reputation will be derived as an 'Unknown'.
    - Here, 'Malicious' reputation has higher priority over 'Suspicious' reputation which
      means if any of the details of the sources of the retrieved IP IoC from search falls
      under the 'Malicious' criteria, then, reputation will be defined as 'Malicious' and
      won't check for the 'Suspicious' criteria.

  - **Example:**

    - Derive reputation of threat intelligence associated with the specific domain artifact
      - Destination IP Address = 192.225.158.2 (Action parameter)

      - Suspicious Int Confidence Score Range for Reputation = 10,30 (Asset configuration
        parameter)

      - **Sample response for this search:**

        ```json
        {
            "sources": [
                {
                    "sourceUrl": "........",
                    "confidenceScore": {
                        "strRawConfidenceScore": "21"
                    },
                    "rawSeverity": "Low",
                    "category": "........",
                    "addresses": [......],
                    .....
                }
            ]
        }
        ```

      - Reputation will be defined as 'Suspicious' as retrieved IoC from search has 21
        strRawConfidenceScore in its sources which lies between the 10 and 30.
- ### List Rules
  - **<u>Action Parameter:</u> Limit**

    - This parameter will be used to limit the number of rules to return.
    - The user can specify a valid non-zero integer. The default value is 1000. If the limit
      is not provided, it will fetch by default 1000 rules.

  - **Example:**

    - Get a list of 200 rules within the enterprise.
      - Limit= 200
- ### List Detections
  - **<u>Action Parameter:</u> Rule ID(s)**

    - This parameter will be used for specifying the comma-separated rule ID(s) of which the
      detections will be fetched.
    - The user can specify rule ID(s) as a comma-separated list. The rule ID(s) can be
      provided with or without version ID appended to it.

  - **<u>Action Parameter:</u> Alert State**

    - This parameter will be used for specifying whether to filter the detections based on
      whether they are ALERTING or NOT_ALERTING. Its default value is ALL.

    - Valid Values:

      - ALERTING
      - NOT_ALERTING
      - ALL

  - **<u>Action Parameter:</u> Time Range**

    - This parameter will be used for specifying the time range of the search.
    - User can provide time using this '\<digit>\<d/h/m/s>' time format. Here, d = Day, h =
      Hour, m = Minutes, and s = Seconds.
    - **Note:** The Start time and End time will be calculated using the specified time range.
      The end time will be present time and according to the specified time range, the start
      time will be calculated for the search.

  - **<u>Action Parameters:</u> Start Time and End Time**

    - These parameters will be used for specifying the time range of the search.
    - Users can provide time using this 'yyyy-MM-ddTHH:mm:ssZ' time format. Here, y=Year,
      M=Month, d=Day, H=Hour, m=Minutes, s=Seconds.
    - **Note:** The number of returned detections can be reduced over a shorter period using
      these parameters.

  - **<u>Action Parameter:</u> Limit**

    - This parameter is used to limit the number of detections to return per rule ID.
    - The user can specify a valid non-zero integer. The default value is 10,000. If the limit
      is not provided, it will fetch by default 10,000 detections.

  - **<u>Note:</u>**

    - If the user doesn't provide any of the time-related action parameters, the action will
      perform a search for the last three days.
    - If the user provides [Time Range] and other time-related action parameters, the
      priority will be given to the [Time Range] action parameter and the search will be
      performed according to its given value.
    - Due to the API limitation, the action may encounter an HTTP 429 (RESOURCE_EXHAUSTED)
      error for the Rule ID(s) with a large number of detections. These Rule ID(s) will be
      stored in the `action_result.data.*.rule_ids_with_partial_detections.*.rule_id`
      datapath. The partially fetched detections will be displayed in the action output.

  - **Example:**

    - Get a list of 200 detections of ALERTING type for the ruleId,
      ru_1f54ab4b-e523-48f7-ae25-271b5ea8337d, discovered within the enterprise for the last
      three days.
      - Rule IDs= ru_1f54ab4b-e523-48f7-ae25-271b5ea8337d
      - Alert State= ALERTING
      - Time Range= 3d
      - Limit= 200
    - Get a list of 100 detections of NOT_ALERTING type for the ruleIds,
      ru_1f54ab4b-e523-48f7-ae25-271b5ea8337d and
      ru_1f54ab4b-e523-48f7-ae25-271b5ea8337d@v_1605892822_687503000, discovered within a
      specified Start Time and End Time.
      - Rule IDs= ru_1f54ab4b-e523-48f7-ae25-271b5ea8337d,
        ru_1f54ab4b-e523-48f7-ae25-271b5ea8337d@v_1605892822_687503000
      - Alert State= NOT_ALERTING
      - Start Time= 2019-11-01T20:37:00Z
      - End Time= 2021-02-01T20:37:00Z
      - Limit= 100

## On Poll

- ### What is On Poll

  - It will ingest data from the external system into the phantom server in the form of
    containers and artifacts. There are two approaches to polling which are mentioned below.

    - POLL NOW (Manual polling)

      - It will fetch the data every time as per the corresponding asset configuration
        parameters. It doesn't store the last run context of the fetched data. The
        corresponding asset configuration parameters for the POLL NOW are the Time range for
        POLL NOW, Max results for POLL NOW.

    - Scheduled/Interval Polling

      - Scheduled Polling: The ingestion action can be triggered at every specified
        timestamp interval.
      - Interval Polling: The ingestion action can be triggered at every time range
        interval.
      - It will fetch the data every time as per the corresponding asset configuration
        parameters based on the stored context from the previous ingestion run. It stores
        the last run context of the fetched data. It starts fetching data based on the
        combination of the values of stored context for the previous ingestion run and the
        corresponding asset configuration parameters having higher priority. The
        corresponding asset configuration parameters for the scheduled/interval polling are
        the Start time for scheduled/interval POLL, Max results for scheduled/interval POLL.

- ### Containers and Artifacts creation

  - We have configured eight ingestion run modes which you can select from the \[Ingestion Run
    Mode\] asset configuration parameters. Below are the eight modes

    - IoC Domain Matches: It will ingest only the domain IoCs discovered within the
      enterprise.
    - Assets with Alerts: It will ingest only the 3rd party security asset alerts tracked
      within the enterprise.
    - User Alerts: It will ingest only the 3rd party security user alerts tracked within the
      enterprise.
    - All Alerts: It will ingest only the 3rd party security alerts (asset alerts and security
      alerts) tracked within the enterprise.
    - Alerting Detections: It will ingest only the alerting detections, for the specified Rule
      ID(s), tracked within the enterprise.
    - Not-alerting Detections: It will ingest only the not-alerting detections, for the
      specified Rule ID(s), tracked within the enterprise.
    - All Detections: It will ingest all the detections (alerting and not-alerting), for the
      specified Rule ID(s), tracked within the enterprise.
    - All: It will ingest all the 3rd party security asset alerts, user alerts, alerting
      detections, not_alerting detections and domain IoCs tracked/discovered within the
      enterprise.

  - Container

    - A container is a composite object that consists of one or more artifacts that can be
      automated. Containers are the top-level data structure that Playbooks operate on. Every
      container has a common header, and beneath that, the ability to store arbitrary less
      structured JSON.

  - Artifacts

    - Artifacts are objects that are associated with a Container and serve as corroboration or
      evidence related to the Container.

  - For the security alerts (asset alerts and user alerts), IoCs and detections (Alerting and
    Not-alerting) data which we are fetching will be ingested in the form of groups of
    entities(five groups; one for each of the ingestion run mode) with the group getting created
    as a container and entities getting created as artifacts in the respective container. Below
    is the explanation based on the ingestion run mode for that.

    - **IoC Domain Matches**

      In this mode, one container will be created for the domain IoC matches.

      - Container 1 :- IoC Domain Matches - creation_timestamp

        - This container will be used to store fetched IOC data in the form of artifacts.
          The container will be saved with a creation timestamp in its name e.g. IoC
          Domain Matches - 2019-01-01T00:00:00Z.

    - **Assets with Alerts**

      In this mode, one container will be created for 3rd party security asset alerts.

      - Container 1 :- Asset with Alerts - creation_timestamp

        - This container will be used to store fetched security asset alerts data in the
          form of artifacts. The container will be saved with a creation timestamp in its
          name e.g. Asset with Alerts - 2019-01-01T00:00:00Z.

    - **User Alerts**

      In this mode, one container will be created for 3rd party security user alerts.

      - Container 1 :- User Alerts - creation_timestamp

        - This container will be used to store fetched security user alerts data in the
          form of artifacts. The container will be saved with a creation timestamp in its
          name e.g. User Alerts - 2019-01-01T00:00:00Z.

    - **Alerting Detections**

      In this mode, one container will be created for the detections having alertState as
      'ALERTING'.

      - Container 1 :- Alerting Detections - creation_timestamp

        - This container will be used to store fetched alerting detections data in the
          form of artifacts. The container will be saved with a creation timestamp in its
          name e.g. Alerting Detections - 2019-01-01T00:00:00Z.

    - **Not-alerting Detections**

      In this mode, one container will be created for the detections having alertState as
      'NOT_ALERTING'.

      - Container 1 :- Not-alerting Detections - creation_timestamp

        - This container will be used to store fetched alerting detections in the form of
          artifacts. The container will be saved with a creation timestamp in its name
          e.g. Not-alerting Detections - 2019-01-01T00:00:00Z.

    - **All Alerts**

      For this mode, two containers will be created for each type of data. One container
      will be created for the security asset alerts data and another container will be created
      for the security user alerts.

      - Container 1 :- Assets with Alerts - creation_timestamp

        - This container will be used to store fetched security asset alerts data in the
          form of artifacts. The container will be saved with a creation timestamp in its
          name e.g. Asset with Alerts - 2019-01-01T00:00:00Z.

      - Container 2 :- User Alerts - creation_timestamp

        - This container will be used to store fetched security user alerts data in the
          form of artifacts. The container will be saved with a creation timestamp in its
          name e.g. User Alerts - 2019-01-01T00:00:00Z.

    - **All Detections**

      For this mode, two containers will be created for each type of data. One container
      will be created for the Alerting Detections and another container will be created for
      the Not-alerting Detections.

      - Container 1 :- Alerting Detections - creation_timestamp

        - This container will be used to store fetched alerting detections data in the
          form of artifacts. The container will be saved with a creation timestamp in its
          name e.g. Alerting Detections - 2019-01-01T00:00:00Z.

      - Container 2 :- Not-alerting Detections - creation_timestamp

        - This container will be used to store fetched not-alerting detections in the form
          of artifacts. The container will be saved with a creation timestamp in its name
          e.g. Not-alerting Detections - 2019-01-01T00:00:00Z.

    - **All**

      For this mode, five containers will be created for each type of data.

      - Container 1 :- IoC Domain Matches - creation_timestamp

        - This container will be used to store fetched IoC data in the form of artifacts.
          The container will be saved with a creation timestamp in its name e.g. IoC
          Domain Matches - 2019-01-01T00:00:00Z.

      - Container 2 :- Asset with Alerts - creation_timestamp

        - This container will be used to store fetched security asset alerts data in the
          form of artifacts. The container will be saved with a creation timestamp in its
          name e.g. Asset with Alerts - 2019-01-01T00:00:00Z.

      - Container 3 :- User Alerts - creation_timestamp

        - This container will be used to store fetched security user alerts data in the
          form of artifacts. The container will be saved with a creation timestamp in its
          name e.g. User Alerts - 2019-01-01T00:00:00Z.

      - Container 4 :- Alerting Detections - creation_timestamp

        - This container will be used to store fetched alerting detections data in the
          form of artifacts. The container will be saved with a creation timestamp in its
          name e.g. Alerting Detections - 2019-01-01T00:00:00Z.

      - Container 5 :- Not-alerting Detections - creation_timestamp

        - This container will be used to store fetched not-alerting detections in the form
          of artifacts. The container will be saved with a creation timestamp in its name
          e.g. Not-alerting Detections - 2019-01-01T00:00:00Z.

  - To make ingested data more manageable in the containers and artifacts, we have provided the
    configuration parameter to specify the maximum allowed artifacts in the single container.
    I.e. [Max allowed artifacts in a single container]

- ### Stored Context

  - It is the concept of storing the context of the previous ingestion run. This concept will be
    used in the scheduled/interval polling. It will use the state file to store the last run
    context. This state file will be created for the created asset for the application on the
    phantom platform.

    - State file location:

      - For non-NRI Instances:
        /opt/phantom/local_data/app_states/8925dbb5-abe1-4e5d-b053-326e35e1e194
      - For NRI Instances:
        /home/phanru/phantomcyber/local_data/app_states/8925dbb5-abe1-4e5d-b053-326e35e1e194

    - The default format of state file: `{"app_version": "2.0.0"}`

- ### Parameters

  - **<u>Manual Polling - Poll Now</u>**

    It will fetch the data every time as per the corresponding asset configuration
    parameters. It doesn't store the last run context of the fetched data. The corresponding
    asset configuration parameters for the POLL NOW are the [Time range for POLL NOW], \[Max
    results for POLL NOW\].

    - **<u>Asset Configuration Parameter</u> - Time range for POLL NOW**

      This is an optional parameter. This parameter will be used to specify the time range
      for the search in the manual polling. Possible values format: 'start_time, end_time' or
      \<digit>\<d/h/m/s> or 'start_time' where d = Day, h = Hour, m = Minutes, and s =
      Seconds. If the value is not given, the value will be considered as 3d(means the last
      three days).

      - Format 1 - 'start_time, end_time'

        - Using this format you can provide start time and end time both for a specified
          time. You can provide time using this 'yyyy-MM-ddTHH:mm:ssZ' time format. Here,
          y=Year, M=Month, d=Day, H=Hour, m=Minutes, s=Seconds.
          E.g. 2020-03-20T00:00:00Z, 2020-06-20T00:00:00Z

      - Format 2 - \<digit>\<d/h/m/s>

        - Using this format you can informally provide a time. For example, 3d = 3 Days,
          3m = 3 Minutes. The Start time and End time will be calculated using the
          specified value. The end time will be present time and according to the
          specified time range, the start time will be calculated for the search.
          E.g. 10d

      - Format 3 - 'start_time'

        - Using this format you can provide start time only. The end time will be
          considered as the present time.
          E.g. 2020-03-20T00:00:00Z

    - **<u>Asset Configuration Parameter</u> - Max results for POLL NOW**

      This is an optional parameter. This parameter is used to specify the maximum number
      of results to return from API calls in the manual polling. The default value is 10,000.
      If the limit is not provided, it will fetch by default 10,000 results.
      Example:

      - Run the manual poll for 'All' ingestion run mode for the last ten days.

        - Time range for POLL NOW = 10d
        - Max results for POLL NOW = 10000
        - Ingestion Run Mode = All

  - **<u>Scheduled/Interval Polling</u>**

    It will fetch the data every time as per the corresponding asset configuration
    parameters based on the stored context from the previous ingestion run. It stores the last
    run context of the fetched data. It starts fetching data based on the combination of the
    values of stored context for the previous ingestion run and the corresponding asset
    configuration parameters having higher priority. The corresponding asset configuration
    parameters for the scheduled/interval polling are the \[Start time for scheduled/interval
    POLL\], [Max results for scheduled/interval POLL].

    - **<u>Asset Configuration Parameter</u> - Start time for scheduled/interval POLL**

      This parameter will be used to specify the start time for the search. Possible
      values format: 'start_time' or \<digit>\<d/h/m/s> where d = Day, h = Hour, m = Minutes,
      and s = Seconds.

      - Format 1 - \<digit>\<d/h/m/s>

        - Using this format you can informally provide a time. For example, 3d = 3 Days,
          3m = 3 Minutes. The Start time and End time will be calculated using the
          specified value. The end time will be present time and according to the
          specified value, the start time will be calculated for the search.
          E.g. 10d

      - Format 2 - 'start_time'

        - Using this format you can provide start time only. The end time will be
          considered as the present time.
          E.g. 2020-03-20T00:00:00Z

    - **<u>Asset Configuration Parameter</u> - Max results for scheduled/interval POLL**

      This is an optional parameter. This parameter is used to specify the maximum number
      of results to return from API calls. The default value is 10,000. If the limit is not
      provided, it will fetch by default 10,000 results.
      Example:

      - Run the Scheduled poll for 'All' ingestion run mode for the last three days.

        - Start time for scheduled/interval POLL = 3d
        - Max results for scheduled/interval POLL = 10000
        - Ingestion Run Mode = All

    - **<u>Asset Configuration Parameter</u> - Backdate Start Time in minutes (for scheduled
      polling)**

      This is an optional parameter. This parameter is used to backdate the start time for
      'Assets with Alerts', 'User Alerts', 'Alerting Detections', 'Not-alerting detections',
      'All Alerts', 'All Detections', and 'All' run modes. This parameter can be used to
      prevent (or minimize) the late-breaking for the mentioned run modes. The default value
      is 15 minutes (15m).
      Example:

      - Run the Scheduled poll for the last three days with backdate start time set to 15
        minutes.

        - Start time for scheduled/interval POLL = 3d
        - Backdate Start Time in minutes (for scheduled polling) = 15m
        - Ingestion Run Mode = All

    - **<u>Stored Context</u> - State file intervention**

      The state file will be used to save the last run context. For the first run, the
      state is mentioned below. Hence, the action will run as the provided asset configuration
      parameters. After performing the first run, the action will save the individual last run
      context for the IoC, Asset Alerts, User Alerts, Alerting Detection, and Not-alerting
      Detection for the scheduled/interval polling.

      - State file without the stored context of the previous run: `{"app_version": "2.0.0"}`
      - State file with the stored context of the previous run:
        ```json
        {
            "app_version": "2.0.0",
            "last_run_ioc_time": "2020-01-03T00:00:00Z",
            "last_run_alert_time": "2020-01-03T00:00:00Z",
            "last_run_user_alert_time": "2020-01-03T00:00:00Z",
            "last_run_alerting_detection_time": "2020-01-03T00:00:00Z",
            "last_run_not_alerting_detection_time": "2020-01-03T00:00:00Z"
        }
        ```

  - **<u>Common Asset parameters</u>**

    - **<u>Asset Configuration Parameter</u> - Alert Severity (JSON formatted list)**

      This parameter will be used to filter fetched security asset alerts data based on the
      alert severity. It is an optional parameter. This action will ingest only those alerts
      which have specified severity. If the value is not provided, it will ingest all fetched
      data into the container. This parameter will be validated and used only when the
      ingestion run mode is either 'All', 'All Alerts', or 'Assets with Alerts'.

    - **<u>Asset Configuration Parameter</u> - Max allowed artifacts in a single container**

      This is an optional parameter. This parameter is used to specify the maximum allowed
      artifacts in a single container to ingest. The default value is 10,000. If the value is
      not provided, it will set it to 10,000 by default. If the container limit is exhausted,
      this action will create a new container with a creation timestamp and start ingestion in
      it.

    - **<u>Asset Configuration Parameter</u> - Fetch all live rules created in the Detection
      Engine**

      This parameter will be used to fetch the (alerting and not-alerting) detections. If this
      parameter is set to true (or checked), then the action will first fetch all the rules
      and fetch the detections for the live rules. If the value is set to false (or
      unchecked), then the detections will be fetched based on the **Comma-separated Rule
      ID(s) (with or without versionId) for fetching the detections** asset configuration
      parameter. This parameter will be used only when the ingestion run mode is either 'All',
      'All Detections', 'Alerting Detections', or 'Not-alerting Detections'.

    - **<u>Asset Configuration Parameter</u> - Comma-separated Rule ID(s) (with or without
      versionId) for fetching the detections**

      This parameter will be used to fetch the (alerting and not-alerting) detections. It is
      an optional parameter. The detections will be fetched for the provided Rule ID(s). The
      user can provide multiple values in the form of a comma-separated string. If the value
      is not provided and **Fetch all live rules created in the Detection Engine** asset
      configuration parameter is set to true, it will ingest detections for all the live
      rules. This parameter will be validated and used only when the ingestion run mode is
      either 'All', 'All Detections', 'Alerting Detections', or 'Not-alerting Detections'.

    - **<u>Note:</u>**

      - For Scheduled/Interval Polling, if the user adds a new Rule ID to the existing list
        of Rule IDs, the On Poll action will be triggered, for all the current Rule IDs
        (including the newly added Rule ID), with the last run context of the previous
        scheduled/interval run. This may lead to the data loss of the detections of the
        newly added Rule ID. To overcome this issue, user can perform any one of the
        following options:

        - Create a new asset and configure it with the required Rule ID(s).
        - Reset the state file mentioned in [<u>this section</u>](#stored-context) .

      **Manual Polling (POLL NOW)**

      - In this case, every time the action will create a new container. If the fetched data
        has more data than the specified value of 'Max allowed artifacts in a single
        container', it will create multiple containers to ingest data as it satisfies the
        maximum allowed artifacts limit in a single container.

      **Scheduled/Interval Polling**
      The action will determine the run whether is the first run or not based on the stored
      context for scheduled/interval polling.

      - For the first ingestion run for Scheduled/Interval polling

        - In this case, every time the action will create a new container. If the fetched
          data has more data than the specified value of \[Max allowed artifacts in a
          single container\], it will create multiple containers to ingest data as it
          satisfies the maximum allowed artifacts limit in a single container.

      - For the subsequent ingestion run for Scheduled/Interval polling

        - In this case, there three possible ways to ingest artifacts into the container.

          - **Container does not exist:** In this way, the action will create a new
            container and start ingesting artifacts in it.
          - **Container already exists and having a sufficient margin for artifacts
            creation:** In this way, the action will ingest artifacts into the already
            existing container.
          - **Container already exists and not having sufficient margin:** In this way,
            the action will ingest artifacts into the already existing container until
            the limit is reached, then, the action will create a new container and start
            ingesting artifacts in it.

- ### Sample of Ingested Artifacts

  There are a total of two types of artifacts getting ingested into the phantom server which are
  mentioned below.

  - **Alert Artifact**

    This artifact will be created when ingestion run mode is either 'All', 'All Alerts', or
    'Assets with Alerts'. This artifact will be ingested into the separate container named
    'Assets with Alerts \<creation_timestamp>'.

    - Sample response of the ListAlerts endpoint which is used to fetch the alerts data:

      ```json
      {
          "asset": {
            "hostname": "mary-gonzalez-laptop"
          },
          "alertInfos": [
            {
              "name": "if match then match [1]",
              "sourceProduct": "Rule Generated Alert [456def]",
              "severity": "High",
              "timestamp": "2020-01-27T22:07:12Z",
              "rawLog": "...",
              "uri": ["..."]
            }
          ]
        }
      ```

    - Sample 'Alert artifact' which gets created from the received response:

      ```json
        {
          ...
          "cef": {
            "assetIndicator": "hostname",
            "assetValue": "mary-gonzalez-laptop",
            "alertName": "if match then match [1]",
            "sourceProduct": "Rule Generated Alert [456def]"
            "severity": "High",
            "timestamp": "2020-01-27T22:07:12Z",
            "rawLog": "..."
            "uri": "...",
          }
          ...
        }
      ```

  - **User Alert Artifact**

    This artifact will be created when ingestion run mode is either 'All', 'All Alerts' or User
    Alerts'. This artifact will be ingested into the separate container named User Alerts
    \<creation_timestamp>'.

    - Sample response of the ListAlerts endpoint which is used to fetch the user alerts data:

      ```json
        {
          "user": {
            "email": "test_user@gmail.com"
          },
          "alertInfos": [
            {
              "name": "Unspecified",
              "sourceProduct": "Office 365",
              "timestamp": "2020-09-07T19:46:44Z",
              "rawLog": "...",
              "uri": ["..."]
            }
          ]
        }
      ```

    - Sample 'User Alert artifact' which gets created from the received response:

      ```json
        {
          ...
          "cef": {
            "userIndicator": "email",
            "userValue": "test_user@gmail.com",
            "alertName": "Unspecified",
            "sourceProduct": "Office 365",
            "timestamp": "2020-09-07T19:46:44Z",
            "rawLog": "...",
            "uri": "..."
          }
          ...
        }
      ```

  - **IoC Domain Artifact**

    This artifact will be created when ingestion run mode is either 'All' or 'IoC Domain
    Matches'. This artifact will be ingested into the separate container named 'IoC Domain
    Matches \<creation_timestamp>'.

    - Sample response of the ListIoCs endpoint which is used to fetch the IoCs data:
      ```json
        {
          "artifact": {
            "domainName": "speedtest.net"
          },
          "firstSeenTime": "2018-11-05T12:00:57Z",
          "iocIngestTime": "2018-07-21T20:00:00Z",
          "uri": ["..."],
          "lastSeenTime": "2020-03-23T23:51:00.241330Z",
          "sources": [
            {
              "category": "IP Check Services",
              "source": "ET Intelligence Rep List",
              "rawSeverity": "Info",
              "confidenceScore": {
                "normalizedConfidenceScore": "Medium",
                "intRawConfidenceScore": 0
              }
            }
          ]
        }
      ```
    - Sample 'IoC Domain artifact' which gets created from the received response:
      ```json
        {
          ...
          "cef": {
            "artifactIndicator": "domainName",
            "artifactValue": "speedtest.net",
            "category": "IP Check Services",
            "rawSeverity": "Info",
            "normalizedConfidenceScore": "Medium",
            "iocIngestTime": "2018-07-21T20:00:00Z",
            "uri": "...",
            "lastSeenTime": "2020-03-23T23:51:00.241330Z",
            "sources": "ET Intelligence Rep List",
            "firstSeenTime": "2018-11-05T12:00:57Z",
            "intRawConfidenceScore": "0",
            "rawJSON": "{\"artifact\": {\"domainName\": \"speedtest.net\"}, \"sources\": [{\"source\": \"ET Intelligence Rep List\", \"confidenceScore\": {\"normalizedConfidenceScore\": \"Medium\", \"intRawConfidenceScore\": 0}, \"rawSeverity\": \"Info\", \"category\": \"IP Check Services\"}], \"iocIngestTime\": \"2018-07-21T20:00:00Z\", \"firstSeenTime\": \"2018-11-05T12:00:57Z\", \"lastSeenTime\": \"2020-03-23T23:51:00.241330Z\", \"uri\": [\"...\"]}"
          }
          ...
        }
      ```
      **NOTE -** Here, the category, sources, rawSeverity, normalizedConfidenceScore,
      intRawConfidenceScore keys of the IoC Domain Artifact are the details of IoC sources and
      it has comma-separated string datatype. There are chances to retrieved multiple sources
      for a single IoC so that to club all the details in the single key make all these keys
      as a comma-separated string.

  - **Alerting Detection Artifact**

    This artifact will be created when ingestion run mode is either 'All', 'All Detections' or
    'Alerting Detections'. This artifact will be ingested into the separate container named
    'Alerting Detections \<creation_timestamp>'.

    - Sample response of the ListDetections endpoint which is used to fetch the Alerting
      Detections data:

      ```json
        {
          "type": "RULE_DETECTION",
          "detection": [
            {
              "ruleName": "ms_office_to_suspicious_url",
              "urlBackToProduct": "...",
              "uri": ["..."],
              "ruleId": "ru_c25c2673-6551-4156-bf96-e883225feb6c",
              "ruleVersion": "ru_c25c2673-6551-4156-bf96-e883225feb6c@v_1601246241_474367000",
              "alertState": "ALERTING",
              "ruleType": "MULTI_EVENT",
              "detectionFields": [
                {
                  "key": "hostname",
                  "value": "betty-decaro-pc"
                }
              ],
            }
          ],
          "createdTime": "2020-10-04T20:11:35.159233Z",
          "id": "de_f3769bfc-7cfc-43c7-bca2-5e9b413c63c2",
          "timeWindow": {
            "startTime": "2020-10-04T17:34:48Z",
            "endTime": "2020-10-04T17:35:48Z"
          },
          "collectionElements": [...],
          "detectionTime": "2020-10-04T17:35:48Z"
        }
      ```

    - Sample 'Alerting Detection artifact' which gets created from the received response:

      ```json
        {
          ...
          "cef": {
            "alertState": "Alerting",
            "createdTime": "2020-10-04T20:11:35.159233Z",
            "detectionId": "de_f3769bfc-7cfc-43c7-bca2-5e9b413c63c2",
            "detectionTime": "2020-10-04T17:35:48Z",
            "events": [{"..."}],
            "ruleId": "ru_c25c2673-6551-4156-bf96-e883225feb6c",
            "ruleName": "ms_office_to_suspicious_url",
            "ruleType": "MULTI_EVENT",
            "uri": "...",
            "versionId": "ru_c25c2673-6551-4156-bf96-e883225feb6c@v_1601246241_474367000"
          }
          ...
        }
      ```

  - **Not-alerting Detection Artifact**

    This artifact will be created when ingestion run mode is either 'All', 'All Detections' or
    'Not-alerting Detections'. This artifact will be ingested into the separate container named
    'Alerting Detections \<creation_timestamp>'.

    - Sample response of the ListDetections endpoint which is used to fetch the Alerting
      Detections data:
      ```json
        {
          "type": "RULE_DETECTION",
          "detection": [
            {
              "ruleName": "ms_office_to_suspicious_url",
              "urlBackToProduct": "...",
              "uri": ["..."],
              "ruleId": "ru_c25c2673-6551-4156-bf96-e883225feb6c",
              "ruleVersion": "ru_c25c2673-6551-4156-bf96-e883225feb6c@v_1601246241_474367000",
              "alertState": "NOT_ALERTING",
              "ruleType": "MULTI_EVENT",
              "detectionFields": [
                {
                  "key": "hostname",
                  "value": "betty-decaro-pc"
                }
              ],
            }
          ],
          "createdTime": "2020-10-30T17:59:07.388755Z",
          "id": "de_5f498fa7-9db2-4f16-58d1-fe2025c7b457",
          "timeWindow": {
            "startTime": "2020-10-30T16:07:48Z",
            "endTime": "2020-10-30T16:08:48Z"
          },
          "collectionElements": [...],
          "detectionTime": "2020-10-30T16:08:48Z"
        }
      ```
    - Sample 'Not-alerting Detection artifact' which gets created from the received response:
      ```json
        {
          ...
          "cef": {
            "alertState": "Not Alerting",
            "createdTime": "2020-10-30T17:59:07.388755Z",
            "detectionId": "de_5f498fa7-9db2-4f16-58d1-fe2025c7b457",
            "detectionTime": "2020-10-30T16:08:48Z",
            "events": [{"..."}],
            "ruleId": "ru_c25c2673-6551-4156-bf96-e883225feb6c",
            "ruleName": "ms_office_to_suspicious_url",
            "ruleType": "MULTI_EVENT",
            "uri": "...",
            "versionId": "ru_c25c2673-6551-4156-bf96-e883225feb6c@v_1601246241_474367000"
          }
          ...
        }
      ```

## Error code caveats

- #### Handling for HTTP 429 (RESOURCE_EXHAUSTED) Error

  The Chronicle API enforces limits on the volume of requests that can be made by anyone against
  the Chronicle platform. If the user reaches or exceeds the query limit, the Chronicle API server
  returns HTTP 429 (RESOURCE_EXHAUSTED) to the caller. Hence, while executing the actions of the
  Chronicle Phantom integration, there were situations where the actions failed due to the
  above-mentioned API error. To handle this scenario, we have implemented the below-mentioned
  logic.

  - **Scenarios when the user may encounter this error**
    - This error can be encountered when the user wants to fetch a large number of data and
      the Chronicle instance also has a large volume of data for the provided parameters. The
      actions for which this error can be encountered are as follows:
      - List Events
      - List Rules
      - List Detections
    - For all the other actions, if the user runs multiple actions, simultaneously, then this
      error can be encountered.
  - **Mitigation Strategy**
    - The action will execute as per the normal action flow.
    - If the Chronicle APIs return HTTP 429 (RESOURCE_EXHAUSTED) error, then, the retry API
      calls workflow will be executed. The retry workflow is governed by the 2 asset
      configuration parameters named "Retry Wait Period(in seconds)" and "Number Of Retries".
      The explanation of both the parameters is provided below.
      - **Number of Retries:** The value of this parameter defines the number of attempts
        for which the action will keep on retrying if the Chronicle API continuously returns
        the HTTP 429 (RESOURCE_EXHAUSTED) error. If the error gets eliminated before the
        number of retries gets exhausted, then, the action execution will continue along its
        workflow with the next set of API calls and if the error is still persistent and all
        the number of retries are exhausted, then, the action will fail with the latest
        error message being displayed.
      - **Retry Wait Period (in seconds):** The value of this parameter defines the waiting
        period in seconds for which to hold the current execution of the action on receiving
        the HTTP 429 (RESOURCE_EXHAUSTED) error and then, retry the same API call after the
        waiting period is exhausted. This ensures that the integration provides a mechanism
        of attempting to overcome the HTTP 429 (RESOURCE_EXHAUSTED) error. If the error
        persists, then the user should retry the action by providing a greater value to this
        parameter.

- #### The HTTP 500 Internal Server Error

  The 500 Internal Server Error is a general HTTP status code which means that something on the
  server has gone wrong, but the server couldn't be more precise about the exact issue. There are
  certain cases where this error may occur with this Chronicle Phantom Integration which are
  listed below. There are possibilities to get this error in any other invalid scenarios.

  - **<u>Action</u> - List Assets**
    - When the destination IP address is not valid but it has a valid IP format.
  - **<u>Action</u> - List Events**
    - When the asset IP address is not valid but it has a valid IP format.
    - When an incorrect product ID is given for the asset.

### Configuration variables

This table lists the configuration variables required to operate Chronicle. These variables are specified when configuring a Chronicle asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | A Base URL |
**scopes** | required | string | Chronicle API Scope (JSON formatted list) |
**key_json** | required | password | Contents Of Service Account JSON File |
**wait_timeout_period** | optional | numeric | Retry Wait Period (in seconds) |
**no_of_retries** | optional | numeric | Number Of Retries |
**malicious_category** | optional | string | Malicious Categories for Reputation (JSON formatted list) |
**malicious_severity** | optional | string | Malicious Severity for Reputation (JSON formatted list) |
**malicious_str_confidence_score** | optional | string | Malicious Str Confidence Score for Reputation (JSON formatted list) |
**malicious_int_confidence_score** | optional | string | Malicious Int Score Range for Reputation (Use this format 'min_score,max_score') |
**suspicious_category** | optional | string | Suspicious Categories for Reputation (JSON formatted list) |
**suspicious_severity** | optional | string | Suspicious Severity for Reputation (JSON formatted list) |
**suspicious_str_confidence_score** | optional | string | Suspicious Str Confidence Score for Reputation (JSON formatted list) |
**suspicious_int_confidence_score** | optional | string | Suspicious Int Confidence Score Range for Reputation (Use this format 'min_score,max_score') |
**run_mode** | optional | string | Ingestion Run Mode for ON POLL |
**backdate_time** | optional | string | Backdate Start Time in minutes (for scheduled polling) |
**rule_ids** | optional | string | Comma-separated Rule ID(s) (with or without versionId) for fetching the detections |
**fetch_live_rules** | optional | boolean | Fetch all live rules created in the Detection Engine |
**run_automation** | optional | boolean | Flag to Trigger Active Playbooks upon Completion of the Ingestion Action |
**alerts_severity** | optional | string | Alert Severity to Ingest Alerts (JSON formatted list) (If not given ingest all the alerts) |
**start_time_scheduled_poll** | optional | string | Start Time for Scheduled/Interval POLL (Use this format: '<digit>\<d/h/m/s>' or 'start_time') |
**time_range_poll_now** | optional | string | Time Range for POLL NOW (Use this format: 'start_time, end_time' or '<digit>\<d/h/m/s>' or 'start_time') |
**max_results_scheduled_poll** | optional | numeric | Max Results for Scheduled/Interval POLL (Page Size) |
**max_results_poll_now** | optional | numeric | Max Results for POLL NOW (Page Size) |
**max_artifacts** | optional | numeric | Max Allowed Artifacts in a Single Container |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[list ioc details](#action-list-ioc-details) - Return any threat intelligence associated with the specified artifact \
[list iocs](#action-list-iocs) - List all of the IoCs discovered within the enterprise within the specified time \
[list assets](#action-list-assets) - List all of the assets that accessed the specified artifact within the specified time \
[list events](#action-list-events) - List all of the events discovered within the enterprise on a particular device within the specified time \
[domain reputation](#action-domain-reputation) - Derive the reputation of the specified domain artifact (The reputation can be either of 'Malicious', 'Suspicious', and 'Unknown') \
[ip reputation](#action-ip-reputation) - Derive the reputation of the specified destination IP address artifact (The reputation can be either of 'Malicious', 'Suspicious', and 'Unknown') \
[list alerts](#action-list-alerts) - List all of the security alerts tracked within the enterprise on particular assets and|or users for the specified time \
[list rules](#action-list-rules) - List the latest versions of the rules created in the Detection Engine within the enterprise \
[list detections](#action-list-detections) - List all the detections for the specific versions of the given Rule ID(s) \
[on poll](#action-on-poll) - Action handler for the on poll ingest functionality

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list ioc details'

Return any threat intelligence associated with the specified artifact

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**artifact_indicator** | required | Specify the artifact indicator | string | |
**value** | required | Specify the artifact indicator value | string | `ip` `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.artifact_indicator | string | | Domain Name Destination IP Address |
action_result.parameter.value | string | `ip` `domain` | wp.com 45.64.104.167 |
action_result.data.\*.sources.\*.addresses.\*.domain | string | `domain` | psoftdevserver.in |
action_result.data.\*.sources.\*.addresses.\*.ipAddress | string | `ip` | 45.64.104.167 |
action_result.data.\*.sources.\*.addresses.\*.port | numeric | | 80 |
action_result.data.\*.sources.\*.category | string | | Drop site for logs or stolen credentials |
action_result.data.\*.sources.\*.confidenceScore.strRawConfidenceScore | string | | 24 High |
action_result.data.\*.sources.\*.firstActiveTime | string | | 2018-12-26T00:00:00Z |
action_result.data.\*.sources.\*.lastActiveTime | string | | 2019-12-04T00:00:00Z |
action_result.data.\*.sources.\*.rawSeverity | string | | Medium |
action_result.data.\*.sources.\*.sourceUrl | string | `url` | https://tools.emergingthreats.net/docs/ET%20Intelligence%20Rep%20List%20Tech%20Description.pdf |
action_result.data.\*.uri | string | `url` | https://demodev.backstory.chronicle.security/destinationIpResults?ip=45.64.104.167&referenceTime=2020-06-30T14%3A47%3A32.985603Z&selectedList=IpViewDistinctAssets |
action_result.summary.total_sources | numeric | | 2 |
action_result.message | string | | Total sources: 2 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list iocs'

List all of the IoCs discovered within the enterprise within the specified time

Type: **investigate** \
Read only: **True**

The action will fetch the list of all of the IoCs discovered within the enterprise within the specified time. If the user receives 'moreDataAvailable' as a true value in the action output datapaths, there might still be more IoCs within the user's Chronicle account. The user can narrow the time range and run the action again to ensure visibility into all possible IoCs. If the user doesn't provide any of the time-related action parameters, the action will perform a search for the last three days. If the user provides [Time Range] and other time-related action parameters, the priority will be given to the [Time Range] action parameter and the search will be performed according to its given value.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**time_range** | optional | Specify the time range of the search (Use this format <digit>\<d/h/m/s> where d=Days, h=Hours, m=Minutes, s=Seconds) | string | `gc time range` |
**start_time** | optional | Specify the start time of the search (Use this format yyyy-MM-ddTHH:mm:ssZ where y=Year, M=Month, d=Day, H=Hour, m=Minutes, s=Seconds) | string | `gc time` |
**limit** | optional | Specify the maximum number of IoCs results to return. You can specify between 1 and 10,000. (Default is 10,000) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 10000 |
action_result.parameter.start_time | string | `gc time` | 2018-12-26T00:00:00Z |
action_result.parameter.time_range | string | `gc time range` | 10d |
action_result.data.\*.done | boolean | | True False |
action_result.data.\*.response.@type | string | | type.googleapis.com/chronicle.backstory.v1.ListIoCsResponse |
action_result.data.\*.response.matches.\*.artifact.domainName | string | `domain` | connect.ok.ru |
action_result.data.\*.response.matches.\*.firstSeenTime | string | `gc time` | 2018-10-03T01:26:38Z |
action_result.data.\*.response.matches.\*.iocIngestTime | string | `gc time` | 2020-06-29T00:00:00Z |
action_result.data.\*.response.matches.\*.lastSeenTime | string | `gc time` | 2020-07-06T09:30:29Z |
action_result.data.\*.response.matches.\*.sources.\*.category | string | | Drop site for logs or stolen credentials |
action_result.data.\*.response.matches.\*.sources.\*.confidenceScore.intRawConfidenceScore | numeric | | 0 |
action_result.data.\*.response.matches.\*.sources.\*.confidenceScore.normalizedConfidenceScore | string | | Medium |
action_result.data.\*.response.matches.\*.sources.\*.rawSeverity | string | | Medium |
action_result.data.\*.response.matches.\*.sources.\*.source | string | | ET Intelligence Rep List |
action_result.data.\*.response.matches.\*.uri | string | `url` | https://demodev.backstory.chronicle.security/domainResults?domain=aa.online-metrix.net&selectedList=DomainViewDistinctAssets&whoIsTimestamp=2020-07-06T10%3A57%3A54.946836093Z |
action_result.data.\*.response.moreDataAvailable | boolean | | True False |
action_result.summary.total_iocs | numeric | | 32 |
action_result.message | string | | Total IoCs: 32 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list assets'

List all of the assets that accessed the specified artifact within the specified time

Type: **investigate** \
Read only: **True**

If the user doesn't provide any of the time-related action parameters, the action will perform a search for the last three days. If the user provides [Time Range] and other time-related action parameters, the priority will be given to the [Time Range] action parameter and the search will be performed according to its given value.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**artifact_indicator** | required | Specify the artifact indicator | string | |
**value** | required | Specify the artifact indicator value | string | `ip` `domain` `md5` `sha1` `sha256` |
**time_range** | optional | Specify the time range of the search (Use this format <digit>\<d/h/m/s> where d=Days, h=Hours, m=Minutes, s=Seconds) | string | `gc time range` |
**start_time** | optional | Specify the start time of the search (Use this format yyyy-MM-ddTHH:mm:ssZ where y=Year, M=Month, d=Day, H=Hour, m=Minutes, s=Seconds) | string | `gc time` |
**end_time** | optional | Specify the end time of the search (Use this format yyyy-MM-ddTHH:mm:ssZ where y=Year, M=Month, d=Day, H=Hour, m=Minutes, s=Seconds) | string | `gc time` |
**limit** | optional | Specify the maximum number of assets to return. You can specify between 1 and 10,000. (Default is 10,000) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.artifact_indicator | string | | Domain Name |
action_result.parameter.end_time | string | `gc time` | 2020-07-06T06:19:46Z |
action_result.parameter.limit | numeric | | 10000 |
action_result.parameter.start_time | string | `gc time` | 2020-07-01T06:19:46Z |
action_result.parameter.time_range | string | `gc time range` | 3d |
action_result.parameter.value | string | `ip` `domain` `md5` `sha1` `sha256` | wp.com |
action_result.data.\*.assets.\*.asset.assetIpAddress | string | `ip` | 10.0.28.233 |
action_result.data.\*.assets.\*.asset.hostname | string | `host name` | user-hostname |
action_result.data.\*.assets.\*.firstSeenArtifactInfo.artifactIndicator.domainName | string | `domain` | i2.wp.com |
action_result.data.\*.assets.\*.firstSeenArtifactInfo.seenTime | string | `gc time` | 2018-10-18T01:40:32Z |
action_result.data.\*.assets.\*.lastSeenArtifactInfo.artifactIndicator.domainName | string | `domain` | i0.wp.com |
action_result.data.\*.assets.\*.lastSeenArtifactInfo.seenTime | string | `gc time` | 2020-07-06T06:19:46Z |
action_result.data.\*.uri | string | `url` | https://demodev.backstory.chronicle.security/domainResults?domain=wp.com&selectedList=DomainViewDistinctAssets&whoIsTimestamp=2020-07-06T08%3A01%3A43.935834040Z |
action_result.summary.total_assets | numeric | | 100 |
action_result.message | string | | Total assets: 100 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list events'

List all of the events discovered within the enterprise on a particular device within the specified time

Type: **investigate** \
Read only: **True**

If the user doesn't provide any of the time-related action parameters, the action will perform a search for the last three days. If the [Reference Time] action parameter is not given, the action will consider start time as reference time. And if the value is given for it, the value will be validated and used in the search request. If the user provides [Time Range] and other time-related action parameters, the priority will be given to the [Time Range] action parameter and the search will be performed according to its given value.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**asset_indicator** | required | Specify the asset indicator | string | |
**value** | required | Specify the asset indicator value | string | `gc mac` `gc product id` `host name` `ip` |
**time_range** | optional | Specify the time range of the search (Use this format <digit>\<d/h/m/s> where d=Days, h=Hours, m=Minutes, s=Seconds) | string | `gc time range` |
**start_time** | optional | Specify the start time of the search (Use this format yyyy-MM-ddTHH:mm:ssZ where y=Year, M=Month, d=Day, H=Hour, m=Minutes, s=Seconds) | string | `gc time` |
**end_time** | optional | Specify the end time of the search (Use this format yyyy-MM-ddTHH:mm:ssZ where y=Year, M=Month, d=Day, H=Hour, m=Minutes, s=Seconds) | string | `gc time` |
**reference_time** | optional | Specify the time for the asset you are investigating (Use this format yyyy-MM-ddTHH:mm:ssZ where y=Year, M=Month, d=Day, H=Hour, m=Minutes, s=Seconds) | string | `gc time` |
**limit** | optional | Specify the maximum number of events results to return (Default is 10,000) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.asset_indicator | string | | Hostname |
action_result.parameter.end_time | string | `gc time` | 2019-11-02T00:00:00Z |
action_result.parameter.limit | numeric | | 3000 |
action_result.parameter.reference_time | string | `gc time` | 2019-11-01T00:00:00Z |
action_result.parameter.start_time | string | `gc time` | 2019-11-01T00:00:00Z |
action_result.parameter.time_range | string | `gc time range` | 24h |
action_result.parameter.value | string | `gc mac` `gc product id` `host name` `ip` | franklin-guzman-laptop |
action_result.data.\*.events.\*.metadata.ingestedTimestamp | string | | 2021-11-02T08:47:42.040912Z |
action_result.data.\*.events.\*.metadata.collectedTimestamp | string | `gc time` | 2019-11-02T00:00:00Z |
action_result.data.\*.events.\*.metadata.eventTimestamp | string | `gc time` | 2019-11-01T23:57:46Z |
action_result.data.\*.events.\*.metadata.eventType | string | | NETWORK_DNS |
action_result.data.\*.events.\*.metadata.productName | string | | ExtraHop |
action_result.data.\*.events.\*.network.applicationProtocol | string | | DNS |
action_result.data.\*.events.\*.network.dns.answers.\*.data | string | `ip` | 151.101.32.203 |
action_result.data.\*.events.\*.network.dns.answers.\*.name | string | | gateway.answerscloud.com |
action_result.data.\*.events.\*.network.dns.answers.\*.ttl | numeric | | 11111 |
action_result.data.\*.events.\*.network.dns.answers.\*.type | numeric | | 1 |
action_result.data.\*.events.\*.network.dns.questions.\*.name | string | | gateway.answerscloud.com |
action_result.data.\*.events.\*.network.dns.questions.\*.type | numeric | | 1 |
action_result.data.\*.events.\*.network.dns.response | boolean | | True False |
action_result.data.\*.events.\*.network.http.responseCode | numeric | | 200 |
action_result.data.\*.events.\*.principal.hostname | string | `host name` | franklin-guzman-laptop |
action_result.data.\*.events.\*.principal.ip | string | `ip` | 10.0.29.236 |
action_result.data.\*.events.\*.principal.mac | string | `gc mac` | ae:7d:81:1f:79:a0 |
action_result.data.\*.events.\*.target.ip | string | `ip` | 8.8.8.8 |
action_result.data.\*.eventsSummary.\*.count | numeric | | 3000 |
action_result.data.\*.eventsSummary.\*.eventType | string | | NETWORK_DNS |
action_result.data.\*.uri | string | | https://demodev.backstory.chronicle.security/assetResults?assetIdentifier=10.5.29.232&referenceTime=2020-06-30T16%3A59%3A40Z&selectedList=AssetViewTimeline&startTime=2020-07-07T09%3A59%3A54Z&endTime=2020-07-22T09%3A59%3A54Z |
action_result.summary.total_events | numeric | | 3000 |
action_result.message | string | | Total events: 3000 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'domain reputation'

Derive the reputation of the specified domain artifact (The reputation can be either of 'Malicious', 'Suspicious', and 'Unknown')

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain_name** | required | Specify a domain name | string | `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain_name | string | `domain` | wp.com |
action_result.data.\*.reputation | string | | Malicious |
action_result.data.\*.sources.\*.addresses.\*.domain | string | `domain` | wp.com |
action_result.data.\*.sources.\*.addresses.\*.port | numeric | | 80 |
action_result.data.\*.sources.\*.category | string | | Malware Command and Control Server |
action_result.data.\*.sources.\*.confidenceScore.strRawConfidenceScore | string | | 22 |
action_result.data.\*.sources.\*.firstActiveTime | string | `gc time` | 2020-03-07T00:00:00Z |
action_result.data.\*.sources.\*.lastActiveTime | string | `gc time` | 2020-03-07T00:00:00Z |
action_result.data.\*.sources.\*.rawSeverity | string | | High |
action_result.data.\*.sources.\*.sourceUrl | string | `url` | https://tools.emergingthreats.net/docs/ET%20Intelligence%20Rep%20List%20Tech%20Description.pdf |
action_result.data.\*.uri | string | `url` | https://demodev.backstory.chronicle.security/domainResults?domain=wp.com&selectedList=DomainViewDistinctAssets&whoIsTimestamp=2020-07-06T19%3A09%3A01.099580930Z |
action_result.summary.reputation | string | | Malicious |
action_result.message | string | | Reputation: Malicious |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'ip reputation'

Derive the reputation of the specified destination IP address artifact (The reputation can be either of 'Malicious', 'Suspicious', and 'Unknown')

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**destination_ip_address** | required | Specify a destination IP address | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.destination_ip_address | string | `ip` | 45.64.104.167 |
action_result.data.\*.reputation | string | | Suspicious |
action_result.data.\*.sources.\*.addresses.\*.domain | string | `domain` | psoftdevserver.in |
action_result.data.\*.sources.\*.addresses.\*.ipAddress | string | `ip` | 45.64.104.167 |
action_result.data.\*.sources.\*.addresses.\*.port | numeric | | 80 |
action_result.data.\*.sources.\*.category | string | | Drop site for logs or stolen credentials |
action_result.data.\*.sources.\*.confidenceScore.strRawConfidenceScore | string | | 24 |
action_result.data.\*.sources.\*.firstActiveTime | string | `gc time` | 2018-12-26T00:00:00Z |
action_result.data.\*.sources.\*.lastActiveTime | string | `gc time` | 2019-12-04T00:00:00Z |
action_result.data.\*.sources.\*.rawSeverity | string | | Medium |
action_result.data.\*.sources.\*.sourceUrl | string | `url` | https://tools.emergingthreats.net/docs/ET%20Intelligence%20Rep%20List%20Tech%20Description.pdf |
action_result.data.\*.uri | string | `url` | https://demodev.backstory.chronicle.security/destinationIpResults?ip=45.64.104.167&referenceTime=2020-07-06T19%3A10%3A22.181506788Z&selectedList=IpViewDistinctAssets |
action_result.summary.reputation | string | | Suspicious |
action_result.message | string | | Reputation: Suspicious |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list alerts'

List all of the security alerts tracked within the enterprise on particular assets and|or users for the specified time

Type: **investigate** \
Read only: **True**

The user can specify the [Alert Type] to fetch. If the user doesn't provide any of the time-related action parameters, the action will perform a search for the last three days. If the user provides [Time Range] and other time-related action parameters, the priority will be given to the [Time Range] action parameter and the search will be performed according to its given value.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**time_range** | optional | Specify the time range of the search (Use this format <digit>\<d/h/m/s> where d=Days, h=Hours, m=Minutes, s=Seconds) | string | `gc time range` |
**start_time** | optional | Specify the start time of the search (Use this format yyyy-MM-ddTHH:mm:ssZ where y=Year, M=Month, d=Day, H=Hour, m=Minutes, s=Seconds) | string | `gc time` |
**end_time** | optional | Specify the end time of the search (Use this format yyyy-MM-ddTHH:mm:ssZ where y=Year, M=Month, d=Day, H=Hour, m=Minutes, s=Seconds) | string | `gc time` |
**limit** | optional | Specify the maximum number of results to return. You can specify between 1 and 100,000. (Default is 10,000) | numeric | |
**alert_type** | optional | Specify the type of alerts to fetch | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.alert_type | string | | Asset Alerts User Alerts All |
action_result.parameter.end_time | string | `gc time` | 2019-11-10T00:00:00Z |
action_result.parameter.limit | numeric | | 10000 |
action_result.parameter.start_time | string | `gc time` | 2019-11-01T00:00:00Z |
action_result.parameter.time_range | string | `gc time range` | 30d |
action_result.data.\*.alerts.\*.alertInfos.\*.name | string | | Suspicious download by Office Application |
action_result.data.\*.alerts.\*.alertInfos.\*.rawLog | string | | SnVuIDIyIDE0OjU5OjU3IDEwLjAuMzAuNzMgam9fYzdmY2E5ODItNGFkOC00MzkyLTliMTktYTM2ODQ5MmY1ZDE0IGJldHR5LWRlY2Fyby1wYyBIaWdoIFN1c3BpY2lvdXMgZG93bmxvYWQgYnkgT2ZmaWNlIEFwcGxpY2F0aW9u |
action_result.data.\*.alerts.\*.alertInfos.\*.severity | string | | High |
action_result.data.\*.alerts.\*.alertInfos.\*.sourceProduct | string | | Rule Generated Alert [jo_c7fca982-4ad8-4392-9b19-a368492f5d14] |
action_result.data.\*.alerts.\*.alertInfos.\*.timestamp | string | `gc time` | 2020-06-22T14:59:57Z |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.about.\*.hostname | string | | betty-decaro-pc |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.metadata.collectedTimestamp | string | | 2019-02-12T23:26:52.569Z |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.metadata.eventTimestamp | string | | 2020-12-01T20:48:43Z |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.metadata.eventType | string | | NETWORK_HTTP |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.metadata.ingestedTimestamp | string | | 2020-12-04T15:53:57.066889Z |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.metadata.productEventType | string | | THREAT - vulnerability |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.metadata.productLogId | string | | 9100631352310467889 |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.metadata.productName | string | | Example product |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.metadata.vendorName | string | | Example vendor |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.network.applicationProtocol | string | | HTTP |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.network.http.method | string | | GET |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.network.http.referralUrl | string | | Unknown |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.network.http.responseCode | numeric | | 200 |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.network.http.userAgent | string | | Unknown |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.network.ipProtocol | string | | TCP |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.network.receivedBytes | string | | 926318 |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.network.sentBytes | string | | 3112 |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.principal.port | numeric | | 55250 |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.principal.user.userid | string | | stanlee4@acme.com |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.securityResult.\*.description | string | | Allowed |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.securityResult.\*.ruleName | string | | QA-RULE-57 |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.securityResult.\*.severity | string | | HIGH |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.securityResult.\*.severityDetails | string | | Medium |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.securityResult.\*.summary | string | | Internet Services : Malicious URL |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.target.hostname | string | | oli-materlik.de |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.target.port | numeric | | 80 |
action_result.data.\*.alerts.\*.alertInfos.\*.udmEvent.target.url | string | | http://oli-materlik.de/live/wjeos17/ |
action_result.data.\*.alerts.\*.alertInfos.\*.uri | string | `url` | https://demodev.backstory.chronicle.security/assetResults?assetIdentifier=david-lee-laptop&referenceTime=2020-06-29T16%3A00%3A01Z&selectedList=AssetViewTimeline&startTime=2020-06-29T15%3A55%3A01Z&endTime=2020-06-29T16%3A05%3A01Z&selectedAlert=1998215878&selectedEventTimestamp=2020-06-29T16%3A00%3A01Z |
action_result.data.\*.alerts.\*.alertSummary.\*.count | numeric | | 3 |
action_result.data.\*.alerts.\*.alertSummary.\*.name | string | | Suspicious download by Office Application |
action_result.data.\*.alerts.\*.alertSummary.\*.occurrences | string | | 2020-06-29T16:00:01Z |
action_result.data.\*.alerts.\*.asset.assetIpAddress | string | `ip` | 10.0.29.109 |
action_result.data.\*.alerts.\*.asset.hostname | string | `host name` | betty-decaro-pc |
action_result.data.\*.alerts_assets_association.\*.affected_assets.assetIpAddress | string | `ip` | 10.0.29.109 |
action_result.data.\*.alerts_assets_association.\*.affected_assets.hostname | string | | testuser-pc |
action_result.data.\*.alerts_assets_association.\*.alert_name | string | | Suspicious download by Office Application |
action_result.data.\*.alerts_assets_association.\*.asset_count | numeric | | 1 |
action_result.data.\*.alerts_users_association.\*.affected_users.email | string | `email` | test_user@gmail.com |
action_result.data.\*.alerts_users_association.\*.affected_users.username | string | `gc username` | test_user |
action_result.data.\*.alerts_users_association.\*.alert_name | string | | Unspecified |
action_result.data.\*.alerts_users_association.\*.user_count | numeric | | 3 |
action_result.data.\*.userAlerts.\*.alertInfos.\*.name | string | | Unspecified |
action_result.data.\*.userAlerts.\*.alertInfos.\*.rawLog | string | | eyJDcmVhdGlvblRpbWUiOiAiMjAyMC0wOS0wN1QxOTo0Njo0My4yMjQrMDA6MDAiLCAiQ2xpZW50SVAiOiAiMTAzLjIwMi4xNDMuMjEzIiwgIkV4Y2hhbmdlRGV0YWlscyI6IHsiRnJvbSI6ICJ0b255QHN0YXJraW5kdXN0cmllcy5jb20iLCAiSW50ZXJuZXRNZXNzYWdlSWQiOiAiYzE2ZWYxY2ItNzA1MC00NmM4LWEwNmItNzEyYmY0MzI0NGYzQGUzN2U2ZjcwY2Q3YS5wcm9kLm91dGxvb2suY29tIiwgIk1lc3NhZ2VUaW1lIjogIjIwMjAtMDktMDdUMTk6NDY6MzcuMjI0KzAwOjAwIiwgIk5ldHdvcmtNZXNzYWdlSWQiOiAiNzA5YTdjYzUtMzVlZi00ZmVjLWE2MmUtMDgwZWUxZTE1NDEyIiwgIlJlY2lwaWVudHMiOiBbImNhbGlmb3JuaWFAYWNtZS5jb20iXSwgIlN1YmplY3QiOiAiSW52b2ljZSBmb3IgR29vZHMifSwgIklkIjogImY0ZTg4MGY0LWQ0N2EtNDc3Yi05NWIyLWNhMzVjMzc3NTJlYyIsICJPYmplY3RJZCI6ICJjYWxpZm9ybmlhQGFjbWUuY29tIiwgIk9wZXJhdGlvbiI6ICJTdXBlcnZpc29yeVJldmlld09MQXVkaXQiLCAiT3JnYW5pemF0aW9uSWQiOiAiOGNjYTQxMTktNDE1NS00NTY5LWJjOTEtNTQxNTY2YjhjMWYyIiwgIlJlY29yZFR5cGUiOiA2OCwgIlJlc3VsdFN0YXR1cyI6ICJUaHJlYXQgTW9kZWwgUG9zaXRpdmUgU2NvcmU6NzgiLCAiVXNlcklkIjogImNhbGlmb3JuaWEiLCAiVXNlcktleSI6ICI1MzY0MTY2NjYwIiwgIlVzZXJUeXBlIjogMCwgIlZlcnNpb24iOiAxLCAiV29ya2xvYWQiOiAiRXhjaGFuZ2UiLCAiU2VjdXJpdHlDb21wbGlhbmNlQ2VudGVyRXZlbnRUeXBlIjogMH0= |
action_result.data.\*.userAlerts.\*.alertInfos.\*.sourceProduct | string | | Example product |
action_result.data.\*.userAlerts.\*.alertInfos.\*.timestamp | string | | 2020-09-07T19:46:43Z |
action_result.data.\*.userAlerts.\*.alertInfos.\*.udmEvent.metadata.eventTimestamp | string | | 2020-09-07T19:46:43Z |
action_result.data.\*.userAlerts.\*.alertInfos.\*.udmEvent.metadata.eventType | string | | EMAIL_TRANSACTION |
action_result.data.\*.userAlerts.\*.alertInfos.\*.udmEvent.metadata.ingestedTimestamp | string | | 2020-09-10T01:59:40.639434Z |
action_result.data.\*.userAlerts.\*.alertInfos.\*.udmEvent.metadata.productEventType | string | | SupervisoryReviewOLAudit |
action_result.data.\*.userAlerts.\*.alertInfos.\*.udmEvent.metadata.productName | string | | Example product |
action_result.data.\*.userAlerts.\*.alertInfos.\*.udmEvent.metadata.vendorName | string | | Example vendor |
action_result.data.\*.userAlerts.\*.alertInfos.\*.udmEvent.network.email.from | string | | tony@starkindustries.com |
action_result.data.\*.userAlerts.\*.alertInfos.\*.udmEvent.principal.user.userid | string | | california |
action_result.data.\*.userAlerts.\*.alertInfos.\*.udmEvent.securityResult.\*.confidence | string | | HIGH_CONFIDENCE |
action_result.data.\*.userAlerts.\*.alertInfos.\*.udmEvent.securityResult.\*.confidenceDetails | string | | 78 |
action_result.data.\*.userAlerts.\*.alertInfos.\*.udmEvent.securityResult.\*.severity | string | | HIGH |
action_result.data.\*.userAlerts.\*.alertInfos.\*.udmEvent.securityResult.\*.summary | string | | Threat Model Positive Score:78 |
action_result.data.\*.userAlerts.\*.alertInfos.\*.udmEvent.target.application | string | | Example application |
action_result.data.\*.userAlerts.\*.user.email | string | `email` | testuser@gmail.com |
action_result.data.\*.userAlerts.\*.user.email | string | | stanlee1@acme.com |
action_result.data.\*.userAlerts.\*.user.username | string | `gc username` | testuser |
action_result.data.\*.userAlerts.\*.userAlertSummary.\*.count | numeric | | 1 |
action_result.data.\*.userAlerts.\*.userAlertSummary.\*.name | string | | Unspecified |
action_result.data.\*.userAlerts.\*.userAlertSummary.\*.occurrences | string | | 2020-09-07T19:46:44Z |
action_result.summary.total_alerts | numeric | | 728 |
action_result.summary.total_asset_alerts | numeric | | 153 |
action_result.summary.total_assets_with_alerts | numeric | | 7 |
action_result.summary.total_user_alerts | numeric | | 4 |
action_result.summary.total_users_with_alerts | numeric | | 3 |
action_result.message | string | | Total assets with alerts: 7, Total alerts: 728 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list rules'

List the latest versions of the rules created in the Detection Engine within the enterprise

Type: **investigate** \
Read only: **True**

If the user doesn't provide any value in the [Limit] action parameter, then the action will fetch 1000 rules (or less, if there are lesser rules created in the Detection Engine within the enterprise).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**limit** | optional | Specify the number of rules to return (Default is 1000) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 1000 |
action_result.data.\*.rules.\*.alertingEnabled | boolean | | True |
action_result.data.\*.rules.\*.compilationError | string | | generic::invalid_argument: validating rule: invalid regex pattern: \*/../vpns/\*: error parsing regexp: missing argument to repetition operator: `\*` line: 10 column: 36-49 |
action_result.data.\*.rules.\*.compilationState | string | | SUCCEEDED |
action_result.data.\*.rules.\*.liveRuleEnabled | boolean | | True |
action_result.data.\*.rules.\*.metadata.author | string | | Test Author |
action_result.data.\*.rules.\*.metadata.category | string | | Initial Access/Phishing |
action_result.data.\*.rules.\*.metadata.created | string | | 2021-01-25 |
action_result.data.\*.rules.\*.metadata.description | string | | Detects known malicious service installs that only appear in cases of lateral movement, credential dumping and other suspicious activity License: https://github.com/Neo23x0/sigma/blob/master/LICENSE.Detection.Rules.md. |
action_result.data.\*.rules.\*.metadata.logsource | string | | windows |
action_result.data.\*.rules.\*.metadata.product | string | | windows |
action_result.data.\*.rules.\*.metadata.reference | string | | https://tdm.socprime.com/tdm/info/GSl0T6YKFl3J |
action_result.data.\*.rules.\*.metadata.severity | string | | Medium |
action_result.data.\*.rules.\*.metadata.technique | string | | T1566 |
action_result.data.\*.rules.\*.metadata.updated | string | | 2020-01-20 |
action_result.data.\*.rules.\*.metadata.version | string | | 0.01 |
action_result.data.\*.rules.\*.metadata.yara_version | string | | YL2.0 |
action_result.data.\*.rules.\*.ruleId | string | `gc rule id` | ru_6996bc7a-3cbd-46c6-ad6d-2cec6f46744e |
action_result.data.\*.rules.\*.ruleName | string | | malicious_service_installations |
action_result.data.\*.rules.\*.ruleText | string | | rule malicious_service_installations { meta: author = \]"Test Author" description = "Detects known malicious service installs that only appear in cases of lateral movement, credential dumping and other suspicious activity License: https://github.com/Neo23x0/sigma/blob/master/LICENSE.Detection.Rules.md." reference = "[]" version = "0.01" created = "2021-01-25" logsource = "windows" events: ($selection.metadata.product_log_id = "7045" and (($selection.target.process.command_line = "WCESERVICE" or $selection.target.process.command_line = "WCE SERVICE") or $selection.target.process.command_line = "\\\\PAExec" or $selection.target.process.command_line = "winexesvc.exe" or $selection.target.process.command_line = "\\\\DumpSvc.exe" or $selection.target.process.command_line = "mssecsvc2.0" or $selection.target.process.command_line = " net user " or ($selection.target.process.command_line = "pwdump" or $selection.target.process.command_line = "gsecdump" or $selection.target.process.command_line = "cachedump"))) condition: $selection } |
action_result.data.\*.rules.\*.versionCreateTime | string | | 2021-01-28T12:34:50.901151Z |
action_result.data.\*.rules.\*.versionId | string | `gc rule id` | ru_6996bc7a-3cbd-46c6-ad6d-2cec6f46744e@v_1611837290_901151000 |
action_result.summary.total_rules | numeric | | 45 |
action_result.message | string | | Total rules: 45 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list detections'

List all the detections for the specific versions of the given Rule ID(s)

Type: **investigate** \
Read only: **True**

The comma-separated [Rule ID(s)] can be provided with or without versionId appended to each Rule ID. If the user doesn't provide any of the time-related action parameters, the action will perform a search for the last three days. If the user provides [Time Range] and other time-related action parameters, the priority will be given to the [Time Range] action parameter and the search will be performed according to its given value.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**rule_ids** | required | Comma-separated Rule ID(s) (with or without versionId) | string | `gc rule id` |
**alert_state** | optional | Alert State to filter the detections | string | |
**time_range** | optional | Specify the time range of the search (Use this format <digit>\<d/h/m/s> where d=Days, h=Hours, m=Minutes, s=Seconds) | string | `gc time range` |
**start_time** | optional | Specify the start time of the search (Use this format yyyy-MM-ddTHH:mm:ssZ where y=Year, M=Month, d=Day, H=Hour, m=Minutes, s=Seconds) | string | `gc time` |
**end_time** | optional | Specify the end time of the search (Use this format yyyy-MM-ddTHH:mm:ssZ where y=Year, M=Month, d=Day, H=Hour, m=Minutes, s=Seconds) | string | `gc time` |
**limit** | optional | Specify the maximum number of detections to return (Default is 10,000) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.alert_state | string | | ALERTING NOT_ALERTING ALL |
action_result.parameter.end_time | string | `gc time` | 2019-11-10T00:00:00Z |
action_result.parameter.limit | numeric | | 10000 |
action_result.parameter.rule_ids | string | `gc rule id` | ru_e6abfcb5-1b85-41b0-b64c-695b3250436f ru_e6abfcb5-1b85-41b0-b64c-695b3250436f,ru_746bd6d6-6b84-4007-b74c-ec90c7306a71 ru_e6abfcb5-1b85-41b0-b64c-695b3250436f@v_1602631093_146879000 ru_e6abfcb5-1b85-41b0-b64c-695b3250436f@v_1602631093_146879000,ru_746bd6d6-6b84-4007-b74c-ec90c7306a71 |
action_result.parameter.start_time | string | `gc time` | 2019-11-01T00:00:00Z |
action_result.parameter.time_range | string | `gc time range` | 3d 24h 60m 3600s |
action_result.data.\*.detections.\*.collectionElements.\*.label | string | | event |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.metadata.eventTimestamp | string | | 2020-11-11T18:21:56.234Z |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.metadata.eventType | string | | NETWORK_DNS |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.metadata.ingestedTimestamp | string | | 2020-11-11T18:28:20.520884Z |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.metadata.productName | string | | ExtraHop |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.network.applicationProtocol | string | | DNS |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.network.dns.answers.\*.data | string | | 130.211.13.189 |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.network.dns.answers.\*.name | string | | nxtck.com |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.network.dns.answers.\*.ttl | numeric | | 11111 |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.network.dns.answers.\*.type | numeric | | 1 |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.network.dns.questions.\*.name | string | | manifest.prod.boltdns.net |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.network.dns.questions.\*.type | numeric | | 1 |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.network.dns.response | boolean | | True |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.principal.hostname | string | | test-user-laptop |
action_result.data.\*.detections.\*.createdTime | string | | 2020-11-11T20:46:02.016034Z |
action_result.data.\*.detections.\*.detection.\*.alertState | string | | ALERTING NOT_ALERTING |
action_result.data.\*.detections.\*.detection.\*.detectionFields.\*.key | string | | client_ip |
action_result.data.\*.detections.\*.detection.\*.detectionFields.\*.value | string | | 10.0.5.130 |
action_result.data.\*.detections.\*.detection.\*.ruleId | string | `gc rule id` | ru_746bd6d6-6b84-4007-b74c-ec90c7306a71 |
action_result.data.\*.detections.\*.detection.\*.ruleName | string | | dns_events_on_timeline |
action_result.data.\*.detections.\*.detection.\*.ruleType | string | | MULTI_EVENT |
action_result.data.\*.detections.\*.detection.\*.ruleVersion | string | `gc rule id` | ru_746bd6d6-6b84-4007-b74c-ec90c7306a71@v_1604081489_593503000 |
action_result.data.\*.detections.\*.detection.\*.urlBackToProduct | string | | https://demodev.backstory.chronicle.security/ruleDetections?ruleId=ru_746bd6d6-6b84-4007-b74c-ec90c7306a71&selectedList=RuleDetectionsViewTimeline&selectedDetectionId=de_0088100f-b8d8-f29c-4766-b05de66c68e8&selectedTimestamp=2020-11-11T18:48:00Z |
action_result.data.\*.detections.\*.detectionTime | string | | 2020-11-11T18:48:00Z |
action_result.data.\*.detections.\*.id | string | | de_0088100f-b8d8-f29c-4766-b05de66c68e8 |
action_result.data.\*.detections.\*.timeWindow.endTime | string | | 2020-11-11T18:48:00Z |
action_result.data.\*.detections.\*.timeWindow.startTime | string | | 2020-11-11T17:48:00Z |
action_result.data.\*.detections.\*.type | string | | RULE_DETECTION |
action_result.data.\*.detections_summary.\*.detections_count | numeric | | 2 |
action_result.data.\*.detections_summary.\*.rule_id | string | `gc rule id` | ru_746bd6d6-6b84-4007-b74c-ec90c7306a71 |
action_result.data.\*.invalid_rule_ids.\*.rule_id | string | | abcd |
action_result.data.\*.rule_ids_with_partial_detections.\*.rule_id | string | | ru_746bd6d6-6b84-4007-b74c-ec90c7306a71 |
action_result.data.\*.detections.\*.detection.\*.ruleLabels.\*.key | string | | author |
action_result.data.\*.detections.\*.detection.\*.ruleLabels.\*.value | string | | rule1 |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.target.hostname | string | | dhcp_server |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.network.dhcp.type | string | | ACK |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.network.dhcp.chaddr | string | | 0d:60:ff:08:2c:ea |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.network.dhcp.giaddr | string | | 10.0.5.64 |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.network.dhcp.opcode | string | | BOOTREPLY |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.network.dhcp.yiaddr | string | | 10.0.5.64 |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.network.dhcp.clientHostname | string | | |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.network.dhcp.clientIdentifier | string | | |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.network.dhcp.leaseTimeSeconds | numeric | | 14410 |
action_result.data.\*.detections.\*.collectionElements.\*.references.\*.event.principal.asset.hostname | string | | |
action_result.summary.total_detections | numeric | | 5 |
action_result.message | string | | Total detections: 5 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'on poll'

Action handler for the on poll ingest functionality

Type: **ingest** \
Read only: **True**

The action will ingest all of the 3rd party security alerts tracked within the enterprise and domain IoCs matches discovered within the enterprise as per the selected ingestion run mode.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_time** | optional | Parameter ignored in this app | numeric | |
**end_time** | optional | Parameter ignored in this app | numeric | |
**container_count** | optional | Parameter ignored in this app | numeric | |
**artifact_count** | optional | Parameter ignored in this app | numeric | |

#### Action Output

No Output

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2025 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
