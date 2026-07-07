# Bugfender Add-on for Splunk
Modular Input developed with Add-On Builder to query endpoints from the Bugfender API, namely:
- Get Apps List (https://dashboard.bugfender.com/api/#tag/App/operation/AppList)
- Get App Devices (https://dashboard.bugfender.com/api/#tag/App/operation/DownloadDevices)
- Get App Logs (paginated) (https://dashboard.bugfender.com/api/#tag/App/operation/AppLogs)
- Get App Issues (Not documented anymore)

Associated Jira request: https://splunk.atlassian.net/browse/FDSE-1630


## Features 
This modular input avoids the usage of checkpointing for duplicate events due to unnecessary high computational cost associated with it.

As an alternative, it utilizes timestamps. The moment just before the modular input starts execution, the time is temporarily saved. Upon successful termination of the input, this time stamp is saved in the KV store, and retrieved during the next execution of the input. The next time the input executes, it queries only events from the retrieved time on to the present. 
This process is repeated.

You can provide an optional initial start date for the very first time the input is run.

## Getting Started

### Installation
Clone this repository directly to `$SPLUNK_HOME/etc/apps`, or clone it, zipp it, and install it via Splunk's Web Interface via the "Install app from file"-button in the "Manage Apps"-section.

### Usage
Firstly, set up your Bugfender Account in the "Configuration" in the Add-On page. Click on the "Add"-button, and in the input field that is popping up, provide an account name for later reference, your Bugfender Client ID as username, and your Bugfender Client Secret as password.

In the "Inputs" page you can create new inputs, in which you can reference the Bugfender account that you have created earlier.