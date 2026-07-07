# Sophos Endpoint Protection

Publisher: Splunk Community \
Connector Version: 1.2.1 \
Product Vendor: Sophos \
Product Name: Sophos Endpoint Protection \
Minimum Product Version: 5.5.0

This app supports various investigative and containment actions on Sophos Endpoint Protection

### Configuration variables

This table lists the configuration variables required to operate Sophos Endpoint Protection. These variables are specified when configuring a Sophos Endpoint Protection asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**client_id** | required | string | Enter the Client ID here |
**client_secret** | required | password | Enter the Client Secret here |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[list endpoints](#action-list-endpoints) - List all the endpoints/sensors configured on the device \
[check updates](#action-check-updates) - Send a request to the endpoint to check for Sophos management agent software updates \
[tamper protection switch](#action-tamper-protection-switch) - Turn Tamper Protection on or off on the endpoint \
[get tamperprotection settings](#action-get-tamperprotection-settings) - Get the Tamper Protection settings for the specified endpoint \
[perform scan](#action-perform-scan) - Send a request to the specified endpoint to perform or configure a scan \
[delete endpoint](#action-delete-endpoint) - Delete the specified endpoint \
[get individual endpoint](#action-get-individual-endpoint) - Get the endpoint based on ID \
[list items](#action-list-items) - Get all allowed or blocked items \
[delete item](#action-delete-item) - Delete the specified blocked or allowed item \
[block item](#action-block-item) - Add item to blocked list \
[allow item](#action-allow-item) - Add item to allowed list \
[list sites](#action-list-sites) - Get all local sites \
[delete site](#action-delete-site) - Delete the specified local site \
[add site](#action-add-site) - Add a new local site \
[get isolation settings](#action-get-isolation-settings) - Get isolation settings for an endpoint \
[isolation switch](#action-isolation-switch) - Turn on or off endpoint isolation for multiple endpoints

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list endpoints'

List all the endpoints/sensors configured on the device

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**page_from_key** | optional | The key of the item from where to fetch a page | string | |
**page_size** | optional | The size of the page requested | string | |
**sort** | optional | Define how to sort the data (comma separated) | string | |
**health_status** | optional | Get endpoints having any of the specified health status (comma separated) | string | |
**type** | optional | Get endpoints having any of the specified endpoint type (comma separated) | string | |
**tamper_protection_enabled** | optional | Tamper protection status | boolean | |
**lockdown_status** | optional | Get endpoints having any of the specified lockdown statuses (comma separated) | string | |
**last_seen_before** | optional | Last seen after date and time (UTC) or duration inclusive | string | |
**last_seen_after** | optional | Last seen before date and time (UTC) or duration exclusive | string | |
**ids** | optional | Get endpoints having any of the specified ids (comma separated) | string | |
**fields** | optional | The fields to return in a partial response | string | |
**view** | optional | Type of view to be returned in response | string | |
**search** | optional | Term to search for in the specified search fields | string | |
**search_fields** | optional | List of search fields for finding the given search term (comma separated). Defaults to all applicable fields | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.fields | string | | |
action_result.parameter.health_status | string | | |
action_result.parameter.ids | string | | |
action_result.parameter.last_seen_after | string | | |
action_result.parameter.last_seen_before | string | | |
action_result.parameter.lockdown_status | string | | |
action_result.parameter.page_from_key | string | | |
action_result.parameter.page_size | string | | |
action_result.parameter.search | string | | |
action_result.parameter.search_fields | string | | |
action_result.parameter.sort | string | | |
action_result.parameter.tamper_protection_enabled | string | | |
action_result.parameter.type | string | | |
action_result.parameter.view | string | | |
action_result.data.\*.assignedProducts.\*.code | string | | coreAgent |
action_result.data.\*.assignedProducts.\*.status | string | | installed |
action_result.data.\*.assignedProducts.\*.version | string | | |
action_result.data.\*.associatedPerson.id | string | | |
action_result.data.\*.associatedPerson.viaLogin | string | | |
action_result.data.\*.encryption.volumes.\*.status | string | | notEncrypted |
action_result.data.\*.encryption.volumes.\*.volumeId | string | | |
action_result.data.\*.group.name | string | | |
action_result.data.\*.health.overall | string | | good |
action_result.data.\*.health.services.serviceDetails.\*.name | string | | |
action_result.data.\*.health.services.serviceDetails.\*.status | string | | running |
action_result.data.\*.health.services.status | string | | good |
action_result.data.\*.health.threats.status | string | | good |
action_result.data.\*.hostname | string | | |
action_result.data.\*.id | string | | 3fa85f64-5717-4562-b3fc-2c963f66afa6 |
action_result.data.\*.ipv4Addresses | string | | |
action_result.data.\*.ipv6Addresses | string | | |
action_result.data.\*.lastSeenAt | string | | 2019-09-23T12:02:01.700Z |
action_result.data.\*.lockdown.status | string | | creatingWhitelist |
action_result.data.\*.lockdown.updateStatus | string | | upToDate |
action_result.data.\*.macAddresses | string | | |
action_result.data.\*.os.build | numeric | | 0 |
action_result.data.\*.os.isServer | boolean | | True False |
action_result.data.\*.os.majorVersion | numeric | | 0 |
action_result.data.\*.os.minorVersion | numeric | | 0 |
action_result.data.\*.os.name | string | | |
action_result.data.\*.os.platform | string | | windows |
action_result.data.\*.tamperProtectionEnabled | boolean | | True False |
action_result.data.\*.tenant.id | string | | 3fa85f64-5717-4562-b3fc-2c963f66afa6 |
action_result.data.\*.type | string | | computer |
action_result.summary.total_number_of_items | numeric | | 1 |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'check updates'

Send a request to the endpoint to check for Sophos management agent software updates

Type: **contain** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**endpointid** | required | The endpoint ID | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.endpointid | string | | |
action_result.data.\*.id | string | | 3fa85f64-5717-4562-b3fc-2c963f66afa6 |
action_result.data.\*.requestedAt | string | | |
action_result.data.\*.status | string | | requested |
action_result.summary.number_of_endpoints_checked | numeric | | 1 |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'tamper protection switch'

Turn Tamper Protection on or off on the endpoint

Type: **contain** \
Read only: **False**

Turn Tamper Protection on or off on the endpoint or generate a new Tamper Protection password. Note that Tamper Protection can be enabled for an endpoint only if it has also been enabled globally.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**endpointid** | required | The endpoint ID | string | |
**enabled** | optional | Whether Tamper Protection should be turned on for the endpoint | boolean | |
**regenerate_password** | optional | Whether a new Tamper Protection password should be generated | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.enabled | boolean | | True False |
action_result.parameter.endpointid | string | | |
action_result.parameter.regenerate_password | boolean | | True False |
action_result.data.\*.enabled | boolean | | |
action_result.data.\*.password | password | | |
action_result.data.\*.previousPasswords.\*.invalidatedAt | string | | |
action_result.data.\*.previousPasswords.\*.password | password | | |
action_result.summary.number_of_endpoints_tamperprotection_settings_updated | numeric | | 1 |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get tamperprotection settings'

Get the Tamper Protection settings for the specified endpoint

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**endpointid** | required | The endpoint ID | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.endpointid | string | | |
action_result.data.\*.enabled | boolean | | True False |
action_result.data.\*.password | password | | |
action_result.data.\*.previousPasswords.\*.invalidatedAt | string | | |
action_result.data.\*.previousPasswords.\*.password | password | | |
action_result.summary.number_of_endpoints_tamperprotection_settings_received | numeric | | |
action_result.summary.number_of_times_passwords_changed | numeric | | 1 |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'perform scan'

Send a request to the specified endpoint to perform or configure a scan

Type: **contain** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**endpointid** | required | The endpoint ID | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.endpointid | string | | |
action_result.data.\*.id | string | | 3fa85f64-5717-4562-b3fc-2c963f66afa6 |
action_result.data.\*.status | string | | requested |
action_result.summary.number_of_scans_performed | numeric | | 1 |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete endpoint'

Delete the specified endpoint

Type: **correct** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**endpointid** | required | The endpoint ID | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.endpointid | string | | |
action_result.data.\*.endpoint_deleted | string | | |
action_result.summary.total_endpoints_deleted | numeric | | 1 |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get individual endpoint'

Get the endpoint based on ID

Type: **contain** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**endpointid** | required | The endpoint ID | string | |
**fields** | optional | The fields to return in a partial response | string | |
**view** | optional | Type of view to be returned in response | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.endpointid | string | | |
action_result.parameter.fields | string | | |
action_result.parameter.view | string | | basic summary full |
action_result.data.\*.assignedProducts.\*.code | string | | coreAgent interceptX endpointProtection deviceEncryption mtr mtd ztna |
action_result.data.\*.assignedProducts.\*.status | string | | installed notInstalled |
action_result.data.\*.assignedProducts.\*.version | string | | |
action_result.data.\*.associatedPerson.name | string | | |
action_result.data.\*.associatedPerson.viaLogin | string | | |
action_result.data.\*.cloud.instanceId | string | | |
action_result.data.\*.cloud.provider | string | | aws azure |
action_result.data.\*.encryption.volumes.\*.status | string | | notEncrypted encrypted encrypting notSupported suspended unknown |
action_result.data.\*.encryption.volumes.\*.volumeId | string | | |
action_result.data.\*.group.id | string | | |
action_result.data.\*.group.name | string | | |
action_result.data.\*.health.overall | string | | good suspicious bad unknown |
action_result.data.\*.health.services.serviceDetails.\*.name | string | | |
action_result.data.\*.health.services.serviceDetails.\*.status | string | | running stopped missing |
action_result.data.\*.health.services.status | string | | good suspicious bad unknown |
action_result.data.\*.health.threats.status | string | | good suspicious bad unknown |
action_result.data.\*.hostname | string | | |
action_result.data.\*.id | string | | 3fa85f64-5717-4562-b3fc-2c963f66afa6 |
action_result.data.\*.ipv4Addresses | string | | |
action_result.data.\*.ipv6Addresses | string | | |
action_result.data.\*.isolation.status | string | | isolated notIsolated |
action_result.data.\*.lastSeenAt | string | | 2019-09-23T12:02:01.700Z |
action_result.data.\*.lockdown.status | string | | creatingWhitelist installing locked notInstalled registering starting stopping unavailable uninstalled unlocked |
action_result.data.\*.lockdown.updateStatus | string | | upToDate updating rebootRequired notInstalled |
action_result.data.\*.macAddresses | string | | |
action_result.data.\*.os.build | numeric | | |
action_result.data.\*.os.isServer | boolean | | True False |
action_result.data.\*.os.majorVersion | numeric | | |
action_result.data.\*.os.minorVersion | numeric | | |
action_result.data.\*.os.name | string | | |
action_result.data.\*.os.platform | string | | windows linux macOS |
action_result.data.\*.tamperProtectionEnabled | boolean | | True False |
action_result.data.\*.tenant.id | string | | 3fa85f64-5717-4562-b3fc-2c963f66afa6 |
action_result.data.\*.type | string | | computer |
action_result.summary.total_number_of_items | numeric | | 1 |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list items'

Get all allowed or blocked items

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**page** | optional | The page number to fetch, starting with 1 | numeric | |
**page_size** | optional | The size of the page requested | numeric | |
**items_type** | required | Specifies the type of items to be fetched: blocked or allowed | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.items_type | string | | |
action_result.parameter.page | numeric | | |
action_result.parameter.page_size | numeric | | |
action_result.data.\*.comment | string | | |
action_result.data.\*.createdAt | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.properties.sha256 | string | | |
action_result.data.\*.type | string | | |
action_result.summary.total_number_of_items | numeric | | 1 |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete item'

Delete the specified blocked or allowed item

Type: **correct** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**item_id** | required | The item ID to be deleted | string | |
**item_type** | required | Specifies the type of item to be deleted: blocked or allowed | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.item_id | string | | |
action_result.parameter.item_type | string | | |
action_result.data.\*.deleted | boolean | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'block item'

Add item to blocked list

Type: **investigate** \
Read only: **True**

Block an item from exoneration by SHA256 checksum.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**file_name** | required | The file name | string | |
**path** | required | The path for the application | string | |
**sha256** | required | The SHA256 value for the application | string | `sha256` |
**certificate_signer** | required | The value saved for the certificate signer | string | |
**comment** | required | Comment indicating why the item should be blocked | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.certificate_signer | string | | |
action_result.parameter.comment | string | | |
action_result.parameter.file_name | string | | |
action_result.parameter.path | string | | |
action_result.parameter.sha256 | string | `sha256` | |
action_result.data.\*.comment | string | | |
action_result.data.\*.createdAt | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.properties.certificate_signer | string | | |
action_result.data.\*.properties.sha256 | string | `sha256` | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'allow item'

Add item to allowed list

Type: **investigate** \
Read only: **True**

Exempt an item from conviction by path, SHA256 checksum or certificate signer.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**property_type** | required | Specifies the property by which an item is allowed: path, sha256 or certificateSigner | string | |
**file_name** | required | The file name | string | |
**path** | required | The path for the application | string | |
**sha256** | required | The SHA256 value for the application | string | `sha256` |
**certificate_signer** | required | The value saved for the certificate signer | string | |
**comment** | required | Comment indicating why the item should be allowed | string | |
**origin_person_id** | optional | Person associated with the endpoint where the item to be allowed was last seen | string | |
**origin_endpoint_id** | optional | Endpoint where the item to be allowed was last seen | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.certificate_signer | string | | |
action_result.parameter.comment | string | | |
action_result.parameter.file_name | string | | |
action_result.parameter.origin_endpoint_id | string | | |
action_result.parameter.origin_person_id | string | | |
action_result.parameter.path | string | | |
action_result.parameter.property_type | string | | |
action_result.parameter.sha256 | string | `sha256` | |
action_result.data.\*.comment | string | | |
action_result.data.\*.createdAt | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.properties.certificate_signer | string | | |
action_result.data.\*.properties.path | string | | |
action_result.data.\*.properties.sha256 | string | `sha256` | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list sites'

Get all local sites

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**page** | optional | The page number to fetch, starting with 1 | numeric | |
**page_size** | optional | The size of the page requested | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.page | string | | |
action_result.parameter.page_size | string | | |
action_result.data.\*.categoryId | string | | |
action_result.data.\*.comment | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.tags | string | | |
action_result.data.\*.url | string | | |
action_result.summary.total_number_of_items | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'delete site'

Delete the specified local site

Type: **correct** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**site_id** | required | The local site ID | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.site_id | string | | |
action_result.data.\*.deleted | boolean | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add site'

Add a new local site

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**category_id** | optional | The category Id associated with this local site | numeric | |
**tags** | optional | An array of tags associated with this local site setting (comma separated) | string | |
**url** | required | Local site URL | string | `url` |
**comment** | optional | Comment indicating why the site should be added | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.category_id | numeric | | |
action_result.parameter.comment | string | | |
action_result.parameter.tags | string | | |
action_result.parameter.url | string | `url` | |
action_result.data.\*.categoryId | string | | |
action_result.data.\*.comment | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.tags | string | | |
action_result.data.\*.url | string | `url` | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get isolation settings'

Get isolation settings for an endpoint

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**endpoint_id** | required | The endpoint ID | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.endpoint_id | string | | |
action_result.data.\*.enabled | boolean | | |
action_result.data.\*.lastDisabledAt | string | | |
action_result.data.\*.lastDisabledBy.id | string | | |
action_result.data.\*.lastDisabledBy.type | string | | user service |
action_result.data.\*.lastEnabledAt | string | | |
action_result.data.\*.lastEnabledBy.id | string | | |
action_result.data.\*.lastEnabledBy.type | string | | user service |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'isolation switch'

Turn on or off endpoint isolation for multiple endpoints

Type: **contain** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ids** | required | List of endpoint IDs (comma separated) | string | |
**enabled** | required | Whether the endpoints should be isolated | boolean | |
**comment** | optional | Reason the endpoints should be isolated | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.comment | string | | |
action_result.parameter.enabled | string | | |
action_result.parameter.ids | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.isolation.enabled | string | | |
action_result.data.\*.isolation.lastDisabledAt | string | | |
action_result.data.\*.isolation.lastDisabledBy.id | string | | |
action_result.data.\*.isolation.lastDisabledBy.type | string | | user service |
action_result.data.\*.isolation.lastEnabledAt | string | | |
action_result.data.\*.isolation.lastEnabledBy.id | string | | |
action_result.data.\*.isolation.lastEnabledBy.type | string | | user service |
action_result.summary.number_of_endpoints_isolation_settings_updated | numeric | | |
action_result.message | string | | |
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
