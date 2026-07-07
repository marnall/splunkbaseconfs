## On Poll

Polling involves collecting information about the entity, including its detections and assignments. Users have the option to apply different filters to focus on specific entities and detections.

- ### Prerequisite for On Poll
  - This application requires permission to delete artifact(s).

  - By default, the automation user is selected to run the Vectra Cognito Detect Splunk SOAR ingestion action. (See **Asset Configuration**>**Asset Settings**>**Advanced**) The automation user does **NOT** have permission to delete the artifacts. This can cause duplication of detection artifacts.

  - In order to solve this problem, you must create a user of type **Automation** with **Administrator** role. Then, choose this user in your Vectra Cognito Detect Splunk SOAR **Asset Settings** under **Advanced**.

    **Administration**>**User Management**>**Users**\*\*> + User\*\*

    [![](/app_resource/vectracognitodetectsplunksoar_93878b88-0aad-45de-9505-8602deeab5e8/img/create_role.png)](/app_resource/vectracognitodetectsplunksoar_93878b88-0aad-45de-9505-8602deeab5e8/img/create_role.png)

    **Asset Settings** > **Advanced**

    [![](/app_resource/vectracognitodetectsplunksoar_93878b88-0aad-45de-9505-8602deeab5e8/img/asset_settings.png)](/app_resource/vectracognitodetectsplunksoar_93878b88-0aad-45de-9505-8602deeab5e8/img/asset_settings.png)

  - Ensure that the SOAR instance includes severities such as low, medium, high, and critical. Performing a test connectivity will generate these severities, with priority levels in the order of **Critical** > **High** > **Medium** > **Low**.

    **NOTE:** To check severity refer this path: **Administration** > **Event Settings** > **Severity**

  - **Manual Polling (POLL NOW)**

    - It will fetch the data when initiated, as per the corresponding asset configuration parameters. It does not store the last run context of the fetched data.

  - **Schedule/Interval Polling**

    - **Schedule Polling:** The ingestion action can be triggered at every specified time interval.
    - **Interval Polling:** The ingestion action can be triggered at every time range interval.
    - It retrieves data in each run, using the context stored from the previous ingestion. The last run's context for fetched data is saved, and subsequent data retrieval is based on the stored context values from the prior ingestion.
    - **NOTE:** If the user changes the filter related parameter or stored context while the schedule/interval polling is running, then the next polling cycle will start fetching the latest data according to the updated configured parameters.

## Explanation of the Asset Configuration Parameters

Configuration parameters of the asset impact the 'test connectivity' and various other actions within the application. The parameters specific to the test connectivity action are listed below.

- **Vectra Base URL:** Base URL of Vectra instance.

- **Verify Server Certificate:** Validate the authenticity of the server's certificate.

- **Vectra API Token:** API Token of Vectra instance.

  - **Action Parameter: Type of entities to fetch**

    - This parameter has two options - Account, Host.
    - These parameters are mainly used for additional filtering of entities. If no entity will be found with given entity type, there would be no detection or assignments ingested.

  - **Action Parameter: Comma-separated entity tags to filter entities for ingestion**

    - This parameter accepts comma-separated names of the entity tags.
    - It will filter entities which have any of the given tags.
    - **NOTE:** This asset parameter is case-insensitive.

  - **Action Parameter: Poll entity which certainty score is greater than equal to given value (0-100)**

    - This parameter accepts the integer value between 0 to 100.
    - It will filter the entities which certainty score is greater or equal to it's value.

  - **Action Parameter: Poll entity which threat score is greater than equal to given value (0-100)**

    - This parameter accepts the integer value between 0 to 100.
    - It will filter the entities which certainty score is greater or equal to it's value.

  - **Action Parameter: Filter detection category (On Poll)**

    - This parameter has these options
      - Command and Control
      - Botnet
      - Reconnaissance
      - Lateral Movement
      - Exfiltration
      - Info
      - All
    - These parameters are mainly used for additional filtering of detections. If no detections match the provided filter criteria, there will be no detections ingested.

  - **Action Parameter: Filter detection type (On Poll)**

    - This will filter detections with given type.
    - These parameters are mainly used for additional filtering of detections. If no detections match the provided filter criteria, there will be no detections ingested.
    - **NOTE:** This asset parameter is case-insensitive.

  - **Action Parameter: Start time for manual polling and first run of schedule polling( Valid ISO date and time format string)**

    - Schedule polling will start from given date and time. In case of schedule poll, this time will be considered for the very first polling cycle only. If the user changes this value after the first polling cycle, there won't be any effect as the time stored in state file will be prioritised after first polling cycle.
    - All entities would be fetched which have 'last_detection_timestamp' greater or equal to given data and time.
    - Only valid ISO format date and time is allowed. Examples are 2023-02-02, 2023-07-24T14:13:34Z.
    - If value is not given it will fetch past 3 days data from the current time.

  - **Action Parameter: Max entities to ingest for manual polling**

    - Restrict number of container(s) to get ingested for manual poll.

  - **Action Parameter: Max entities to ingest for schedule polling**

    - Restrict number of container(s) to get ingested for schedule poll.
