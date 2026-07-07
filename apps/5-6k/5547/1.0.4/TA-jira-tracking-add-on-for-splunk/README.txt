## Introduction:

This is an add-on powered by the Splunk Add-on Builder. Uses Atlassian Jira REST API v3 service to collect Issues and Worklogs from a Jira Cloud Server.

A new event is indexed every time an issue or worklog is updated or created.

Jira Issues events contains every navigable field, including the following fields/information:

    Issue Summary

    Issue Creator Name

    Issue Assigne Name

    Issue Reporter Name

    Aggregate Time Spent

    Customfields

Jira Worklogs events contains every navigable field, including the following fields/information:

    Worklog Update Author

    Worklog Update Date

    Worklog Time Spent (in hours and seconds)


## Prerequisites:

Requires a Jira Cloud server and an account with privileges to get issues and worklogs information.


## Architecture:

Based on a standard app created with Splunk Add-On Builder. Consists in two modular inputs that collects issues and worklogs using a python3 script that implements the Jira REST API service requests with the collection queries.

Contains two distinct sourcetypes:

    atlassian:jira:issues

    atlassian:jira:worklogs

Contains fields aliases for the “id” field because “id” is the identification field in issues and in worklogs.


## Installation:

Extract the app to your apps directory, and then restart the Splunk instance.

Create a new index to store this new data.

In the Splunk apps menu you can access the TA settings, it allows you to create and configure data inputs (one for issues and one for worklogs). Its required to set a Jira server url, user account, API token.

Warning: the checkbox “Restart checkpoint” was implemented for debug purposes. It deletes the actual checkpoint reindexing all the data again from the begining. Use with caution.


## WARNING: Upgrading to 1.0.4

The 1.0.4 is a major rework on credentials usage on configurations and requires reconfiguring the inputs using global accounts.


## Common use cases:

Our internal use case consists in a single instance Splunk Enterprise server with a custom dashboard that tracks Jira worklogs data, showing user participation, total time spend, etc, by issues or projects.
Developement:

Currently there are no plans to expand the collection to more Jira data and the custom dashboard is still in early developement and not included in this TA.


## References:

    Atlassian Developer: https://developer.atlassian.com/

    Jira Cloud Platform Api: https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/

    Atlassian Account Token: https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/

## Changelog

1.0.4 - Now uses global accounts for configurations.
1.0.3 - Added HTTPS requirement for base URL.
1.0.2 - AOB upgrade for jquery 3.5 and python3 requirements.
1.0.1 - Splunk 8.2 validations.
1.0.0 - Release.
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-jira-tracking-add-on-for-splunk/bin/ta_jira_tracking_add_on_for_splunk/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-jira-tracking-add-on-for-splunk/bin/ta_jira_tracking_add_on_for_splunk/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-jira-tracking-add-on-for-splunk/bin/ta_jira_tracking_add_on_for_splunk/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-jira-tracking-add-on-for-splunk/bin/ta_jira_tracking_add_on_for_splunk/aob_py3/setuptools/gui-arm64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-jira-tracking-add-on-for-splunk/bin/ta_jira_tracking_add_on_for_splunk/aob_py3/setuptools/gui-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-jira-tracking-add-on-for-splunk/bin/ta_jira_tracking_add_on_for_splunk/aob_py3/setuptools/cli.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-jira-tracking-add-on-for-splunk/bin/ta_jira_tracking_add_on_for_splunk/aob_py3/setuptools/gui.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-jira-tracking-add-on-for-splunk/bin/ta_jira_tracking_add_on_for_splunk/aob_py3/setuptools/gui-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-jira-tracking-add-on-for-splunk/bin/ta_jira_tracking_add_on_for_splunk/aob_py3/setuptools/cli-arm64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-jira-tracking-add-on-for-splunk/bin/ta_jira_tracking_add_on_for_splunk/aob_py3/setuptools/cli-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-jira-tracking-add-on-for-splunk/bin/ta_jira_tracking_add_on_for_splunk/aob_py3/setuptools/cli-32.exe: this file does not require any source code
