# Vectra Stream App

**Author:** Vectra AI (TME)

**Version:**

- 1.5.0

**Supported products:**

- Vectra Stream

## Using this App

- Install this App on Search Heads
- Adjust the index containing Vectra Stream Data in the macro `vectra_stream_index` in local/macros.conf

## Compatibility

- Vectra_Stream_JSON_TA >=1.0.0

## Changelog

- **1.5.0 / 2024-11-04**

  - New release for version 9.x

- **1.4.0 / 2022-08-05**

  - **Bugfixes:**
    - TM-1343: _Remove searches with no time limit (NTLM Table)_

- **1.3.0 / 2022-03-23**
  
  - **Improvements:**
    - Compatibility with Vectra Stream JSON Add-on and backward compatibiulity with Standard Stream Add-on

- **1.2.3 / 2021-08-31**
  
  - **Bugfixes:**
    - TM-594: _Previous version wasn't Cloud compabible_

- **1.2.2 / 2021-08-27**

  - **Improvements:**
    - TM-581: _Compatibility with Splunk Cloud and Splunk 8.2 versions regarding jQuery security updates_
  
  - **Bugfixes:**
    - TM-590: _Logo wasn't properly displayed_

- **1.2.1 / 2020-06-30**

  - **Bugfixes:**
    - Minor fixes for Splunk Cloud Vetting process

- **1.2.0 / 2020-06-18**

  - **New features:**
    - SMTP Dashboard
    - Update Host and Session dasboards with SMTP metadata
  
  - **Bugfixes:**
    - Minor bug fixes in drill down

- **1.1.3 / 2020-02-13**

  - **Bugfixes:**
    - Remove inputs.conf file
    - Add icons

- **1.1.2 / 2019-11-26**

  - **Bugfixes:**
    - Some bug fixes

- **1.1.1 / 2019-10-16**

  - **Improvements:**
    - Add an IP to Hostname lookup page
    - Searches optimizations using based searches
    - Time ramge is carry over between dashboards
    - Revamp Security Dashboards
    - Remove dashboards autorun. *It is recommended to narrow down your search first and not run it accross all your data.*

  - **Bugfixes:**
    - Some bug fixes

- **1.1.0 / nc.**

  - **New features:**
    - SSH dashboard
    - Update Host and Session dashboards with SSH metadata
  
  - **Improvements:**
    - Add total number of beacons in Beacons dashboard
    - Remove Treemap in DNS dashboard to use table instead (perf)

  - **Bugfixes:**
    - Fix the link from Host view to Beacons dashboard
    - Fix drilldown searches into Beacons dashboard

- **1.0.5 / nc.**

  - **Bugfixes:**
    - Use metadata_type attribute for searches instead of vectra_metadata_xyz as it is discarded by syslog forwarder
    - Minor fixes on few searches

- **1.0.4 / nc.**

  - **New features:**
    - Add Host Privilege score in the Host View
    - Add Threat and Certainty scores + Severity into Host View

  - **Improvements:**
    - Enhanced JA3 lookup file to contain only the most popular UA for a JA3 hash
    - Minor typo fixes

- **1.0.3 / nc.**

  - **New features:**
    - Add local lookup CSV files for JA3, JA3S, Alexa 1M and Open public DNS

- **1.0.2 / nc.**

  Initial release
