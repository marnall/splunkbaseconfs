Knowledge Object Sync(KOS)
* Description *
Using KOS you can verify if all your Knowledge Objects(KO) were moved correctly and with the same content(search,data,etc.)
This works if you are migrating from on-prem to on-prem of on-prem to the cloud
 
* Setup *
Splunk Enterprise:
Go to Manage Apps > Browse more Apps > Look for Knowledge Object Sync(KOS) and install it
 
Splunk Cloud:
Go to Manage Apps > Browse more Apps > Look for Knowledge Object Sync(KOS) and install it
 
* Help *
While this app is not formally supported, the developer can be reached at bran1501@gmail.com (OR in splunk-usergroups slack, Christhian Bran (C)). Responses are made on a best effort basis. Feedback is always welcome and appreciated!
(if you use the User Group approach, include: Learn more about splunk-usergroups slack here: https://docs.splunk.com/Documentation/Community/current/community/Chat#Join_us_on_Slack)

Details:
# Instructions
 
## Prerequisites
Before installing this app, the following needs to be addressed.
Export these lookups, here is an example if the environment is called cloud-test:
| rest splunk_server=local /servicesNS/-/-/data/ui/views | fields eai:acl.sharing, eai:acl.app, disabled, label, title, eai:acl.owner eai:data updated
| rest splunk_server=local /servicesNS/-/-/saved/searches | fields eai:acl.app title is_scheduled eai:acl.owner eai:acl.sharing search updated
-> LOOKUP: cloud-test_all_saved_searches_src.csv 

| rest splunk_server=local /servicesNS/-/-/data/props/extractions | fields title eai:acl.app, eai:acl.owner,eai:acl.sharing author attribute value updated
-> LOOKUP: cloud-test_all_field_extraction_src.csv

| rest splunk_server=local servicesNS/-/-/saved/eventtypes | fields eai:acl.app,eai:acl.owner,eai:acl.sharing,search,tags,title, updated
-> LOOKUP: cloud-test_all_eventtypes_src.csv

| rest splunk_server=local /servicesNS/-/-/search/tags | fields title updated
-> LOOKUP: cloud-test_all_tags.csv

| rest splunk_server=local /servicesNS/-/-/datamodel/model | fields title eai:acl.app, eai:acl.owner,eai:acl.sharing,description,updated
-> LOOKUP: cloud-test_all_datamodel_src.csv

| rest splunk_Server=local /servicesNS/-/-/data/lookup-table-files | fields title eai:acl.app, eai:acl.owner,eai:acl.sharing,updated
-> LOOKUP: cloud-test_all_lookup_src.csv 

| rest splunk_server=local /servicesNS/-/-/configs/conf-macros | fields title eai:acl.app eai:acl.owner eai:acl.sharing definition args disabled updated
-> LOOKOUP: cloud-test_all_macros_src.csv 

| rest splunk_server=local /servicesNS/-/-/data/ui/panels |fields eai:acl.owner, eai:acl.app, eai:acl.sharing, eai:data, panel.title, title, updated, disabled
-> LOOKOUP: cloud-test_all_panels_src.csv 

| rest splunk_server=local /servicesNS/-/-/apps/local | fields label title 
-> LOOKUP: cloud-test_all_apps_src.csv 

| rest splunk_server=local /servicesNS/-/-/authentication/users | fields email realname title type 
-> LOOKUP: cloud-test_all_users_src.csv 

| rest /servicesNS/-/-/authorization/roles |fields capabilities, imported_capabilities, imported_roles, srchIndexesAllowed,srchIndexesDefault,title |mvexpand imported_roles
-> LOOKUP: cloud-test_all_roles_src.csv 

| rest splunk_server=local /servicesNS/-/-/authorization/roles | fields capabilities, imported_capabilities, imported_roles, title,srchIndexesAllowed,srchIndexesDefault,title |mvexpand srchIndexesAllowed
-> LOOKUP: cloud-test_all_roles_src_indexes.csv 

| rest splunk_server=IDX /services/data/indexes | search title!="_*" |fields title, updated
-> LOOKUP: cloud-test_all_indexes_src.csv 

| rest splunk_server=local /servicesNS/-/-/saved/sourcetypes |fields title
-> LOOKUP: cloud-test_all_sourcetypes_src.csv 

| rest splunk_server=local /servicesNS/-/-/admin/(SAML|LDAP)-groups | fields title roles type
-> LOOKUP: cloud-test_all_groups_src.csv

 
## Install
This app should be installed on Search Heads
https://docs.splunk.com/Documentation/SplunkCloud/latest/Admin/Experience Install the app. For Splunk Cloud, refer to [Install apps in your Splunk Cloud deployment](https://docs.splunk.com/Documentation/SplunkCloud/latest/Admin/SelfServiceAppInstall). For customer managed deployments, refer to the standard methods for Splunk Add-on installs as documented for a [Single Server Install](http://docs.splunk.com/Documentation/AddOns/latest/Overview/Singleserverinstall) or a [Distributed Environment Install](http://docs.splunk.com/Documentation/AddOns/latest/Overview/Distributedinstall).
 
## Configuration
Make sure you are sc_admin and share the lookups to this app only.
 
## Usage
Content Validation V2:
This Panel will make sure all titles are migrated.
src = on-prem
dest = Splunk Cloud/on-prem destination
If src=true and dest=true, this means the KO titles were migrated successfully.
Inputs:
Exclude: Click on the apps you don’t want to see populating.
Missing: By default is set up to true in order to check all missing KOs.
Content: Select if you would like to see all content(User, global and app) or just User content or any user content.
Environment: Click on the stack name(Remember to replace lookup) or setup the static value
Select the KO you would like to see(By default Savedsearches are gonna show up)

Update Validation:
Type a date and Splunk will check the updated KOs since this date.
Data Validator:
Here you can check if all buckets from on-prem were migrated.
Check the source and pre-requisites, then assign the correct name to the lookup
Useful dashboards:
Event Parser: Parse your data using the magic 8.
Data Quality: Check the sourcetypes with issues and use this dashboard to identify better and faster the main issues.
 
 
# Known Issues
See the release notes of the latest version for known issues
 
# Troubleshooting Steps
If no information is returned, make sure you renamed the lookup correctly.
If Lookup is correct, this means all content was migrated successfully.
If you make sure everything is migrated but user content is showing up, until the user logs in, this content will disappear from the search.
If you click on the panel, it will show another search that is comparing the content of the title(This would only check existing content on both environments).
 
# Upgrade
No special instructions for upgrading this app to a newer version.
 
# Help
While this app is not formally supported, the developer can be reached at bran1501@gmail.com(OR in splunk-usergroups slack, @Christhian Bran). Responses are made on a best effort basis. Feedback is always welcome and appreciated!
(if you use the User Group approach, include: Learn more about splunk-usergroups slack here: https://docs.splunk.com/Documentation/Community/current/community/Chat#Join_us_on_Slack)

