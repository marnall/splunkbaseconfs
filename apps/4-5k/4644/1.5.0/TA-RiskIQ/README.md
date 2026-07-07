RiskIQ Digital Footprint Add-on for Splunk
========================

OVERVIEW
--------

The RiskIQ Digital Footprint Add-on for Splunk is used to get data from the RiskIQ platform. For the dashboard with RiskIQ data, please install `(LEGACY) RiskIQ Digital Footprint App` for the legacy API and `RiskIQ Digital Footprint App` for the global inventory endpoint.

* Author - RiskIQ
* Version - 1.5.0
* Creates Index - False
* Prerequisites - RiskIQ API Key, Token, Business Org Name for data collection

## COMPATIBILITY MATRIX

* Browser: Google Chrome, Mozilla Firefox, Safari
* OS: Platform Independent
* Splunk Enterprise version: 8.1.X, 8.2.X
* Supported Splunk Deployment: Splunk Cluster, Splunk Standalone, and Distributed Deployment

## RELEASE NOTES

### Version 1.5.0

* Upgraded AOB from v3.0.1 to v4.0.0
* Upgraded iso8601 library from v0.1.12 to v1.0.2
* Added support for extracting field name with numbers.

### Version 1.4.0

* Added support for multiple accounts and inputs.
* Migrated events and global inventory assets scripted inputs to modular inputs.
* UI overhaul using Splunk Add-on Builder with all previous functionalities retained.
  * Add-on setup is now divided into 2 pages.
    * Configuration. (For API details, proxy and logging configuration)
    * Inputs. (For input configuration)
* Removed support for legacy assets.

### Version 1.3.0

* Added support to filter assets data based on tag, brand, or organization selection from the configuration page.

### Version 1.2.0

* Added the global inventory endpoint for assets data collection.
* Made the Add-on Python2 and Python3 compatible.

### Version 1.1.0

* Moved and Added lookups and custom commands in TA from the main app.
* Updated /event/search API data collection to use parameter scroll instead of offset to resolve the Internal Server Error.
* Added proxy support.
* Bifurcated assets and events data into different source types.
* Provided support for enabling/disabling data inputs.
* Provided support to collect only new and updated assets information.
* Added validation for API credentials in the setup page.

OPEN SOURCE COMPONENTS AND LICENSES
------------------------------

* Some of the components included in RiskIQ Digital Footprint Add-on for Splunk are licensed under free or open source licenses. We wish to thank the contributors to those projects.

* requests version 2.25.1 <https://requests.readthedocs.io/en/master/> (LICENSE <https://github.com/requests/requests/blob/master/LICENSE>)

* certifi version 2021.05.30 <https://pypi.python.org/pypi/certifi> (LICENSE <https://github.com/certifi/python-certifi/blob/master/LICENSE>)

* chardet version 4.0.0 <https://pypi.python.org/pypi/chardet> (LICENSE <https://github.com/chardet/chardet/blob/master/LICENSE>)

* idna version 2.10 <https://pypi.python.org/pypi/idna/> (LICENSE <https://github.com/kjd/idna/blob/master/LICENSE.rst>)

* urllib3 version 1.26.6 <https://pypi.python.org/pypi/urllib3/> (LICENSE <https://github.com/shazow/urllib3/blob/master/LICENSE.txt>)

* pytz version 2021.3 <http://pythonhosted.org/pytz> (LICENSE <https://pythonhosted.org/pytz/#license>)

THIRD PARTY LIBRARIES
------------------------------

* We have used external library iso8601(version: 1.0.2) to convert time in ISO 8601 format to epoch format.
  <https://pypi.python.org/pypi/iso8601>

# RECOMMENDED SYSTEM CONFIGURATION

* Because this Add-on runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
------------------------------------------

This Add-On can be set up in two ways:

1. Standalone Mode: Install the Add-on app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup.
2. Distributed Environment: Install Add-on on search head and Heavy forwarder.
    * Add-on resides on search head machine need not require any configuration here.
    * Add-on needs to be installed and configured on the Heavy forwarder system.
    * Execute the following command on Heavy forwarder to forward the collected data to the indexer.
      /opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997
    * On the Indexer machine, enable event listening on port 9997 (recommended by Splunk).
    * If you are using custom index define it on the indexer.
    * Add-on needs to be installed on search head for CIM mapping.

**Note: If you're using legacy assets data then please install the (LEGACY) RiskIQ Digital Footprint App.**

External Data Sources
---------------------

* We are using RiskIQ Events API and global inventory endpoint for data collection.

INSTALLATION
------------

