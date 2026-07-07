# Akamai WAF

Publisher: Robert Drouin <br>
Connector Version: 2.1.4 <br>
Product Vendor: Akamai <br>
Product Name: Network Lists <br>
Minimum Product Version: 6.3.0

The WAF API allows you to manage a common set of lists for use in various Akamai security products such as Kona Site Defender, Web App Protector, and Bot Manager

The Network Lists API allows you to manage a common set of lists for use in various Akamai security
products such as Kona Site Defender, Web App Protector, and Bot Manager. Network lists are shared
sets of IP addresses, CIDR blocks, or broad geographic areas. Along with managing your own lists,
you can also access read-only lists that Akamai dynamically updates for you.

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Akamai WAF server. Below are the
default ports used by Splunk SOAR.

|         Service Name | Transport Protocol | Port |
|----------------------|--------------------|------|
|         http | tcp | 80 |
|         https | tcp | 443 |

### Configuration variables

This table lists the configuration variables required to operate Akamai WAF. These variables are specified when configuring a Network Lists asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Base URL for the API. This URL is given to you when you setup the API Client in the Akamai Control Center. e.g. https://akaa-WWWWWWWWWWWW.luna.akamaiapis.net |
**access_token** | required | password | Access Token for the API |
**client_token** | required | password | Client Token for the API |
**client_secret** | required | password | Client Secret for the API |
**akamai_verify_ssl** | optional | boolean | Verify SSL certificates |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using the supplied configuration <br>
[list networks](#action-list-networks) - Get a network list <br>
[get network](#action-get-network) - Gets a network list's most recent syncPoint version <br>
[create network](#action-create-network) - Create a new network list <br>
[delete network](#action-delete-network) - Removes a network list <br>
[update network](#action-update-network) - Update the network list items and properties <br>
[add element](#action-add-element) - Adds the specified element(s) to a list <br>
[remove element](#action-remove-element) - Remove the specified element(s) from the list <br>
[activate network](#action-activate-network) - Activate the most recent syncPoint version of a network list in either the STAGING or PRODUCTION environment <br>
[activation status](#action-activation-status) - Shows a network list activation status on either the STAGING or PRODUCTION environment <br>
[activation snapshot](#action-activation-snapshot) - Gets a version of a network list <br>
[activation details](#action-activation-details) - Provides detailed status for a given activation <br>
[list siteshields](#action-list-siteshields) - Get akamai site shields ip ranges

## action: 'test connectivity'

Validate the asset configuration for connectivity using the supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list networks'

Get a network list

Type: **investigate** <br>
Read only: **True**

List all network lists available for an authenticated user who belongs to a group, optionally filtered by listType or based on a search string. For <strong>extended</strong> parameter, when enabled, provides additional response data identifying who and when the lists were created and updated, and the network list's deployment status in both STAGING and PRODUCTION environments. For <strong>includeelements</strong> parameter, if enabled, the response list includes all items. For large network lists, this may slow responses and yield large response objects. Results appear within the networkLists array, which might be empty if no network lists are available to the client.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**search** | optional | Only list items that match the specified substring in any network list's name or list of items | string | |
**extended** | optional | When enabled, provides additional response data (Default: false) | boolean | |
**includeelements** | optional | If enabled, the response list includes all items (Default: false) | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.search | string | | |
action_result.parameter.extended | boolean | | True False |
action_result.parameter.includeelements | boolean | | True False |
action_result.data.\*.networkLists.\*.name | string | | |
action_result.data.\*.networkLists.\*.networkListType | string | | |
action_result.data.\*.networkLists.\*.elementCount | numeric | | |
action_result.data.\*.networkLists.\*.list | string | `ip` | |
action_result.data.\*.networkLists.\*.uniqueId | string | `akamai networklist id` | |
action_result.data.\*.networkLists.\*.type | string | | |
action_result.data.\*.networkLists.\*.description | string | | |
action_result.data.\*.networkLists.\*.createDate | string | | |
action_result.data.\*.networkLists.\*.createdBy | string | | |
action_result.data.\*.networkLists.\*.updateDate | string | | |
action_result.data.\*.networkLists.\*.updateBy | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get network'

Gets a network list's most recent syncPoint version

Type: **investigate** <br>
Read only: **True**

For <strong>extended</strong> parameter, when enabled, provides additional response data identifying who and when the lists were created and updated, and the network list's deployment status in both STAGING and PRODUCTION environments. For <strong>includeelements</strong> parameter, if enabled, the response list includes all items. For large network lists, this may slow responses and yield large response objects.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**networklistid** | required | Unique identifier for each network list. Comma-separated list is allowed | string | `akamai networklist id` |
**extended** | optional | When enabled, provides additional response data (Default: false) | boolean | |
**includeelements** | optional | If enabled, the response list includes all items (Default: false) | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.networklistid | string | `akamai networklist id` | |
action_result.parameter.extended | boolean | | True False |
action_result.parameter.includeelements | boolean | | True False |
action_result.data.\*.name | string | | |
action_result.data.\*.networkListType | string | | |
action_result.data.\*.elementCount | numeric | | |
action_result.data.\*.list | string | `ip` | |
action_result.data.\*.uniqueId | string | `akamai networklist id` | |
action_result.data.\*.type | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.createDate | string | | |
action_result.data.\*.createdBy | string | | |
action_result.data.\*.updateDate | string | | |
action_result.data.\*.updatedBy | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create network'

Create a new network list

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Name for the new network list | string | |
**type** | required | Type of the new network list | string | |
**description** | required | Description of the new network list | string | |
**list** | required | IP(s) for the new network list. Comma-separated list is allowed | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.name | string | | |
action_result.parameter.type | string | | |
action_result.parameter.description | string | | |
action_result.parameter.list | string | `ip` | |
action_result.data.\*.name | string | | |
action_result.data.\*.networkListType | string | | |
action_result.data.\*.elementCount | numeric | | |
action_result.data.\*.list | string | `ip` | |
action_result.data.\*.uniqueId | string | `akamai networklist id` | |
action_result.data.\*.type | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete network'

Removes a network list

Type: **generic** <br>
Read only: **False**

You can only remove network lists that never activated. To deactivate a list, you can empty its list of elements.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**networklistid** | required | Unique identifier for the network list | string | `akamai networklist id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.networklistid | string | `akamai networklist id` | |
action_result.data.\*.status | string | | |
action_result.data.\*.uniqueId | string | `akamai networklist id` | |
action_result.data.\*.syncPoint | numeric | `akamai networklist syncpoint` | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update network'

Update the network list items and properties

Type: **generic** <br>
Read only: **False**

Allows you to set the name, description, and set of network list items to the resource. The current state of the list will be replaced with the properties and items you provide. The type cannot be changed.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**networklistid** | required | Unique identifier for each network list | string | `akamai networklist id` |
**name** | required | Update or change the name of the network list | string | |
**description** | required | Update or change the description of the network list | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.networklistid | string | `akamai networklist id` | |
action_result.parameter.name | string | | |
action_result.parameter.description | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.networkListType | string | | |
action_result.data.\*.elementCount | numeric | | |
action_result.data.\*.list | string | `ip` | |
action_result.data.\*.uniqueId | string | `akamai networklist id` | |
action_result.data.\*.type | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add element'

Adds the specified element(s) to a list

Type: **generic** <br>
Read only: **False**

If the network list's type is IP, the value needs to be a URL-encoded IP address or CIDR block.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**networklistid** | required | Unique identifier for the network list | string | `akamai networklist id` |
**elements** | required | Element(s) to add to the network list. Comma-separated list is allowed | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.networklistid | string | `akamai networklist id` | |
action_result.parameter.elements | string | `ip` | |
action_result.data.\*.name | string | | |
action_result.data.\*.networkListType | string | | |
action_result.data.\*.elementCount | numeric | | |
action_result.data.\*.list | string | `ip` | |
action_result.data.\*.uniqueId | string | `akamai networklist id` | |
action_result.data.\*.type | string | | |
action_result.data.\*.description | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remove element'

Remove the specified element(s) from the list

Type: **generic** <br>
Read only: **False**

If the network list's type is IP, the value needs to be a URL-encoded IP address or CIDR block.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**networklistid** | required | Unique identifier for the network list | string | `akamai networklist id` |
**elements** | required | Element(s) to be removed from the network list. Comma-separated list is allowed | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.networklistid | string | `akamai networklist id` | |
action_result.parameter.elements | string | `ip` | |
action_result.data.\*.name | string | | |
action_result.data.\*.networkListType | string | | |
action_result.data.\*.elementCount | numeric | | |
action_result.data.\*.list | string | `ip` | |
action_result.data.\*.uniqueId | string | `akamai networklist id` | |
action_result.data.\*.type | string | | |
action_result.data.\*.description | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'activate network'

Activate the most recent syncPoint version of a network list in either the STAGING or PRODUCTION environment

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**networklistid** | required | Unique identifier for the network list | string | `akamai networklist id` |
**environment** | required | Environment to activate the network (Default: STAGING) | string | |
**comments** | optional | Comments to add to the network | string | |
**notification** | optional | Notification Recipients for the network list. Comma-separated list is allowed | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.networklistid | string | `akamai networklist id` | |
action_result.parameter.environment | string | | |
action_result.parameter.comments | string | | |
action_result.parameter.notification | string | | |
action_result.data.\*.activationId | numeric | `akamai networklist activationid` | |
action_result.data.\*.activationComments | string | | |
action_result.data.\*.activationStatus | string | | |
action_result.data.\*.syncPoint | numeric | `akamai networklist syncpoint` | |
action_result.data.\*.uniqueId | string | `akamai networklist id` | |
action_result.data.\*.fast | boolean | | True False |
action_result.data.\*.dispatchCount | numeric | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'activation status'

Shows a network list activation status on either the STAGING or PRODUCTION environment

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**networklistid** | required | Unique identifier for the network list | string | `akamai networklist id` |
**environment** | required | The environment in which the list activation occurs (Default: STAGING) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.networklistid | string | `akamai networklist id` | |
action_result.parameter.environment | string | | |
action_result.data.\*.activationId | numeric | `akamai networklist activationid` | |
action_result.data.\*.activationComments | string | | |
action_result.data.\*.activationStatus | string | | |
action_result.data.\*.syncPoint | numeric | `akamai networklist syncpoint` | |
action_result.data.\*.uniqueId | string | `akamai networklist id` | |
action_result.data.\*.fast | boolean | | True False |
action_result.data.\*.dispatchCount | numeric | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'activation snapshot'

Gets a version of a network list

Type: **investigate** <br>
Read only: **True**

Gets a version of a network list in its state when activated, with each version identified by its syncPoint value. You can only get syncPoint versions that have been activated. For <strong>extended</strong> parameter, when enabled, provides additional response data identifying who and when the lists were created and updated, and the network list's deployment status in both STAGING and PRODUCTION environments.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**networklistid** | required | Unique identifier for the network list | string | `akamai networklist id` |
**syncpoint** | required | The network list version for which to retrieve the snapshot | numeric | `akamai networklist syncpoint` |
**extended** | optional | When enabled, provides additional response data (Default: false) | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.networklistid | string | `akamai networklist id` | |
action_result.parameter.syncpoint | numeric | `akamai networklist syncpoint` | |
action_result.parameter.extended | boolean | | True False |
action_result.data.\*.name | string | | |
action_result.data.\*.networkListType | string | | |
action_result.data.\*.elementCount | numeric | | |
action_result.data.\*.list | string | `ip` | |
action_result.data.\*.uniqueId | string | `akamai networklist id` | |
action_result.data.\*.type | string | | |
action_result.data.\*.syncPoint | numeric | `akamai networklist syncpoint` | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'activation details'

Provides detailed status for a given activation

Type: **investigate** <br>
Read only: **True**

Provides detailed status for a given activation, including progress on fast activation and other audit information, in addition to information ordinarily available from the "activation status" action.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**activationid** | required | Unique identifier for the network list | numeric | `akamai networklist activationid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.activationid | numeric | `akamai networklist activationid` | |
action_result.data.\*.activationId | numeric | `akamai networklist activationid` | |
action_result.data.\*.createDate | string | | |
action_result.data.\*.createdBy | string | | |
action_result.data.\*.environment | string | | |
action_result.data.\*.fast | boolean | | True False |
action_result.data.\*.networkList.activationComments | string | | |
action_result.data.\*.networkList.activationStatus | string | | |
action_result.data.\*.syncPoint | numeric | `akamai networklist syncpoint` | |
action_result.data.\*.uniqueId | string | `akamai networklist id` | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list siteshields'

Get akamai site shields ip ranges

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.cidr | string | | 202.31.0.0/16 |
action_result.message | string | | |
action_result.summary.num_data | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

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
