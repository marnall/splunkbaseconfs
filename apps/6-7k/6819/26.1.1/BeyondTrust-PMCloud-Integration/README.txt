# BeyondTrust PM Cloud + Splunk Integration

This document describes the installation and configuration of the integration between BeyondTrust Privilege Management Cloud and Splunk.

The integration consists of a application which can be installed in a Splunk instance directly from [splunkbase](https://splunkbase.splunk.com/).

---

# Prerequisites

Before proceeding with the installation and configuration of the integration with PM Cloud, it's important to ensure a few things are in place.

### Network Considerations

Your Splunk instance will need the ability to connect to various REST API endpoints provided by your PM Cloud site.  Communication is in the form of **secure HTTP traffic on TCP port 443**  The purpose of this connectivity is to query the PM Cloud site for event information which can be ingested by Splunk.

### Create a PM Cloud API Account

The API account is used from within Splunk to make API calls to PM cloud. This process is covered in the [PM Cloud Admin Guide](https://www.beyondtrust.com/docs/privilege-management/console/pm-cloud/configuration/configure-api-settings.htm).

---

# Installation and Configuration

Once the prerequisites have been satisfied, you can move on to the installation and configuration of the integration.

### Install Application

The app is currently available for installation via [splunkbase](https://splunkbase.splunk.com/).  To install the application:
1. Authenticate to your Splunk instance as an administrator
2. Click **Apps > Manage Apps**
3. At the top, click the **Browse more apps** button
4. Simply search for **BeyondTrust Privilege Management Cloud**
5. Click the **Install** button on the app listing

### Configure Application

Once the applicaton is installed in your Splunk instance, you can add configuration for one or both data feeds that it is able to consume.

The two basic categories of events that can be consumed by the application are:
1. **Client Events** - These events originate from the individual systems being managed by BeyondTrust Endpoint Privilege Management. The flow back to the PM Cloud site, and are retrievable via the API.  Examples include: user logon, a process started, a process blocked, etc.
2. **Activity Audits** - These events represent activities that occur within the PM Cloud web interface.  Examples include: user role changes, editing or committing a policy draft, assigning a computer to a group, etc.

The following steps describe how to add an input for either of the two data feeds:
1. Authenticate to your Splunk instance as an administrator
2. Click **Apps > BeyondTrust Privilege Management Cloud**
3. On the **Inputs** tab, click the **Create New Input** button
4. You should be presented with two options for the type of input to create.  Select the type (Client Events or Audit Activity) for which you'd like to create an input
5. Enter the appropriate values in each of the configuration fields:
    - **Name** - Give the input configuration a unique name
    - **Interval** - The number of seconds between each attempt to retrieve new data
    - **Index** - The name of the index into which all events from this input should be placed
    - **PM Cloud Services Hostname** - The *services* hostname of your PM Cloud site. For example, if you access your PM Cloud web interface at *mysite.example.com*, then the appropriate value here would be *mysite***-services***.example.com*
    - **Client ID** - The ID value of the API Account created in the Prequisites section
    - **Client Secret** - The secret value of the API Account created in the Prequisites section
    - **Events Batch Size** *(Client Events only)* - If the integration needs to make multiple calls to retrieve available events, this is the number that will be returned in one batch or response.  1000 is both the default and the max value
    - **Audit Activity Page Size** *(Activity Audits only)* - If the integration needs to make multiple calls to retrieve available events, this is the number that will be returned in one page or response.  200 is both the default and the max value
    - Click **Add** to save the configuration. The input will start running immediately.
6. *(Optional)* If it is desired to ingest event data from both data feeds, repeat steps 4 and 5 for the other input type

---

# Troubleshooting and Support

Should you encounter issues with event ingestion, the application does write separate log files for each input type.  In an on-prem Splunk Enterprise deployment, these would be located in a location similar to *C:\Program Files\Splunk\var\log\splunk* using files with the following names:
- Client Events - beyondtrust_pmcloud_integration_beyondtrust_pm_cloud_rest_api_client_events.log
- Activity Audits - beyondtrust_pmcloud_integration_beyondtrust_pm_cloud_rest_api_audit_data.log

It is also worth noting that the log level can be changed in order to provide more detail if needed when debugging an issue.  To do this, simply access the application in Splunk and select the **Configuration** tab.  From there, change the log level to DEBUG (or whatever level is desired - INFO is the default), and save the change.

Finally, for any issues which require additional assistance, please contact BeyondTrust Support at [mysupport@beyondtrust.com](mailto:mysupport@beyondtrust.com) or through the Customer Support Portal.# Binary File Declaration
C:\Program Files\Splunk\var\data\tabuilder\package\BeyondTrust-PMCloud-Integration\bin\beyondtrust_pmcloud_integration\aob_py3\pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\BeyondTrust-PMCloud-Integration\bin\beyondtrust_pmcloud_integration\aob_py3\markupsafe\_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\BeyondTrust-PMCloud-Integration\bin\beyondtrust_pmcloud_integration\aob_py3\setuptools\cli-32.exe: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\BeyondTrust-PMCloud-Integration\bin\beyondtrust_pmcloud_integration\aob_py3\setuptools\cli-64.exe: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\BeyondTrust-PMCloud-Integration\bin\beyondtrust_pmcloud_integration\aob_py3\setuptools\cli-arm64.exe: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\BeyondTrust-PMCloud-Integration\bin\beyondtrust_pmcloud_integration\aob_py3\setuptools\cli.exe: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\BeyondTrust-PMCloud-Integration\bin\beyondtrust_pmcloud_integration\aob_py3\setuptools\gui-32.exe: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\BeyondTrust-PMCloud-Integration\bin\beyondtrust_pmcloud_integration\aob_py3\setuptools\gui-64.exe: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\BeyondTrust-PMCloud-Integration\bin\beyondtrust_pmcloud_integration\aob_py3\setuptools\gui-arm64.exe: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\BeyondTrust-PMCloud-Integration\bin\beyondtrust_pmcloud_integration\aob_py3\setuptools\gui.exe: this file does not require any source code
# Binary File Declaration
C:\Program Files\Splunk\var\data\tabuilder\package\BeyondTrust-PMCloud-Integration\bin\beyondtrust_pmcloud_integration\aob_py3\setuptools\cli-32.exe: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\BeyondTrust-PMCloud-Integration\bin\beyondtrust_pmcloud_integration\aob_py3\setuptools\cli-64.exe: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\BeyondTrust-PMCloud-Integration\bin\beyondtrust_pmcloud_integration\aob_py3\setuptools\cli-arm64.exe: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\BeyondTrust-PMCloud-Integration\bin\beyondtrust_pmcloud_integration\aob_py3\setuptools\cli.exe: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\BeyondTrust-PMCloud-Integration\bin\beyondtrust_pmcloud_integration\aob_py3\setuptools\gui-32.exe: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\BeyondTrust-PMCloud-Integration\bin\beyondtrust_pmcloud_integration\aob_py3\setuptools\gui-64.exe: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\BeyondTrust-PMCloud-Integration\bin\beyondtrust_pmcloud_integration\aob_py3\setuptools\gui-arm64.exe: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\BeyondTrust-PMCloud-Integration\bin\beyondtrust_pmcloud_integration\aob_py3\setuptools\gui.exe: this file does not require any source code
