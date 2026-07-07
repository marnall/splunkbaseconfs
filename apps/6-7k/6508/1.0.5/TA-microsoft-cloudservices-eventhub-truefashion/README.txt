# Microsoft Cloud Services Event Hub True Fashion Add-on for Splunk

## Introduction

This add-on provides natural access to field names being delivered through Azure Event Hubs in conjunction with [Splunk Add-on for Microsoft Cloud Services](https://splunkbase.splunk.com/app/3110/).

No extra field extractions or CIM compatibility is done.

Instead it uses SEDCMDs to re-format Event Hub message format structure safely. This way Splunk can keep JSON format parsing intact (KV_MODE=json) while overhead in processing and field naming does get reduced. Because of minor changes how data is being indexed upcoming schema changes (new fields) by vendor Microsoft are automatically supported.
Using this add-on will give the following advantages:

- Direct field name access as designed by the original format on the backend, prior data was sent to Event Hub (no more body.properties or body.records.properties prefix prefix in field names for example)
- Cuts off unnecessary fields from Event Hub messages (x-opt-sequence-number, x-opt-offset and x-opt-enqueued-time)
- Ingested data via Event Hub is easier interpreted because of original field names. SPLs and detections are easier to write because field names are kept in original format.

Supports Azure Event Hubs messages sent by:
* [Microsoft 365 Defender Streaming-API](https://docs.microsoft.com/en-US/microsoft-365/security/defender/streaming-api-event-hub?view=o365-worldwide) - Advanced Hunting telemetry like: DeviceAlertEvents DeviceProcessEvents DeviceNetworkInfo DeviceLogonEvents DeviceEvents DeviceTvmSoftwareVulnerabilitiesKB etc.
* [Azure Blade monitor logs](https://docs.microsoft.com/en-US/azure/azure-monitor/essentials/platform-logs-overview) - Azure platform telemetry like: AuditLogs SignInLogs NonInteractiveUserSignInLogs ServicePrincipalSignInLogs ManagedIdentitySignInLogs RiskyUsers UserRiskEvents etc.

### How is this different from other add-on 'Splunk Add on for Microsoft Azure'?
#### [Splunk Add on for Microsoft Azure](https://splunkbase.splunk.com/app/3757/)
* The above is used to ingest data from Azure Event Hubs via classic REST-API.
* Your fields will ALREADY look nice when you use this add-on. Nothing more is required and you will not need Microsoft Cloud Services Event Hub True Fashion Add-on for Splunk.
* But this approach is deprecated and has no official Splunk CIM support.

### How is this different from other add-on 'Splunk Add-on for Microsoft Cloud Services' (MSCS)?
#### [Splunk Add-on for Microsoft Cloud Services](https://splunkbase.splunk.com/app/3110/)
* The above is used to ingest data from Azure Event Hubs via modern Azure AD app with Event Hub Reader permission.
* Your fields will NOT LOOK nice using sourcetype: `mscs:azure:eventhub`
* You may now use further add-ons to improve field naming, for example "Microsoft Defender Advanced Hunting Add-on for Splunk" using sourcetype `mscs:azure:eventhub:defender:advancedhunting` or use this add-on here you are looking at which introduces sourcetype `mscs:azure:eventhub:truefashion`
#### Difference between [Splunk Add-on for Microsoft Cloud Services](https://splunkbase.splunk.com/app/3110/) version 4.3.3 and version 4.4.0?
* In version 4.4.0 it has been natively improved to remove body and Event Hub messages fields x-opt-sequence-number, x-opt-offset and x-opt-enqueued-time - overall nesting has been reduced (documented in [MSCS Release History](https://docs.splunk.com/Documentation/AddOns/released/MSCloudServices/ReleaseHistory))
* Still properties.* fieldnames are used which you can use this add-on for to remove prefix

### How is this different from other add-on 'Microsoft Defender Advanced Hunting Add-on for Splunk'?
#### [Microsoft Defender Advanced Hunting Add-on for Splunk](https://splunkbase.splunk.com/app/5518/)
* The above is used to extract and normalize data from Microsoft 365 Defender Streaming-API into Splunk CIM and it is supported by Splunk in conjunction with 'Splunk Add-on for Microsoft Cloud Services' (MSCS).
* But it does not map out every field to CIM, does assumptions and does not fix the core field naming prefixes during ingestion at index time.
* Means this will not help you in case of getting the original field names better readable (even when MSCS v4.3.3+ parses body.records in loop now).

### So why and when should I use 'Microsoft Cloud Services Event Hub True Fashion Add-on for Splunk'?
* If you want to ingest any data from Azure Event Hubs using [Splunk Add-on for Microsoft Cloud Services](https://splunkbase.splunk.com/app/3110/) (MSCS) while keeping the original field names intact without doing any further modifications and/or extractions with the data.
* This simply gets you the original field names. For example to build your own index / summary index / custom CIM.
* In short: it simply removes body.properties and body.records.properties which makes fields much more readable, without any fancy transformations.

## Installation

1. Configure Microsoft Defender for Endpoint to stream Advanced Hunting events to an Azure Event Hub or configure Azure Blade diagnostic events to be forward to an Event Hub. See: https://docs.microsoft.com/en-us/microsoft-365/security/defender-endpoint/raw-data-export-event-hub?view=o365-worldwide
You can use multiply sourcetypes of data in the same Event Hub. This add-on re-renders all Event Hub messages safely. It is best-practice to separate Event Hubs per each sourcetype though.

2. Install this add-on on your Search Heads, Indexers and Heavy Forwarders (if part of your data collection topology)

3. Install and use this Splunk add-on to ingest data from Azure Event Hub: [Splunk Add-on for Microsoft Cloud Services](https://splunkbase.splunk.com/app/3110/) version 4.3.3+

4. When setting the up the input, enter sourcetype: `mscs:azure:eventhub:truefashion`
Note: Starting with version 4.4.0 of [Splunk Add-on for Microsoft Cloud Services](https://splunkbase.splunk.com/app/3110/) it is no longer possible to manually set a sourcetype, which is not part of the dropdown list.
Select sourcetype: `mscs:azure:eventhub` and edit file
`Splunk_TA_microsoft-cloudservices/local/inputs.conf` manually to replace
`sourcetype = mscs:azure:eventhub` 
with
`sourcetype = mscs:azure:eventhub:truefashion`

5. Verify that raw data is arriving by running the following search: `index=* sourcetype="mscs:azure:eventhub:truefashion"`

## Changelog

- Version 1.0.5: Added support for new Microsoft raw data key called Tenant (framed key-value pairs: category, operationName, tenantId, time, properties and now Tenant are available after flattening)
- Version 1.0.4: Added support for Splunk Add-on for Microsoft Cloud Services version v4.4.0 & v4.5.0 (includes backwards compatibility for v4.3.3)
- Version 1.0.3: First public release based on Splunk Add-on for Microsoft Cloud Services version v4.3.3

## Data Sample (without and with this add-on)

Original Event Hub message format in Splunk Add-on for Microsoft Cloud Services 4.3.3:

```json
{
    "body": {
        "time": "2022-07-07T12:45:18.3907246Z",
		"tenantId": "a4547165-6daa-4e9e-b2c3-8e7fb7142e4d",
		"operationName": "Publish",
		"category": "AdvancedHunting-DeviceNetworkEvents",
		"properties": {
			"RemotePort": 63967,
			"RemoteIP": "127.0.0.1",
			"Protocol": "Tcp",
			"LocalIP": "127.0.0.1",
			"LocalPort": 63968,
			"RemoteUrl": "",
			"LocalIPType": "Loopback",
			"RemoteIPType": "Loopback",
			"AdditionalFields": null,
			"ActionType": "ConnectionSuccess",
			"InitiatingProcessVersionInfoCompanyName": "Microsoft Corporation",
			"InitiatingProcessVersionInfoProductName": "Microsoft\u00ae Windows\u00ae Operating System",
			"InitiatingProcessVersionInfoProductVersion": "10.8048.22439.1065",
			"InitiatingProcessVersionInfoInternalFileName": "MsSense.exe",
			"InitiatingProcessVersionInfoOriginalFileName": "MsSense.exe",
			"InitiatingProcessVersionInfoFileDescription": "Windows Defender Advanced Threat Protection Service Executable",
			"InitiatingProcessFolderPath": "c:\\program files\\windows defender advanced threat protection\\mssense.exe",
			"InitiatingProcessFileSize": 472368,
			"InitiatingProcessMD5": "f23bada6ff4f6f9bf4c5342093156855",
			"InitiatingProcessSHA256": "cb993f887eff06aec7bcfe5fc7f14e890adb18871ced1e8edbb57e858e126978",
			"InitiatingProcessSHA1": "73285ffb57122d7822a979b909cf41b999b1cc6e",
			"InitiatingProcessAccountSid": "S-1-5-18",
			"InitiatingProcessAccountDomain": "nt authority",
			"InitiatingProcessAccountName": "system",
			"InitiatingProcessAccountUpn": null,
			"InitiatingProcessAccountObjectId": null,
			"InitiatingProcessCreationTime": "2022-07-07T11:02:16.5447066Z",
			"InitiatingProcessId": 2988,
			"InitiatingProcessFileName": "MsSense.exe",
			"InitiatingProcessCommandLine": "\"MsSense.exe\"",
			"InitiatingProcessParentCreationTime": "2022-07-07T11:01:36.8066095Z",
			"InitiatingProcessParentId": 672,
			"InitiatingProcessParentFileName": "services.exe",
			"InitiatingProcessIntegrityLevel": "System",
			"InitiatingProcessTokenElevation": "TokenElevationTypeDefault",
			"DeviceId": "58faa2ef39046f86543ec7fb8849dfd54dd014fa",
			"AppGuardContainerId": null,
			"MachineGroup": null,
			"Timestamp": "2022-07-07T12:44:56.208162Z",
			"DeviceName": "dcwin2016.lab.local",
			"ReportId": 7251
		}
	},
	"x-opt-sequence-number": 6632,
	"x-opt-offset": "21481563656",
	"x-opt-enqueued-time": 1657198004612
}
```

Original Event Hub message format in Splunk Add-on for Microsoft Cloud Services 4.4.0:
(body and x-opt-* fields are now built-in removed but properties.* array fields still exists as extra dimension)


```json
{
	"time": "2022-07-21T15:16:03.6719584Z",
	"tenantId": "a4547165-6daa-4e9e-b2c3-8e7fb7142e4d",
	"operationName": "Publish",
	"category": "AdvancedHunting-DeviceEvents",
	"properties": {
		"AccountSid": null,
		"AccountDomain": null,
		"AccountName": null,
		"LogonId": null,
		"FileName": null,
		"FolderPath": null,
		"MD5": null,
		"SHA1": null,
		"FileSize": null,
		"SHA256": null,
		"ProcessCreationTime": null,
		"ProcessTokenElevation": null,
		"RemoteUrl": null,
		"RegistryKey": null,
		"RegistryValueName": null,
		"RegistryValueData": null,
		"RemoteDeviceName": null,
		"FileOriginIP": null,
		"FileOriginUrl": null,
		"LocalIP": null,
		"LocalPort": null,
		"RemoteIP": null,
		"RemotePort": null,
		"ProcessId": null,
		"ProcessCommandLine": null,
		"AdditionalFields": null,
		"ActionType": "NtProtectVirtualMemoryApiCall",
		"InitiatingProcessVersionInfoCompanyName": "Microsoft Corporation",
		"InitiatingProcessVersionInfoProductName": "Microsoft\u00ae .NET Framework",
		"InitiatingProcessVersionInfoProductVersion": "4.8.4320.0",
		"InitiatingProcessVersionInfoInternalFileName": "mscorsvw.exe",
		"InitiatingProcessVersionInfoOriginalFileName": "mscorsvw.exe",
		"InitiatingProcessVersionInfoFileDescription": ".NET Runtime Optimization Service",
		"InitiatingProcessFolderPath": "c:\\windows\\microsoft.net\\framework\\v4.0.30319\\mscorsvw.exe",
		"InitiatingProcessFileName": "mscorsvw.exe",
		"InitiatingProcessFileSize": 125872,
		"InitiatingProcessMD5": "d7365b80e8951ddc95f3a8e3ac01d37d",
		"InitiatingProcessSHA256": "3e5099f573601926e59862fba2495974688e72677c73f10e4c99e26a76cdcf37",
		"InitiatingProcessSHA1": "0636347981cb05b74859ce7c841753da90ce679a",
		"InitiatingProcessLogonId": 999,
		"InitiatingProcessAccountSid": "S-1-5-18",
		"InitiatingProcessAccountDomain": "nt authority",
		"InitiatingProcessAccountName": "system",
		"InitiatingProcessAccountUpn": null,
		"InitiatingProcessAccountObjectId": null,
		"InitiatingProcessCreationTime": "2022-07-21T15:13:22.3631034Z",
		"InitiatingProcessId": 6504,
		"InitiatingProcessCommandLine": "mscorsvw.exe -StartupEvent 218 -InterruptEvent 0 -NGENProcess 20c -Pipe 214 -Comment \"NGen Worker Process\"",
		"InitiatingProcessParentCreationTime": "2022-07-21T15:13:22.3092735Z",
		"InitiatingProcessParentId": 1368,
		"InitiatingProcessParentFileName": "ngen.exe",
		"DeviceId": "c3f1bb7cb3e12d004b0d317c0842d54f9f51c653",
		"AppGuardContainerId": "",
		"MachineGroup": null,
		"Timestamp": "2022-07-21T15:13:22.426665Z",
		"DeviceName": "clientwin10.lab.local",
		"ReportId": 1974
	}
}
```

Using this add-on data will be re-formatted using SEDCMD so Splunk can parse it easier:

```json
{
        "time": "2022-07-07T12:45:18.3907246Z",
        "tenantId": "a4547165-6daa-4e9e-b2c3-8e7fb7142e4d",
        "Tenant": "DefaultTenant",
        "operationName": "Publish",
        "category": "DeviceNetworkEvents",
        "RemotePort": 63967,
        "RemoteIP": "127.0.0.1",
        "Protocol": "Tcp",
        "LocalIP": "127.0.0.1",
        "LocalPort": 63968,
        "RemoteUrl": "",
        "LocalIPType": "Loopback",
        "RemoteIPType": "Loopback",
        "AdditionalFields": null,
        "ActionType": "ConnectionSuccess",
        "InitiatingProcessVersionInfoCompanyName": "Microsoft Corporation",
        "InitiatingProcessVersionInfoProductName": "Microsoft\u00ae Windows\u00ae Operating System",
        "InitiatingProcessVersionInfoProductVersion": "10.8048.22439.1065",
        "InitiatingProcessVersionInfoInternalFileName": "MsSense.exe",
        "InitiatingProcessVersionInfoOriginalFileName": "MsSense.exe",
        "InitiatingProcessVersionInfoFileDescription": "Windows Defender Advanced Threat Protection Service Executable",
        "InitiatingProcessFolderPath": "c:\\program files\\windows defender advanced threat protection\\mssense.exe",
        "InitiatingProcessFileSize": 472368,
        "InitiatingProcessMD5": "f23bada6ff4f6f9bf4c5342093156855",
        "InitiatingProcessSHA256": "cb993f887eff06aec7bcfe5fc7f14e890adb18871ced1e8edbb57e858e126978",
        "InitiatingProcessSHA1": "73285ffb57122d7822a979b909cf41b999b1cc6e",
        "InitiatingProcessAccountSid": "S-1-5-18",
        "InitiatingProcessAccountDomain": "nt authority",
        "InitiatingProcessAccountName": "system",
        "InitiatingProcessAccountUpn": null,
        "InitiatingProcessAccountObjectId": null,
        "InitiatingProcessCreationTime": "2022-07-07T11:02:16.5447066Z",
        "InitiatingProcessId": 2988,
        "InitiatingProcessFileName": "MsSense.exe",
        "InitiatingProcessCommandLine": "\"MsSense.exe\"",
        "InitiatingProcessParentCreationTime": "2022-07-07T11:01:36.8066095Z",
        "InitiatingProcessParentId": 672,
        "InitiatingProcessParentFileName": "services.exe",
        "InitiatingProcessIntegrityLevel": "System",
        "InitiatingProcessTokenElevation": "TokenElevationTypeDefault",
        "DeviceId": "58faa2ef39046f86543ec7fb8849dfd54dd014fa",
        "AppGuardContainerId": null,
        "MachineGroup": null,
        "Timestamp": "2022-07-07T12:44:56.208162Z",
        "DeviceName": "dcwin2016.lab.local",
        "ReportId": 7251
}
```

## Support

While this app is not formally supported, the developer can be reached at mail@grobendirk.de
Responses are made on a best effort basis. Feedback is always welcome and appreciated!

## Contact

Authored by Dirk Groben (mail@grobendirk.de)