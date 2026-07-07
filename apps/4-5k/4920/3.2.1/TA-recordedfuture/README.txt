Recorded Future App for Splunk
----------------------------------------
    Author: Recorded Future
    Version: 3.2.1
    Source type(s): none
    Input requirements:
    Index-time operations: false
    Supported product(s): Recorded Future API

Using this Add-on:
----------------------------------------
    Configuration: Manual
    Ports for automatic configuration: None
    Scripted input setup: Not applicable

    Usage: This TA adds the following features:

    Modular inputs
    ----------------------
    None

    Searches and reports
    ----------------------

    1. Latest updates of all risklists
        This command is used list when each configured risklist modular input last downloaded the corresponding risklist.

    2. All logs from the App
        Returns log entries for the app.

    3. Validate app deployment
        Performs various checks on the deployment to verify that it is functioning correctly or help troubleshooting if not.

    4. Recorded Future - Download Risk Lists
        This search will synchronize all configured risk lists and threat feeds. A risk list
        is only downloaded if an update is available.

    5. Recorded Future - Sync UI Elements
        The majority of the views available in Recorded Future for Splunk are maintained in
        Recorded Future's API. This way, improvements and fixes can be made available without
        a re-install of the app. This search synchronizes the local versions of the views
        with the API.

    6. Recorded Future - Sync Use Cases
        This search synchronize the list of use cases (ex enrichment views, correlation use
        cases etc) available in the app.

    Custom REST endpoint
    --------------------

    The app provides a custom REST endpoint that implements most of it's functionality.

    Lookup tables
    -------------

    The app creates a number of CSV files in the lookups folder that are available as lookup tables.

    Macros
    ------

    You can see the details of the macros below by viewing them in the advanced search section of the splunk UI or by viewing the contents to the macros.conf file.

    1. unpack_metrics

        Used to unpack the metrics field used in the enrichment dashboards.

    2. unpack_riskyCIDRIPs

        Used to unpack the riskyCIDRIps field used in the IP enrichment dashboard.

    3. to_date(1)

        Used to parse and reformat timestamps returned from Recorded Future. Returns the date.


    4. to_time(1)

        Used to parse and reformat timestamps returned from Recorded Future. Returns the date and time.


    5. to_splunk_time(1)

        Used to parse and reformat timestamps returned from Recorded Future. Returns the date and time in a Splunk timestamp format.


    6. get_updated_time(1)

        Used to format the timestamp of risk list updates.


    Workflow Actions
    ----------------
    rf_intelcard_lookup_<field>

    There are two types of workflows setup:
    - Workflows to open a new tab with the Recorded Future pivot search for the entity.
    - Workflows to open a new tab with the app's enrichment dashboard for the category of the entity.

    The following fields offer both to these workflows:
        IP_Address
        Source_Computer
        cve
        dest
        dest_ip
        domain
        dst
        fqdn
        ip
        src
        src_ip
        target
        target_url
        targets
        url

    Installation
    ------------
    A valid Recorded Future API token is required for this app.  Please see support.recordedfuture.com for more details.

    To configure this add-on:

    1. Install the app by uploading a package or from Splunkbase
    2. Restart Splunk if prompted
    3. When launching the app for the first time it is necessary to add the API token in Configuration->Configuration.
    4. A Proxy is optional
    5. Click save after entering desired information

