# Secure Application

Publisher: Splunk <br>
Connector Version: 1.0.2 <br>
Product Vendor: Splunk <br>
Product Name: Secure Application <br>
Minimum Product Version: 6.4.0.85

This app provides policy management capabilities for proactive runtime app security

The Secure Application connector supports only the cloud-based version of Secure Application. On-prem deployments are not supported.

Introduction

The Secure Application connector is designed to support the saas-based version of Secure Application, a component of AppDynamics SaaS. Please note that on-premises deployments are not supported.

Prerequisites

Before setting up the Secure Application connector, ensure you meet the following prerequisites:
• API Client Registration: Register an API client in your AppDynamics Controller tenant with the necessary permissions to execute the public APIs for Secure Application triggered from the SOAR platform.
• Credentials: Gather the required credentials from your Secure Application console:
• Client Name: A unique identifier for the API client.
• Client Secret: A secret string used for authentication.

Procedure
Asset Configuration

To configure the asset, provide the following information:
1\. API Key: Enter the client ID of your AppDynamics API client.
Example: soar_app_test
2\. API Key Secret: Input the secret associated with the API client.
Example: 89hsooo768890!
3\. Base URL: Specify the full URL of your AppDynamics Controller instance.
Example: https://secureapp-master.cisco.com/
4\. Account ID: State the account name, which is the first part of the Base URL hostname.
Example: secureapp-master

OAuth 2.0 Access Token

The SOAR connector for Secure Application uses the provided API key and secret to obtain an OAuth 2.0 access token from the AppDynamics Controller. This token is used for all authenticated API requests and is automatically refreshed upon expiration.

Testing and Saving Configuration
1\. Test Connectivity: Click "Test Connectivity" to authenticate with the controller and confirm access to Secure Application.
2\. Save Configuration: Click "Save" to store the configuration.

Reference

Secure Application API Docs for Reference:
https://help.splunk.com/en/appdynamics-saas/extend-splunk-appdynamics/25.7.0/extend-splunk-appdynamics/splunk-appdynamics-apis/cisco-secure-application-apis

Version: 25.7.0

### Configuration variables

