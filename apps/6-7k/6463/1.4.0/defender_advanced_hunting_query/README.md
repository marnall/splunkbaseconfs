
# Defender Advanced Hunting Query App by GoAhead 

## Introduction

API wrapper tool for Microsoft Defender Advanced Hunting. 
Advanced Hunting uses Kusto Query Language (KQL) and the KQL is passed as kql="" on "defkqlg" or "defkqls" custom search command.
defkqls StreamingCommand has an unique KQL converter for reducing the query amount against the API quotas limit!

## Installation

The credential set of tenantId, appId and appSecret for getting Azure AD Token are needed to utilize this App.
1. Prepare credential set of tenantId, appId and appSecret on Azure AD (See API reference below). This app needs AdvancedQuery.Read.All for [Advanced Hunting API](https://learn.microsoft.com/en-us/microsoft-365/security/defender-endpoint/run-advanced-query-api?view=o365-worldwide) or AdvancedHunting.Read.All for [Microsoft 365 Defender Advanced Hunting API](https://learn.microsoft.com/en-us/microsoft-365/security/defender/api-advanced-hunting?view=o365-worldwide).
2. Install this App package
3. Set up the credential on the App Setup View. The credentials are encrypted and stored in Secret storage
4. Restarting splunk search head instance may be possibly needed for activating these custom search commands. 
5. App Install user needs "admin_all_objects" privilege and Splunk search users need "list_storage_passwords" privilege in order to utilize "Secret storage".

## Usage

1. **defkqlg**
    - GeneratingCommand to call Microsoft Defender's APIs and fetch event data.
    - Options
        - **api** (required):        Choose "queries" or "hunting", "queries" means to access to *Advanced Hunting API*, "hunting" means to access to *Microsoft 365 Defender Advanced Hunting API*.
        - **kql** (required):        KQL query to run
    - Output field name
        - the same of field names from defender API result or "Defender_api_error" field only when unexpected error happens.
    - Example  
        - ` ...| defkqlg api="queries" kql="DeviceProcessEvents | where DeviceId = "xxxxxxxxx" | limit 10`

2. **defkqls**
    - StreamingCommand for calling Microsoft Defender's APIs and combine the fetch data to splunk previous events.
    - Options
        - **api** (required):        Choose "queries" or "hunting", "queries" means to access to *Advanced Hunting API*, "hunting" means to access to *Microsoft 365 Defender Advanced Hunting API*.
        - **primary_field** (required):      Splunk field used in where/filter KQL covered with `` and the field value matched to that of defender field in order to append the defender events.
        - **kql** (required):         KQL query to run, the same field name in kql are automatically pass to this kql filtering block.
    - Output field name
        - "Defender_<Defender_field_name>" when API results are good and "Defender_api_error" field shows the API result status and errors.
    - "or" is appended between the passed event values and your input KQL is replaced into the final KQL. It makes the API amount to only one query per this command execution.
    - Triggered scalar operators to modify your KQL
      - "==|>=|<=|>|<|=~|has_cs|has_any|has_all|contains_cs|contains|between|in~|in|endswith_cs|endswith|startswith_cs|startswith|hasprefix_cs|hasprefix|hassuffix_cs|hassuffix|has|!=|!~|!has_cs|!contains_cs|!contains|!between|!in~|!in|!endswith_cs|!endswith|!startswith_cs|!startswith|!hasprefix_cs|!hasprefix|!hassuffix_cs|!hassuffix|!has"
      - Only == or =~ is available for primary_field.
    - Example
        - ```| makeresults | eval pcname="xxxxxxxx" | defkqls api=queries primary_field=pcname kql="DeviceProcessEvents | where DeviceName == `pcname` | limit 10" | table _time pcname Defender_*```
        - ```source="pcname_id_timestamp_sample.csv" | defkqls api=queries primary_field=id kql="DeviceProcessEvents | where Timestamp > datetime(`timestamp`) | filter DeviceName =~ `pcname` and DeviceId == `id` | limit 10" | table _time pcname Defender*```
        - ``` source="src_dst_sample.csv" | defkqls api=queries primary_field=srcip kql="DeviceNetworkEvents | where LocalIP == `srcip` or RemoteIP == `dstip` and InitiatingProcessFileName has_cs "chrome" | project Timestamp,LocalIP,RemoteIP,InitiatingProcessCommandLine,InitiatingProcessFolderPath,InitiatingProcessMD5 | limit 5" ```
  

Command usages are also described in searchbnf.conf, thus you can see it on search window by writing the command name on. 

The command exception and **final KQL query** per execution will be dumped in "search.log" or "%SPLUNK_HOME%/var/log/defender_advanced_hunting_query.log".

Please feel free to contact us if you have any issue or request about **defkqls** command.

`defkqlg` command is just an API rapper command and this app don't touch the KQL query and its output.

**Note. Please use single quote or escaped double quote inside your kql query because simple double quote is interpreted as a part of splunk SPL.**

- OK: kql="brabra | where Protocol == \"NTLM\" | fugafuga"
- OK: kql="brabra | where Protocol == 'NTLM' | fugafuga"
- `NG: kql="brabra | where Protocol == "NTLM" | fugafuga"`



## Microsoft Defender API reference


### How to prepare to utilize these APIs and API Quotas Limit

#### Create an app to access Microsoft 365 Defender without a user 
- https://learn.microsoft.com/en-us/microsoft-365/security/defender-endpoint/exposed-apis-create-app-webapp?view=o365-worldwide
- For "Microsoft Defender for Endpoint Plan 2" users
- In addition, it needs AdvancedQuery.Read.All permission.
- Call Advanced Hunting API by setting an app option: *api=queries*
- [API Quotas Limit](https://learn.microsoft.com/en-us/microsoft-365/security/defender-endpoint/run-advanced-query-api?view=o365-worldwide#limitations)

#### Create an app to access Microsoft 365 Defender without a user
- https://learn.microsoft.com/en-us/microsoft-365/security/defender/api-create-app-web?view=o365-worldwide
- For "Microsoft 365" users 
- In addition, it needs AdvancedHunting.Read.All permission.
- Call Microsoft 365 Defender Advanced hunting API by setting an app option: *api=hunting*
- [API Quotas Limit](https://learn.microsoft.com/en-us/microsoft-365/security/defender/api-advanced-hunting?view=o365-worldwide#quotas-and-resource-allocation) 

#### Appendix
ref: [Compare Microsoft Defender for Endpoint plans](https://learn.microsoft.com/en-us/microsoft-365/security/defender-endpoint/defender-endpoint-plan-1-2?view=o365-worldwide)


## Included 3rd party's additional import modules

None

## Support

Splunk 9.x


## License

[LGPLv3](https://www.gnu.org/licenses/lgpl-3.0.en.html)

## Release Note
- 1.0.0
    - initial version, implemented defkqlg GeneratingCommand and defkqls StreamingCommand. (passed appinspect "private_app" criteria)

- 1.1.0
    - improvement of defkqls StreamingCommand ,which much operators, primary_field option and a complex condition's conbination were implemented.

- 1.1.1 and 1.1.2
    - only update appIcon

- 1.1.3
    - Potential bug fix:
    - Changed secret storage's secret username for avoiding collisions in the global share (system) setting mode.

- 1.1.4
    - minor changes of documents and conf.
    - update splunk-sdk-python to 1.7.3 latest
    - copy right update

- 1.2.0
    - update api endpoint urls of "Microsoft 365 Defender Advanced hunting API"

- 1.3.0
    - distibutable streaming for defkqls
    - adjust to the latest appinspect review

- 1.3.1 
    - renewal of access method to secret storage

## Copyright

Copyright 2025 GoAhead Inc.
