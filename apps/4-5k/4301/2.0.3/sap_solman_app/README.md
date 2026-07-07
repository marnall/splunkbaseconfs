# SAP Solman Technology Add-on for Splunk ITSI (SSTA)

## Overview

SSTA (formerly SSCM) includes SAP infrastructure monitoring and business data in Splunk enterprise operational intelligence analytics (both on-premise and cloud versions of SAP) alongside with other enterprise components.


## Release Notes

**Version 2.0.3**

WARNING - Breaking changes in version 2.0:

- Completely switched from PySlet to Requests-based ODATA client implementation. Changed state from experimental to stable
- Splunk ITSI support is has been dropped from SSTA Community and moved to SSTA Enterprise as a feature
- Allowing a limited number of SAP SolMan enabled metrics to ingest into Splunk

**Version 1.5.4**

- Add License

**Version 1.5.3**

- Update Copyright notice
- Fix issue with password masking
- Require encrypted connections (mandatory https links)

**Version 1.5.2**

- Updated logo
- Appinspect issues and warnings fixing

**Version 1.5.0**

- Python 3 support was added
- Page load ui bug fixed

**Version 1.4.4**

- Add Copyright notice

**Version 1.4.3**

- Fix bug with inputs update


**Version 1.4.2**

- Add Windows compatibility


**Version 1.4.1**

- Add more informative error messages on Setup dashboard.
- Add more verbose logging. Now debug messages become more informative. Useful for debuging and troubleshooting.
- Fix error handlin in Requests-based ODATA client implementation.


**Version 1.4.0**

