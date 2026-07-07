This is an add-on powered by the Splunk Add-on Builder.
# SOC Prime CCM App for Splunk - Optimized

## Description
With SOC Prime CCM App for Splunk - Optimized, you can continuously stream new rules and rule updates from the SOC Prime Platform to your cloud or on-prem Splunk instance.  

To enable rule streaming, configure Jobs in the Continuous Content Management (CCM) module of the SOC Prime Platform and specify them in the App's data input. Jobs are configured with Content Lists to select rules for deployment, Presets to automatically modify the rules' parameters, and Filters to include additional conditions. You can also set up and apply Custom Field Mapping profiles to make the names of indexes, fields, and even field values in the rule code match your custom data schema.  

This guide describes how to install the SOC Prime CCM App for Splunk - Optimized and set up integration with CCM to enable the streaming of detection content directly into your Splunk environment.  

To obtain rules via the CCM module and stream them into your environment, you need access to the SOC Prime CCM API. For more details on the API, see our [Platform Guides](https://help.socprime.com/en/articles/6265791-api) (to open the Guides, you need to be logged in to your SOC Prime Platform account).

## App Version

**SOC Prime CCM App for Splunk - Optimized** is SOC Prime CCM App for Splunk v2.0.1 or later. You can find earlier versions of the App [here](https://splunkbase.splunk.com/app/5725).

## Requirements

SIEM: Splunk v. 9.x or higher, or Splunk Cloud.  
Note: If you have an all-in-one Splunk environment, use this guide to install the app. If you have a distributed Splunk environment, please contact SOC Prime support for help with installation since it may be specific to your configuration.

## Installation

There are two ways of installing the app: via the Splunk app listing or manually with the add-on package. If you already have v2.0.0 or older of this App installed, remove it before installing the new version.  

To install the app via the listing, follow these steps:

1. Open the Splunk Web Console.
2. Select the gear icon on the **Apps** tab.
3. Click the **Browse more apps** button.
4. Type "SOC Prime CCM App for Splunk - Optimized" in the search field to find the app and proceed to its installation in your environment.

To install the add-on manually, follow these steps:

1. Open the Splunk Web Console.
2. In the Splunk Web Console, select the **Apps** tab.
3. Click the **Install app from file** button.
4. Select the "SOC Prime CCM App for Splunk - Optimized" package and proceed to its installation in your environment.

After successful installation, the app should appear as **SOC Prime CCM App for Splunk - Optimized** in Splunk’s **Apps** menu.

## Configuration

After installation, configure the rule import on the **Inputs** tab:

1. Select *SOC Prime CCM App for Splunk - Optimized* in the main *Apps* menu.  
2. Select the *Inputs* tab.  
3. Click *Create New Input*.  
4. Fill in the parameters.  

## Changelog:

* 1.0.0 — Initial release of the SOC Prime CCM App for Splunk providing functionality to import Alerts from the SOC Prime TDM Platform.  
* 1.0.1 — General minor improvements.  
* 1.0.3 — We've made several updates:  
    * Fixed filters in dashboards  
    * Resolved the issue with rule names that could lead to rule duplication  
    * Fixed and optimized the API script  
* 2.0.0 — We've introduced several substantial improvements:  
    * Streamlined the configuration of content to be deployed by introducing Jobs that replace all the separate settings used before. Now, you set up Jobs in SOC Prime Patform's CCM (adding Content Lists, Field Mappings, Presets, and Configs), and specify the Jobs in the App's data input.  
    * Removed deprecated options (Content List Name, Mapping Name, Preset Name, Alt Translation Config) from data input parameters.  
    * Added data input parameters to configure Jobs as well as rule exceptions, proxy, and distributed deployment.  
* 2.0.1 — We've made some updates:  
    * Added integration with Splunk Enterprise Security.
    * Added the Inputs tab where you can configure data inputs.  
    * Added the Configuration tab where you can configure proxy and logging level.
    * Fixed bugs.
* 2.0.2 — We've made some updates:  
    * Implemented changes to comply with the updated Splunk Cloud Platform compatibility requirements.
    * Fixed bugs.
* 2.0.3 — We've made some updates:  
    * Implemented changes to comply with the updated Splunk Cloud Platform compatibility requirements.
    * Fixed bugs.
* 2.0.4 — We've made some updates:
    * Implemented changes to comply with the updated Splunk Cloud Platform compatibility requirements.
    * Changed the convention of Rule naming: using the case ID in the rule name is not required anymore.
    * Added the possibility of assigning the ownership of installed Rules to a specific user.
    * Fixed bugs.
* 2.0.5 — We've made some updates:
    * Updated libraries to comply with the new Splunkbase requirements.
    * Made some optimizations.
    * Added the CCM API URL input parameter so that the user can set a non-default URL.
* 2.0.6 — Updates:
    * Implemented changes to comply with the updated Splunk Cloud Platform compatibility
* 2.0.7 — Updates:
    * Implemented changes to comply with the updated Splunk Cloud Platform compatibility
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/cli-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/cli-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/cli-arm64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/cli.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/gui-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/gui-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/gui-arm64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/gui.exe: this file does not require any source code
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/cli-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/cli-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/cli-arm64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/cli.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/gui-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/gui-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/gui-arm64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/gui.exe: this file does not require any source code
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/cli-arm64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/cli-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/gui-arm64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/gui-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/gui-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/gui.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/cli-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/setuptools/cli.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-ccm-app-for-splunk/bin/ta_soc_prime_ccm_app_for_splunk/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
