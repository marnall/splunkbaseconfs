# Forcepoint Web Security

Publisher: Splunk Community \
Connector Version: 2.0.3 \
Product Vendor: Forcepoint \
Product Name: Web Security \
Minimum Product Version: 6.3.0

This app provides category management and blocking actions for the Forcepoint Web Security platform

### Configuration variables

This table lists the configuration variables required to operate Forcepoint Web Security. These variables are specified when configuring a Web Security asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Hostname |
**port** | required | numeric | Port (Forcepoint default: 15873) |
**verify_server_cert** | optional | boolean | Verify server certificate |
**username** | required | string | User Name |
**password** | required | password | Password |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[block ip](#action-block-ip) - Block IP or list of IPs by adding them to the supplied category \
[block url](#action-block-url) - Block URL or list of URLs by adding them to the supplied category \
[unblock ip](#action-unblock-ip) - Unblock IP or list of IPs by removing them from the supplied category \
[unblock url](#action-unblock-url) - Unblock URL or list of URLs by removing them from the supplied category \
[lookup ip](#action-lookup-ip) - Lookup the categories related to the IP or list of IPs \
[lookup url](#action-lookup-url) - Lookup the categories related to the URL or list of URLs \
[get category](#action-get-category) - Return the category list contents \
[list categories](#action-list-categories) - Return a list of all API-managed categories \
[delete category](#action-delete-category) - Delete API-managed category \
[add category](#action-add-category) - Add API-managed category to Forcepoint

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'block ip'

Block IP or list of IPs by adding them to the supplied category

Type: **contain** \
Read only: **False**

Adding an IP to a category automatically sets it into a blocking action.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP or list of IPs to block | string | `ip` |
**category** | required | Add the IP(s) to this category | string | `forcepoint category` |
**create_category** | optional | If the category does not exist, create it | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.category | string | `forcepoint category` | Phantom Block List |
action_result.parameter.create_category | boolean | | False True |
action_result.parameter.ip | string | `ip` | 1.1.1.1 |
action_result.data.\*.Category ID | numeric | | 0 |
action_result.data.\*.Category Name | string | `forcepoint category` | Phantom Block List |
action_result.data.\*.Totals.Added IPs | numeric | | 1 |
action_result.data.\*.Totals.Added URLs | numeric | | 0 |
action_result.summary.category | string | `forcepoint category` | Phantom Block List |
action_result.summary.transaction_id | string | | dd6ff080-c109-11e8-853a-cedf71c89df7 |
action_result.message | string | | Block IPs/ URLs completed |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'block url'

Block URL or list of URLs by adding them to the supplied category

Type: **contain** \
Read only: **False**

Adding URLs to a category automatically sets it into a blocking action.<br />NOTE: If a url is provided without the protocol, it will block HTTP, HTTPS, and FTP.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL or list of URLs to block | string | `url` `domain` |
**category** | required | Add the URL(s) to this category | string | `forcepoint category` |
**create_category** | optional | If the category does not exist, create it | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.category | string | `forcepoint category` | Phantom Block List |
action_result.parameter.create_category | boolean | | False True |
action_result.parameter.url | string | `url` `domain` | http://test.com/ |
action_result.data.\*.Category ID | numeric | | 0 |
action_result.data.\*.Category Name | string | `forcepoint category` | Phantom Block List |
action_result.data.\*.Totals.Added IPs | numeric | | 0 |
action_result.data.\*.Totals.Added URLs | numeric | | 1 |
action_result.summary.category | string | `forcepoint category` | Phantom Block List |
action_result.summary.transaction_id | string | | 4ff2d0da-c111-11e8-af31-b2572e0b68cd |
action_result.message | string | | Block IPs/ URLs completed |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unblock ip'

Unblock IP or list of IPs by removing them from the supplied category

Type: **correct** \
Read only: **False**

An empty category will remove them from all available categories.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP or list of IPs to unblock | string | `ip` |
**category** | optional | Category for which to remove the block (if empty, remove from all categories) | string | `forcepoint category` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.category | string | `forcepoint category` | Phantom Block List |
action_result.parameter.ip | string | `ip` | 1.1.1.1 |
action_result.data.\*.Category ID | numeric | | 0 |
action_result.data.\*.Category Name | string | `forcepoint category` | Phantom Block List |
action_result.data.\*.IPs | string | `ip` | 1.1.1.1 |
action_result.data.\*.Totals.Deleted IPs | numeric | | 1 |
action_result.data.\*.Totals.Deleted URLs | numeric | | 0 |
action_result.data.\*.Transaction ID | string | | 99c5d638-c109-11e8-bb9a-ad790ed9aab5 |
action_result.summary.commit_time | string | | September, 25 2018 09:26:15 PM |
action_result.summary.transaction_id | string | | 99c5d638-c109-11e8-bb9a-ad790ed9aab5 |
action_result.message | string | | Unblock IPs/ URLs completed |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unblock url'

Unblock URL or list of URLs by removing them from the supplied category

Type: **correct** \
Read only: **False**

An empty category will remove them from all available categories.<br />NOTE: If a url is provided without the protocol, it will unblock HTTP, HTTPS, and FTP.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL or list of URLs to unblock | string | `url` `domain` |
**category** | optional | Category for which to remove the block (if empty, remove from all categories) | string | `forcepoint category` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.category | string | `forcepoint category` | Phantom Block List |
action_result.parameter.url | string | `url` `domain` | test.com |
action_result.data.\*.Category ID | numeric | | 0 |
action_result.data.\*.Category Name | string | `forcepoint category` | Phantom Block List |
action_result.data.\*.Totals.Deleted IPs | numeric | | 0 |
action_result.data.\*.Totals.Deleted URLs | numeric | | 3 |
action_result.data.\*.Transaction ID | string | | a293f3ee-c109-11e8-a4da-e38a189e8fdb |
action_result.data.\*.URLs | string | | test.com |
action_result.summary.commit_time | string | | September, 25 2018 09:26:30 PM |
action_result.summary.transaction_id | string | | a293f3ee-c109-11e8-a4da-e38a189e8fdb |
action_result.message | string | | Unblock IPs/ URLs completed |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'lookup ip'

Lookup the categories related to the IP or list of IPs

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP or list of IPs to lookup | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` | 1.1.1.1 |
action_result.data.\*.categories | string | `forcepoint category` | Phantom Block List |
action_result.data.\*.ip | string | `ip` | 1.1.1.1 |
action_result.summary.found category count | numeric | | 1 |
action_result.summary.lookup count | numeric | | 1 |
action_result.message | string | | Retrieved categories for each object: ['1.1.1.1'] |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'lookup url'

Lookup the categories related to the URL or list of URLs

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL or list of URLs to lookup | string | `url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.url | string | `url` | test.com, http://test.com |
action_result.data.\*.categories | string | `forcepoint category` | Phantom Block List |
action_result.data.\*.url | string | `url` | test.com |
action_result.summary.found category count | numeric | | 3 |
action_result.summary.lookup count | numeric | | 4 |
action_result.message | string | | Retrieved categories for each object: ['test.com', 'http://test.com'] |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get category'

Return the category list contents

Type: **investigate** \
Read only: **True**

Return all URLs and IPs in a specified category.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**category** | required | Category name | string | `forcepoint category` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.category | string | `forcepoint category` | Phantom Block List |
action_result.data.\*.ip | string | `ip` | 1.1.1.1 |
action_result.data.\*.url | string | `url` | http://test.com |
action_result.summary.category_id | numeric | | 1919 |
action_result.summary.category_name | string | `forcepoint category` | Phantom Block List |
action_result.message | string | | Retrieved contents of category: Phantom Block List |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list categories'

Return a list of all API-managed categories

Type: **investigate** \
Read only: **True**

Only API-managed categories can be viewed or changed.

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.Category Description | string | | Automation ARIC makes Forcepoint API calls to block requested URLs and IPs |
action_result.data.\*.Category Hierarchy | numeric | | 0 |
action_result.data.\*.Category ID | numeric | | 1913 |
action_result.data.\*.Category Name | string | `forcepoint category` | Automation Block List |
action_result.data.\*.Category Owner | string | | API |
action_result.summary.category count | numeric | | 2 |
action_result.message | string | | Retrieved list of categories |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete category'

Delete API-managed category

Type: **generic** \
Read only: **False**

Only API-managed categories can be viewed or changed.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**category** | required | Category name | string | `forcepoint category` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.category | string | `forcepoint category` | Phantom Block List |
action_result.data.\*.category | string | | Phantom Block List |
action_result.summary.commit_time | string | | September, 25 2018 09:15:13 PM |
action_result.summary.transaction_id | string | | 0fb93292-c108-11e8-9f60-8a6b095871f8 |
action_result.message | string | | Category deleted: Phantom Block List |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add category'

Add API-managed category to Forcepoint

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**category** | required | Category name, must be unique | string | `forcepoint category` |
**description** | optional | Description of the category | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.category | string | `forcepoint category` | Phantom Block List |
action_result.parameter.description | string | | Phantom generated Phantom Block List |
action_result.data.\*.Categories.\*.Category Name | string | `forcepoint category` | Phantom Block List |
action_result.summary.commit_time | string | | September, 25 2018 09:17:32 PM |
action_result.summary.transaction_id | string | | 620f71b4-c108-11e8-b029-8a3671f954e5 |
action_result.message | string | | Added category: Phantom Block List |
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
