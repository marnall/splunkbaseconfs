# AWS Athena

Publisher: Splunk <br>
Connector Version: 2.3.1 <br>
Product Vendor: AWS <br>
Product Name: Athena <br>
Minimum Product Version: 6.3.0

This app supports investigative actions on AWS Athena

## Asset Configuration

There are two ways to configure an AWS Athena asset. The first is to configure the **access_key** ,
**secret_key** and **region** variables. If it is preferred to use a role and Phantom is running as
an EC2 instance, the **use_role** checkbox can be checked instead. This will allow the role that is
attached to the instance to be used. Please see the [AWS EC2 and IAM
documentation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html)
for more information.

This app also requires some integration with AWS S3. Query results will be stored in a folder on S3
specified during a query action. These results can be encrypted using various encryption schemes,
some of which require a KMS key. This KMS key should be provided when configuring the asset and must
be applicable for the given region.

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

This table lists the configuration variables required to operate AWS Athena. These variables are specified when configuring a Athena asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**access_key** | optional | password | AWS Access Key |
**secret_key** | optional | password | AWS Secret Key |
**region** | required | string | Default Region |
**kms_key** | optional | password | KMS key |
**use_role** | optional | boolean | Use attached role when running Phantom in EC2 |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[list queries](#action-list-queries) - List named queries on Athena <br>
[run query](#action-run-query) - Run a named query on Athena

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list queries'

List named queries on Athena

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.NamedQuery.Database | string | | sampledb |
action_result.data.\*.NamedQuery.Description | string | | Sample query to get the top 10 airports with the most number of departures since 2000 |
action_result.data.\*.NamedQuery.Name | string | | Flights Select Query |
action_result.data.\*.NamedQuery.NamedQueryId | string | `athena named query` | 1234abcd-12ab-ab12-ab12-123456abcdef |
action_result.data.\*.NamedQuery.QueryString | string | `athena query` | SELECT origin, count(\*) AS total_departures FROM test_table WHERE year >= '2000' GROUP BY origin ORDER BY total_departures DESC LIMIT 10; |
action_result.data.\*.ResponseMetadata.HTTPHeaders.connection | string | | keep-alive |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 389 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/x-amz-json-1.1 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Tue, 03 Oct 2017 23:24:08 GMT Tue, 03 Oct 2017 23:29:58 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | 1234abcd-12ab-ab12-ab12-123456abcdef |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 200 |
action_result.data.\*.ResponseMetadata.RequestId | string | | 1234abcd-12ab-ab12-ab12-123456abcdef |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | 0 |
action_result.summary.num_queries | numeric | | 7 |
action_result.message | string | | Num queries: 7 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'TESTSJL6ZZZZZ3M7TEST', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |

## action: 'run query'

Run a named query on Athena

Type: **investigate** <br>
Read only: **True**

The <b>query</b> parameter can take either a named query ID, or a query string.<br><br>If the <b>database</b> parameter is not included, the query will run on the default database configured on Athena.<br><br>The AWS API requires Athena query results be stored in a location on S3. Use the <b>s3_location</b> parameter to specify this location.<br><br>To encypt the files containing the results, specify the desired encryption scheme with the <b>encryption</b> parameter. If the given encryption scheme requires a KMS key, the action will use the <b>kms_key</b> app configuration parameter.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query** | required | Query to run | string | `athena query` `athena named query` |
**database** | optional | Database to run query on | string | |
**s3_location** | required | S3 location to save results | string | |
**encryption** | optional | Encyption scheme of S3 location | string | |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.database | string | | sampledb |
action_result.parameter.encryption | string | | SSE_S3 |
action_result.parameter.query | string | `athena query` `athena named query` | 1234abcd-12ab-ab12-ab12-123456abcdef |
action_result.parameter.s3_location | string | | s3://test-bucket/test-queries s3://test-bucket/test-queries/kms_encrypt |
action_result.data.\*.\*.VarCharValue | string | | os |
action_result.summary.num_rows | numeric | | 0 |
action_result.message | string | | Num rows: 0 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'TESTSJL6ZZZZZ3M7TEST', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |

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
