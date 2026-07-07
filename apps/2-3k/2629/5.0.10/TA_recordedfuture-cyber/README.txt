Recorded Future Splunk Technology Add-on
----------------------------------------
    Author: Recorded Future
    Version: 5.0.10
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
    --------------
    
    1. recorded_future_risklist
        These modular inputs are used to download the latest risklists from Recorded Future. Five categories of risklists are supported: ip, domain, vulnerability, hash and url. Default inputs are configured for each of these categories. For Recorded Future Fusion customers additional custom risklists can be added as needed.

    2. recorded_future_alerts
        These modular inputs are used to fetch status of alerts setup in Recorded Future's system. A default input is configured which fetches all alerts.

    Searches and reports
    ----------------------

    1. Latest updates of all risklists
        This command is used list when each configured risklist modular input last downloaded the corresponding risklist.

    2. All logs from the App
        Returns log entries for the app.

    3. Validate app deployment
        Performs various checks on the deployment to verify that it is functioning correctly or help troubleshooting if not.

    Each of these searches has a corresponding report.
    
    Lookup tables
    -------------

    Each active risklist modular input will create a CSV file in the lookups folder that is available as a lookup table. The name will be that of the modular input with a csv suffix (ex a modular input named custom will yield a csv file custom.csv).

    Macros
    ------
    
    You can see the details of the macros below by viewing them in the advanced search section of the splunk UI or by viewing the contents to the macros.conf file.
    
    1. format_evidence
    
        Used to expand and format the EvidenceDetails field provided by risklists.

    2. rf_hits(1)
        Used to correlate IP numbers against a IP category risklist. Depreciation warning: this macro will be retired in a future release.

    3. unpack_metrics

        Used to unpack the metrics field used in the enrichment dashboards.

    4. unpack_relatedEntities(1)

        Used to unpack related entities of a specified type. Used in the enrichment dashboards.

    5. unpack_riskyCIDRIPs

        Used to unpack the riskyCIDRIps field used in the IP enrichment dashboard.

    6. to_date(1)

        Used to parse and reformat timestamps returned from Recorded Future. Returns the date.


    6. to_time(1)

        Used to parse and reformat timestamps returned from Recorded Future. Returns the date and time.


    6. to_splunk_time(1)

        Used to parse and reformat timestamps returned from Recorded Future. Returns the date and time in a Splunk timestamp format.


    Workflow Actions
    ----------------
    1. rf_intelcard_lookup_<field>

        There are two types of workflows setup:
	    - Workflows to open a new tab with the Recorded Future intelligence card for the entity.
	    - Workflows to open a new tab with the app's enrichment dashboard for the category of the entity.

        Workflows leading to IP intelligence cards: dest, dest_ip, dst, ip, IP_Address, Source_Computer src, src_ip, target, targets

	Workflows leading to IP enrichment dashboard: dest, dest_ip, dst, ip, IP_Address, Source_Computer src, src_ip, target, targets
    
        Workflows leading to domain intelligence cards: domain, fqdn

	Workflows leading to domain enrichment dashboard: domain, fqdn
    
        Workflows leading to hash intelligence cards: Application_Hash, file_hash, hash, md5, sha1

	Workflows leading to hash enrichment dashboard: Application_Hash, file_hash, hash, md5, sha1

	Workflows leading to vulnerability enrichment dashboard: cve

	Workflows leading to url enrichment dest, target_url, url

    Installation
    ------------
    A valid Recorded Future API token is required for this app.  Please see www.recordedfuture.com for more details.

    A complete installation guide can be found at /resources/Recorded Future Splunk App - Installation Guide.pdf
    
    To configure this add-on:

    1. Install the app by uploading a package or from Splunkbase
    2. Restart Splunk if prompted
    3. When launching the app for the first time it is necessary to add the API token in Configuration->Global configuration->Add-on Settings.
    4. A Proxy is optional
    5. Click save after entering desired information
