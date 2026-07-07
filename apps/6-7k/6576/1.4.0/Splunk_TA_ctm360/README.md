# CTM360 Add-on for Splunk

The CTM360 Add-on for Splunk allows subscribed users to import their asset inventory,  issues, and incidents into Splunk®, and utilize this data to build reports, trigger alerts and identify vulnerabilities, exposures  and misconfigurations against your assets.
The CTM360 Splunk App and Add-on are designed to work together.

Steps:

- Install the CTM360 Add-on
- Configure the Add-on
- Install the CTM360 App

## Prerequisites

- CBS/HackerView API key

    Get your API key on the CBS/HackerView portal:

    - [CBS integrations page][cbs-integrations].

    - [HackerView integrations page][hv-integrations].

- A Splunk account and installation.

## Configure the Add-on

From the Inputs page, select Create New Input. Choose CBS/HackerView Feeds from the dropdown. Fill out the following fields:
- A name for your data input.
- The interval field can be modified, if required. This decides the frequency at which data will be fetched from CTM360. The minimum interval is 1 hour(3600 seconds) and maximum is 24 hours(86400 seconds), the default is set to 6 hours(21600 seconds).
- The index field is set to default and can be modified, if required.
- API key from [CBS integrations page][cbs-integrations]/[HackerView integrations page][hv-integrations].

Once the configurations are saved, the Add-on polls for data from CTM360 at set intervals and saves the data to the configured index. The CTM360 App for Splunk uses the data indexed by the Add-on to populate dashboards and generate reports.

## Use the Add-on

You can query your data inputs with the Search tab.
Refer to following helpful resources from Splunk if you are not familiar with Splunk search syntax:
- [Splunk Search Documentation][splunk-search-documentation]
- [Splunk Search Tutorial][splunk-search-tutorial]

<!-- References -->
[cbs-integrations]: https://cbs.ctm360.com/settings/entity_management/integrations
[hv-integrations]: https://hackerview.ctm360.com/integrations
[splunk-search-documentation]: https://docs.splunk.com/Documentation/Splunk/8.2.5/Search/GetstartedwithSearch?ref=hk
[splunk-search-tutorial]: https://docs.splunk.com/Documentation/Splunk/8.2.5/SearchTutorial/WelcometotheSearchTutorial?ref=hk

<!--
## Binary File Declaration

```plain
./Splunk_TA_ctm360/bin/splunk_ta_ctm360/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
./Splunk_TA_ctm360/bin/splunk_ta_ctm360/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
./Splunk_TA_ctm360/bin/splunk_ta_ctm360/aob_py3/setuptools/cli.exe: this file does not require any source code
./Splunk_TA_ctm360/bin/splunk_ta_ctm360/aob_py3/setuptools/cli-arm64.exe: this file does not require any source code
./Splunk_TA_ctm360/bin/splunk_ta_ctm360/aob_py3/setuptools/gui-32.exe: this file does not require any source code
./Splunk_TA_ctm360/bin/splunk_ta_ctm360/aob_py3/setuptools/gui-64.exe: this file does not require any source code
./Splunk_TA_ctm360/bin/splunk_ta_ctm360/aob_py3/setuptools/cli-64.exe: this file does not require any source code
./Splunk_TA_ctm360/bin/splunk_ta_ctm360/aob_py3/setuptools/cli-32.exe: this file does not require any source code
./Splunk_TA_ctm360/bin/splunk_ta_ctm360/aob_py3/setuptools/gui.exe: this file does not require any source code
./Splunk_TA_ctm360/bin/splunk_ta_ctm360/aob_py3/setuptools/gui-arm64.exe: this file does not require any source code
```
-->