## ES Mothership App for Splunk Documentation

#### Table of Contents
1. App Description
2. Installation
3. Configuration

#### App Description
ES Mothership App for Splunk provides a single pane of glass into multi-instance Splunk Enterprise Security deployments including a roll-up of notable events and security posture dashboards. **ES Mothership App for Splunk is dependent on the Mothership App for Splunk** being installed. See the following link for more information on the Mothership App for Splunk: https://splunkbase.splunk.com/app/4646/

#### Installation

##### Single-Instance Deployment
* If you have the internet access from your Splunk server, download and install the app by clicking 'Browse More Apps' from the Manage Apps page in the Splunk platform.

##### In a Distributed Deployment or a Search Head Cluster Deployment
Please see the Mothership App for Splunk 'Distributed Deployment or a Search Head Cluster Deployment' documentation for proper setup and configuration.

##### Configuration
* The Mothership App for Splunk administrative user interface can be found in the Environments dashboard of the ES Mothership App for Splunk.
* From this dashboard, an administrator has full lifecycle (create, read, update, delete) control of the environments and associated environment searches.
* The following quickstart will walk through the configuration of a single environment with multiple searches required to power the Security Posture and Incident Review dashboards from the management page.

##### Quickstart
* To get started, let's configure an environment and associated environment searches which will allow us to query an existing Enterprise Security Splunk instance and populate the bundled dashboards.
* We will be using the ES Mothership administrative user interface.
    * Select the 'New Environment' button and fill out the fields as follows.
        * Name: "An ES Environment"
        * Management Server: "https://localhost:8089" (edit the hostname and port to reflect the management host server port of the environment Splunk Enterprise Security is running on)
        * Web Server: "http//localhost:8000" (edit hostname and port to reflect the web UI)
        * Username: Provide the username of a properly credentialed service account (should be able to search)
        * Password: Provide the password of the service account provided above
        * Search Templates: Click 'Apply' to assign all pre-bundled search templates from the app
        * Leave all other fields as is and click 'Save'.
* We will now review the environment searches for the environment that were just created.
    * Expand the environment by clicking the '>' column.
    * You should see the three associated environment searches:
        * All Notables - Last 24 hours
        * Notable Events By Urgency - Generator
        * Notable Events - Generator
* Check that the environment is correctly configured and the searches have ran. This can be accomplished by clicking the refresh icon next to the `Environments` or `Searches` heading to see the latest status.
* This remote environment is now being regularly queried on the provided schedule with the provided searches. You can view the results of this query by clicking on the `Edit` menu in the `Actions` column and selecting `Results`.
* Explore the Dashboards available by clicking on the `Multi-ES Dashboards` navigation items `Multi-ES Incident Review` or `Multi-ES  Security Posture`.
