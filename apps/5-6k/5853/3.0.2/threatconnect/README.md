# ThreatConnect

Publisher: Splunk <br>
Connector Version: 3.0.2 <br>
Product Vendor: ThreatConnect <br>
Product Name: ThreatConnect <br>
Minimum Product Version: 6.3.0

This app integrates with the ThreatConnect platform to provide various hunting actions in addition to threat ingestion

## Playbook Backward Compatibility

- In version 3.0.0 of the connector, the API endpoints were updated from V2 to V3. Additionally, below three new parameters were added to the actions **'hunt ip', 'hunt file', 'hunt email', 'hunt domain',** and **'hunt url'**:

  - **attribute** - Retrieves Indicator attributes (default: **false**).
  - **tag** - Retrieves Indicator tags (default: **false**).
  - **security label** - Retrieves Indicator security labels (default: **false**).

- As a result, the output data paths have been updated. To ensure your existing playbooks function correctly, please **update, reinsert, modify, or delete** the affected action blocks accordingly.

### Asset Configuration Update

- The **base_url** parameter in the asset configuration should be set according to your ThreatConnect instance. Examples:

  - `https://api.threatconnect.com`
  - `https://sandbox.threatconnect.com`
  - `https://companyabc.threatconnect.com/api`

- For more details, please refer to the [ThreatConnect API documentation](https://docs.threatconnect.com/en/latest/rest_api/quick_start.html#using-the-api).

### Configuration variables

This table lists the configuration variables required to operate ThreatConnect. These variables are specified when configuring a ThreatConnect asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**access_id** | required | string | Access ID |
**base_url** | required | string | Base URL for instance (e.g. https://api.threatconnect.com or https://companyabc.threatconnect.com/api) |
**secret_key** | required | password | Secret Key |
**max_containers** | optional | numeric | Max containers per poll |
**interval_days** | optional | numeric | Last 'N' Days to get data during 'Poll Now' and scheduled polling |
**verify_server_cert** | optional | boolean | Verify server cert |

### Supported Actions

[on poll](#action-on-poll) - Callback action for the on_poll ingest functionality <br>
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity <br>
[list owners](#action-list-owners) - List the owners visible with the configured credentials <br>
[post data](#action-post-data) - Create an indicator and post it to ThreatConnect <br>
[hunt ip](#action-hunt-ip) - Hunt an IP and retrieve any available information <br>
[hunt file](#action-hunt-file) - Hunt a file hash and retrieve available information <br>
[hunt email](#action-hunt-email) - Hunt an email and retrieve available information <br>
[hunt domain](#action-hunt-domain) - Hunt a domain and retrieve available information <br>
[hunt url](#action-hunt-url) - Hunt a URL and retrieve available information

## action: 'on poll'

Callback action for the on_poll ingest functionality

Type: **ingest** <br>
Read only: **True**

<p>Basic polling configuration is available within the asset configuration.  <b>On_poll</b>'s maximum ingested indicators is, by default, 100.  This can be found in the asset configuration under <b>max_containers</b>.  The other optional parameter in the asset configuration, <b>num_of_days</b>, specifies how old to start polling from during the first ingestion cycle.  The default value is 7 days.  This <b>num_of_days</b> parameter also affects when the Poll Now starts polling as well.</p><p>This action will start from the oldest indicator and create a container for each.</p><p>The following CEF fields will be created, depending upon the IOC type:</p><table><tr><th>IOC</th><th>Artifact Name</th><th>CEF Field</th></tr><tr><td>Address IPv4</td><td>IP Artifact</td><td>deviceAddress</td></tr><tr><td>Address IPv6</td><td>IP Artifact</td><td>deviceCustomIPv6Address1</td></tr><tr><td>Email</td><td>Email Address Artifact</td><td>emailAddress</td></tr><tr><td>File</td><td>File Artifact</td><td>fileHashMd5, fileHashSha1, fileHashSha256 (where applicable)</td></tr><tr><td>Host</td><td>Domain Artifact</td><td>DeviceDnsDomain</td></tr><tr><td>URL</td><td>URL Artifact</td><td>requestURL</td></tr><tr><td>CIDR IPv4</td><td>CIDR Artifact</td><td>deviceAddress (IP), cidrPrefix, cidr (CIDR)</td></tr><tr><td>Mutex</td><td>Mutex Artifact</td><td>mutex</td></tr><tr><td>Registry Key</td><td>Registry Key Artifact</td><td>registryKey (Registry Key Name), registryValue (Value Name), registryType (Value Type)</td></tr><tr><td>ASN</td><td>ASN Artifact</td><td>asn</td></tr><tr><td>User Agent</td><td>User Agent Artifact</td><td>requestClientApplication</td></tr></table><p>Additional CEF fields that all artifacts will have are:</p><table><tr><th>CEF Field</th><th>Description</th></tr><tr><td>deviceCustomDate1</td><td>Date Created</td></tr><tr><td>deviceCustomDate1Label</td><td>Label for above</td></tr><tr><td>deviceCustomDate2</td><td>Last Modified Date</td></tr><tr><td>deviceCustomDate2Label</td><td>Label for above</td></tr><tr><td>rating</td><td>Indicator rating</td></tr><tr><td>confidence</td><td>Indicator confidence</td></tr><tr><td>threatAssessRating</td><td>Threat Assessment rating</td></tr><tr><td>threatAssessConfidence</td><td>Threat Assessment Confidence</td></tr></table><p>Rating, confidence, threatAssessRating, and threatAssessConfidence will only be added if they are present within the indicator.</p><p>Any indicator that does not fall within any of the categories above is considered a custom indicator, and, as a result, will have a CEF field of 'cn1'.</p><p>It is also very important that the Maximum Container for scheduled polling configured should be greater than the maximum events that are generated per second. If the app detects it got the maximum configured events and all occurred in the same second, it will start polling from the next second in the next polling cycle.</p>

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'test connectivity'

Validate the asset configuration for connectivity

Type: **test** <br>
Read only: **True**

This action attempts to authenticate a GET request with the ThreatConnect API using a signature.

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list owners'

List the owners visible with the configured credentials

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.data.\*.id | numeric | | 11111797252348111 |
action_result.data.\*.data.\*.name | string | | TestUser |
action_result.data.\*.data.\*.type | string | | Organization |
action_result.data.\*.data.\*.permTag | string | | FULL |
action_result.data.\*.data.\*.permApps | string | | BUILD |
action_result.data.\*.data.\*.permPost | string | | FULL |
action_result.data.\*.data.\*.permTask | string | | FULL |
action_result.data.\*.data.\*.ownerRole | string | | Organization Administrator |
action_result.data.\*.data.\*.permGroup | string | | FULL |
action_result.data.\*.data.\*.permTrack | string | | FULL |
action_result.data.\*.data.\*.permUsers | string | | FULL |
action_result.data.\*.data.\*.permInvite | string | | FULL |
action_result.data.\*.data.\*.permVictim | string | | FULL |
action_result.data.\*.data.\*.permCaseTag | string | | FULL |
action_result.data.\*.data.\*.permComment | string | | FULL |
action_result.data.\*.data.\*.permMembers | string | | READ |
action_result.data.\*.data.\*.permPublish | string | | FULL |
action_result.data.\*.data.\*.permArtifact | string | | FULL |
action_result.data.\*.data.\*.permCopyData | string | | FULL |
action_result.data.\*.data.\*.permSettings | string | | FULL |
action_result.data.\*.data.\*.permTimeline | string | | FULL |
action_result.data.\*.data.\*.permAttribute | string | | FULL |
action_result.data.\*.data.\*.permIndicator | string | | FULL |
action_result.data.\*.data.\*.permPlaybooks | string | | FULL |
action_result.data.\*.data.\*.permAttributeType | string | | FULL |
action_result.data.\*.data.\*.permSecurityLabel | string | | FULL |
action_result.data.\*.data.\*.permPlaybooksExecute | string | | FULL |
action_result.data.\*.data.\*.permWorkflowTemplate | string | | FULL |
action_result.data.\*.count | numeric | | 1 |
action_result.data.\*.status | string | | Success |
action_result.summary.num_owners | numeric | | 16 |
action_result.summary.total_objects | numeric | | |
action_result.message | string | | List owners succeeded |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'post data'

Create an indicator and post it to ThreatConnect

Type: **generic** <br>
Read only: **False**

<p>This action will post an indicator back to the ThreatConnect platform. The only required field is <b>primary_field</b>. This parameter can be an IP address, an email, a hash (MD5, SHA-1, or SHA-256), a hostname, or a URL.</p><p>This action also allows for one to post multiple hashes into one indicator. To post multiple hashes to one indicator, put all the hashes in the <b>primary_field</b> separated by commas. An indicator can have a maximum of one MD5, one SHA-1, and one SHA-256 hash. If multiple hashes of the same type are entered into the primary field, such as multiple MD5 hashes, the last hash will be the only one posted.</p><p>All indicator types can take the optional parameters <b>rating</b> and <b>confidence</b>. The specialized optional parameters for files and hosts are below:</p>Files<ul><li>size</li></ul>Hosts<ul><li>dns_active</li><li>whois_active</li></ul><p>This action also allows for the addition of attributes to the specified indicator that is created. The attribute will only be created if both the <b>attribute_name</b> and the <b>attribute_value</b> values are populated. If attempting to write an attribute with a name that does not exist or apply to the indicator's type, the action will fail.</p><p>The data paths listed below are all the <i>possible</i> data paths, but they will differ based upon the given parameter in <b>primary_field</b>. The data paths will be of the form of <b>action_result.data.\*.[Indicator Type].\*</b>, where the Indicator Type is the type given to the parameter in <b>primary_field</b>. All file hashes will have the same Indicator Type. If one attempts to post an indicator that already exists on ThreatConnect, that indicator will be updated.</p>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**confidence** | optional | Analytic confidence (0 to 100) | numeric | |
**dns_active** | optional | Is DNS active | boolean | |
**primary_field** | required | IP, email, file hash, domain, or URL | string | `ip` `ipv6` `email` `hash` `md5` `sha1` `sha256` `domain` `url` |
**rating** | optional | Indicator rating (0 to 5) | numeric | |
**size** | optional | Size of file in bytes | numeric | |
**whois_active** | optional | Is WHOIS active | boolean | |
**attribute_name** | optional | Name of attribute to add | string | |
**attribute_value** | optional | Value of attribute to add | string | |
**tag** | optional | Name of Indicator Tag to add | string | |
**security_label** | optional | Name of Security Label to add | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.attribute_name | string | | |
action_result.parameter.attribute_value | string | | |
action_result.parameter.confidence | numeric | | 50 |
action_result.parameter.dns_active | boolean | | |
action_result.parameter.primary_field | string | `ip` `ipv6` `email` `hash` `md5` `sha1` `sha256` `domain` `url` | 80f7be8806019283777fdeed1ab09c4c |
action_result.parameter.rating | numeric | | 2 |
action_result.parameter.size | string | | |
action_result.parameter.tag | string | | |
action_result.parameter.security_label | string | | |
action_result.parameter.whois_active | boolean | | |
action_result.data.\*.data.id | numeric | | 1125800916204668 |
action_result.data.\*.data.md5 | string | `md5` | AAA0985A485969F70C0B414EF328DAAA |
action_result.data.\*.data.type | string | | File |
action_result.data.\*.data.active | boolean | | True False |
action_result.data.\*.data.ownerId | numeric | | 11111797252348111 |
action_result.data.\*.data.summary | string | `ip` `ipv6` `email` `hash` `md5` `sha1` `sha256` `domain` `url` | AAA0985A485969F70C0B414EF328DAAA |
action_result.data.\*.data.webLink | string | | https://testxyz.threatconnect.com/#/details/indicators/1125800916204668 |
action_result.data.\*.data.dateAdded | string | | 2025-03-07T10:32:16Z |
action_result.data.\*.data.ownerName | string | | TestUser |
action_result.data.\*.data.legacyLink | string | | https://testxyz.threatconnect.com/auth/indicators/details/file.xhtml?file=AAA0985A485969F70C0B414EF328DAAA&owner=TestUser |
action_result.data.\*.data.privateFlag | boolean | | True False |
action_result.data.\*.data.activeLocked | boolean | | True False |
action_result.data.\*.data.lastModified | string | | 2025-03-07T10:32:16Z |
action_result.data.\*.status | string | | Success |
action_result.data.\*.message | string | | Created |
action_result.data.\*.data.text | string | | http://www.test.ru |
action_result.data.\*.data.ip | string | `ip` `ipv6` | 17.5.7.8 |
action_result.data.\*.data.sha256 | string | `sha256` | AAAA30BA2F79F45ED475BA35205D6332ABF201830A4979355C53C66F3220AAAA |
action_result.data.\*.data.rating | numeric | | 2 |
action_result.data.\*.data.confidence | numeric | | 50 |
action_result.data.\*.data.hostName | string | `domain` | www.test.com |
action_result.data.\*.data.dnsActive | boolean | | True False |
action_result.data.\*.data.whoisActive | boolean | | True False |
action_result.data.\*.data.attributes.data.\*.id | numeric | | 2251700947844857 |
action_result.data.\*.data.attributes.data.\*.type | string | | Description |
action_result.data.\*.data.attributes.data.\*.value | string | | valid description |
action_result.data.\*.data.attributes.data.\*.pinned | boolean | | True False |
action_result.data.\*.data.attributes.data.\*.default | boolean | | True False |
action_result.data.\*.data.attributes.data.\*.createdBy.id | numeric | | 2251700814002001 |
action_result.data.\*.data.attributes.data.\*.createdBy.owner | string | | TestUser |
action_result.data.\*.data.attributes.data.\*.createdBy.lastName | string | | LastName |
action_result.data.\*.data.attributes.data.\*.createdBy.userName | string | | 11111797252345448111 |
action_result.data.\*.data.attributes.data.\*.createdBy.firstName | string | | FirstName |
action_result.data.\*.data.attributes.data.\*.createdBy.pseudonym | string | | APIUserYSRPA |
action_result.data.\*.data.attributes.data.\*.dateAdded | string | | 2025-03-07T13:26:22Z |
action_result.data.\*.data.attributes.data.\*.lastModified | string | | 2025-03-07T13:26:22Z |
action_result.data.\*.data.description | string | | valid description |
action_result.data.\*.data.address | string | | abcde@gmail.com |
action_result.data.\*.data.tags.data.\*.id | numeric | | 153484 |
action_result.data.\*.data.tags.data.\*.name | string | | 漢©ᇗḈ✔❤╬⎋ᾧ҈₯⅏⌛ï دગુж!@#$%^&\* |
action_result.data.\*.data.tags.data.\*.lastUsed | string | | 2025-03-07T13:26:28Z |
action_result.data.\*.data.securityLabels.data.\*.id | numeric | | 3 |
action_result.data.\*.data.securityLabels.data.\*.name | string | | TLP:AMBER |
action_result.data.\*.data.securityLabels.data.\*.color | string | | FFC000 |
action_result.data.\*.data.securityLabels.data.\*.owner | string | | System |
action_result.data.\*.data.securityLabels.data.\*.dateAdded | string | | 2016-08-31T00:00:00Z |
action_result.data.\*.data.securityLabels.data.\*.description | string | | This security label is used for information that requires support to be effectively acted upon, yet carries risks to privacy, reputation, or operations if shared outside of the organizations involved. Information with this label can be shared with members of an organization and its clients. |
action_result.data.\*.data.size | numeric | | 10 |
action_result.summary | string | | |
action_result.summary.attribute_added | boolean | | False True |
action_result.summary.indicator_created/updated | boolean | | False True |
action_result.summary.total_objects | numeric | | 1 |
action_result.message | string | | Data successfully posted to ThreatConnect |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'hunt ip'

Hunt an IP and retrieve any available information

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to hunt | string | `ip` `ipv6` |
**owner** | optional | Indicator Owner within ThreatConnect | string | |
**attribute** | optional | Retrieves Indicator attributes | boolean | |
**tag** | optional | Retrieves Indicator tags | boolean | |
**security_label** | optional | Retrieves Indicator security labels | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` `ipv6` | |
action_result.parameter.owner | string | | |
action_result.parameter.attribute | boolean | | |
action_result.parameter.tag | boolean | | |
action_result.parameter.security_label | boolean | | |
action_result.data.\*.status | string | | Success |
action_result.data.\*.data.\*.id | numeric | | 11111797252348111 |
action_result.data.\*.data.\*.ip | string | `ip` `ipv6` | 123.23.124.32 |
action_result.data.\*.data.\*.tags.data.\*.id | numeric | | 153676 |
action_result.data.\*.data.\*.tags.data.\*.name | string | | testing |
action_result.data.\*.data.\*.tags.data.\*.lastUsed | string | | 2025-03-08T09:35:46Z |
action_result.data.\*.data.\*.type | string | | Address |
action_result.data.\*.data.\*.active | boolean | | True False |
action_result.data.\*.data.\*.rating | numeric | | 3 |
action_result.data.\*.data.\*.ownerId | numeric | | 11111797252348111 |
action_result.data.\*.data.\*.summary | string | `ip` `ipv6` | 123.23.124.32 |
action_result.data.\*.data.\*.webLink | string | `url` | https://testxyz.threatconnect.com/#/details/indicators/11111797252348111 |
action_result.data.\*.data.\*.dateAdded | string | | 2025-03-08T09:35:46Z |
action_result.data.\*.data.\*.ownerName | string | | TestUser |
action_result.data.\*.data.\*.attributes.data.\*.id | numeric | | 11111797252348111 |
action_result.data.\*.data.\*.attributes.data.\*.type | string | | Description |
action_result.data.\*.data.\*.attributes.data.\*.value | string | | This is testing data |
action_result.data.\*.data.\*.attributes.data.\*.pinned | boolean | | True False |
action_result.data.\*.data.\*.attributes.data.\*.default | boolean | | True False |
action_result.data.\*.data.\*.attributes.data.\*.createdBy.id | numeric | | 11111797252348111 |
action_result.data.\*.data.\*.attributes.data.\*.createdBy.owner | string | | TestUser |
action_result.data.\*.data.\*.attributes.data.\*.createdBy.lastName | string | | lab |
action_result.data.\*.data.\*.attributes.data.\*.createdBy.userName | string | | 11111797252345448111 |
action_result.data.\*.data.\*.attributes.data.\*.createdBy.firstName | string | | test |
action_result.data.\*.data.\*.attributes.data.\*.createdBy.pseudonym | string | | APIUserYSRPA |
action_result.data.\*.data.\*.attributes.data.\*.dateAdded | string | | 2025-03-08T09:35:46Z |
action_result.data.\*.data.\*.attributes.data.\*.lastModified | string | | 2025-03-08T09:35:46Z |
action_result.data.\*.data.\*.confidence | numeric | | 23 |
action_result.data.\*.data.\*.legacyLink | string | | https://testxyz.threatconnect.com/auth/indicators/details/address.xhtml?address=123.23.124.32&owner=TestUser |
action_result.data.\*.data.\*.description | string | | This is testing data |
action_result.data.\*.data.\*.privateFlag | boolean | | True False |
action_result.data.\*.data.\*.activeLocked | boolean | | True False |
action_result.data.\*.data.\*.lastModified | string | | 2025-03-08T09:35:46Z |
action_result.data.\*.data.\*.securityLabels.data.\*.id | numeric | | 3 |
action_result.data.\*.data.\*.securityLabels.data.\*.name | string | | TLP:AMBER |
action_result.data.\*.data.\*.securityLabels.data.\*.color | string | | FFC000 |
action_result.data.\*.data.\*.securityLabels.data.\*.owner | string | | System |
action_result.data.\*.data.\*.securityLabels.data.\*.dateAdded | string | | 2016-08-31T00:00:00Z |
action_result.data.\*.data.\*.securityLabels.data.\*.description | string | | This security label is used for information that requires support to be effectively acted upon, yet carries risks to privacy, reputation, or operations if shared outside of the organizations involved. Information with this label can be shared with members of an organization and its clients. |
action_result.summary.total_objects | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'hunt file'

Hunt a file hash and retrieve available information

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | File hash (md5, sha1, sha256) | string | `hash` `md5` `sha1` `sha256` |
**owner** | optional | Indicator Owner within ThreatConnect | string | |
**attribute** | optional | Retrieves Indicator attributes | boolean | |
**tag** | optional | Retrieves Indicator tags | boolean | |
**security_label** | optional | Retrieves Indicator security labels | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.hash | string | `hash` `md5` `sha1` `sha256` | |
action_result.parameter.owner | string | | |
action_result.parameter.attribute | boolean | | |
action_result.parameter.tag | boolean | | |
action_result.parameter.security_label | boolean | | |
action_result.data.\*.data.\*.id | numeric | | 1111799822086111 |
action_result.data.\*.data.\*.md5 | string | `md5` | AAAAF2DB1295FA419B190BD7478DAAAA |
action_result.data.\*.data.\*.type | string | | File |
action_result.data.\*.data.\*.active | boolean | | True False |
action_result.data.\*.data.\*.rating | numeric | | 5 |
action_result.data.\*.data.\*.ownerId | numeric | | 11111797252348111 |
action_result.data.\*.data.\*.summary | string | `hash` `md5` `sha1` `sha256` | AAAAF2DB1295FA419B190BD7478DAAAA |
action_result.data.\*.data.\*.webLink | string | `url` | https://testxyz.threatconnect.com/#/details/indicators/1111799822086111 |
action_result.data.\*.data.\*.dateAdded | string | | 2025-03-05T13:28:46Z |
action_result.data.\*.data.\*.ownerName | string | | TestUser |
action_result.data.\*.data.\*.confidence | numeric | | 50 |
action_result.data.\*.data.\*.legacyLink | string | | https://testxyz.threatconnect.com/auth/indicators/details/file.xhtml?file=AAAAF2DB1295FA419B190BD7478DAAAA&owner=TestUser |
action_result.data.\*.data.\*.privateFlag | boolean | | True False |
action_result.data.\*.data.\*.activeLocked | boolean | | True False |
action_result.data.\*.data.\*.lastModified | string | | 2025-03-05T13:28:46Z |
action_result.data.\*.status | string | | Success |
action_result.summary.total_objects | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'hunt email'

Hunt an email and retrieve available information

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**email** | required | Email address | string | `email` |
**owner** | optional | Indicator Owner within ThreatConnect | string | |
**attribute** | optional | Retrieves Indicator attributes | boolean | |
**tag** | optional | Retrieves Indicator tags | boolean | |
**security_label** | optional | Retrieves Indicator security labels | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.email | string | `email` | |
action_result.parameter.owner | string | | |
action_result.parameter.attribute | boolean | | |
action_result.parameter.tag | boolean | | |
action_result.parameter.security_label | boolean | | |
action_result.data.\*.data.\*.id | numeric | | 1111899916230111 |
action_result.data.\*.data.\*.tags.data.\*.id | numeric | | 153676 |
action_result.data.\*.data.\*.tags.data.\*.name | string | | testing |
action_result.data.\*.data.\*.rating | numeric | | 4 |
action_result.data.\*.data.\*.confidence | numeric | | 24 |
action_result.data.\*.data.\*.tags.data.\*.lastUsed | string | | 2025-03-08T10:06:59Z |
action_result.data.\*.data.\*.type | string | | EmailAddress |
action_result.data.\*.data.\*.active | boolean | | True False |
action_result.data.\*.data.\*.address | string | `email` | abcxyz@test.com |
action_result.data.\*.data.\*.ownerId | numeric | | 11111797252348111 |
action_result.data.\*.data.\*.summary | string | `email` | abcxyz@test.com |
action_result.data.\*.data.\*.webLink | string | `url` | https://testxyz.threatconnect.com/#/details/indicators/1111899916230111 |
action_result.data.\*.data.\*.dateAdded | string | | 2025-03-08T10:06:59Z |
action_result.data.\*.data.\*.ownerName | string | | TestUser |
action_result.data.\*.data.\*.attributes.data.\*.id | numeric | | 1111900049338111 |
action_result.data.\*.data.\*.attributes.data.\*.type | string | | Description |
action_result.data.\*.data.\*.attributes.data.\*.value | string | | only_value_provided |
action_result.data.\*.data.\*.attributes.data.\*.pinned | boolean | | True False |
action_result.data.\*.data.\*.attributes.data.\*.default | boolean | | True False |
action_result.data.\*.data.\*.attributes.data.\*.createdBy.id | numeric | | 11111797252348111 |
action_result.data.\*.data.\*.attributes.data.\*.createdBy.owner | string | | TestUser |
action_result.data.\*.data.\*.attributes.data.\*.createdBy.lastName | string | | lab |
action_result.data.\*.data.\*.attributes.data.\*.createdBy.userName | string | | 11111797252345448111 |
action_result.data.\*.data.\*.attributes.data.\*.createdBy.firstName | string | | test |
action_result.data.\*.data.\*.attributes.data.\*.createdBy.pseudonym | string | | APIUserYSRPA |
action_result.data.\*.data.\*.attributes.data.\*.dateAdded | string | | 2025-03-08T10:06:59Z |
action_result.data.\*.data.\*.attributes.data.\*.lastModified | string | | 2025-03-08T10:06:59Z |
action_result.data.\*.data.\*.legacyLink | string | | https://testxyz.threatconnect.com/auth/indicators/details/emailaddress.xhtml?emailaddress=wp-security%40hotmail.com&owner=TestUser |
action_result.data.\*.data.\*.description | string | | only_value_provided |
action_result.data.\*.data.\*.privateFlag | boolean | | True False |
action_result.data.\*.data.\*.activeLocked | boolean | | True False |
action_result.data.\*.data.\*.lastModified | string | | 2025-03-08T10:06:59Z |
action_result.data.\*.data.\*.securityLabels.data.\*.id | numeric | | 3 |
action_result.data.\*.data.\*.securityLabels.data.\*.name | string | | TLP:AMBER |
action_result.data.\*.data.\*.securityLabels.data.\*.color | string | | FFC000 |
action_result.data.\*.data.\*.securityLabels.data.\*.owner | string | | System |
action_result.data.\*.data.\*.securityLabels.data.\*.dateAdded | string | | 2016-08-31T00:00:00Z |
action_result.data.\*.data.\*.securityLabels.data.\*.description | string | | This security label is used for information that requires support to be effectively acted upon, yet carries risks to privacy, reputation, or operations if shared outside of the organizations involved. Information with this label can be shared with members of an organization and its clients. |
action_result.data.\*.status | string | | Success |
action_result.summary.total_objects | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'hunt domain'

Hunt a domain and retrieve available information

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain or URL name | string | `url` `domain` |
**owner** | optional | Indicator Owner within ThreatConnect | string | |
**attribute** | optional | Retrieves Indicator attributes | boolean | |
**tag** | optional | Retrieves Indicator tags | boolean | |
**security_label** | optional | Retrieves Indicator security labels | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain | string | `url` `domain` | |
action_result.parameter.owner | string | | |
action_result.parameter.attribute | boolean | | |
action_result.parameter.tag | boolean | | |
action_result.parameter.security_label | boolean | | |
action_result.data.\*.status | string | | Success |
action_result.data.\*.data.\*.id | numeric | | 1111900049338111 |
action_result.data.\*.data.\*.type | string | | Host |
action_result.data.\*.data.\*.active | boolean | | True False |
action_result.data.\*.data.\*.rating | numeric | | 2 |
action_result.data.\*.data.\*.ownerId | numeric | | 11111797252348111 |
action_result.data.\*.data.\*.summary | string | `url` `domain` | vclub.credit |
action_result.data.\*.data.\*.webLink | string | `url` | https://testxyz.threatconnect.com/#/details/indicators/1111900049338111 |
action_result.data.\*.data.\*.hostName | string | `domain` | vclub.credit |
action_result.data.\*.data.\*.dateAdded | string | | 2025-03-08T06:44:39Z |
action_result.data.\*.data.\*.dnsActive | boolean | | True False |
action_result.data.\*.data.\*.ownerName | string | | TestUser |
action_result.data.\*.data.\*.confidence | numeric | | 63 |
action_result.data.\*.data.\*.legacyLink | string | | https://testxyz.threatconnect.com/auth/indicators/details/host.xhtml?host=vclub.credit&owner=TestUser |
action_result.data.\*.data.\*.privateFlag | boolean | | True False |
action_result.data.\*.data.\*.whoisActive | boolean | | True False |
action_result.data.\*.data.\*.activeLocked | boolean | | True False |
action_result.data.\*.data.\*.lastModified | string | | 2025-03-08T06:44:39Z |
action_result.data.\*.data.\*.tags.data.\*.id | numeric | | 153676 |
action_result.data.\*.data.\*.tags.data.\*.name | string | | testing |
action_result.data.\*.data.\*.tags.data.\*.lastUsed | string | | 2025-03-08T09:37:02Z |
action_result.data.\*.data.\*.attributes.data.\*.id | numeric | | 1111900049338111 |
action_result.data.\*.data.\*.attributes.data.\*.type | string | | Description |
action_result.data.\*.data.\*.attributes.data.\*.value | string | | This is testing data |
action_result.data.\*.data.\*.attributes.data.\*.pinned | boolean | | True False |
action_result.data.\*.data.\*.attributes.data.\*.default | boolean | | True False |
action_result.data.\*.data.\*.attributes.data.\*.createdBy.id | numeric | | 11111797252348111 |
action_result.data.\*.data.\*.attributes.data.\*.createdBy.owner | string | | TestUser |
action_result.data.\*.data.\*.attributes.data.\*.createdBy.lastName | string | | lab |
action_result.data.\*.data.\*.attributes.data.\*.createdBy.userName | string | | 11111797252345448111 |
action_result.data.\*.data.\*.attributes.data.\*.createdBy.firstName | string | | test |
action_result.data.\*.data.\*.attributes.data.\*.createdBy.pseudonym | string | | APIUserYSRPA |
action_result.data.\*.data.\*.attributes.data.\*.dateAdded | string | | 2025-03-08T09:37:02Z |
action_result.data.\*.data.\*.attributes.data.\*.lastModified | string | | 2025-03-08T09:37:02Z |
action_result.data.\*.data.\*.description | string | | This is testing data |
action_result.data.\*.data.\*.securityLabels.data.\*.id | numeric | | 3 |
action_result.data.\*.data.\*.securityLabels.data.\*.name | string | | TLP:AMBER |
action_result.data.\*.data.\*.securityLabels.data.\*.color | string | | FFC000 |
action_result.data.\*.data.\*.securityLabels.data.\*.owner | string | | System |
action_result.data.\*.data.\*.securityLabels.data.\*.dateAdded | string | | 2016-08-31T00:00:00Z |
action_result.data.\*.data.\*.securityLabels.data.\*.description | string | | This security label is used for information that requires support to be effectively acted upon, yet carries risks to privacy, reputation, or operations if shared outside of the organizations involved. Information with this label can be shared with members of an organization and its clients. |
action_result.summary.total_objects | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'hunt url'

Hunt a URL and retrieve available information

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL to find | string | `url` |
**owner** | optional | Indicator Owner within ThreatConnect | string | |
**attribute** | optional | Retrieves Indicator attributes | boolean | |
**tag** | optional | Retrieves Indicator tags | boolean | |
**security_label** | optional | Retrieves Indicator security labels | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.owner | string | | |
action_result.parameter.url | string | `url` | |
action_result.parameter.attribute | boolean | | |
action_result.parameter.tag | boolean | | |
action_result.parameter.security_label | boolean | | |
action_result.data.\*.data.\*.id | numeric | | 2251799822191373 |
action_result.data.\*.data.\*.text | string | `url` | http://www.test.com/list/oz/ |
action_result.data.\*.data.\*.type | string | | URL |
action_result.data.\*.data.\*.active | boolean | | True False |
action_result.data.\*.data.\*.ownerId | numeric | | 11111797252348111 |
action_result.data.\*.data.\*.summary | string | | http://www.test.com/list/oz/ |
action_result.data.\*.data.\*.webLink | string | `url` | https://testxyz.threatconnect.com/#/details/indicators/2251799822191373 |
action_result.data.\*.data.\*.dateAdded | string | | 2025-03-07T12:16:05Z |
action_result.data.\*.data.\*.ownerName | string | | TestUser |
action_result.data.\*.data.\*.legacyLink | string | | https://testxyz.threatconnect.com/auth/indicators/details/url.xhtml?orgid=2251799822191373&owner=TestUser |
action_result.data.\*.data.\*.privateFlag | boolean | | True False |
action_result.data.\*.data.\*.activeLocked | boolean | | True False |
action_result.data.\*.data.\*.lastModified | string | | 2025-03-07T12:16:05Z |
action_result.data.\*.status | string | | Success |
action_result.data.\*.data.\*.rating | numeric | | 1 |
action_result.data.\*.data.\*.confidence | numeric | | 60 |
action_result.summary.total_objects | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

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
