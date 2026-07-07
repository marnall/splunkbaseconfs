# Google People

Publisher: Splunk <br>
Connector Version: 1.1.9 <br>
Product Vendor: Google <br>
Product Name: Google People <br>
Minimum Product Version: 6.3.0

This app integrates with Google People to support various generic and investigative actions

## SDK and SDK Licensing details for the app

#### cachetools

This app uses the cachetools module, which is licensed under the MIT License (MIT), Copyright (c)
2014-2020 Thomas Kemmer.

#### google-api-python-client

This app uses the google-api-python-client module, which is licensed under the Apache Software
License (Apache 2.0), Copyright (c) Google LLC.

#### google-auth-httplib2

This app uses the google-auth-httplib2 module, which is licensed under the Apache Software License
(Apache 2.0), Copyright (c) Google Cloud Platform.

#### google-auth-oauthlib

This app uses the google-auth-oauthlib module, which is licensed under the Apache Software License
(Apache 2.0), Copyright (c) Google Cloud Platform.

#### google-auth

This app uses the google-auth module, which is licensed under the Apache Software License (Apache
2.0), Copyright (c) Google Cloud Platform.

#### httplib2

This app uses the httplib2 module, which is licensed under the MIT License (MIT), Copyright (c) Joe
Gregorio.

#### oauth2client

This app uses the oauth2client module, which is licensed under the Apache Software License (Apache
2.0), Copyright (c) Google Inc.

#### pyasn1-modules

This app uses the pyasn1-modules module, which is licensed under the BSD License (BSD-2-Clause),
Copyright (c) Ilya Etingof.

#### rsa

This app uses the rsa module, which is licensed under the Apache Software License (ASL 2), Copyright
(c) Sybren A. Stuvel.

#### uritemplate

This app uses the uritemplate module, which is licensed under the OSI Approved, Apache Software
License, BSD License (BSD 3-Clause License or Apache License, Version 2.0), Copyright (c) Ian
Stapleton Cordasco.

### Service Account

