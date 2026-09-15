# Zscaler v2

Publisher: Splunk <br>
Connector Version: 1.0.1 <br>
Product Vendor: Zscaler <br>
Product Name: Zscaler v2 <br>
Minimum Product Version: 7.0.0

This app implements containment and investigative actions for Zscaler Internet Access

### Configuration variables

This table lists the configuration variables required to operate Zscaler v2. These variables are specified when configuring a Zscaler v2 asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**vanity_domain** | required | string | Zscaler OneAPI vanity-domain prefix, for example 'dev-new-soar-splunk' rather than a full URL or email address |
**client_id** | required | string | OAuth client ID for the Zscaler OneAPI API client |
**client_secret** | required | password | OAuth client secret for the Zscaler OneAPI API client |
**cloud** | optional | string | Zscaler OneAPI cloud environment used to derive OAuth and API endpoints |

### Supported Actions

[test connectivity](#action-test-connectivity) - Authenticate through OneAPI and read the ZIA configuration activation status. <br>
[list url categories](#action-list-url-categories) - List all URL categories <br>
[block web destination](#action-block-web-destination) - Add web destinations to the global blocklist <br>
[remove blocked web destination](#action-remove-blocked-web-destination) - Remove web destinations from the global blocklist <br>
[allow web destination](#action-allow-web-destination) - Add web destinations to the global allowlist <br>
[remove allowed web destination](#action-remove-allowed-web-destination) - Remove web destinations from the global allowlist <br>
[lookup web destination](#action-lookup-web-destination) - Look up ZIA classifications for web destinations <br>
[get admin users](#action-get-admin-users) - Get a list of admin users <br>
[get users](#action-get-users) - Get users, optionally filtered by name, department, or group <br>
[get groups](#action-get-groups) - Get a list of groups <br>
[add user to group](#action-add-user-to-group) - Add a user to a group <br>
[remove user from group](#action-remove-user-from-group) - Remove a user from a group <br>
[get allowlist](#action-get-allowlist) - Get web destinations on the allowlist <br>
[get denylist](#action-get-denylist) - Get web destinations on the denylist <br>
[update user](#action-update-user) - Update the user with the specified ID <br>
[add category destination](#action-add-category-destination) - Add web destinations to a custom URL category <br>
[remove category destination](#action-remove-category-destination) - Remove web destinations from a custom URL category <br>
[create destination group](#action-create-destination-group) - Create a destination group <br>
[list destination groups](#action-list-destination-groups) - List destination groups <br>
[edit destination group](#action-edit-destination-group) - Edit a destination group <br>
[delete destination group](#action-delete-destination-group) - Delete destination groups <br>
[get departments](#action-get-departments) - Get a list of departments <br>
[get category details](#action-get-category-details) - Get the URLs and keywords of a category <br>
[make request](#action-make-request) - Send an authenticated request to a ZIA OneAPI endpoint

## action: 'test connectivity'

Authenticate through OneAPI and read the ZIA configuration activation status.

Type: **test** <br>
Read only: **True**

Basic test for app.

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list url categories'

List all URL categories

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**get_ids_and_names_only** | optional | Return only category IDs and configured names instead of complete category records | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.get_ids_and_names_only | boolean | | |
action_result.data.\*.id | string | `zscaler url category` | test OTHER_RESTRICTED_WEBSITE |
action_result.data.\*.configuredName | string | | test Test-Caution |
action_result.data.\*.description | string | | test OTHER_RESTRICTED_WEBSITE_DESC |
action_result.data.\*.customCategory | boolean | | True False |
action_result.data.\*.editable | boolean | | True False |
action_result.data.\*.customIpRangesCount | numeric | | 0 |
action_result.data.\*.customUrlsCount | numeric | | 0 |
action_result.data.\*.dbCategorizedUrls.\* | string | | test 6.5.3.2.4 |
action_result.data.\*.ipRangesRetainingParentCategoryCount | numeric | | 0 |
action_result.data.\*.scopes.\*.Type | string | | test ORGANIZATION |
action_result.data.\*.type | string | | test URL_CATEGORY |
action_result.data.\*.urlsRetainingParentCategoryCount | numeric | | 0 |
action_result.data.\*.val | numeric | | 1 |
action_result.summary.total_url_categories | numeric | | 10 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'block web destination'

Add web destinations to the global blocklist

Type: **contain** <br>
Read only: **False**

Adds URLs, domains, IPv4 addresses, and IPv6 addresses to the global ZIA blocklist. HTTP and HTTPS schemes are removed before submission.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**destinations** | required | A comma-separated list of URLs, domains, IPv4 addresses, or IPv6 addresses | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.destinations | string | | |
action_result.summary.ignored.\* | string | | test example.com |
action_result.summary.updated.\* | string | | test 192.0.2.10 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remove blocked web destination'

Remove web destinations from the global blocklist

Type: **correct** <br>
Read only: **False**

Removes URLs, domains, IPv4 addresses, and IPv6 addresses from the global ZIA blocklist. HTTP and HTTPS schemes are removed before submission.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**destinations** | required | A comma-separated list of URLs, domains, IPv4 addresses, or IPv6 addresses | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.destinations | string | | |
action_result.summary.ignored.\* | string | | test example.com |
action_result.summary.updated.\* | string | | test 192.0.2.10 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'allow web destination'

Add web destinations to the global allowlist

Type: **contain** <br>
Read only: **False**

Adds URLs, domains, IPv4 addresses, and IPv6 addresses to the global ZIA allowlist. HTTP and HTTPS schemes are removed before submission.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**destinations** | required | A comma-separated list of URLs, domains, IPv4 addresses, or IPv6 addresses | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.destinations | string | | |
action_result.data.\*.whitelistUrls.\* | string | | test example.com test 192.0.2.10 |
action_result.summary.ignored.\* | string | | test example.com |
action_result.summary.updated.\* | string | | test 192.0.2.10 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remove allowed web destination'

Remove web destinations from the global allowlist

Type: **correct** <br>
Read only: **False**

Removes URLs, domains, IPv4 addresses, and IPv6 addresses from the global ZIA allowlist. HTTP and HTTPS schemes are removed before submission.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**destinations** | required | A comma-separated list of URLs, domains, IPv4 addresses, or IPv6 addresses | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.destinations | string | | |
action_result.data.\*.whitelistUrls.\* | string | | test example.com |
action_result.summary.ignored.\* | string | | test example.com |
action_result.summary.updated.\* | string | | test 192.0.2.10 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'lookup web destination'

Look up ZIA classifications for web destinations

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**destinations** | required | A comma-separated list of URLs, domains, IPv4 addresses, or IPv6 addresses | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.destinations | string | | |
action_result.data.\*.destination | string | `url` `domain` `ip` `ipv6` | test example.com test 8.8.8.8 |
action_result.data.\*.urlClassifications.\* | string | | test WEB_SEARCH |
action_result.data.\*.urlClassificationsWithSecurityAlert.\* | string | | |
action_result.data.\*.blocklisted | boolean | | True False |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get admin users'

Get a list of admin users

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**limit** | optional | Maximum number of records to fetch | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.limit | numeric | | |
action_result.data.\*.id | numeric | `zscaler user id` | 889814 |
action_result.data.\*.name | string | | test new_test_long_email_id_new_test_long_email_id_new_test_long_email_id_new_test_long_email |
action_result.data.\*.loginName | string | | test first.last@domain.com |
action_result.data.\*.email | string | `email` | test first.last@emaildomain.com |
action_result.data.\*.role.extensions.adminRank | string | | |
action_result.data.\*.role.extensions.roleType | string | | |
action_result.data.\*.role.id | numeric | | |
action_result.data.\*.role.isNameL10nTag | boolean | | True False |
action_result.data.\*.role.name | string | | test Super Admin |
action_result.data.\*.disabled | boolean | | True False |
action_result.data.\*.adminScopeScopeEntities.\*.id | numeric | | 4460340 |
action_result.data.\*.adminScopeScopeEntities.\*.name | string | | test Example App |
action_result.data.\*.adminScopeType | string | | |
action_result.data.\*.adminScopescopeGroupMemberEntities.\*.id | numeric | | 8035054 |
action_result.data.\*.comments | string | | test This is test user |
action_result.data.\*.isDefaultAdmin | boolean | | True False |
action_result.data.\*.isDeprecatedDefaultAdmin | boolean | | True False |
action_result.data.\*.isExecMobileAppEnabled | boolean | | True False |
action_result.data.\*.isNonEditable | boolean | | True False |
action_result.data.\*.isPasswordLoginAllowed | boolean | | True False |
action_result.data.\*.isProductUpdateCommEnabled | boolean | | True False |
action_result.data.\*.isSecurityReportCommEnabled | boolean | | True False |
action_result.data.\*.isServiceUpdateCommEnabled | boolean | | True False |
action_result.data.\*.pwdLastModifiedTime | numeric | | |
action_result.data.\*.userName | string | | test Last, First |
action_result.summary.total_admin_users | numeric | | 10 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get users'

Get users, optionally filtered by name, department, or group

Type: **investigate** <br>
Read only: **True**

Get users, optionally filtered by name, department, or group. The name parameter performs a partial match. The department and group parameters perform a 'starts with' match.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | optional | User Name/ID | string | |
**department** | optional | User department | string | |
**group** | optional | User group | string | |
**limit** | optional | Maximum number of records to fetch | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.name | string | | |
action_result.parameter.department | string | | |
action_result.parameter.group | string | | |
action_result.parameter.limit | numeric | | |
action_result.data.\*.id | numeric | `zscaler user id` | 889814 |
action_result.data.\*.name | string | | test First Last |
action_result.data.\*.email | string | `email` | test first.last@domain.com |
action_result.data.\*.department.id | numeric | | 81896690 |
action_result.data.\*.department.name | string | | test IT |
action_result.data.\*.disabled | boolean | | True False |
action_result.data.\*.groups.\*.id | numeric | `zscaler group id` | 8894813 |
action_result.data.\*.groups.\*.name | string | | test Super Admin |
action_result.data.\*.adminUser | boolean | | True False |
action_result.data.\*.comments | string | | test This is test user |
action_result.data.\*.deleted | boolean | | True False |
action_result.data.\*.isNonEditable | boolean | | True False |
action_result.summary.total_users | numeric | | 10 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get groups'

Get a list of groups

Type: **investigate** <br>
Read only: **True**

Get groups whose name or comments match the search parameter.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**search** | optional | The search string used to match against a group's name or comments attributes | string | |
**limit** | optional | Maximum number of records to fetch | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.search | string | | |
action_result.parameter.limit | numeric | | |
action_result.data.\*.id | numeric | `zscaler group id` | 8894813 |
action_result.data.\*.name | string | | test Frothly Internet Access |
action_result.data.\*.comments | string | | test This is for testing |
action_result.data.\*.isNonEditable | boolean | | True False |
action_result.summary.total_groups | numeric | | 4 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add user to group'

Add a user to a group

Type: **generic** <br>
Read only: **False**

Add a group to the user's profile.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user_id** | required | Zscaler user ID | numeric | `zscaler user id` |
**group_id** | required | Zscaler group ID | numeric | `zscaler group id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.user_id | numeric | `zscaler user id` | |
action_result.parameter.group_id | numeric | `zscaler group id` | |
action_result.data.\*.adminUser | boolean | | True False |
action_result.data.\*.deleted | boolean | | True False |
action_result.data.\*.department.id | numeric | | 4459551 |
action_result.data.\*.department.name | string | | test Service Admin |
action_result.data.\*.email | string | | test 134@example.us |
action_result.data.\*.groups.\*.id | numeric | | 4460341 |
action_result.data.\*.groups.\*.name | string | | test Example App |
action_result.data.\*.id | numeric | | 9840695 |
action_result.data.\*.name | string | | test Test user |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remove user from group'

Remove a user from a group

Type: **correct** <br>
Read only: **False**

Remove a group from the user's profile.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user_id** | required | Zscaler user ID | numeric | `zscaler user id` |
**group_id** | required | Zscaler group ID | numeric | `zscaler group id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.user_id | numeric | `zscaler user id` | |
action_result.parameter.group_id | numeric | `zscaler group id` | |
action_result.data.\*.adminUser | boolean | | True False |
action_result.data.\*.deleted | boolean | | True False |
action_result.data.\*.department.id | numeric | | 4459551 |
action_result.data.\*.department.name | string | | test Service Admin |
action_result.data.\*.email | string | | test 134@example.us |
action_result.data.\*.groups.\*.id | numeric | | 4459550 |
action_result.data.\*.groups.\*.name | string | | test Service Admin |
action_result.data.\*.id | numeric | | 9840695 |
action_result.data.\*.name | string | | test Elsie |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get allowlist'

Get web destinations on the allowlist

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.data.\*.url | string | `url` `domain` `ip` `ipv6` | |
action_result.summary.total_allowlist_items | numeric | | 10 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get denylist'

Get web destinations on the denylist

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**filter** | optional | Filter results by URL or IP | string | |
**query** | optional | Regular expression to match against each URL or IP | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.filter | string | | |
action_result.parameter.query | string | | |
action_result.data.\*.url | string | `url` `domain` `ip` `ipv6` | |
action_result.summary.total_denylist_items | numeric | | 10 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update user'

Update the user with the specified ID

Type: **correct** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user_id** | required | Zscaler user ID | numeric | `zscaler user id` |
**user** | required | JSON object containing the user details (see https://help.zscaler.com/zia/user-management#/users/{userId}-put) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.user_id | numeric | `zscaler user id` | |
action_result.parameter.user | string | | |
action_result.data.\*.adminUser | boolean | | True False |
action_result.data.\*.comments | string | | test This is test user |
action_result.data.\*.deleted | boolean | | True False |
action_result.data.\*.department.id | numeric | | 81896690 |
action_result.data.\*.department.name | string | | test IT |
action_result.data.\*.email | string | `email` | test first.last@domain.com |
action_result.data.\*.groups.\*.id | numeric | `zscaler group id` | 8894813 |
action_result.data.\*.groups.\*.name | string | | test Super Admin |
action_result.data.\*.id | numeric | `zscaler user id` | 889814 |
action_result.data.\*.name | string | | test First Last |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add category destination'

Add web destinations to a custom URL category

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**category_id** | required | The ID of the custom category to update | string | `zscaler url category` |
**destinations** | optional | Comma-separated destinations to add to the category | string | |
**retaining_parent_category_destinations** | optional | Comma-separated destinations to add while retaining their parent category | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.category_id | string | `zscaler url category` | |
action_result.parameter.destinations | string | | |
action_result.parameter.retaining_parent_category_destinations | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.val | numeric | | |
action_result.data.\*.type | string | | |
action_result.data.\*.urls.\* | string | | |
action_result.data.\*.scopes.\*.Type | string | | |
action_result.data.\*.editable | boolean | | True False |
action_result.data.\*.keywords.\* | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.configuredName | string | | |
action_result.data.\*.customCategory | boolean | | True False |
action_result.data.\*.customUrlsCount | numeric | | |
action_result.data.\*.dbCategorizedUrls.\* | string | | |
action_result.data.\*.customIpRangesCount | numeric | | |
action_result.data.\*.keywordsRetainingParentCategory.\* | string | | |
action_result.data.\*.urlsRetainingParentCategoryCount | numeric | | |
action_result.data.\*.ipRangesRetainingParentCategoryCount | numeric | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remove category destination'

Remove web destinations from a custom URL category

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**category_id** | required | The ID of the custom category to update | string | `zscaler url category` |
**destinations** | optional | Comma-separated destinations to remove from the category | string | |
**retaining_parent_category_destinations** | optional | Comma-separated destinations to remove from the retaining-parent-category list | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.category_id | string | `zscaler url category` | |
action_result.parameter.destinations | string | | |
action_result.parameter.retaining_parent_category_destinations | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.val | numeric | | |
action_result.data.\*.type | string | | |
action_result.data.\*.urls.\* | string | | |
action_result.data.\*.scopes.\*.Type | string | | |
action_result.data.\*.editable | boolean | | True False |
action_result.data.\*.keywords.\* | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.configuredName | string | | |
action_result.data.\*.customCategory | boolean | | True False |
action_result.data.\*.customUrlsCount | numeric | | |
action_result.data.\*.dbCategorizedUrls.\* | string | | |
action_result.data.\*.customIpRangesCount | numeric | | |
action_result.data.\*.keywordsRetainingParentCategory.\* | string | | |
action_result.data.\*.urlsRetainingParentCategoryCount | numeric | | |
action_result.data.\*.ipRangesRetainingParentCategoryCount | numeric | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create destination group'

Create a destination group

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Destination group name | string | |
**type** | required | Destination group type. Supported values: DSTN_IP, DSTN_FQDN, DSTN_DOMAIN, and DSTN_OTHER | string | |
**addresses** | optional | Comma-separated destination IP addresses, FQDNs, or wildcard FQDNs to add to the group | string | |
**description** | optional | Additional information about the destination group. | string | |
**ip_categories** | optional | Destination IP address URL categories | string | |
**countries** | optional | Destination IP address countries. You can identify destinations based on the location of a server. | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.name | string | | |
action_result.parameter.type | string | | |
action_result.parameter.addresses | string | | |
action_result.parameter.description | string | | |
action_result.parameter.ip_categories | string | | |
action_result.parameter.countries | string | | |
action_result.data.\*.id | numeric | | |
action_result.data.\*.name | string | | |
action_result.data.\*.type | string | | DSTN_IP DSTN_FQDN DSTN_DOMAIN DSTN_OTHER |
action_result.data.\*.addresses.\* | string | | 192.168.1.1 |
action_result.data.\*.countries.\* | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.ipCategories.\* | string | | TRADING_BROKARAGE_INSURANCE |
action_result.data.\*.isNonEditable | boolean | | True False |
action_result.data.\*.creatorContext | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list destination groups'

List destination groups

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_group_ids** | optional | A comma-separated list of unique identifiers for the IP destination groups | string | |
**exclude_type** | optional | The IP group type to be excluded from the results | string | |
**category_type** | optional | Comma-separated IP group types to include. This parameter is supported only when 'lite' is true | string | |
**limit** | optional | Limit of the results to be retrieved | numeric | |
**lite** | optional | Whether to retrieve only limited information of IP destination groups. Includes ID, name and type of the IP destination groups | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.ip_group_ids | string | | |
action_result.parameter.exclude_type | string | | |
action_result.parameter.category_type | string | | |
action_result.parameter.limit | numeric | | |
action_result.parameter.lite | boolean | | |
action_result.data.\*.id | numeric | | |
action_result.data.\*.name | string | | |
action_result.data.\*.type | string | | DSTN_IP DSTN_FQDN DSTN_DOMAIN DSTN_OTHER |
action_result.data.\*.addresses.\* | string | | 192.168.1.1 |
action_result.data.\*.countries.\* | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.ipCategories.\* | string | | TRADING_BROKARAGE_INSURANCE |
action_result.data.\*.isNonEditable | boolean | | True False |
action_result.data.\*.creatorContext | string | | |
action_result.summary.total_destination_groups | numeric | | 10 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'edit destination group'

Edit a destination group

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_group_id** | required | The unique identifier for the IP destination group | numeric | |
**name** | optional | Destination group name | string | |
**addresses** | optional | Comma-separated destination IP addresses, FQDNs, or wildcard FQDNs to assign to the group | string | |
**description** | optional | Additional information about the destination group. | string | |
**ip_categories** | optional | Destination IP address URL categories | string | |
**countries** | optional | Destination IP address countries. You can identify destinations based on the location of a server. | string | |
**is_non_editable** | optional | If set to true, the destination IP address group is non-editable. This field is applicable only to predefined IP address groups, which cannot be modified | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.ip_group_id | numeric | | |
action_result.parameter.name | string | | |
action_result.parameter.addresses | string | | |
action_result.parameter.description | string | | |
action_result.parameter.ip_categories | string | | |
action_result.parameter.countries | string | | |
action_result.parameter.is_non_editable | boolean | | |
action_result.data.\*.id | numeric | | |
action_result.data.\*.name | string | | |
action_result.data.\*.type | string | | DSTN_IP DSTN_FQDN DSTN_DOMAIN DSTN_OTHER |
action_result.data.\*.addresses.\* | string | | 192.168.1.1 |
action_result.data.\*.countries.\* | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.ipCategories.\* | string | | TRADING_BROKARAGE_INSURANCE |
action_result.data.\*.isNonEditable | boolean | | True False |
action_result.data.\*.creatorContext | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete destination group'

Delete destination groups

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_group_ids** | required | A comma-separated list of unique identifiers for the IP destination groups | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.ip_group_ids | string | | |
action_result.data.\*.ip_group_id | string | | |
action_result.summary.deleted_destination_groups | numeric | | 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get departments'

Get a list of departments

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | optional | Filter by department name | string | |
**page** | optional | Page number, starting at 1 | numeric | |
**page_size** | optional | Number of departments per page, from 1 to 1000 | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.name | string | | |
action_result.parameter.page | numeric | | |
action_result.parameter.page_size | numeric | | |
action_result.data.\*.id | numeric | | |
action_result.data.\*.name | string | | |
action_result.data.\*.isNonEditable | boolean | | True False |
action_result.summary.total_departments | numeric | | 97 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get category details'

Get the URLs and keywords of a category

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**category_ids** | required | Comma-separated list of category IDs to query | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.category_ids | string | | |
action_result.data.\*.id | string | `zscaler url category` | test OTHER_RESTRICTED_WEBSITE |
action_result.data.\*.configuredName | string | | test Test-Caution |
action_result.data.\*.description | string | | test OTHER_RESTRICTED_WEBSITE_DESC |
action_result.data.\*.customCategory | boolean | | True False |
action_result.data.\*.editable | boolean | | True False |
action_result.data.\*.keywords.\* | string | | |
action_result.data.\*.urls.\* | string | | |
action_result.data.\*.customIpRangesCount | numeric | | 0 |
action_result.data.\*.customUrlsCount | numeric | | 0 |
action_result.data.\*.dbCategorizedUrls.\* | string | | test 6.5.3.2.4 |
action_result.data.\*.keywordsRetainingParentCategory.\* | string | | |
action_result.data.\*.ipRangesRetainingParentCategoryCount | numeric | | 0 |
action_result.data.\*.scopes.\*.Type | string | | test ORGANIZATION |
action_result.data.\*.type | string | | test URL_CATEGORY |
action_result.data.\*.urlsRetainingParentCategoryCount | numeric | | 0 |
action_result.data.\*.val | numeric | | 1 |
action_result.summary.total_categories | numeric | | 97 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'make request'

Send an authenticated request to a ZIA OneAPI endpoint

Type: **generic** <br>
Read only: **False**

Sends an authenticated request using the asset's Zscaler OneAPI OAuth credentials. Provide a relative /zia/api/v1 path; full URLs and Sandbox endpoints are not accepted. Mutating requests do not automatically activate pending ZIA changes.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**http_method** | required | The HTTP method to use for the request. | string | |
**endpoint** | required | ZIA API path relative to the OneAPI gateway, for example '/zia/api/v1/status'. Do not include a base URL or query string. | string | |
**headers** | optional | The headers to send with the request (JSON object). An example is {'Content-Type': 'application/json'} | string | |
**query_parameters** | optional | Parameters to append to the URL (JSON object or query string). An example is ?key=value&key2=value2 | string | |
**body** | optional | The body to send with the request (JSON object). An example is {'key': 'value', 'key2': 'value2'} | string | |
**timeout** | optional | Request timeout in seconds. Must be between 1 and 240. Default is 240. | numeric | |
**verify_ssl** | optional | Verify the TLS certificate. This must be true. | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.http_method | string | | |
action_result.parameter.endpoint | string | | |
action_result.parameter.headers | string | | |
action_result.parameter.query_parameters | string | | |
action_result.parameter.body | string | | |
action_result.parameter.timeout | numeric | | |
action_result.parameter.verify_ssl | boolean | | |
action_result.data.\*.status_code | numeric | | 200 404 500 |
action_result.data.\*.response_body | string | | {"key": "value"} |
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