- Switched from PySlet to Requests-based ODATA client implementation.
This release is experimental. If you will to test it - download version 1.4.0.
We discovered, that python PySlet library is less stable and a lot more complicated, than python requests library.
There was an issue, that Splunk didn`t close connections to SAP Solman. Using new version, this issue will be closed, because the requests-based implementation kills idle connections automatically.


**Version 1.3.2**

- Add automatic modular input log ingestion into \_internal index

**Version 1.3.0**

- Application setup page for initial modular input configuration
- Improved handling of Solman-provided KPI threshold information, support of "Info" status for the metrics with no threshold data
- Advanced modular input and dashboard handler logging support, improved troubleshooting capabilities
- Smart calculation of actual Solman metric update periods; this eliminates "N/A" values within ITSI service analyzer
- Support of non-standard splunkd port setup

**Version 1.2.0**

- Support of distributed ITSI deployment including ITSI cloud + Splunk Heavy Forwarder
- Navigation improvements for configuration page
- Improved input validation with verbose error messages for modular input creation
- Package rename: SAP Solman Connectivity module for Splunk ITSI to SAP Solman Technology Add-on for Splunk ITSI

**Version 1.1.0**

- Optimized performance for initial service creation with high number of metrics
- Improvements for Solman-ITSI metadata integration: thresholds, units of measurement, time period calculations
- UI enhancements: pagination, metrics disabling warning, error box in the configuration dashboard

**Version 1.0.0**

- First release
- Integration with Solution Manager  7.0 and upper versions
- Solman metrics retrieval throughout OData protocol
- Connectivity configuration
- Metrics auto discovery and  metrics ingestion configuration
- Seamless integration with ITSI.

## Value Added

- Splunk as a single source of Enterprise Data DNA - Ability to track SAP infrastructure and business data in a single enterprise solution alongside with other enterprise components
- Operational Insights. Baseline for enabling advanced correlative views with predictive analytics and machine learning.
- Easy migration to the cloud.



## Main Features

1. **Connects multiple SAP Solution Managers with Splunk instance.**  
Ability to connect to SolMan instances with granted permissions (See Configuration and SAP Prerequisites sections).

2. **Discovers each SAP Solution Manager metrics and adds the data into Splunk monitoring.**  
Customization of usage of existing metrics by including meaningful or excluding less important details from the monitoring.

3. **Ingests monitoring metrics into Splunk ITSI.**  
All the metrics chosen for ingestion will be instantly shown up on ITSI side. Predefined SAP metrics will be appropriately interpreted on ITSI side.



## Support

Contact information for asking questions and reporting issues:

[Operational\_Intelligence\_Support@epam.com](mailto:Operational\_Intelligence\_Support@epam.com)

## Download

Download the SSTA application from Splunkbase - [https://splunkbase.splunk.com/app/4301/](https://splunkbase.splunk.com/app/4301/)

## Requirements

- Splunk Enterprise 7.0 or later.  
This app is designed to ingest SAP Solman data into Splunk metrics index (added in Splunk 7.0).
- Splunk ITSI 4.0.1.
- System Landscape Requirements for SAP Solution Manager were described on [Monitor Systems - SAP Help Portal](https://help.sap.com/viewer/34eaf25a11d54485aecf05e041f78555/106/en-US/dfce9b553badcf07e10000000a44538d.html).

## SAP and Splunk Prerequisites

Before deploying the app, you must ensure the following:

1. You have activated the required OData Service **AI\_SYSMON\_OVERVIEW\_SRV** and **SAPUI5** application service **SM\_TM\_SYSMON** according to [App Implementation: Monitor Systems - SAP Help Portal](https://help.sap.com/viewer/34eaf25a11d54485aecf05e041f78555/106/en-US/6a8b9a55a5ddd007e10000000a44538d.html).

2. Authorization settings are required to be set in SAP Solution Manager and to fetch data using relevant OData service. Authorizations were described in Security Guide for SAP Fiori Apps – SAP Solution Manager 7.2 SPS8 [System Monitoring - SAP Help Portal](https://help.sap.com/viewer/265ae41071e34a8ea98c39acb9056ffb/7.2.08/en-US/55b6d286fe4e1a68e10000000a42189c.html).

3. Configuration System monitoring SAP landscape and custom metrics were described on [System Monitoring 7.2 - Setup and Configuration - SCN Wiki](https://wiki.scn.sap.com/wiki/display/TechOps/System+Monitoring+7.2+-+Setup+and+Configuration).

4. Add-on requires Splunk kvstore to be operational on the instance that it is deployed on. Make sure that it is not disabled.

5. Add-on is designed to store obtained data within metrics index. Create a metrics index on your indexer(s) (for example called solman\_metrics).

6. In distributed deployment option (see option 2 below), on ITSI environment, create a user that has the capabilities to create ITSI service via REST interface.


## Installation

There are two options for add-on deployment: standalone ITSI server and distributed option.
Versions 1.0.0 and 1.1.0 support only the first option.
Versions 1.2.0 and above support both.

In standalone ITSI option, the add-on is installed on the same Splunk instance that also has ITSI REST interface.
Here the ITSI Splunk instance must have direct network connectivity to SAP OData interface (be within organization's security perimeter).

The first option does not work well for ITSI in Splunk Cloud or other distributed environment when ITSI instance can not or should not access SAP instances directly.
In that case, install the add-on on Splunk Heavy Forwarder that is close to SAP instances.
It will forward all collected data to the Splunk indexers and create corresponding ITSI services using ITSI REST interface.

Install the technology add-on on either ITSI instance (option 1) or on Splunk Heavy Forwarder (option 2):

1. Log in to Splunk and go to Apps > Manage Apps.

2. Click install app from file.

3. Upload the app package file and click upload.


## Upgrading

### Upgrading from v1.2.0 to v1.3.0

Version 1.3.0 introduced initial setup page. In order to let the v1.3.0 app understand that the application has been previously configured, edit $SPLUNK\_HOME/etc/apps/sap\_solman\_app/local/app.conf adding the following stanza:
```
[install]
is_configured = 1
```
Starting with v1.3.0, the modular input instance has to be named as &quot;main\_input&quot;. Edit $SPLUNK\_HOME/etc/apps/sap\_solman\_app/local/inputs.conf so that the stanza is called:
```
[sap_solman_mi://main_input]
...
```
After these configuration preparations, proceed with application upgrade. This can be done using UI.

Once the upgrade is done, please wait for several hours to let the application learn the actual metric update intervals. This should help eliminating gray N/A values that could be present in pre-1.3 versions of the app for the metrics that are rarely updated. The more you wait, the more precise the update intervals become.

In order to apply the new threshold level logic, after upgrade, navigate to Solman Configuration Dashboard and perform the following:

1. Click **Disable all** button and hit **Save**
2. Enable back the relevant metrics and hit **Save**

This will enforce new threshold rules and update period intervals.


## Configuration

1. After installing the application, perform the initial setup
    * Go to the **Manage Apps** page and click **Set up**
    
    ![](d3b29896-77e2-11e9-9a50-0ad0e42e326c.png)

    ![](c6ed8c76-77db-11e9-a741-0ad0e42e326c.png)

    * Enter the Solman URL, user, and password. In case of standalone deployment option, do not enter ITSI REST-related fields. In case of distributed deployment, enter ITSI REST URL, user, and password. The recommended update interval is 300 seconds (5 minutes), this may be set to a higher value to reduce the load on Solman server. Choose the metrics index that has to be used for data ingestion.

    ![](c898fb14-77db-11e9-8fec-0ad0e42e326c.png)

    * Check use `new server version` if you want to use new Odata client.

    ![]()

2. Configure the metrics to be collected. On the first invocation, modular input populates solman\_metrics key-value store collection discovering all the systems and metrics available on SAP Solman. On the host having the add-on deployed, go to Solman Configuration Dashboard. Click on the button corresponding to the SAP system to be configured. Click on the sliders to enable or disable metrics collection. Once done, click on green Save button. Please wait for the Solman data to refresh before it gets into Splunk index (may take several minutes).  
    ![](44ce2ea8-f171-11e8-b5c9-021ec6cb6b4a.png)

3. Navigate to ITSI Service Analyzer dashboard. You will see the data from the configured system
    ![](b65be5e2-77db-11e9-8ba9-0ad0e42e326c.png)


## Troubleshooting

Use the troubleshooting dashboard within the app.
     ![](ca3d2a62-77db-11e9-80df-0ad0e42e326c.png)

By default, app logging level is set to WARN.

To increase logging verbosity, edit $SPLUNK\_HOME/etc/apps/sap\_solman\_app/local/log.conf adding the following stanzas:
```
[default]
log_level = DEBUG

[splunklib.modularinput.script]
log_level = DEBUG

[sap_solman_mi]
log_level = DEBUG
```

If still in trouble, ask a question on [Splunk Answers](https://answers.splunk.com/app/questions/4301.html) and email [Operational\_Intelligence\_Support@epam.com](mailto:Operational\_Intelligence\_Support@epam.com).


## Open Source Components

### simplePagination.js

Project repository [https://github.com/flaviusmatis/simplePagination.js/](https://github.com/flaviusmatis/simplePagination.js/)

Version number 1.6

### text.js

Project repository [https://github.com/requirejs/text](https://github.com/requirejs/text)

Version number 2.0.15


## Copyright, Licensing and Attribution

### SSTA application module

Copyright 2020 EPAM Systems

EULA [https://d38o4gzaohghws.cloudfront.net/static/misc/eula.html](https://d38o4gzaohghws.cloudfront.net/static/misc/eula.html)


### simplePagination.js

Copyright 2012, Flavius Matis

License [https://github.com/flaviusmatis/simplePagination.js/blob/master/LICENSE.txt](https://github.com/flaviusmatis/simplePagination.js/blob/master/LICENSE.txt)

### text.js

Copyright jQuery Foundation and other contributors

License [https://raw.githubusercontent.com/requirejs/text/master/LICENSE](https://raw.githubusercontent.com/requirejs/text/master/LICENSE)

### SAP

SAP, SAP Fiori are the trademarks or registered trademarks of SAP SE in Germany and in several other countries.