This app requires a pre-configured service account to operate. Please follow the procedure outlined
at [this link](https://support.google.com/a/answer/7378726?hl=en) to create a service account.\
The following APIs will need to be enabled:

- AdminSDK
- Google People API

At the end of the creation process, the admin console should ask you to save the config as a JSON
file. Copy the contents of the JSON file in the clipboard and paste it as the value of the "Contents
of Service Account JSON file" asset configuration parameter.

### Scopes

Once the service account has been created and APIs enabled, the next step is to configure scopes on
these APIs to allow the App to access them. Every action requires different scopes to operate, these
are listed in the action documentation.\
To enable scopes please complete the following steps:

- Go to your G Suite domain's [Admin console](http://admin.google.com/) .
- Select **Security** from the list of controls.
- Select **API Controls** then select **Manage Domain Wide Delegation** under **Domain Wide
  Delegation**
- In the **Client Name** field enter the service account's **Client ID** . You can find your
  service account's client ID in the [Service accounts credentials
  page](https://console.developers.google.com/apis/credentials) or the service account JSON file
  (key named **client_id** ).
- Click **Add new** to add another API client or use an existing client if you have one. Hover
  over the newly created API client then select **Edit** to add the scopes that you wish to grant
  access to the App. For example, to enable all the scopes required by this app enter:
  - 'https://www.googleapis.com/auth/contacts'
  - 'https://www.googleapis.com/auth/contacts.other.readonly'
  - 'https://www.googleapis.com/auth/directory.readonly'
  - 'https://www.googleapis.com/auth/userinfo.profile'
- Click **Authorize** .

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Google People server. Below are the
default ports used by Splunk SOAR.

|         Service Name | Transport Protocol | Port |
|----------------------|--------------------|------|
|         http | tcp | 80 |
|         https | tcp | 443 |

### Configuration variables

This table lists the configuration variables required to operate Google People. These variables are specified when configuring a Google People asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**key_json** | required | password | Contents of service account JSON file |
**login_email** | required | string | Login email |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[list other contacts](#action-list-other-contacts) - Lists all contacts that are not in a contact group <br>
[copy contact](#action-copy-contact) - Copy 'Other contact' to 'myContacts' group <br>
[list directory](#action-list-directory) - Lists all contacts and profiles in the user's domain directory <br>
[get user profile](#action-get-user-profile) - Provides information about a person given account ID <br>
[list people](#action-list-people) - Lists authenticated user's contacts

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list other contacts'

Lists all contacts that are not in a contact group

Type: **investigate** <br>
Read only: **True**

This action lists all "Other contacts" which are contacts that are not in another contact group. These contacts are typically automatically created from interactions.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**read_mask** | optional | Comma-separated list of fields to be returned for each person. If not provided, default values will be used | string | |
**limit** | optional | Number of contacts to include in the response | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.read_mask | string | | names,emailAddresses |
action_result.parameter.limit | numeric | | 500 |
action_result.data.\*.etag | string | | %EgcBAj0JPjcuGgECIgxwRmJmNytycjB4RT0= |
action_result.data.\*.names.\*.metadata.source.id | string | | 6babaf04880e3563 |
action_result.data.\*.names.\*.metadata.source.type | string | | OTHER_CONTACT |
action_result.data.\*.names.\*.metadata.primary | boolean | | True False |
action_result.data.\*.names.\*.givenName | string | | Test user |
action_result.data.\*.names.\*.familyName | string | | Test user |
action_result.data.\*.names.\*.displayName | string | | Test user |
action_result.data.\*.names.\*.unstructuredName | string | | Test user |
action_result.data.\*.names.\*.displayNameLastFirst | string | | Test, user |
action_result.data.\*.names.\*.middleName | string | | Test user |
action_result.data.\*.resourceName | string | `googlepeople resource name` | otherContacts/c7758487217073173859 |
action_result.data.\*.emailAddresses.\*.value | string | `email` | user@example.com |
action_result.data.\*.emailAddresses.\*.metadata.source.id | string | | 6babaf04880e3563 |
action_result.data.\*.emailAddresses.\*.metadata.source.type | string | | OTHER_CONTACT |
action_result.data.\*.emailAddresses.\*.metadata.primary | boolean | | True False |
action_result.data.\*.emailAddresses.\*.type | string | | other |
action_result.data.\*.emailAddresses.\*.formattedType | string | | Other |
action_result.data.\*.metadata.sources.\*.id | string | | 6babaf04880e3563 |
action_result.data.\*.metadata.sources.\*.etag | string | | #pFbf7+rr0xE= |
action_result.data.\*.metadata.sources.\*.type | string | | OTHER_CONTACT |
action_result.data.\*.metadata.sources.\*.updateTime | string | | 2017-05-24T23:40:54.632001Z |
action_result.data.\*.metadata.objectType | string | | PERSON |
action_result.status | string | | success failed |
action_result.message | string | | Successfully retrieved 6 otherContactss |
action_result.summary.total_otherContacts_returned | numeric | | 6 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'copy contact'

Copy 'Other contact' to 'myContacts' group

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource_name** | required | Resource name of the "Other contact" to copy | string | `googlepeople resource name` |
**copy_mask** | optional | Comma-separated list of fields to be copied into the new contact | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.resource_name | string | `googlepeople resource name` | otherContacts/c8038824399000987793 |
action_result.parameter.copy_mask | string | | names,emailAddresses,phoneNumbers |
action_result.data.\*.etag | string | | %EgcBAj0JPjcuGgQBAgUHIgxkaU5rT3hHZm5BVT0= |
action_result.data.\*.metadata.sources.\*.id | string | | 59b7075988160d30 |
action_result.data.\*.metadata.sources.\*.etag | string | | #diNkOxGfnAU= |
action_result.data.\*.metadata.sources.\*.type | string | | CONTACT |
action_result.data.\*.metadata.sources.\*.updateTime | string | | 2020-07-27T17:48:29.240Z |
action_result.data.\*.metadata.sources.\*.profileMetadata.userTypes | string | | GOOGLE_USER |
action_result.data.\*.metadata.sources.\*.profileMetadata.objectType | string | | PERSON |
action_result.data.\*.metadata.objectType | string | | PERSON |
action_result.data.\*.memberships.\*.metadata.source.id | string | | 59b7075988160d30 |
action_result.data.\*.memberships.\*.metadata.source.type | string | | CONTACT |
action_result.data.\*.memberships.\*.contactGroupMembership.contactGroupId | string | | myContacts |
action_result.data.\*.memberships.\*.contactGroupMembership.contactGroupResourceName | string | | contactGroups/myContacts |
action_result.data.\*.memberships.\*.domainMembership.inViewerDomain | boolean | | True False |
action_result.data.\*.resourceName | string | `googlepeople resource name` | people/c6464643871230266672 |
action_result.data.\*.phoneNumbers.\*.value | string | | |
action_result.data.\*.phoneNumbers.\*.metadata.source.id | string | | 36f9f3a8888aca24 |
action_result.data.\*.phoneNumbers.\*.metadata.source.type | string | | CONTACT |
action_result.data.\*.phoneNumbers.\*.metadata.primary | boolean | | True False |
action_result.data.\*.phoneNumbers.\*.canonicalForm | string | | |
action_result.data.\*.emailAddresses.\*.metadata.verified | boolean | | True False |
action_result.data.\*.emailAddresses.\*.value | string | `email` | user@example.com |
action_result.data.\*.emailAddresses.\*.type | string | | other |
action_result.data.\*.emailAddresses.\*.formattedType | string | | Other |
action_result.data.\*.emailAddresses.\*.metadata.source.id | string | | 59b7075988160d30 |
action_result.data.\*.emailAddresses.\*.metadata.source.type | string | | CONTACT |
action_result.data.\*.emailAddresses.\*.metadata.primary | boolean | | True False |
action_result.data.\*.names.\*.metadata.source.id | string | | 71d4a4d58a0990ed |
action_result.data.\*.names.\*.metadata.source.type | string | | CONTACT |
action_result.data.\*.names.\*.metadata.primary | boolean | | True False |
action_result.data.\*.names.\*.givenName | string | | Test user |
action_result.data.\*.names.\*.familyName | string | | Test user |
action_result.data.\*.names.\*.displayName | string | | Test user |
action_result.data.\*.names.\*.unstructuredName | string | | Test user |
action_result.data.\*.names.\*.displayNameLastFirst | string | | Test, user |
action_result.data.\*.names.\*.middleName | string | | Test user |
action_result.status | string | | success failed |
action_result.message | string | | Successfully copied 1 contact |
action_result.summary.total_contacts_copied | numeric | | 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list directory'

Lists all contacts and profiles in the user's domain directory

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**read_mask** | optional | Comma-separated list of fields to be returned for each person. If not provided, default values will be used | string | |
**limit** | optional | Number of responses to include in the response | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.read_mask | string | | names,emailAddresses |
action_result.parameter.limit | numeric | | 100 |
action_result.data.\*.etag | string | | %EgcBAj0JPjcuGgMBBwg= |
action_result.data.\*.resourceName | string | `googlepeople resource name` | people/113211632970586460828 |
action_result.data.\*.names.\*.metadata.source.id | string | | 7c6136a10b0a9c93 |
action_result.data.\*.names.\*.metadata.source.type | string | | CONTACT |
action_result.data.\*.names.\*.metadata.primary | boolean | | True False |
action_result.data.\*.names.\*.givenName | string | | Test user |
action_result.data.\*.names.\*.familyName | string | | Test user |
action_result.data.\*.names.\*.displayName | string | | Test user |
action_result.data.\*.names.\*.unstructuredName | string | | Test user |
action_result.data.\*.names.\*.displayNameLastFirst | string | | Test, user |
action_result.data.\*.names.\*.middleName | string | | Test user |
action_result.data.\*.emailAddresses.\*.value | string | `email` | user@example.com |
action_result.data.\*.emailAddresses.\*.metadata.source.id | string | | 117111371020715649097 |
action_result.data.\*.emailAddresses.\*.metadata.source.type | string | | DOMAIN_PROFILE |
action_result.data.\*.emailAddresses.\*.metadata.primary | boolean | | True False |
action_result.data.\*.emailAddresses.\*.metadata.verified | boolean | | True False |
action_result.data.\*.emailAddresses.\*.type | string | | work |
action_result.data.\*.emailAddresses.\*.formattedType | string | | Work |
action_result.data.\*.phoneNumbers.\*.type | string | | work |
action_result.data.\*.phoneNumbers.\*.value | string | | |
action_result.data.\*.phoneNumbers.\*.metadata.source.id | string | | 107701908237315216077 |
action_result.data.\*.phoneNumbers.\*.metadata.source.type | string | | DOMAIN_PROFILE |
action_result.data.\*.phoneNumbers.\*.metadata.primary | boolean | | True |
action_result.data.\*.phoneNumbers.\*.formattedType | string | | Work |
action_result.status | string | | success failed |
action_result.message | string | | Successfully retrieved 7 peoples |
action_result.summary.total_people_returned | numeric | | 7 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get user profile'

Provides information about a person given account ID

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource_name** | required | Resource name of the person to provide info about | string | `googlepeople resource name` |
**person_fields** | optional | Comma-separated list of fields to be returned for the person | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.resource_name | string | `googlepeople resource name` | people/116919555361086422724 |
action_result.parameter.person_fields | string | | names,emailAddresses |
action_result.data.\*.metadata.sources.\*.id | string | | 7d369160095862fe |
action_result.data.\*.metadata.sources.\*.etag | string | | #JgTYM+ybUz4= |
action_result.data.\*.metadata.sources.\*.type | string | | CONTACT |
action_result.data.\*.metadata.sources.\*.updateTime | string | | 2020-08-04T23:06:55.492Z |
action_result.data.\*.metadata.objectType | string | | PERSON |
action_result.data.\*.etag | string | | %EgcBAj0JPjcuGgQBAgUH |
action_result.data.\*.names.\*.middleName | string | | Test user |
action_result.data.\*.names.\*.metadata.source.id | string | | 113211632970586460828 |
action_result.data.\*.names.\*.metadata.source.type | string | | PROFILE |
action_result.data.\*.names.\*.metadata.primary | boolean | | True False |
action_result.data.\*.names.\*.givenName | string | | Test user |
action_result.data.\*.names.\*.familyName | string | | Test user |
action_result.data.\*.names.\*.displayName | string | | Test user |
action_result.data.\*.names.\*.unstructuredName | string | | Test user |
action_result.data.\*.names.\*.displayNameLastFirst | string | | Test, user |
action_result.data.\*.names.\*.honorificSuffix | string | | Test |
action_result.data.\*.resourceName | string | `googlepeople resource name` | people/113211632970586460828 |
action_result.data.\*.emailAddresses.\*.type | string | | other |
action_result.data.\*.emailAddresses.\*.formattedType | string | | Other |
action_result.data.\*.emailAddresses.\*.value | string | `email` | user@example.com |
action_result.data.\*.emailAddresses.\*.metadata.source.id | string | | 116919555361086422724 |
action_result.data.\*.emailAddresses.\*.metadata.source.type | string | | DOMAIN_PROFILE |
action_result.data.\*.emailAddresses.\*.metadata.primary | boolean | | True False |
action_result.data.\*.emailAddresses.\*.metadata.verified | boolean | | True False |
action_result.status | string | | success failed |
action_result.message | string | | Successfully retrieved user profile |
action_result.summary.resource_id_returned | string | | people/113211632970586460828 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list people'

Lists authenticated user's contacts

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**person_fields** | optional | Comma-separated list of fields to be returned for each person. If not provided, default values will be used | string | |
**limit** | optional | Number of connections to include in the response | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.person_fields | string | | names,emailAddresses |
action_result.parameter.limit | numeric | | 100 |
action_result.data.\*.names.\*.metadata.source.id | string | | 7c6136a10b0a9c93 |
action_result.data.\*.names.\*.metadata.source.type | string | | CONTACT |
action_result.data.\*.names.\*.metadata.primary | boolean | | True False |
action_result.data.\*.names.\*.givenName | string | | Test user |
action_result.data.\*.names.\*.familyName | string | | Test user |
action_result.data.\*.names.\*.displayName | string | | Test user |
action_result.data.\*.names.\*.unstructuredName | string | | Test user |
action_result.data.\*.names.\*.displayNameLastFirst | string | | Test, user |
action_result.data.\*.names.\*.middleName | string | | Test user |
action_result.data.\*.etag | string | | %EgcBAj0JPjcuGgQBAgUHIgxYcEJzUVA3cmlaWT0= |
action_result.data.\*.resourceName | string | `googlepeople resource name` | people/c6275782728248360584 |
action_result.data.\*.emailAddresses.\*.type | string | | work |
action_result.data.\*.emailAddresses.\*.formattedType | string | | Work |
action_result.data.\*.emailAddresses.\*.value | string | `email` | user@example.com |
action_result.data.\*.emailAddresses.\*.metadata.source.id | string | | 57180f240cc67e88 |
action_result.data.\*.emailAddresses.\*.metadata.source.type | string | | CONTACT |
action_result.data.\*.emailAddresses.\*.metadata.primary | boolean | | True False |
action_result.data.\*.metadata.sources.\*.id | string | | 26162f4b8f0439b6 |
action_result.data.\*.metadata.sources.\*.etag | string | | #G/xJmvdEqkU= |
action_result.data.\*.metadata.sources.\*.type | string | | CONTACT |
action_result.data.\*.metadata.sources.\*.updateTime | string | | 2020-11-27T05:26:14.900Z |
action_result.data.\*.metadata.objectType | string | | PERSON |
action_result.data.\*.birthdays.\*.date.day | numeric | | 1 |
action_result.data.\*.birthdays.\*.date.year | numeric | | 1990 |
action_result.data.\*.birthdays.\*.date.month | numeric | | 1 |
action_result.data.\*.birthdays.\*.text | string | | 1990-01-01 |
action_result.data.\*.birthdays.\*.metadata.source.id | string | | 75b1dd3c0f20cb95 |
action_result.data.\*.birthdays.\*.metadata.source.type | string | | CONTACT |
action_result.data.\*.birthdays.\*.metadata.primary | boolean | | True |
action_result.status | string | | success failed |
action_result.message | string | | Successfully retrieved 15 users |
action_result.summary.total_people_returned | numeric | | 1 |
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
