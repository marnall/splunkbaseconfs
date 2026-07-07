# Vectra App

**Author:** Vectra AI

**Version:** 1.5.0

## Supported products

* Vectra Detect

## Using this App

* Install this App on Search Heads
* Adjust the index containing Vectra Cognito Data in the macro `vectra_cognito_index`

## Compatibility

* [Technology Add-On for Vectra Detect (JSON)](https://splunkbase.splunk.com/app/5271/) >=1.2.0
* [Vectra SaaS Add-on for Splunk](https://splunkbase.splunk.com/app/6517/]) >= 1.0.0

## Release Notes

***

* **1.5.0 / 2025-May-08**

    * Supportability update.

* **1.4.0 / 2023-April-18**

    * #TM-1854: _Add dashboard for Vectra Match_


* **1.3.0 / 2022-July-14**

    * #TM-1301: _Compatibility with Vectra SaaS Add-on_
    * #TM-1303: _Unified View for Entities (Hosts and Accounts accross data sources)_
    * #TM-1304:	_Unified View for Detections_
    * #TM-1305: _Simplified UI - Unified Entities is the default landing page_
    * #TM-1307: _Add a dashboard for Hosts and Accounts lockdown_
    * #TM-1309:	_Remove Cognito references from the App_
    * #TM-1317: _Support of multi-brains where the same entity is seen by different brains in different places of the network (Entities view only)_
    * #TM-1323: _Ability to filter based on Assignment to entities_
    * #TM-1324: _Ability to filter based on Data Sources (AWS, M365/AAD, Network)_
    * #TM-1325:	_Update Vectra's logo_

* **1.2.1 / 2021-Aug-26**

  * **Improvements:**
    * TM-581: _Compatibility with Splunk Cloud and Splunk 8.2 versions regarding jQuery security updates_

* **1.2.0 / 2021-Apr-21**

  * **Improvements:**
    * #TM-256: _Allows to use both CEF TA and Json TA data at the same time_
    * #TM-298: _Add pagination selector_

  * **Bugfixes:**
    * #TM-283: _Overview drilldowns could not work if the install folder was not the default one_
    * #TM-314: _Some drilldowns were broken_
    * #TM-315: _Timeranges were not kept on drilldown_
    * #TM-321: _Audit dropdown list were not linked with timerange picker_

* **1.1.0 / 2020-05-07**

  * Account dashboard
  * Fixed Overview quadrant issue

* **1.0.2 / 2019-04-24**

  * Minor bugfix

* **1.0.1 / 2019-04-09**

  * Improved Drilldowns

* **1.0.0 / 2019-03-09**

  * Initial Release
