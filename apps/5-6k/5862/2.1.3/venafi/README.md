# Venafi

Publisher: Splunk <br>
Connector Version: 2.1.3 <br>
Product Vendor: Venafi <br>
Product Name: Venafi <br>
Minimum Product Version: 6.1.1

This app integrates with an instance of Venafi to perform generic and investigative actions

### Configuration variables

This table lists the configuration variables required to operate Venafi. These variables are specified when configuring a Venafi asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Venafi API URL |
**username** | required | string | Venafi API Username to authenticate with |
**password** | required | password | Venafi API Password to authenticate with |
**client_id** | required | string | API Application Integration application ID |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[list policies](#action-list-policies) - Returns a list of all policies in Venafi <br>
[create certificate](#action-create-certificate) - Enrolls a certificate in Venafi <br>
[list certificates](#action-list-certificates) - Returns a list of certificates in Venafi <br>
[renew certificate](#action-renew-certificate) - Requests immediate renewal for an existing certificate in Venafi <br>
[revoke certificate](#action-revoke-certificate) - Requests to revoke an existing certificate in Venafi <br>
[get certificate](#action-get-certificate) - Downloads specified certificate to the vault

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list policies'

Returns a list of all policies in Venafi

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.AbsoluteGUID | string | | {TESTe447-74f4-4c8a-8972-62aff3b2fee3}{EXAMPLE63f4-0bfc-468a-b41f-d8fa477bd1c0}{EXAMPLEaa0-1de7-4be4-bfe8-fbcb7e948502}{TESTbb4b-1cde-4d48-9684-a04effa3be7f} |
action_result.data.\*.DN | string | `venafi policy dn` | \\VED\\Policy\\Certificates\\test |
action_result.data.\*.GUID | string | | {TESTbb4b-1cde-4d48-9684-a04effa3be7f} |
action_result.data.\*.Id | numeric | | 2139 |
action_result.data.\*.Name | string | | Test |
action_result.data.\*.Parent | string | | \\VED\\Policy\\Certificates |
action_result.data.\*.Revision | numeric | | 636747885144784172 |
action_result.data.\*.TypeName | string | | Policy |
action_result.summary.num_policies | numeric | | 3 |
action_result.message | string | | Num policies: 3 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create certificate'

Enrolls a certificate in Venafi

Type: **generic** <br>
Read only: **False**

Either Subject or ObjectName parameter must be filled out.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_dn** | required | The folder DN for the new certificate | string | `venafi policy dn` |
**subject** | optional | The Common Name (CN) field for the certificate. Either the subject or object_name parameter must be filled in | string | |
**object_name** | optional | The Common Name (CN) field for the certificate. Either the subject or object_name parameter must be filled in | string | |
**approvers** | optional | An array of one or more identities for certificate workflow approvers | string | |
**cadn** | optional | The Distinguished Name (DN) of the Trust Protection Platform Certificate Authority Template object | string | |
**ca_specific_attributes** | optional | An array of name/value pairs providing any CA attributes to be stored with the Certificate object and submitted to the CA during enrollment | string | |
**city** | optional | Locality/City attribute of Certificate | string | |
**contacts** | optional | An array of one or more identities for users or groups who receive notifications about events pertaining to the object | string | |
**country** | optional | The Country field for the certificate Subject DN | string | |
**created_by** | optional | The setting to identify the object that initiated enrollment or provisioning changes | string | |
**devices** | optional | An array of devices that require enrollment or provisioning | string | |
**disable_automatic_renewal** | optional | The setting to control whether manual intervention is required for certificate renewal | boolean | |
**elliptical_curve** | optional | P256, P384, or P521 encryption for Elliptical Curve Cryptography | string | |
**key_algorithm** | optional | Algorithm for public key of Certificate | string | |
**key_bit_size** | optional | The number of bits to allow for key generation | numeric | |
**management_type** | optional | The level of management that Trust Protection Platform applies to the certificate | string | |
**organization** | optional | Organization attribute of the certificate | string | |
**organizational_unit** | optional | Organizational unit attribute of the certificate | string | |
**pkcs10** | optional | The PKCS10 formatted CSR for the certificate | string | |
**reenable** | optional | Option to renew a previously disabled certificate | boolean | |
**set_work_to_do** | optional | Option to control certificate processing | boolean | |
**state** | optional | State/Province attribute of Certificate | string | |
**subject_alt_names** | optional | Skip parameter if the policy already specifies SAN Types. Array of subject alternative names (SANS) for the certificate. For each SAN, specify an array element with a Type and a corresponding Name. For example, SubjectAltNames:[ {Type:2, Name:www.example.com}, {Type:7, Name:122.122.122.122} ]. The Type parameter is an integer that represents the kind of SAN which can be 0:OtherName, 1: Email, 2:DNS, 6: URI, or 7:IPAddress. The Name value is the SAN Friendly name that corresponds to the Type parameter | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.approvers | string | | [{"PrefixedUniversal":"local:test"}] |
action_result.parameter.ca_specific_attributes | string | | [{"Adaptable CA":"Validity Period"}] |
action_result.parameter.cadn | string | | \\VED\\Policy\\Partner Dev\\TLS\\Certificates\\Testing\\tpp.testdemo.com |
action_result.parameter.city | string | | London |
action_result.parameter.contacts | string | | [{"PrefixedUniversal":"local:testuser"}] |
action_result.parameter.country | string | | US |
action_result.parameter.created_by | string | | admin |
action_result.parameter.devices | string | | |
action_result.parameter.disable_automatic_renewal | boolean | | True False |
action_result.parameter.elliptical_curve | string | | P256 |
action_result.parameter.key_algorithm | string | | RSA |
action_result.parameter.key_bit_size | numeric | | 2048 |
action_result.parameter.management_type | string | | Monitoring |
action_result.parameter.object_name | string | | splk.com |
action_result.parameter.organization | string | | Venafi, Inc. |
action_result.parameter.organizational_unit | string | | Sales |
action_result.parameter.pkcs10 | string | | |
action_result.parameter.policy_dn | string | `venafi policy dn` | \\VED\\Policy\\Certificates\\Test |
action_result.parameter.reenable | boolean | | True False |
action_result.parameter.set_work_to_do | boolean | | True False |
action_result.parameter.state | string | | Ohio |
action_result.parameter.subject | string | | splk.com |
action_result.parameter.subject_alt_names | string | | [{"TypeName":"2", "Name":"www.example.com"}, {"TypeName":"7", "Name":"9.5.45.11"}] |
action_result.data.\*.CertificateDN | string | `venafi certificate dn` | \\VED\\Policy\\Certificates\\test\\test.com |
action_result.data.\*.Guid | string | | TEST6419-8615-40ce-b556-63EXAMPLEe833b |
action_result.summary.status | string | | Successfully added certificate |
action_result.message | string | | Status: Successfully added certificate |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list certificates'

Returns a list of certificates in Venafi

Type: **investigate** <br>
Read only: **True**

Returns certificate details and the total number of certificates that match specified search filters.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**limit** | optional | Maximum number of certificates to return. Possible values are 1-100 | numeric | |
**offset** | optional | Number of results to skip (offset=5 begins results at page five) | numeric | |
**country** | optional | Country attribute of Certificate | string | |
**common_name** | optional | Common name attribute of Certificate | string | `domain` `url` |
**key_algorithm** | optional | Algorithm for public key of Certificate | string | |
**key_size** | optional | Public key size of Certificate | numeric | |
**key_size_greater** | optional | Find certificates with a key size greater than the specified value | numeric | |
**key_size_less** | optional | Find certificates with a key size less than the specified value | numeric | |
**city** | optional | Locality/City attribute of Certificate | string | |
**organization** | optional | Organization attribute of Certificate | string | |
**organization_unit** | optional | Organization unit attribute of Certificate | string | |
**state** | optional | State/Province attribute of Certificate | string | |
**san_dns** | optional | Subject Alternative Name (SAN) Distinguished Name Server (DNS) attribute of Certificate | string | `domain` `url` |
**san_email** | optional | Subject Alternative Name (SAN) Email RFC822 attribute of Certificate | string | `email` |
**san_ip** | optional | Subject Alternative Name (SAN) IP Address attribute of Certificate | string | `ip` |
**san_upn** | optional | Subject Alternative Name (SAN) User Principle Name (UPN) attribute of Certificate | string | `email` |
**san_uri** | optional | Subject Alternative Name (SAN) Uniform Resource Identifier (URI) attribute of Certificate | string | `url` |
**serial** | optional | Serial number attribute of Certificate | string | |
**signature_algorithm** | optional | Algorithm used to sign the Certificate | string | |
**thumbprint** | optional | SHA-1 thumbprint of the Certificate | string | `sha1` |
**valid_from** | optional | YYYY-MM-DD or ISO 8601 format YYYY-MM-DDTHH:MM:SS.mmmmmmmZ (Find certificates by the date of issue) | string | |
**valid_to** | optional | YYYY-MM-DD or ISO 8601 format YYYY-MM-DDTHH:MM:SS.mmmmmmmZ (Find certificates by expiration date) | string | |
**valid_to_greater** | optional | YYYY-MM-DD or ISO 8601 format YYYY-MM-DDTHH:MM:SS.mmmmmmmZ (Find certificates that expire after a certain date) | string | |
**valid_to_less** | optional | YYYY-MM-DD or ISO 8601 format YYYY-MM-DDTHH:MM:SS.mmmmmmmZ (Find certificates that expire before a certain date) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.city | string | | London |
action_result.parameter.common_name | string | `domain` `url` | tpp.testdemo.com |
action_result.parameter.country | string | | US |
action_result.parameter.key_algorithm | string | | RSA |
action_result.parameter.key_size | numeric | | 2048 |
action_result.parameter.key_size_greater | numeric | | 2048 |
action_result.parameter.key_size_less | numeric | | 2048 |
action_result.parameter.limit | numeric | | 20 |
action_result.parameter.offset | numeric | | 0 |
action_result.parameter.organization | string | | Venafi, Inc. |
action_result.parameter.organization_unit | string | | Sales |
action_result.parameter.san_dns | string | `domain` `url` | testdemo.com |
action_result.parameter.san_email | string | `email` | example@test.com |
action_result.parameter.san_ip | string | `ip` | 8.8.8.8 |
action_result.parameter.san_upn | string | `email` | test@example.com |
action_result.parameter.san_uri | string | `url` | https://www.example.com |
action_result.parameter.serial | string | | 2F0000009D4E9635EFF0E758CB00000000009D |
action_result.parameter.signature_algorithm | string | | sha256RSA |
action_result.parameter.state | string | | Ohio |
action_result.parameter.thumbprint | string | `sha1` | |
action_result.parameter.valid_from | string | | 2020-02-28 |
action_result.parameter.valid_to | string | | 2019-01-31 |
action_result.parameter.valid_to_greater | string | | 2021-04-31 |
action_result.parameter.valid_to_less | string | | 2020-02-23 |
action_result.parameter.valid_to_less | string | | 2020-03-16 |
action_result.data.\*.CreatedOn | string | | 2018-10-26T15:30:01.6903192Z |
action_result.data.\*.DN | string | `venafi certificate dn` | \\VED\\Policy\\Certificates\\test\\Venafi Generated\\example.venafi.com |
action_result.data.\*.Guid | string | | {TEST27f9-938f-42fe-a1a6-475afdc5TEST} |
action_result.data.\*.Name | string | | example.test.com |
action_result.data.\*.ParentDn | string | | \\VED\\Policy\\Certificates\\test\\Venafi Generated |
action_result.data.\*.SchemaClass | string | | X509 Server Certificate |
action_result.data.\*.X509.CN | string | | example.venafi.com |
action_result.data.\*.X509.SANS.DNS | string | | CSR1 |
action_result.data.\*.X509.SANS.Email.\* | string | `email` | test@123.com |
action_result.data.\*.X509.Serial | string | | TEST5338000100009FA9 |
action_result.data.\*.X509.Thumbprint | string | `sha1` | TEST15E5C9664FF67587A24BFA0CC87BA8C66B87 |
action_result.data.\*.X509.ValidFrom | string | | 2019-03-28T22:39:49.0000000Z |
action_result.data.\*.X509.ValidTo | string | | 2020-03-27T22:39:49.0000000Z |
action_result.data.\*.\_links.\*.Details | string | | /vedsdk/certificates/%TEST5827f9-938f-42fe-a1a6-475afdc51448%7d |
action_result.summary.num_certificates | numeric | | 20 |
action_result.message | string | | Num certificates: 20 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'renew certificate'

Requests immediate renewal for an existing certificate in Venafi

Type: **generic** <br>
Read only: **False**

A renewable certificate cannot be currently processing, in error, or contain a 'Monitoring' Management Type.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**certificate_dn** | required | The Distinguished Name (DN) of the certificate to renew | string | `venafi certificate dn` |
**pkcs10** | optional | The PKCS10 formatted CSR to use for the renewal | string | |
**reenable** | optional | Option to renew a previously disabled certificate | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.certificate_dn | string | `venafi certificate dn` | \\VED\\Policy\\Certificates\\test\\Venafi Generated\\example.venafi.com |
action_result.parameter.pkcs10 | string | | |
action_result.parameter.reenable | boolean | | True False |
action_result.data.\*.Success | boolean | | True False |
action_result.summary.status | string | | Successfully renewed certificate |
action_result.message | string | | Status: Successfully renewed certificate |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'revoke certificate'

Requests to revoke an existing certificate in Venafi

Type: **correct** <br>
Read only: **False**

The caller must have write permissions to the certificate object and either the CertificateDN or the Thumbprint parameter must be provided.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**certificate_dn** | optional | The Distinguished Name (DN) of the certificate to revoke | string | `venafi certificate dn` |
**thumbprint** | optional | The thumbprint (hash) of the certificate to revoke | string | `sha1` |
**reason** | optional | The reason for revocation of the certificate. 0: None, 1: User key compromised, 2: CA key compromised, 3: User changed affiliation, 4: Certificate superseded, 5: Original use no longer valid | numeric | |
**comments** | optional | Details about why the certificate is being revoked | string | |
**disable** | optional | The setting to manage the certificate upon revocation. If true, the certificate is disabled and no new certificate may replace it. If false, the certificate is allowed to be replaced by a new certificate | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.certificate_dn | string | `venafi certificate dn` | \\VED\\Policy\\Certificates\\test\\shiba.com |
action_result.parameter.comments | string | | Please refer to test generated certificates |
action_result.parameter.disable | boolean | | True False |
action_result.parameter.reason | numeric | | 3 |
action_result.parameter.thumbprint | string | `sha1` | TESTCDA4F588CFC22DB0F407A8A85D79B088TEST |
action_result.data.\*.Requested | boolean | | True False |
action_result.data.\*.Revoked | boolean | | True False |
action_result.data.\*.Success | boolean | | True False |
action_result.data.\*.Warning | string | | Revocation is already completed. The certificate "\\VED\\Policy\\Partner Dev\\TLS\\Certificates\\Testing\\testfriendlyname2" revocation was requested by another request or process. |
action_result.summary.status | string | | |
action_result.message | string | | Error from server. Status Code: 403 Data from server: {"Error":"Failed to revoke certificate; no permission."} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 0 |

## action: 'get certificate'

Downloads specified certificate to the vault

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**certificate_dn** | required | The Distinguished Name (DN) of the certificate to download | string | `venafi certificate dn` |
**format** | optional | The certificate format for the return data | string | |
**friendly_name** | optional | The label or alias to use for Base64, JKS, or PKCS #12 formats. Required for the JKS format | string | |
**include_chain** | optional | When the Format is Base64, PKCS #7, PKCS #12, or JKS, you can include the parent or root chain in the return data | boolean | |
**include_private_key** | optional | When the Format is Base64, PKCS #12, or JKS, you can specify whether to return the private key | boolean | |
**keystore_password** | optional | If the Format is JKS, you must set a keystore password. Use the same requirements as required for the Password parameter | string | |
**password** | optional | If the IncludePrivateKey value is true, you must create a password. Password must be 12 characters and comprised of at least 3 of the following: uppercase alphabetic letters, lowercase alphabetic letters, numeric characters, special characters | string | |
**root_first_order** | optional | The order of the certificate chain to trust | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.certificate_dn | string | `venafi certificate dn` | \\VED\\Policy\\Certificates\\test\\testing Generated\\pge.com |
action_result.parameter.format | string | | Base64 |
action_result.parameter.friendly_name | string | | tpp.exampledemo.com |
action_result.parameter.include_chain | boolean | | True False |
action_result.parameter.include_private_key | boolean | | True False |
action_result.parameter.keystore_password | string | | |
action_result.parameter.password | string | | |
action_result.parameter.root_first_order | boolean | | True False |
action_result.data.\*.name | string | | pge.com.cer |
action_result.data.\*.size | numeric | | 2074 |
action_result.data.\*.vault_id | string | `sha1` `vault id` | TEST86f38c9e7c50c1998c0ce0974faab4c9TEST |
action_result.summary.status | string | | Successfully retrieved certificate and downloaded it to vault |
action_result.message | string | | Status: Successfully retrieved certificate and downloaded it to vault |
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
