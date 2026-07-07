# SecurityScorecard App For Splunk

## This is an app powered by the Splunk Add-on Builder

## OVERVIEW
* The SecurityScorecard App for Splunk provides value and insight of your collected data by SecurityScorecard Add-on for Splunk
* Author -SecurityScorecard, Inc.
* Version - 1.0.2

## COMPATIBILITY MATRIX
* Browser: Google Chrome, Mozilla Firefox, Safari
* OS: Platform independent
* Splunk Enterprise version: 10.4.0, 10.2.x, 9.4.x, 9.3.x
* Supported Splunk Deployment: Splunk Cluster, Splunk Standalone, and Distributed Deployment

## OPEN SOURCE COMPONENTS AND LICENSES
* Some of the components included in SecurityScorecard App for Splunk are licensed under free or open-source licenses. We wish to thank the contributors to those projects.

## RECOMMENDED SYSTEM CONFIGURATION
* Because this App runs on Splunk Enterprise, all of the Splunk Enterprise system requirements apply.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
* This app has been distributed in two parts.
   * SecurityScorecard Add-on for Splunk: It collects data from the SecurityScorecard platform.
   * SecurityScorecard App for Splunk: It is used for visualizing SecurityScorecard Add-on data.
* This app can be set up in two ways:
   * Standalone Mode:
      * Install the SecurityScorecard App for Splunk and SecurityScorecard Add-on for Splunk.
      * The SecurityScorecard App for Splunk uses the data collected by SecurityScorecard Add-on for Splunk and builds the dashboard on it.
   * Distributed Environment:
      * Install the SecurityScorecard App for Splunk and SecurityScorecard Add-on for Splunk on the search head. The user only needs to configure an account in SecurityScorecard Add-on for Splunk but should not create data input.
      * Users need to manually create an index on the indexer (No need to install SecurityScorecard App for Splunk or SecurityScorecard Add-on for Splunk on the indexer).

## INSTALLATION
### Follow the below-listed steps to install an Add-on from the bundle:
* Download the App package.
* From the UI navigate to Apps-> Manage Apps.
* In the top right corner, select Install the app from file.
* Select Choose File and select the App package.
* Select Upload and follow the prompts.

OR

* Directly from the Find More Apps section provided in Splunk Home Dashboard.

## CONFIGURATION
* The App requires My company and index configuration to visualize the Dashboard follow the steps below
   1. Configure My company
      * Click on the SecurityScorecard App for Splunk icon on the left side. This will open the setup page for configuration
      * Select your company and Click on the Save button. After that, You will be redirect to Dashboards.
   2. Configure index using Macro
      * Navigate to Settings > Advanced search > Search macros.
      * Filter `ssc_index` and click `ssc_index` under the Name.
      * Edit the definition macro definition `(index=<index>)` and click`Save`.

## Search

To see data logged by `SecurityScorecard Add-on for Splunk`, select the `Search` tab. Search  ``ssc_index`` macro.

## TROUBLESHOOTING
* If dashboards are not getting populated:
   * Make sure you have data in a given time range.
   * To check whether is data collected or not, run the"`ssc_index` | stats count by sourcetype" query in the search.
   * Try expanding TimeRange.

## UNINSTALL APP
* To uninstall app, user can follow below steps: SSH to the Splunk instance -> Go to folder apps($SPLUNK_HOME/etc/apps) -> Remove the SecurityScorecard folder from apps directory -> Restart Splunk

## SUPPORT
* Support Offered: Yes
* Support Email: support@securityscorecard.io

## COPYRIGHT
© 2024 SecurityScorecard
