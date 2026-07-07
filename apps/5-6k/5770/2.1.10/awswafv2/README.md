# AWS WAF V2

Publisher: Splunk <br>
Connector Version: 2.1.10 <br>
Product Vendor: AWS <br>
Product Name: WAF V2 <br>
Minimum Product Version: 6.3.0

This app integrates with AWS WAF to add and delete IP addresses using API version V2

## Asset Configuration

There are two ways to configure an AWS WAF asset. The first is to configure the **access_key** ,
**secret_key** and **region** variables. If it is preferred to use a role and Phantom is running as
an EC2 instance, the **use_role** checkbox can be checked instead. This will allow the role that is
attached to the instance to be used. Please see the [AWS EC2 and IAM
documentation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html)
for more information.

Region parameter provided in the asset configuration parameter and region of the bucket which is
created in AWS console must match, otherwise the user will get an InvalidLocationConstraint error.

For the **Update bucket** action, the
API is unable to validate the KMS key. Hence, it is recommended to provide a
valid KMS key in this action parameter, otherwise it will affect the S3 bucket. For example,
if we update the S3 bucket with an invalid KMS key and run the
'create object' action on the bucket then the action will not work for encryption = NONE.

## Assumed Role Credentials

The optional **credentials** action parameter consists of temporary **assumed role** credentials
that will be used to perform the action instead of those that are configured in the **asset** . The
parameter is not designed to be configured manually, but should instead be used in conjunction with
the Phantom AWS Security Token Service app. The output of the **assume_role** action of the STS app
with data path **assume_role\_\<number>:action_result.data.\*.Credentials** consists of a dictionary
containing the **AccessKeyId** , **SecretAccessKey** , **SessionToken** and **Expiration** key/value
pairs. This dictionary can be passed directly into the credentials parameter in any of the following
actions within a playbook. For more information, please see the [AWS Identity and Access Management
documentation](https://docs.aws.amazon.com/iam/index.html) .

### Configuration variables

This table lists the configuration variables required to operate AWS WAF V2. These variables are specified when configuring a WAF V2 asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**access_key_id** | optional | password | Access Key ID |
**access_key_secret** | optional | password | Access Key Secret |
**scope** | required | string | Specifies whether this is for an AWS CloudFront distribution or a regional application |
**region** | required | string | Region |
**use_role** | optional | boolean | Use attached role when running Phantom in EC2 |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[add ip](#action-add-ip) - Add new IP(s) to an existing IP set or a new IP set <br>
[delete ip](#action-delete-ip) - Remove IP(s) from an existing IP set <br>
[delete ip set](#action-delete-ip-set) - Remove the specified IP Set <br>
[list acls](#action-list-acls) - List all ACLs <br>
[list ip sets](#action-list-ip-sets) - List all IP sets

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'add ip'

Add new IP(s) to an existing IP set or a new IP set

Type: **contain** <br>
Read only: **False**

The ip_set_id or ip_set_name must be given as input for adding an IP to the IP set, ip_set_id will be considered if both ip_set_id and ip_set_name is provided in input. If the given ip_set_name does not exist on the server and the name matches the WAF IP set name criteria, the new IP set with a given input will be created on the server.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_set_id** | optional | ID of the IP set | string | `awswaf ip set id` |
**ip_set_name** | optional | Name of the IP set | string | `awswaf ip set name` |
**ip_address** | required | IP Address (Allows comma-separated) | string | `awswaf ip mask` |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_address | string | `awswaf ip mask` | 126.0.0.0/24 |
action_result.parameter.ip_set_id | string | `awswaf ip set id` | 0778db34-cc96-4795-8c14-d1a146888391 |
action_result.parameter.ip_set_name | string | `awswaf ip set name` | test_ip_set test_ip_set_6 |
action_result.data.\*.Id | string | `awswaf ip set id` | b53eef26-f2be-44ef-9bcf-c16c3d07d791 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 54 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/x-amz-json-1.1 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Thu, 04 Apr 2019 09:02:54 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | 6e762be6-56b8-11e9-ab52-739c81485c05 |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 200 |
action_result.data.\*.ResponseMetadata.RequestId | string | | 6e762be6-56b8-11e9-ab52-739c81485c05 |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | 0 |
action_result.summary.ip_status | string | | IP(s) added successfully |
action_result.message | string | | Ip status: IP(s) added successfully |
action_result.data.\*.NextLockToken | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': '\*REDACTED\*', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': '\*REDACTED\*', 'SessionToken': '\*REDACTED\*'} |

## action: 'delete ip'

Remove IP(s) from an existing IP set

Type: **correct** <br>
Read only: **False**

The ip_set_id or ip_set_name must be given as input for deleting an IP from the IP set, ip_set_id will be considered if both ip_set_id and ip_set_name is provided in input.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_set_id** | optional | IP Set ID | string | `awswaf ip set id` |
**ip_set_name** | optional | IP Set Name | string | `awswaf ip set name` |
**ip_address** | required | IP Address (Allows comma-separated) | string | `awswaf ip mask` |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_address | string | `awswaf ip mask` | 126.0.0.0/24 |
action_result.parameter.ip_set_id | string | `awswaf ip set id` | 0778db34-cc96-4795-8c14-d1a146888391 |
action_result.parameter.ip_set_name | string | `awswaf ip set name` | test_ip test_ip_set_5 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 54 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/x-amz-json-1.1 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Thu, 04 Apr 2019 09:08:32 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | 389889ac-56b9-11e9-ab52-739c81485c05 |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 200 |
action_result.data.\*.ResponseMetadata.RequestId | string | | 389889ac-56b9-11e9-ab52-739c81485c05 |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | 0 |
action_result.summary.ip_status | string | | IP(s) deleted successfully |
action_result.message | string | | Ip status: IP(s) deleted successfully |
action_result.data.\*.NextLockToken | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': '\*REDACTED\*', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': '\*REDACTED\*', 'SessionToken': '\*REDACTED\*'} |

## action: 'delete ip set'

Remove the specified IP Set

Type: **correct** <br>
Read only: **False**

The ip_set_id or ip_set_name must be given as input for deleting an IP set, ip_set_id will be used if both ip_set_id and ip_set_name is provided in input.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_set_id** | optional | IP Set ID | string | `awswaf ip set id` |
**ip_set_name** | optional | IP Set Name | string | `awswaf ip set name` |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.ResponseMetadata.RequestId | string | | 0c28d801-b618-49b8-b904-2ff6698bb038 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Wed, 22 Sep 2021 20:04:47 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/x-amz-json-1.1 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 2 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | 0c28d801-b618-49b8-b904-2ff6698bb038 |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | 0 |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 200 |
action_result.status | string | | success |
action_result.message | string | | Delete status: IP Set deleted successfully |
action_result.summary.delete_status | string | | IP Set deleted successfully |
action_result.parameter.ip_set_id | string | `awswaf ip set id` | 25b7e872-0645-4229-91d5-28e2369262aa |
action_result.parameter.ip_set_name | string | `awswaf ip set name` | new_ip_set_1383662 |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': '\*REDACTED\*', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': '\*REDACTED\*', 'SessionToken': '\*REDACTED\*'} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list acls'

List all ACLs

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**limit** | optional | Maximum number of results (default: 100) | numeric | |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 50 |
action_result.data.\*.ARN | string | | |
action_result.data.\*.LockToken | string | | |
action_result.data.\*.Description | string | | |
action_result.data.\*.Name | string | | test_acl_2 |
action_result.data.\*.Id | string | | 1d5f92b0-c376-4095-a939-efd04f62fda1 |
action_result.summary.number_of_acls | numeric | | 4 |
action_result.message | string | | Number of acls: 4 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': '\*REDACTED\*', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': '\*REDACTED\*', 'SessionToken': '\*REDACTED\*'} |

## action: 'list ip sets'

List all IP sets

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**limit** | optional | Maximum number of results (default: 100) | numeric | |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 50 |
action_result.data.\*.Id | string | `awswaf ip set id` | 0778db34-cc96-4795-8c14-d1a146888391 |
action_result.data.\*.Name | string | `awswaf ip set name` | test_ip |
action_result.data.\*.ARN | string | | |
action_result.data.\*.LockToken | string | | |
action_result.data.\*.Description | string | | |
action_result.summary.number_of_ip_sets | numeric | | 56 |
action_result.message | string | | Number of ip sets: 56 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': '\*REDACTED\*', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': '\*REDACTED\*', 'SessionToken': '\*REDACTED\*'} |

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