Follow the below-listed steps to install an Add-on from the bundle:

* Download the App package.
* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package.
* Select `Upload` and follow the prompts.

UPGRADE
-------

#### Follow the below steps when upgrading from TA-RiskIQ 1.4.0 to 1.5.0

* Navigate to `RiskIQ Digital Footprint Add-on for Splunk -> Inputs`. Disable all the existing inputs.
* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package.
* Check the upgrade option.
* Select `Upload` and follow the prompts.
* Restart Splunk.

#### Follow the below steps when upgrading from TA-RiskIQ 1.3.0 to 1.4.0

* From the UI, navigate to `Settings -> Data Inputs -> Scripts`.
* Under the local inputs sections, find the RiskIQ inputs (`<`riskiq`>`_events|assets|gi_assets) that have been set-up and disable them.
* Then install the new version of the addon (1.4.0) and then follow the configuration steps.

**Note: For a given input/endpoint, the new input will use the corresponding checkpoint from the older version (if it exists), and thereafter, it will create its own checkpoint to be used in the future.**

#### Follow the below steps when upgrading from TA-RiskIQ 1.0.0 to 1.1.0

* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package.
* Check the upgrade option.
* Select `Upload` and follow the prompts.
* Restart Splunk.
* Navigate to `Settings->Data Inputs->Scripts` and disable the AccessRiskIQ.py.
* Enable riskiq_events.py and riskiq_assets.py to collect data of events and assets respectively.

CONFIGURATION
-------------

* After the installation, you'll be asked to restart Splunk. Click on Restart Now.
* After the restart, you need to set up the data collection. From the UI navigate to `Apps->RiskIQ Digital Footprint Add-on For Splunk`
* Users will be required to have admin_all_objects capability to configure RiskIQ Add-On. This Add-on allows a user to configure multiple accounts of RiskIQ Instance. In case a user is using the integration in the search head cluster environment, configuration on all the search cluster nodes will be overwritten as and when a user changes some configuration on any one of the search head cluster members. Hence a user should configure the integration on only one of the search head cluster members. Once the installation is done successfully, follow the below steps to configure.

## 1. Add RiskIQ Account

To configure the RiskIQ account, navigate to RiskIQ Add-On, click on "Configuration", go to the "Accounts" tab, click on the "Add" button and fill in the details asked, and click "Add". Field descriptions are as below:

| Field Name                 | Field Description                                 |
| -------------------------- | ------------------------------------------------- |
| Account Name`*`            | Unique name for your account                      |
| Business Org Name`*`       | Business Org's name to associate with the account |
| API Key`*`                 | API Token associated with your RiskIQ account     |
| API Secret`*`              | API Secret corresponding to your API Key          |
| Endpoints`*`               | Endpoints from which you want to collect data     |

**Note**: `*` denotes required fields

## 2. Configure Proxy (Required only if the requests should go via proxy server)

Navigate to RiskIQ Add-On, click on "Configuration", go to the "Proxy" tab, fill in the details asked, and click "Save". Field descriptions are as below:

| Field Name            | Field Description                                                              |
| -------------------   | ------------------------------------------------------------------------------ |
| Enable                | Enable/Disable proxy                                                           |
| Proxy Type`*`         | Type of proxy                                                                  |
| Host`*`               | Hostname/IP Address of the proxy                                               |
| Port`*`               | Port of proxy                                                                  |
| Username              | Username for proxy authentication (Username and Password are inclusive fields) |
| Password              | Password for proxy authentication (Username and Password are inclusive fields) |

**Note**: `*` denotes required fields

After enabling proxy, re-visit the "Account" tab, edit/create a new account and save it to verify if the proxy is working.

## 3. Configure Logging (Optional)

Navigate to RiskIQ Add-On, click on "Configuration", go to the "Logging" tab, select the preferred "Log level" value from the dropdown, and click "Save".

## 4. Create Data Inputs

This Add-On allows a user to configure multiple inputs to collect data from the RiskIQ instance. To create an input, navigate to RiskIQ Add-on, click on the "Inputs" tab, and then select the endpoint for which you want to create an input. Fill in the details asked and click "Add".

### 1. RiskIQ Events

Field descriptions are as below:

| Field Name       | Field Description                                                                   | Default Value       |
| ---------------- | ----------------------------------------------------------------------------------- | ------------------- |
| Name`*`          | Unique name of your data input.                                                     | None                |
| Interval`*`      | Time interval of input in seconds. Interval can be in the range of 30 to 86400 seconds. | 300                 |
| Index`*`         | Splunk index you want to index your data into.                                     | default             |
| Global Account`*`| Account to be used for data collection.                                             | None                |
| Page Size      | Page size of each response.                                                           |100                 |

