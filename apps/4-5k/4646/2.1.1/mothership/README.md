## Mothership Documentation

#### Table of Contents
1. App Description
2. Installation
3. Configuration
4. Quickstart
5. Troubleshooting

#### App Description
Mothership is a Splunk App that provides a single pane of glass into large multi-instance Splunk deployments. Mothership dispatches SPL on remote Splunk instances on a scheduled interval and retrieves and stores search results locally. Field extraction is preserved, requiring no configuration other than a valid username and password for a service account on the remote machine.  An administrative interface with REST services is provided to simplify management and reporting. All remote search results are stored in RBAC controllable stores (i.e., lookups, indexes).

#### Installation

##### In a Single-Instance Deployment
* If you have internet access from your Splunk server, download and install the app by clicking 'Browse More Apps' from the Manage Apps page in the Splunk platform.
* Otherwise, download the app from Splunkbase and install it using the Manage Apps page in the Splunk platform.

##### In a Distributed Deployment or a Search Head Cluster Deployment
The Mothership app will write summary results to lookups (transforming searches) and/or indexes (non-transforming searches). In a distributed environment or Search Head Cluster, lookups populated by Mothership can be replicated across the cluster, this means that Mothership running exclusively transforming searches (which write to a lookup) will work with a properly configured Distributed or Search Head Cluster Deployment. Non-transforming searches (which write to an index) are currently not supported in a distributed or Search Head Cluster deployment.

Include the following in your server.conf settings (pushed out by the deploymer)

```[shclustering]
conf_replication_include.environments   = true
conf_replication_include.environment_searches   = true
```



##### Configuration
* The Mothership administrative user interface can be found in the Environments dashboard of the Mothership Splunk App.
* From this dashboard, and administrator has full lifecycle (create, read, update, delete) control of environments and associated environment searches.
* The following quickstart will walk through the configuration of a single environment with a single search from the management page.

##### Quickstart
* To get started, let's configure an environment and environment search which will allow us to query the Splunk instance running Mothership.
* We will be using the Mothership administrative user interface.
    * Select the 'New Environment' button and fill out the fields as follows.
        * Name: "My First Environment"
        * Management Server: "https://localhost:8089" (edit the hostname and port to reflect the management host server port of the environment Mothership is running on)
        * Web Server: Leave blank
        * Username: Provide the username of a properly credentialed service account (should be able to search)
        * Password: Provide the password of the service account provided above
        * Leave all other fields as is and click 'Save'.
* We will now configure an environment search for the environment we just created.
    * Expand the environment by clicking the '>' column.
    * Select the 'New Search' button and fill out the fields as follows.
        * Label: "My First Search"
        * In the inline search text area, provide the following SPL search string: `| rest /services/licenser/groups`
        * Leave all other fields as is and click 'Save'.
* You may need to refresh the tables. This can be accomplished by clicking the refresh icon next to the `Environments` or `Searches` heading.
* This environment is now being regularly queried on the provided schedule with the provided search. You can view the results of this query by clicking on the `Edit` menu in the `Actions` column and selecting `Results`.
* Explore the other options available to you in the `Edit` menu. This menu will provide you with lifecycle management options (create, read, update, delete) ad-hoc querying, metrics and debug logs, and more.

##### Troubleshooting
Mothership logs all transactions made to a remote machine including success and error state to the _internal index with the following source `*environment_poller_debug.log`. Click on the "Debug" link found in the "Actions" dropdown for either the Environment or Environment Search to debug errors.
