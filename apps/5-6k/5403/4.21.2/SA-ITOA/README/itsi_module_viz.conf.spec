# This file contains possible attributes and values for changing tab names and panel
# titles in a module details dashboard.
#
# There is an itsi_module_viz.conf in each module-specific directory within ITSI (for example, 
# $SPLUNK_HOME/etc/apps/DA-ITSI-OS/default for the Operating System module). To edit these 
# configurations, place an itsi_module_viz.conf in $SPLUNK_HOME/etc/apps/DA-ITSI-OS/local.
# You must restart Splunk software to enable configurations.
#
# To learn more about configuration files (including precedence) please see
# the documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles
#
# WARNING: Manual editing of this file is not recommended. Contact Support before proceeding. 

[<view_name>]
* The name of the deep dive drilldown view within the ITSI module.

tabs = <comma-separated list>
* A list of tab IDs that will be included in this drilldown view.

<tabId>.control_token = <string>
* Used to run all the panel searches in a given tab.
* When the tab is shown, a list of search tokens are retrieved, the search tokens for
  all inactive tabs are removed from the list, and the search token for the active tab
  is added to the list. This guarantees that only the shown tab's panels are displayed.

<tabId>.title = <string>
* The title of the tab that is displayed in the UI. 

<tabId>.row.<int> = <comma-separated list>
* A list of panels that are displayed on each row on a tab.
* The panels are formatted as follows: <module_name>:<panel_name>.
* These settings start at 'row.0' and go up to any number of rows that is needed for a tab.
* Example: 
	row.0 = DA-ITSI-OS:panel1,DA-ITSI-LB:panel2

<tabId>.extendable_tab = <boolean>
* Whether the tab is considered an extendable tab. 
* This setting is for user-created tabs so that a delete button appears on the tab
  in the UI.  
* Any tabs that ship with the module default to "false".

<tabId>.activation_rule = <comma-separated list>
* A list of KPI elements that are associated with a given tab so that
  context-aware drilldown is enabled based on the selected KPI from the deep dive.
* Each element here is defined as the content from the "target_field" parameter from each
  selected KPI from the file itsi_kpi_template.conf.

entity_search_filter = <JSON>
* A JSON blob of entity rules to use to filter entities for entity dropdown.

requested_entity_tokens = <comma-separated list>
* A list of entity attributes that are submitted as tokens.
