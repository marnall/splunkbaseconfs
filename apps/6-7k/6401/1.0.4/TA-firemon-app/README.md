##FireMon App Add-on and App for Splunk

FireMon App Add-on for Splunk provides details of HealthCheck, Control Status, NSG Count and UnUsedNSG count details using REST API data and the App provides visualizations on these data.

Splunk Enterprise:

* Version 8.2.5

Python:

* Version 3.6

## Installation

1. Log in to Splunk and navigate to Apps > Manage Apps. Click install app from file.

2. Select the zip/spl file you want to install, then check on the update addon check box and click on upload button.

3. Once the installation is complete, restart splunk.

4. Go to the apps list and open FireMon App for Splunk.

5. Navigate through different tabs

6. Create index by navigating to Settings > Indexes > New Index. Provide the Index Name > Select app-name from App drop-down.
   (Create custom indexes which are already mentioned in Inputs tab)


### Inputs

Go to the apps list and open FireMon App. 

From inputs screen, click on new input. Enter the values and click on `Add`.

The following input configurations are available.

* Name(Required) - Provide a name for the input configuration.
* Interval(Required) - Time interval between each addon invocation. For example, the addon will run in every 5 minutes
if it is set to 300.
* Index(Required) - Select the index to save the data. It will be default
* API URL(Required) - Provide the base url of the api.
* Username(Required) - Provide the username to access data from url.
* Password(Required) - Provide the password to access data from url.