This table lists the configuration variables required to operate Secure Application. These variables are specified when configuring a Secure Application asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Base URL for accessing Secure Application APIs |
**account_id** | required | string | Account Name, first part of SAAS URL Host Name |
**api_key** | required | string | API Key Name |
**api_key_secret** | required | password | API Key Secret |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[create new policy](#action-create-new-policy) - Create a policy for an attack or vulnerability at runtime <br>
[create new policy for http transaction header](#action-create-new-policy-for-http-transaction-header) - Create a policy for headers in HTTP transactions <br>
[delete policy](#action-delete-policy) - Delete a runtime policy given its ID <br>
[get policy by id](#action-get-policy-by-id) - Retrieve details of a specific policy using its ID <br>
[list all policies](#action-list-all-policies) - Fetch and display all existing policies <br>
[update policy](#action-update-policy) - Update an existing policy given its ID <br>
[add a rule to command execution policy](#action-add-a-rule-to-command-execution-policy) - Add a rule to the command execution policy to detect, ignore or block the runtime activity <br>
[add a rule to filesystem access policy](#action-add-a-rule-to-filesystem-access-policy) - Add a rule to the filesystem access policy to detect, ignore or block the runtime activity <br>
[add a rule to network or socket access policy](#action-add-a-rule-to-network-or-socket-access-policy) - Add a rule to the network or socket access policy to detect, ignore or block the runtime activity <br>
[delete a rule from command execution policy](#action-delete-a-rule-from-command-execution-policy) - Delete a rule from the command execution policy <br>
[delete a rule from filesystem access policy](#action-delete-a-rule-from-filesystem-access-policy) - Delete a rule from the filesystem access policy <br>
[delete a rule from network or socket access policy](#action-delete-a-rule-from-network-or-socket-access-policy) - Delete a rule from the network or socket access policy <br>
[list all rules](#action-list-all-rules) - List all rules in a policy given its policy id

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'create new policy'

Create a policy for an attack or vulnerability at runtime

Type: **generic** <br>
Read only: **False**

Create and configure runtime policy to specify an action to mitigate the attacks and vulnerabilities. To create policies, you require the Configure permission for Secure Application. By default, Secure Application includes a runtime policy that provides the best detection of all the attacks and vulnerabilities, reducing the false positives. There can be only one policy of each type for a given combination of application, tier, and tenant.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**type** | required | Type of Runtime Policy | string | |
**application_id** | required | Application that includes the tiers or services on which you require to apply the policy. Default value is "all" | string | |
**tier_id** | required | Application-specific tier to apply the policy. Default value is "all" | string | |
**default_action** | required | Default action for this policy. You can select IGNORE for no notifications for the runtime activity; select DETECT to detect the runtime activity; select BLOCK to block a specific runtime activity. Default value is "DETECT" | string | |
**enable_policy** | required | Select Yes/No to enable/disable the policy | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.type | string | | |
action_result.parameter.application_id | string | | |
action_result.parameter.tier_id | string | | |
action_result.parameter.default_action | string | | |
action_result.parameter.enable_policy | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.status | string | | |
action_result.data.\*.action | string | | |
action_result.data.\*.operative_policy_type_id | string | | |
action_result.data.\*.version | string | | |
action_result.data.\*.created_at | string | | |
action_result.data.\*.updated_at | string | | |
action_result.status | string | | |
action_result.message | string | | |
action_result.summary.total_objects | numeric | | |
action_result.summary.total_objects_successful | numeric | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'create new policy for http transaction header'

Create a policy for headers in HTTP transactions

Type: **generic** <br>
Read only: **False**

Create and configure runtime policy to detect or add a specific HTTP header to each HTTP response. The default action is detect. Specify which headers to add with the patch option. To create policies, you require the Configure permission for Secure Application. By default, Secure Application includes a runtime policy that provides the best detection of all the attacks and vulnerabilities, reducing the false positives. There can be only one policy of each type for a given combination of application, tier, and tenant.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**application_id** | required | Application that includes the tiers or services on which you require to apply the policy. Default value is "all" | string | |
**tier_id** | required | Application-specific tier to apply the policy. Default value is "all" | string | |
**default_action** | required | Default action for this policy. You can select IGNORE for no notifications for the runtime activity; select DETECT to detect the runtime activity; select BLOCK to block a specific runtime activity. Default value is "DETECT" | string | |
**enable_policy** | required | Select Yes/No to enable/disable the policy | string | |
**action for Strict-Transport-Security** | required | Action for Strict-Transport-Security header. Default value is "DETECT" | string | |
**patch value for Strict-Transport-Security** | optional | Value to patch for Strict-Transport-Security header. This value is applicable only if the action chosen is "PATCH" | string | |
**action for X-Frame-Options** | required | Action for X-Frame-Options header. Default value is "DETECT" | string | |
**patch value for X-Frame-Options** | optional | Value to patch for X-Frame-Options header. This value is applicable only if the action chosen is "PATCH" | string | |
**action for X-XSS-Protection** | required | Action for X-XSS-Protection header. Default value is "DETECT" | string | |
**patch value for X-XSS-Protection** | optional | Value to patch for X-XSS-Protection header. This value is applicable only if the action chosen is "PATCH" | string | |
**action for X-Content-Type-Options** | required | Action for X-Content-Type-Options header. Default value is "DETECT" | string | |
**patch value for X-Content-Type-Options** | optional | Value to patch for X-Content-Type-Options header. This value is applicable only if the action chosen is "PATCH" | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.application_id | string | | |
action_result.parameter.tier_id | string | | |
action_result.parameter.default_action | string | | |
action_result.parameter.enable_policy | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.status | string | | |
action_result.data.\*.action | string | | |
action_result.data.\*.operative_policy_type_id | string | | |
action_result.data.\*.version | string | | |
action_result.data.\*.created_at | string | | |
action_result.data.\*.updated_at | string | | |
action_result.status | string | | |
action_result.message | string | | |
action_result.summary.total_objects | numeric | | |
action_result.summary.total_objects_successful | numeric | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.action for Strict-Transport-Security | string | | |
action_result.parameter.patch value for Strict-Transport-Security | string | | |
action_result.parameter.action for X-Frame-Options | string | | |
action_result.parameter.patch value for X-Frame-Options | string | | |
action_result.parameter.action for X-XSS-Protection | string | | |
action_result.parameter.patch value for X-XSS-Protection | string | | |
action_result.parameter.action for X-Content-Type-Options | string | | |
action_result.parameter.patch value for X-Content-Type-Options | string | | |

## action: 'delete policy'

Delete a runtime policy given its ID

Type: **generic** <br>
Read only: **False**

Delete a runtime policy given its ID.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_id** | required | Unique Identifier for the policy. The policy id is received in the response after the policy is created or listed. | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.policy_id | string | | |
action_result.status | string | | |
action_result.message | string | | |
action_result.summary.total_objects | numeric | | |
action_result.summary.total_objects_successful | numeric | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get policy by id'

Retrieve details of a specific policy using its ID

Type: **generic** <br>
Read only: **True**

Retrieve details of a specific policy using its ID

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_id** | required | Unique Identifier for the policy. The policy id is received in the response after the policy is created or listed. | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.policy_id | string | | |
action_result.data.\*.status | string | | |
action_result.data.\*.action | string | | |
action_result.data.\*.configTypeId | string | | |
action_result.data.\*.configTypeName | string | | |
action_result.data.\*.applicationId | string | | |
action_result.data.\*.applicationName | string | | |
action_result.data.\*.tierId | string | | |
action_result.data.\*.tierName | string | | |
action_result.data.\*.version | string | | |
action_result.data.\*.policyTypeId | string | | |
action_result.data.\*.policyTypeName | string | | |
action_result.data.\*.policyTypeDescription | string | | |
action_result.message | string | | |
action_result.summary.total_objects | numeric | | |
action_result.summary.total_objects_successful | numeric | | |
action_result.status | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list all policies'

Fetch and display all existing policies

Type: **generic** <br>
Read only: **True**

Fetch and display all existing policies.

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.id | string | | |
action_result.data.\*.status | string | | |
action_result.data.\*.action | string | | |
action_result.data.\*.applicationName | string | | |
action_result.data.\*.applicationId | string | | |
action_result.data.\*.tierName | string | | |
action_result.data.\*.tierId | string | | |
action_result.data.\*.policyTypeName | string | | |
action_result.data.\*.policyTypeDescription | string | | |
action_result.summary.total_policies | numeric | | |
action_result.status | string | | |
action_result.message | string | | |
action_result.summary.total_objects | numeric | | |
action_result.summary.total_objects_successful | numeric | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'update policy'

Update an existing policy given its ID

Type: **generic** <br>
Read only: **False**

Update status, action, tier, or application ID of an existing policy. Policy type cannot be changed

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_id** | required | Unique Identifier for the policy. The policy id is received in the response after the policy is created or listed. | string | |
**application_id** | required | Application that includes the tiers or services on which you require to apply the policy. Default value is "all" | string | |
**tier_id** | required | Application-specific tier to apply the policy. Default value is "all" | string | |
**default_action** | required | Default action for this policy. You can select IGNORE for no notifications for the runtime activity; select DETECT to detect the runtime activity; select BLOCK to block a specific runtime activity. Default value is "DETECT" | string | |
**enable_policy** | required | Select Yes/No to enable/disable the policy | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.policy_id | string | | |
action_result.parameter.application_id | string | | |
action_result.parameter.tier_id | string | | |
action_result.parameter.default_action | string | | |
action_result.parameter.enable_policy | string | | |
action_result.data.\*.status | string | | |
action_result.status | string | | |
action_result.data.\*.action | string | | |
action_result.data.\*.operative_policy_type_id | string | | |
action_result.data.\*.version | string | | |
action_result.data.\*.created_at | string | | |
action_result.data.\*.updated_at | string | | |
action_result.message | string | | |
action_result.summary.total_objects | numeric | | |
action_result.summary.total_objects_successful | numeric | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'add a rule to command execution policy'

Add a rule to the command execution policy to detect, ignore or block the runtime activity

Type: **generic** <br>
Read only: **False**

Add the rules based on your requirement. The action that you specify within the rule supersedes the default action specified in Default Action.
You can select Ignore for no notifications for the runtime activity; select Detect to detect the runtime activity; or select Block to block the runtime activity.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_id** | required | Unique Identifier for the policy. The policy id is received in the response after the policy is created or listed. | string | |
**type** | required | Type of match filter | string | |
**operation** | optional | Operation for the match filter | string | |
**value** | optional | Value for the match filter | string | |
**action** | optional | Action to be taken if the filter matches | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | |
action_result.message | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.type | string | | |
action_result.data.\*.operation | string | | |
action_result.data.\*.value | string | | |
action_result.data.\*.action | string | | |
action_result.summary.total_rules | numeric | | |
action_result.summary.total_objects | numeric | | |
action_result.summary.total_objects_successful | numeric | | |
action_result.parameter.policy_id | string | | |
action_result.parameter.type | string | | |
action_result.parameter.operation | string | | |
action_result.parameter.value | string | | |
action_result.parameter.action | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'add a rule to filesystem access policy'

Add a rule to the filesystem access policy to detect, ignore or block the runtime activity

Type: **generic** <br>
Read only: **False**

Add the rules based on your requirement. The action that you specify within the rule supersedes the default action specified in Default Action.
You can select Ignore for no notifications for the runtime activity; select Detect to detect the runtime activity; or select Block to block the runtime activity.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_id** | required | Unique Identifier for the policy. The policy id is received in the response after the policy is created or listed. | string | |
**type** | required | Type of match filter | string | |
**operation** | optional | Operation for the match filter | string | |
**value** | optional | Value for the match filter | string | |
**action** | optional | Action to be taken if the filter matches | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | |
action_result.message | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.type | string | | |
action_result.data.\*.operation | string | | |
action_result.data.\*.value | string | | |
action_result.data.\*.action | string | | |
action_result.summary.total_rules | numeric | | |
action_result.summary.total_objects | numeric | | |
action_result.summary.total_objects_successful | numeric | | |
action_result.parameter.policy_id | string | | |
action_result.parameter.type | string | | |
action_result.parameter.operation | string | | |
action_result.parameter.value | string | | |
action_result.parameter.action | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'add a rule to network or socket access policy'

Add a rule to the network or socket access policy to detect, ignore or block the runtime activity

Type: **generic** <br>
Read only: **False**

Add the rules based on your requirement. The action that you specify within the rule supersedes the default action specified in Default Action.
You can select Ignore for no notifications for the runtime activity; select Detect to detect the runtime activity; or select Block to block the runtime activity.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_id** | required | Unique Identifier for the policy. The policy id is received in the response after the policy is created or listed. | string | |
**type** | required | Type of match filter | string | |
**operation** | optional | Operation for the match filter | string | |
**value** | optional | Value for the match filter | string | |
**action** | optional | Action to be taken if the filter matches | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | |
action_result.message | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.type | string | | |
action_result.data.\*.operation | string | | |
action_result.data.\*.value | string | | |
action_result.data.\*.action | string | | |
action_result.summary.total_rules | numeric | | |
action_result.summary.total_objects | numeric | | |
action_result.summary.total_objects_successful | numeric | | |
action_result.parameter.policy_id | string | | |
action_result.parameter.type | string | | |
action_result.parameter.operation | string | | |
action_result.parameter.value | string | | |
action_result.parameter.action | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'delete a rule from command execution policy'

Delete a rule from the command execution policy

Type: **generic** <br>
Read only: **False**

Delete a rule from the command execution policy.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_id** | required | Unique Identifier for the policy. The policy id is received in the response after the policy is created or listed. | string | |
**type** | required | Type of match filter | string | |
**operation** | optional | Operation for the match filter | string | |
**value** | optional | Value for the match filter | string | |
**action** | optional | Action to be taken if the filter matches | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | |
action_result.message | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.type | string | | |
action_result.data.\*.operation | string | | |
action_result.data.\*.value | string | | |
action_result.data.\*.action | string | | |
action_result.summary.total_rules | numeric | | |
action_result.summary.total_objects | numeric | | |
action_result.summary.total_objects_successful | numeric | | |
action_result.parameter.policy_id | string | | |
action_result.parameter.type | string | | |
action_result.parameter.operation | string | | |
action_result.parameter.value | string | | |
action_result.parameter.action | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'delete a rule from filesystem access policy'

Delete a rule from the filesystem access policy

Type: **generic** <br>
Read only: **False**

Delete a rule from the filesystem access policy.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_id** | required | Unique Identifier for the policy. The policy id is received in the response after the policy is created or listed. | string | |
**type** | required | Type of match filter | string | |
**operation** | optional | Operation for the match filter | string | |
**value** | optional | Value for the match filter | string | |
**action** | optional | Action to be taken if the filter matches | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | |
action_result.message | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.type | string | | |
action_result.data.\*.operation | string | | |
action_result.data.\*.value | string | | |
action_result.data.\*.action | string | | |
action_result.summary.total_rules | numeric | | |
action_result.summary.total_objects | numeric | | |
action_result.summary.total_objects_successful | numeric | | |
action_result.parameter.policy_id | string | | |
action_result.parameter.type | string | | |
action_result.parameter.operation | string | | |
action_result.parameter.value | string | | |
action_result.parameter.action | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'delete a rule from network or socket access policy'

Delete a rule from the network or socket access policy

Type: **generic** <br>
Read only: **False**

Delete a rule from the network or socket access policy.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_id** | required | Unique Identifier for the policy. The policy id is received in the response after the policy is created or listed. | string | |
**type** | required | Type of match filter | string | |
**operation** | optional | Operation for the match filter | string | |
**value** | optional | Value for the match filter | string | |
**action** | optional | Action to be taken if the filter matches | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | |
action_result.message | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.type | string | | |
action_result.data.\*.operation | string | | |
action_result.data.\*.value | string | | |
action_result.data.\*.action | string | | |
action_result.summary.total_rules | numeric | | |
action_result.summary.total_objects | numeric | | |
action_result.summary.total_objects_successful | numeric | | |
action_result.parameter.policy_id | string | | |
action_result.parameter.type | string | | |
action_result.parameter.operation | string | | |
action_result.parameter.value | string | | |
action_result.parameter.action | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list all rules'

List all rules in a policy given its policy id

Type: **generic** <br>
Read only: **False**

List all rules in a policy given its policy id.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_id** | required | Unique Identifier for the policy. The policy id is received in the response after the policy is created or listed. | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.policy_id | string | | |
action_result.status | string | | |
action_result.data.\*.type | string | | |
action_result.data.\*.operation | string | | |
action_result.data.\*.value | string | | |
action_result.data.\*.action | string | | |
action_result.data.\*.name | string | | |
action_result.summary.total_rules | numeric | | |
action_result.message | string | | |
action_result.summary.total_objects | numeric | | |
action_result.summary.total_objects_successful | numeric | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2026 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
