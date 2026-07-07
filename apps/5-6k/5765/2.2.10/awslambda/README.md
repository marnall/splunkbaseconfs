# AWS Lambda

Publisher: Splunk <br>
Connector Version: 2.2.10 <br>
Product Vendor: AWS <br>
Product Name: Lambda <br>
Minimum Product Version: 6.3.0

This app integrates with AWS Lambda to perform lambda functions

### Configuration variables

This table lists the configuration variables required to operate AWS Lambda. These variables are specified when configuring a Lambda asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**access_key** | optional | password | Access Key |
**secret_key** | optional | password | Secret Key |
**region** | required | string | Default Region |
**use_role** | optional | boolean | Use attached role when running Phantom in EC2 |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[remove permission](#action-remove-permission) - Revokes function-use permission from an AWS service or another account <br>
[invoke lambda](#action-invoke-lambda) - Invoke an AWS Lambda function <br>
[list functions](#action-list-functions) - List available AWS Lambda functions, with the version-specific configuration for each <br>
[add permission](#action-add-permission) - Grants an AWS service or another account permission to use a function

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'remove permission'

Revokes function-use permission from an AWS service or another account

Type: **correct** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**function_name** | required | The name of the Lambda function, version, or alias. The following name formats are accepted: function name, function ARN, and partial ARN | string | `lambda function name` `lambda function arn` |
**statement_id** | required | Statement identifier of the permission to remove | string | |
**qualifier** | optional | Specify a version or alias to remove permissions to a published version of the function | string | |
**revision_id** | optional | Only update the policy if the revision ID matches the ID that's specified. Use this option to avoid modifying a function policy that has changed since you last read it | string | |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.ResponseMetadata.RequestId | string | | 50c47f67-ae1a-4c2a-9651-77f1ba1f3d37 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Fri, 26 Feb 2021 19:07:37 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.connection | string | | keep-alive |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/json |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | 50c47f67-ae1a-4c2a-9651-77f1ba1f3d37 |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | 0 |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 204 |
action_result.status | string | | success |
action_result.message | string | | Status: Successfully removed permission |
action_result.summary.status | string | | Successfully removed permission |
action_result.parameter.function_name | string | `lambda function name` `lambda function arn` | myTestFunction1 |
action_result.parameter.statement_id | string | | statement1 |
action_result.parameter.qualifier | string | | |
action_result.parameter.revision_id | string | | |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'ASIASJL6ZZZZZ3M7QC2J', 'Expiration': '2020-12-09 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'invoke lambda'

Invoke an AWS Lambda function

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**function_name** | required | The name of the AWS Lambda function, version, or alias. The following name formats are accepted: function name, function ARN, and partial ARN | string | `lambda function name` `lambda function arn` |
**invocation_type** | optional | Invocation type | string | |
**log_type** | optional | Set to 'Tail' to include the execution log in the response | string | |
**client_context** | optional | The JSON that you want to provide to your Lambda function in the context object | string | |
**payload** | optional | The JSON that you want to provide to your Lambda function as input | string | |
**qualifier** | optional | Specify a version or alias to invoke a published version of the function | string | |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.client_context | string | | |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'ASIASJL6ZZZZZ3M7QC2J', 'Expiration': '2020-12-09 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |
action_result.parameter.function_name | string | `lambda function name` `lambda function arn` | parsePhantomRegistrationEmail arn:aws:lambda:us-east-1:123456789012:function:example_helloworld |
action_result.parameter.invocation_type | string | | RequestResponse |
action_result.parameter.log_type | string | | None |
action_result.parameter.payload | string | | |
action_result.parameter.qualifier | string | | |
action_result.data.\*.ExecutedVersion | string | | $LATEST |
action_result.data.\*.FunctionError | string | | Unhandled |
action_result.data.\*.Payload | string | | Success |
action_result.data.\*.Payload.errorMessage | string | | 'input_text' |
action_result.data.\*.Payload.errorType | string | | KeyError |
action_result.data.\*.Payload.stackTrace.\* | string | | input_text = event["input_text"] |
action_result.data.\*.Payload.statusCode | numeric | | 200 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.connection | string | | keep-alive |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 167 9 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/json |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Tue, 19 Feb 2019 21:17:06 GMT Tue, 19 Feb 2019 21:26:49 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amz-executed-version | string | | $LATEST |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amz-function-error | string | | Unhandled |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-remapped-content-length | string | | 0 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | 1234abcd-12ab-ab12-ab12-123456abcdef |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-trace-id | string | | root=1-abcd1234-abcdfghi123456789abcd;sampled=0 |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 200 |
action_result.data.\*.ResponseMetadata.RequestId | string | | 1234abcd-12ab-ab12-ab12-123456abcdef |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | 0 |
action_result.data.\*.StatusCode | numeric | | 200 |
action_result.summary.status | string | | Successfully invoked lambda |
action_result.message | string | | Status: Successfully invoked lambda |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list functions'

List available AWS Lambda functions, with the version-specific configuration for each

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**function_version** | optional | Set to 'ALL' to include entries for all published versions of each function | string | |
**next_token** | optional | Specify the pagination token returned by previous request to retrieve next page of results | string | `lambda next token` |
**max_items** | optional | A value between 1 and 50 to limit the number of functions to be returned | numeric | |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'ASIASJL6ZZZZZ3M7QC2J', 'Expiration': '2020-12-09 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |
action_result.parameter.function_version | string | | |
action_result.parameter.max_items | numeric | | 1 |
action_result.parameter.next_token | string | `lambda next token` | 1234abcd12abab12ab12123456abcdef/c3sgqk3eiDRMkct7D8EmptWfHSXssPdS7Bo66iQPTMpVOHZgANewpgGgFGGr4pVjd6VgLUO6qPe1234abcd12abab12ab12123456abcdef/m0k5qVzizwoxFwvyruMbuMx9kADFACSslcabxXl3/jDI4rfFnIsUVdzTLBgPF1hzwrE1f3lcdkBvUp+QgY+Pn3w5QuJmwsp/di8COzFemY89GgOHbLNqsrBsgR/ee2eXoJp0ZkKM4EcBK3HokqBzefLfgR02PnfNOdXwqTlhkSPW0TKiKGIYu3Bw7lSNrLd+q3+wBGNLTnq7RWa21Xjxe5me9SyEscOWAwjnLEf9QpeMhWc+Qq9u3+IYyk7smjCWpIY371RST1llX0KIVaZkBn+agQ6cVvSAmBrKVEdtAzHROaivow8IdH2YG8FxvGmI5HkwSTf60OBM3jFrxw7v5OjCoId/ao6LBGYkuSAPF6YvgvwBdpgZeRmXfx9Iop3eaCNyLeGtKzLqVSOUwazScYgfAk= |
action_result.data.\*.Functions.\*.CodeSha256 | string | | abcdEFG123456ABCDefghijk12345678abDE= |
action_result.data.\*.Functions.\*.CodeSize | numeric | | 279 |
action_result.data.\*.Functions.\*.Description | string | | |
action_result.data.\*.Functions.\*.FunctionArn | string | `lambda function arn` | arn:aws:lambda:us-east-1:123456789012:function:demo9 |
action_result.data.\*.Functions.\*.FunctionName | string | `lambda function name` | demo9 |
action_result.data.\*.Functions.\*.Handler | string | | lambda_function.lambda_handler |
action_result.data.\*.Functions.\*.LastModified | string | | 2019-03-05T09:59:00.351+0000 |
action_result.data.\*.Functions.\*.MemorySize | numeric | | 128 |
action_result.data.\*.Functions.\*.RevisionId | string | | 1234abcd-12ab-ab12-ab12-123456abcdef |
action_result.data.\*.Functions.\*.Role | string | | arn:aws:iam::123456789012:role/service-role/test-role |
action_result.data.\*.Functions.\*.Runtime | string | | ruby2.5 |
action_result.data.\*.Functions.\*.Timeout | numeric | | 3 |
action_result.data.\*.Functions.\*.TracingConfig.Mode | string | | PassThrough |
action_result.data.\*.Functions.\*.Version | string | | $LATEST |
action_result.data.\*.Functions.\*.VpcConfig.VpcId | string | | |
action_result.data.\*.NextMarker | string | `lambda next token` | abcdEFG123456ABCDefghijk12345678abDE/c3sgqk3eiDRMkct7D8EmptWfHSXssPdS7Bo66iQPTMpVOabcdEFG123456ABCDefghijk12345678abDELUO6qPe2EMAuNDBjUTxm8z6N28yhlUwEmKbrAV/abcdEFG123456ABCDefghijk12345678abDE/jDI4rfFnIsUVdzTLBgPF1hzwrE1f3lcdkBvUp+QgY+Pn3w5QuJmwsp/abcdEFG123456ABCDefghijk12345678abDE/ee2eXoJp0ZkKM4EcBK3HokqBzefLfgR02PnfNOdXwqTlhkSPW0TKiKGIYu3Bw7lSNrLd+q3+wBGNLTnq7RWa21Xjxe5me9SyEscOWAwjnLEf9QpeMhWc/irQe4ijLbCnEZbkbt3hmecsTkxYE/lu3VsPd27PAdH4m+u1lfY5PZHNIkqx2ocEw2Ya797ov+QmFZmKBzimXcyNnbWoE7Hp+nZOKcr2BiQK9SSuBCi2Y/wi1dQ0S5F0u/cv42hTH+ak59mYaNJQOl9NZ+wWD72kMC9GUEYigQs= |
action_result.data.\*.ResponseMetadata.HTTPHeaders.connection | string | | keep-alive |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 1925 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/json |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Fri, 08 Mar 2019 01:20:14 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | 1234abcd-12ab-ab12-ab12-123456abcdef |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 200 |
action_result.data.\*.ResponseMetadata.RequestId | string | | 1234abcd-12ab-ab12-ab12-123456abcdef |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | 0 |
action_result.summary.next_token | string | `lambda next token` | 1234abcd12abab12ab12123456abcdef/c3sgqk3eiDRMkct7D8EmptWfHSXssPdS7Bo66iQPTMpVOHZgANewpgGgFGGr4pVjd6Vg1234abcd12abab12ab12123456abcdef/m0k5qVzizwoxFwvyruMbuMx9kADFACSslcabxXl3/jDI4rfFnIsUVdzTLBgPF1hzwrE1f3lcdkBvUp+QgY+Pn3w5QuJmwsp/di8COzFemY89GgOHbLNqsrBsgR/ee2eXoJp0ZkKM4EcBK3HokqBzefLfgR02PnfNOdXwqTlhkSPW0TKiKGIYu3Bw7lSNrLd+q3+wBGNLTnq7RWa21Xjxe5me9SyEscOWAwjnLEf9QpeMhWc/irQe4ijLbCnEZbkbt3hmecsTkxYE/lu3VsPd27PAdH4m+u1lfY5PZHNIkqx2ocEw2Ya797ov+QmFZmKBzimXcyNnbWoE7Hp+nZOKcr2BiQK9SSuBCi2Y/wi1dQ0S5F0u/cv42hTH+ak59mYaNJQOl9NZ+wWD72kMC9GUEYigQs= |
action_result.summary.num_functions | numeric | | 1 |
action_result.message | string | | Next token: 1234abcd12abab12ab12123456abcdef/c3sgqk3eiDRMkct7D8EmptWfHSXssPdS7Bo1234abcd-12ab-ab12-ab12-123456abcdefuNDBjUTxm8z6N28yhlUwEmKbrAV/m0k5qVzizwoxFwvyruMbuMx9kADFACSslcabxXl3/jDI4rfFnIsUVdzTLBgPF1hzwrE1f3lcdkBvUp+QgY+Pn3w5QuJmwsp/di8COzFemY89GgOHbLNqsrBsgR/ee2eXoJp0ZkKM4EcBK3HokqBzefLfgR02PnfNOdXwqTlhkSPW0TKiKGIYu3Bw7lSNrLd+q3+wBGNLTnq7RWa21Xjxe5me9SyEscOWAwjnLEf9QpeMhWc/irQe4ijLbCnEZbkbt3hmecsTkxYE/lu3VsPd27PAdH4m+u1lfY5PZHNIkqx2ocEw2Ya797ov+QmFZmKBzimXcyNnbWoE7Hp+nZOKcr2BiQK9SSuBCi2Y/wi1dQ0S5F0u/cv42hTH+ak59mYaNJQOl9NZ+wWD72kMC9GUEYigQs=, Num functions: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add permission'

Grants an AWS service or another account permission to use a function

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**function_name** | required | The name of the Lambda function, version, or alias. The following name formats are accepted: function name, function ARN, and partial ARN | string | `lambda function name` `lambda function arn` |
**statement_id** | required | A statement identifier that differentiates the statement from others in the same policy | string | |
**action** | required | The action that the principal can use on the function. For example, lambda:InvokeFunction or lambda:GetFunction | string | |
**principal** | required | The AWS service or account that invokes the function. If you specify a service, use SourceArn or SourceAccount to limit who can invoke the function through that service | string | |
**source_arn** | optional | For AWS services, the ARN of the AWS resource that invokes the function. For example, an Amazon S3 bucket or Amazon SNS topic | string | |
**source_account** | optional | For AWS services, the ID of the account that owns the resource. Use this instead of SourceArn to grant permission to resources that are owned by another account (for example, all of an account's Amazon S3 buckets). Or use it together with SourceArn to ensure that the resource is owned by the specified account. For example, an Amazon S3 bucket could be deleted by its owner and recreated by another account | string | |
**event_source_token** | optional | For Alexa Smart Home functions, a token that must be supplied by the invoker | string | |
**qualifier** | optional | Specify a version or alias to add permissions to a published version of the function | string | |
**revision_id** | optional | Only accepts the function's $LATEST revision ID. Use this option to avoid modifying a function policy that has changed since you last read it | string | |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.action | string | | lambda:InvokeFunction |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'ASIASJL6ZZZZZ3M7QC2J', 'Expiration': '2020-12-09 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |
action_result.parameter.event_source_token | string | | |
action_result.parameter.function_name | string | `lambda function name` `lambda function arn` | example_helloworld |
action_result.parameter.principal | string | | s3.amazonaws.com |
action_result.parameter.qualifier | string | | |
action_result.parameter.revision_id | string | | |
action_result.parameter.source_account | string | | |
action_result.parameter.source_arn | string | | arn:aws:lambda:us-east-1:123456789012:function:parseRegistrationEmailBase64 |
action_result.parameter.statement_id | string | | ID-1 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.connection | string | | keep-alive |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 376 359 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/json |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Fri, 15 Feb 2019 20:15:51 GMT Tue, 19 Feb 2019 22:31:11 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | 1234abcd-12ab-ab12-ab12-123456abcdef |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 201 |
action_result.data.\*.ResponseMetadata.RequestId | string | | 1234abcd-12ab-ab12-ab12-123456abcdef |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | 0 |
action_result.data.\*.Statement | string | | {"Sid":"ID-1","Effect":"Allow","Principal":{"Service":"s3.amazonaws.com"},"Action":"lambda:InvokeFunction","Resource":"arn:aws:lambda:us-east-1:123456789012:function:parseRegistrationEmailBase64","Condition":{"ArnLike":{"AWS:SourceArn":"arn:aws:lambda:us-east-1:123456789012:function:parseRegistrationEmailBase64"}}} {"Sid":"ID-1","Effect":"Allow","Principal":{"Service":"s3.amazonaws.com"},"Action":"lambda:InvokeFunction","Resource":"arn:aws:lambda:us-east-1:123456789012:function:example_helloworld","Condition":{"ArnLike":{"AWS:SourceArn":"arn:aws:lambda:us-east-1:123456789012:function:parseRegistrationEmailBase64"}}} |
action_result.summary.status | string | | Successfully added permission |
action_result.message | string | | Status: Successfully added permission |
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
