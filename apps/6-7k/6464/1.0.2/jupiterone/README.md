# JupiterOne

Publisher: JupiterOne Inc. \
Connector Version: 1.0.2 \
Product Vendor: JupiterOne Inc. \
Product Name: JupiterOne \
Minimum Product Version: 5.2.0

This app integrates with JupiterOne to perform investigative actions

### Configuration variables

This table lists the configuration variables required to operate JupiterOne. These variables are specified when configuring a JupiterOne asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**account_id** | required | string | JupiterOne Account ID |
**api_key** | required | password | API Key |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration parameters \
[run query](#action-run-query) - Run a search query

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration parameters

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'run query'

Run a search query

Type: **investigate** \
Read only: **True**

The <b>query </b> parameter accepts J1QL query (eg: find Record) as well as the full-text search. The full-text search query needs to enclosed in double-quotes("") (eg: "assets"). Please refer <a href='https://support.jupiterone.io/hc/en-us/articles/360022720434-J1QL-Query-Tutorial' target='_blank'>JupiterOne Query Language Tutorial</a> for J1QL reference. The <b>max_results</b> parameter overwrites the LIMIT if mentioned in the J1QL. (For instance, if query parameter has value "find Record LIMIT 20" and max_results parameter has value "10", the action would return 10 records. This implementation was added because the LIMIT in query accept values only between 1 and 250.).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query** | required | J1QL query to run | string | `jupiterone query` |
**max_results** | optional | Maximum number of results to fetch for the query. The default value is 250 | numeric | |
**include_deleted** | optional | Include recently deleted entities in query/search | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.query | string | `jupiterone query` | find Record "assets" |
action_result.parameter.max_results | numeric | | 250 |
action_result.parameter.include_deleted | boolean | | True False |
action_result.data.\*.id | string | | 3e61c266-bfb1-4a48-9984-458f756cf5d2 |
action_result.data.\*.entity.\_id | string | | 91b3c4f8-21f0-4c80-8209-c9a0ec2db936 |
action_result.data.\*.entity.\_key | string | | test_vulnerability |
action_result.data.\*.entity.\_source | string | | api |
action_result.data.\*.entity.\_beginOn | string | | 2021-10-21T08:54:30.345Z |
action_result.data.\*.entity.\_deleted | boolean | | True False |
action_result.data.\*.entity.\_version | numeric | | 1 |
action_result.data.\*.entity.\_accountId | string | | c2c0b39c-6a82-4ff1-a53e-0cff10ee93c3 |
action_result.data.\*.entity.\_createdOn | string | | 2021-10-21T08:54:30.345Z |
action_result.data.\*.properties.name | string | | test_name |
action_result.data.\*.properties.DisplayName | string | | test_vuln |
action_result.data.\*.entity.displayName | string | | Tenable.io |
action_result.data.\*.entity.\_integrationName | string | | Test_Tenable |
action_result.data.\*.entity.\_integrationType | string | | tenable-cloud |
action_result.data.\*.entity.\_integrationInstanceId | string | | 8fb92a4f-4730-4f64-be7e-fc21fcb299d7 |
action_result.data.\*.entity.\_integrationDefinitionId | string | | cd4f0f10-aeb1-4c73-8476-5218d6c2e421 |
action_result.data.\*.properties.tag.Production | boolean | | True False |
action_result.data.\*.properties.tag.AccountName | string | | test_tenable_account |
action_result.data.\*.properties.tags | string | | Production |
action_result.data.\*.properties.website | string | | https://www.testsite.com |
action_result.data.\*.properties.emailDomain | string | | www.testdomain.com |
action_result.data.\*.properties.id | string | | Test-account |
action_result.data.\*.properties.accountId | string | | c2c0b39c-6a82-4ff1-a53e-0cff10ee93c3 |
action_result.data.\*.properties.privacyPolicy | boolean | | True False |
action_result.data.\*.properties.accountFullName | string | | Test Name |
action_result.data.\*.properties.companyFullName | string | | Test Company |
action_result.data.\*.properties.companyOverview | string | | |
action_result.data.\*.properties.termsConditions | boolean | | True False |
action_result.data.\*.properties.companyShortName | string | | TestCompany |
action_result.data.\*.properties.companyWebsiteURL | string | | https://www.testsite.com |
action_result.data.\*.properties.accountCompanyRole | string | | Engineering / Development |
action_result.data.\*.properties.companyEmailDomain | string | | www.testcompany.com |
action_result.data.\*.properties.onboardingComplete | boolean | | True False |
action_result.data.\*.properties.currentOnboardingStep | numeric | | 2 |
action_result.data.\*.properties.iconWebLink | string | | |
action_result.data.\*.entity.\_scope | string | | jupiterone |
action_result.data.\*.properties.type | string | | closed |
action_result.data.\*.properties.deleteProtected | boolean | | True False |
action_result.data.\*.properties.endpoints | string | | https://falcon.crowdstrike.com/ |
action_result.data.\*.properties.projectId | string | | integrations-testing-225416 |
action_result.data.\*.properties.dummy_column | string | | hifff |
action_result.data.\*.properties.column1 | numeric | | 12345 |
action_result.data.\*.properties.Test | string | | abc |
action_result.data.\*.properties.email | string | | test.name@testemail.com |
action_result.data.\*.properties.active | boolean | | True False |
action_result.data.\*.properties.picture | string | | https://lh3.googleusercontent.com/a/AATXAJzDYLaI4vF4QidOWEq7cI8pdnk_tZYmnNbVx-zT2Q=s96-c |
action_result.data.\*.properties.username | string | | Google_109085908064582228395 |
action_result.data.\*.properties.createdOn | string | | 2021-08-17T12:27:47.251Z |
action_result.data.\*.properties.givenName | string | | Test |
action_result.data.\*.properties.familyName | string | | Test |
action_result.data.\*.properties.mfaEnabled | boolean | | True False |
action_result.data.\*.properties.emailVerified | boolean | | True False |
action_result.data.\*.properties.instanceId | string | | i-07226fdf7f7df6cfa |
action_result.data.\*.properties.state | string | | OPEN |
action_result.data.\*.properties.output | string | | 1.1.1.1 resolves as one.one.one.one. |
action_result.data.\*.properties.severity | string | | info |
action_result.data.\*.properties.plugin.id | numeric | | 12053 |
action_result.data.\*.properties.port.port | numeric | | 0 |
action_result.data.\*.properties.scan.uuid | string | | a61b3f64-ed7e-4cd2-a857-80ee34b85571 |
action_result.data.\*.properties.asset.uuid | string | | 293f3870-2f3d-41a6-a6e9-92b9c39b5401 |
action_result.data.\*.properties.lastSeenOn | string | | 2021-09-24T07:03:17.772Z |
action_result.data.\*.properties.last_found | string | | 2021-09-24T07:03:17.772Z |
action_result.data.\*.properties.firstSeenOn | string | | 2021-08-16T09:52:10.098Z |
action_result.data.\*.properties.first_found | string | | 2021-08-16T09:52:10.098Z |
action_result.data.\*.properties.severity_id | numeric | | 0 |
action_result.data.\*.properties.port.protocol | string | | TCP |
action_result.data.\*.properties.scan.started_at | string | | 2021-09-24T06:52:04.020Z |
action_result.data.\*.properties.scan.completed_at | string | | 2021-09-24T07:03:17.772Z |
action_result.data.\*.properties.severity_default_id | numeric | | 0 |
action_result.data.\*.properties.severity_modification_type | string | | |
action_result.data.\*.properties.port.service | string | | www |
action_result.data.\*.properties.exception | boolean | | True False |
action_result.data.\*.properties.@exception | string | | |
action_result.data.\*.properties.exceptionReason | string | | Accepted Risk |
action_result.data.\*.properties.@exceptionReason | string | | |
action_result.data.\*.properties.priority | string | | Medium |
action_result.data.\*.properties.numericPriority | numeric | | 4.4 |
action_result.data.\*.properties.updatedOn | string | | 2021-03-15T18:50:37.000Z |
action_result.data.\*.properties.description | string | | Default group for approvers of Report Access Requests |
action_result.data.\*.properties.uuid | string | | 50c09ffd-a6bc-43bd-99a1-1f50c57a3bd9 |
action_result.data.\*.properties.uuidId | string | | 50c09ffd-a6bc-43bd-99a1-1f50c57a3bd9 |
action_result.data.\*.properties.enabled | boolean | | True False |
action_result.data.\*.properties.userName | string | | test.user.sans@tenable.com |
action_result.data.\*.properties.permissions | numeric | | 32 |
action_result.data.\*.properties.containerUuid | string | | f4fbe518-e648-49dd-b6a4-e80c1ff12805 |
action_result.data.\*.properties.loginFailCount | numeric | | 0 |
action_result.data.\*.properties.loginFailTotal | numeric | | 0 |
action_result.data.\*.properties.lastlogin | numeric | | 1623348295397 |
action_result.data.\*.properties.@dummy_column | string | | |
action_result.data.\*.properties.impact | string | | 3 |
action_result.data.\*.properties.category | string | | inquiry |
action_result.data.\*.properties.reporter | string | | abcdefg |
action_result.data.\*.properties.reportable | boolean | | True False |
action_result.data.\*.properties.resolvedAt | string | | |
action_result.data.\*.properties.open | boolean | | True False |
action_result.data.\*.properties.level | string | | HIGH |
action_result.data.\*.properties.status | string | | ACTIVE |
action_result.data.\*.properties.webLink | string | | https://company.apps.us.jupiterone.io/alerts/?alertId=ba156f1d-637e-470b-94ca-d8f44a2ede79 |
action_result.data.\*.properties.numericSeverity | numeric | | 7 |
action_result.data.\*.properties.version | numeric | | 1 |
action_result.data.\*.properties.specVersion | numeric | | 1 |
action_result.data.\*.properties.column2 | numeric | | 4920 |
action_result.data.\*.properties.column3 | string | | test3 |
action_result.data.\*.properties.column4 | numeric | | 9396 |
action_result.data.\*.properties.column5 | string | | test5 |
action_result.data.\*.properties.function | string | | vulnerability-detection |
action_result.data.\*.properties.hasAgent | boolean | | True False |
action_result.data.\*.properties.lastSeen | string | | 2021-09-09T16:18:21.718Z |
action_result.data.\*.properties.createdAt | string | | 2021-09-09T16:18:23.878Z |
action_result.data.\*.properties.firstSeen | string | | 2021-09-09T16:18:21.718Z |
action_result.data.\*.properties.networkId | string | | 00000000-0000-0000-0000-000000000000 |
action_result.data.\*.properties.updatedAt | string | | 2021-09-09T16:18:29.219Z |
action_result.data.\*.properties.networkName | string | | Default |
action_result.data.\*.properties.macAddresses | string | | 00:00:00:07:71:1c |
action_result.data.\*.properties.netbiosNames | string | | WXXCNC1BPBDRCV4Y |
action_result.data.\*.properties.tag.Scan Group | string | | ServiceNow |
action_result.data.\*.properties.operatingSystems | string | | Cpe:/o::windows_10:::x64-home |
action_result.data.\*.properties.servicenowSysid | string | | abcdefg |
action_result.data.\*.properties.hasPluginResults | boolean | | True False |
action_result.data.\*.properties.fqdns | string | | 5n74sctfh1ibgwyr.example |
action_result.data.\*.properties.ipv4s | string | | 226.60.208.153 |
action_result.data.\*.properties.lastScanTime | string | | 2018-10-15T19:14:46.248Z |
action_result.data.\*.properties.firstScanTime | string | | 2018-08-13T14:22:46.464Z |
action_result.data.\*.properties.lastLicensedScanDate | string | | 2018-10-15T17:54:56.303Z |
action_result.data.\*.properties.lastScanId | string | | 98ad62f6-fe69-4624-9f5a-065de8d8996e |
action_result.data.\*.properties.lastScheduleId | string | | template-3c6a1dbf-4c5f-c7cc-3cc2-25277f598aaab01c249ad6d0fc2e |
action_result.data.\*.count(Record) | numeric | | 19684 |
action_result.data.\*.properties.awsVpcId | string | | vpc-0e490abe697f364ce |
action_result.data.\*.properties.awsRegion | string | | us-east-1 |
action_result.data.\*.properties.awsOwnerId | string | | 193468595165 |
action_result.data.\*.properties.awsSubnetId | string | | subnet-08e23be65ecc14f7f |
action_result.data.\*.properties.awsEc2InstanceId | string | | i-0dcb3d7d81686b180 |
action_result.data.\*.properties.awsEc2ProductCode | string | | 7lgvy7mt78lgoi4lant0znp5h |
action_result.data.\*.properties.awsEc2InstanceType | string | | t2.micro |
action_result.data.\*.properties.awsAvailabilityZone | string | | us-east-1b |
action_result.data.\*.properties.awsEc2InstanceAmiId | string | | ami-0212d39aa1d70f26b |
action_result.data.\*.properties.awsEc2InstanceState | string | | running |
action_result.data.\*.properties.awsEc2InstanceGroupName | string | | kali linux-kali linux 2021-3-autogenbyawsmp- |
action_result.data.\*.properties.lastAuthenticatedScanDate | string | | 2018-06-05T13:12:09.000Z |
action_result.data.\*.properties.azureVmId | string | | 80eff9db-bac1-4fc6-a0c4-6aa30708ea78 |
action_result.data.\*.properties.azureResourceId | string | | /subscriptions/4fa12f4e-030d-4867-bb4f-7d58fbea4463/resourcegroups/default-storage-eastus/providers/microsoft.compute/virtualmachines/sc-cert-auth |
action_result.data.\*.properties.tag.bob | string | | nick |
action_result.data.\*.properties.tag.Nick | string | | bob |
action_result.data.\*.properties.tag.Test | string | | Accept Risk |
action_result.data.\*.properties.agentUuid | string | | abcdefg |
action_result.data.\*.properties.terminatedAt | string | | 2021-08-05T23:57:17.000Z |
action_result.data.\*.properties.terminatedBy | string | | AWS |
action_result.data.\*.properties.ipv6s | string | | fe80:0:0:0:d4:89ff:fea6:cea4 |
action_result.data.\*.properties.awsEc2Name | string | | splunk-test |
action_result.data.\*.properties.installedSoftware | string | | cpe:/a:openbsd:openssh:6.9 |
action_result.data.\*.properties.tag.foo | string | | bar |
action_result.data.\*.properties.biosUuid | string | | 9c60da51-762a-4b9b-8504-411056c2f696 |
action_result.data.\*.properties.gcpZone | string | | us-east1-b |
action_result.data.\*.properties.gcpProjectId | string | | integrations-testing-225416 |
action_result.data.\*.properties.gcpInstanceId | string | | 6043552634079149806 |
action_result.data.\*.properties.tag.sample | string | | sample_1 |
action_result.data.\*.properties.agentNames | string | | instance-1 |
action_result.data.\*.entity.\_endOn | string | | 2021-12-21T10:19:24.541Z |
action_result.status | string | | success failed |
action_result.message | string | | Total results: 2 |
action_result.summary.total_results | numeric | | 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2025 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