**Note**: `*` denotes required fields

### 2. RiskIQ Global Inventory Assets

Field descriptions are as below:

| Field Name       | Field Description                                                                   | Default Value       |
| ---------------- | ----------------------------------------------------------------------------------- | ------------------- |
| Name`*`          | Unique name of your data input.                                                     | None                |
| Interval`*`      | Time interval of input in seconds. Interval can be in the range of 30 to 86400 seconds. | 86400                 |
| Index`*`         | Splunk index you want to index your data into.                                     | default             |
| Global Account`*`| Account to be used for data collection.                                             | None                |
| Page Size         | Page size of each response.                                                        |100                  |
| Tags              | comma-separated list of tag filters.                                               |None                |
| Brands            | comma-separated list of brand filters.                                             |None                |
| Organizations     | comma-separated list of organization filters.                                      |None                |
| New and changed assets only| collect new and changed assets only.                                      |Unchecked |
| Last Updated Time | Time in PST timezone in format YYYY-MM-DDTHH:MM:SS.sss                             |None                |

**Note**: `*` denotes required fields

**Guidelines**:

* If you need to collect new and changed assets only then please make sure that the corresponding checkbox is checked and the last updated time value is provided.
* We are not restricting users with limited historical data, but it is recommended not to collect data older than 12 months as it might impact Add-On performance.

CUSTOM COMMANDS
---------------

* `getcves` - This command is used to get CVE(Common Vulnerabilities and Exposures) data from `https://cve.mitre.org/data/downloads/allitems.csv`.

ADDING SSL CERTIFICATE
----------------------

If you have used SSL certificate for your domain, you need to add a certificate into Splunk. Follow the below-listed steps to do the same:

* Go to `$SPLUNK_HOME$/etc/apps/TA-RiskIQ/bin/lib/certifi`.
* Open cacert.pem file and add your custom certificate details at the end of the file.
* Save the file and restart the Splunk.

Note: If your vendor has published the SSL certificate publicly, no need to add that manually.

TROUBLESHOOTING
---------------

* Field extractions not working / Search stops because of memory limit reached / Events are getting truncated.
   1. Create a file 'limits.conf' in the following directory `$SPLUNK_HOME/etc/TA-RiskIQ/local`.
   2. Add the following 3 stanzas in the file:

```
      [kv]
      maxcols  = 1024
      limit    = 750
      maxchars = 1000000
      max_extractor_time = 2000
      avg_extractor_time = 1000
```  

```
      [mvexpand]
      max_mem_usage_mb = 9000
```  

```  
      [lookup]
      max_memtable_bytes = 20000000
```

   3. Restart Splunk

* For the cluster environment, the User needs to deploy limits.conf file on the Heavy forwarder, Indexer and Search Head.
* Authentication Failure: Check the network connectivity and verify that the configuration details provided are correct.
* Ensure that the KV store is enabled. You can check that by visiting: <https://localhost:8089/servicesNS/nobody/TA-RiskIQ/storage/collections/data/TA_RiskIQ_checkpointer>
* For any other unknown failure, please check the $SPLUNK_HOME/var/log/ta_riskiq_*.log files to get more details on the issue. Same logs can be viewed in Search using `index=_internal  sourcetype="tariskiq:log"`
* App icons are not showing up: The Add-On does not require a restart after the installation for all functionalities to work. However, the icons will be visible after one Splunk restart post-installation.

**Note**: $SPLUNK_HOME denotes the path where Splunk is installed. Ex: /opt/splunk

UNINSTALL & CLEANUP STEPS
-------------

* Remove $SPLUNK_HOME/etc/apps/TA-RiskIQ
* Remove $SPLUNK_HOME/var/log/splunk/**ta_riskiq_util.log**
* Remove $SPLUNK_HOME/var/log/splunk/**ta_riskiq_setup.log**
* Remove $SPLUNK_HOME/var/log/splunk/**ta_riskiq_riskiq_events.log**
* Remove $SPLUNK_HOME/var/log/splunk/**ta_riskiq_risk_iq_global_inventory_assets.log**
* Remove $SPLUNK_HOME/var/log/splunk/**ta_riskiq_getcves.log**
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

EULA
-------

Custom EULA for RiskIQ. <https://www.riskiq.com/msa/>

SUPPORT
-------

Contact - support@riskiq.com

### Copyright 2016 - 2022 RiskIQ
