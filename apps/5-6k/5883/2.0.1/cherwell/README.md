# Cherwell

Publisher: Splunk Community \
Connector Version: 2.0.1 \
Product Vendor: Cherwell Software \
Product Name: Cherwell \
Minimum Product Version: 5.2.0

This app implements various ticketing actions on Cherwell

### Configuration variables

This table lists the configuration variables required to operate Cherwell. These variables are specified when configuring a Cherwell asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**api_url** | required | string | API URL |
**username** | required | string | Username |
**password** | required | password | Password |
**client_id** | required | string | Client ID |
**timeout** | optional | numeric | Request timeout in seconds |
**verify_server_cert** | optional | boolean | Verify server certificate |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[list users](#action-list-users) - Get a list of users \
[get user](#action-get-user) - Get information about a user \
[get attachments](#action-get-attachments) - List all of the attachments on a given incident \
[update ticket](#action-update-ticket) - Update an incident \
[create ticket](#action-create-ticket) - Create an incident \
[get ticket](#action-get-ticket) - Get incident information \
[list tickets](#action-list-tickets) - Get a list of incidents

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list users'

Get a list of users

Type: **investigate** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.accountLocked | boolean | | True False |
action_result.data.\*.createDateTime | string | | 0001-01-01T00:00:00 |
action_result.data.\*.displayName | string | | andrew |
action_result.data.\*.errorCode | string | | |
action_result.data.\*.errorMessage | string | | |
action_result.data.\*.fields.Address.dirty | boolean | | True False |
action_result.data.\*.fields.Address.displayName | string | | |
action_result.data.\*.fields.Address.fieldId | string | | 93c1fbff092ee7ffb10d634f9f902baec611301b26 |
action_result.data.\*.fields.Address.fullFieldId | string | | |
action_result.data.\*.fields.Address.html | string | | |
action_result.data.\*.fields.Address.value | string | | |
action_result.data.\*.fields.Availability.dirty | boolean | | True False |
action_result.data.\*.fields.Availability.displayName | string | | |
action_result.data.\*.fields.Availability.fieldId | string | | 9369429dd17a7be3f91a934182b7edf1e653fd5a08 |
action_result.data.\*.fields.Availability.fullFieldId | string | | |
action_result.data.\*.fields.Availability.html | string | | |
action_result.data.\*.fields.Availability.value | string | | |
action_result.data.\*.fields.Avatar.dirty | boolean | | True False |
action_result.data.\*.fields.Avatar.displayName | string | | |
action_result.data.\*.fields.Avatar.fieldId | string | | 93d0a9e5319e3fed72a4644a5398ea78941381dfc6 |
action_result.data.\*.fields.Avatar.fullFieldId | string | | |
action_result.data.\*.fields.Avatar.html | string | | |
action_result.data.\*.fields.Avatar.value | string | | [Imported]Global;(None);Andrew_Simms |
action_result.data.\*.fields.CellPhone.dirty | boolean | | True False |
action_result.data.\*.fields.CellPhone.displayName | string | | |
action_result.data.\*.fields.CellPhone.fieldId | string | | 9338217a2c58b53c195ec0499196c39c1678430e21 |
action_result.data.\*.fields.CellPhone.fullFieldId | string | | |
action_result.data.\*.fields.CellPhone.html | string | | |
action_result.data.\*.fields.CellPhone.value | string | | 353-884-3579 |
action_result.data.\*.fields.City.dirty | boolean | | True False |
action_result.data.\*.fields.City.displayName | string | | |
action_result.data.\*.fields.City.fieldId | string | | 93c1fc1b77ec44348cae4a4dee85c6a3136b0b3577 |
action_result.data.\*.fields.City.fullFieldId | string | | |
action_result.data.\*.fields.City.html | string | | |
action_result.data.\*.fields.City.value | string | | |
action_result.data.\*.fields.Comments.dirty | boolean | | True False |
action_result.data.\*.fields.Comments.displayName | string | | |
action_result.data.\*.fields.Comments.fieldId | string | | 9338217ab731447b9333bf41bbad7ed201dc3dfc57 |
action_result.data.\*.fields.Comments.fullFieldId | string | | |
action_result.data.\*.fields.Comments.html | string | | |
action_result.data.\*.fields.Comments.value | string | | 2nd Level & Design Knowledge Team |
action_result.data.\*.fields.CreatedBy.dirty | boolean | | True False |
action_result.data.\*.fields.CreatedBy.displayName | string | | |
action_result.data.\*.fields.CreatedBy.fieldId | string | | 9338216b3d009c9ed8a3b849c287fb123b179178f6 |
action_result.data.\*.fields.CreatedBy.fullFieldId | string | | |
action_result.data.\*.fields.CreatedBy.html | string | | |
action_result.data.\*.fields.CreatedBy.value | string | | Henri Bryce |
action_result.data.\*.fields.CreatedByID.dirty | boolean | | True False |
action_result.data.\*.fields.CreatedByID.displayName | string | | |
action_result.data.\*.fields.CreatedByID.fieldId | string | | 9338216b3d0a57dc26f79d40a1927d8c4c6b286f67 |
action_result.data.\*.fields.CreatedByID.fullFieldId | string | | |
action_result.data.\*.fields.CreatedByID.html | string | | |
action_result.data.\*.fields.CreatedByID.value | string | | 9354650fbf63b8f69623cd4b179bc739dabe2716c8 |
action_result.data.\*.fields.CreatedCulture.dirty | boolean | | True False |
action_result.data.\*.fields.CreatedCulture.displayName | string | | |
action_result.data.\*.fields.CreatedCulture.fieldId | string | | 940b78b883a2b431752ffa4ad6a41859b89f8cfafd |
action_result.data.\*.fields.CreatedCulture.fullFieldId | string | | |
action_result.data.\*.fields.CreatedCulture.html | string | | |
action_result.data.\*.fields.CreatedCulture.value | string | | |
action_result.data.\*.fields.CreatedDateTime.dirty | boolean | | True False |
action_result.data.\*.fields.CreatedDateTime.displayName | string | | |
action_result.data.\*.fields.CreatedDateTime.fieldId | string | | 9338216b3d6aae467bbf5a417ea6b0faa1e5d6d01e |
action_result.data.\*.fields.CreatedDateTime.fullFieldId | string | | |
action_result.data.\*.fields.CreatedDateTime.html | string | | |
action_result.data.\*.fields.CreatedDateTime.value | string | | 1/25/2007 6:56 PM |
action_result.data.\*.fields.DefaultTeamID.dirty | boolean | | True False |
action_result.data.\*.fields.DefaultTeamID.displayName | string | | |
action_result.data.\*.fields.DefaultTeamID.fieldId | string | | 933a15d17f1f10297df7604b58a76734d6106ac428 |
action_result.data.\*.fields.DefaultTeamID.fullFieldId | string | | |
action_result.data.\*.fields.DefaultTeamID.html | string | | |
action_result.data.\*.fields.DefaultTeamID.value | string | | 93d5f9820b027f0236a27d481c94f51c9d693753fc |
action_result.data.\*.fields.DefaultTeamName.dirty | boolean | | True False |
action_result.data.\*.fields.DefaultTeamName.displayName | string | | |
action_result.data.\*.fields.DefaultTeamName.fieldId | string | | 933a15d131ff727ca7ed3f4e1c8f528d719b99b82d |
action_result.data.\*.fields.DefaultTeamName.fullFieldId | string | | |
action_result.data.\*.fields.DefaultTeamName.html | string | | |
action_result.data.\*.fields.DefaultTeamName.value | string | | 2nd Level Support |
action_result.data.\*.fields.Department.dirty | boolean | | True False |
action_result.data.\*.fields.Department.displayName | string | | |
action_result.data.\*.fields.Department.fieldId | string | | 933821787936216786fd2646b1814c466586fd87dc |
action_result.data.\*.fields.Department.fullFieldId | string | | |
action_result.data.\*.fields.Department.html | string | | |
action_result.data.\*.fields.Department.value | string | | IT |
action_result.data.\*.fields.Email.dirty | boolean | | True False |
action_result.data.\*.fields.Email.displayName | string | | |
action_result.data.\*.fields.Email.fieldId | string | | 933821793f43a638cf23e34723b907956d324ad303 |
action_result.data.\*.fields.Email.fullFieldId | string | | |
action_result.data.\*.fields.Email.html | string | | |
action_result.data.\*.fields.Email.value | string | `email` | andrew.simms@RiverTCorp.com |
action_result.data.\*.fields.EmployeeID.dirty | boolean | | True False |
action_result.data.\*.fields.EmployeeID.displayName | string | | |
action_result.data.\*.fields.EmployeeID.fieldId | string | | 937897dec8308024cd00504c048a572bd7f0dfd711 |
action_result.data.\*.fields.EmployeeID.fullFieldId | string | | |
action_result.data.\*.fields.EmployeeID.html | string | | |
action_result.data.\*.fields.EmployeeID.value | string | | |
action_result.data.\*.fields.EndDate.dirty | boolean | | True False |
action_result.data.\*.fields.EndDate.displayName | string | | |
action_result.data.\*.fields.EndDate.fieldId | string | | 93b2bfe601aff9ef94b15f4e2891021f91f4ac4e3e |
action_result.data.\*.fields.EndDate.fullFieldId | string | | |
action_result.data.\*.fields.EndDate.html | string | | |
action_result.data.\*.fields.EndDate.value | string | | |
action_result.data.\*.fields.FaxNumber.dirty | boolean | | True False |
action_result.data.\*.fields.FaxNumber.displayName | string | | |
action_result.data.\*.fields.FaxNumber.fieldId | string | | 9338217a6b713fbfe3dfce4a94a8d1e5dca2ffa203 |
action_result.data.\*.fields.FaxNumber.fullFieldId | string | | |
action_result.data.\*.fields.FaxNumber.html | string | | |
action_result.data.\*.fields.FaxNumber.value | string | | (838) 898-1337 x |
action_result.data.\*.fields.FirstName.dirty | boolean | | True False |
action_result.data.\*.fields.FirstName.displayName | string | | |
action_result.data.\*.fields.FirstName.fieldId | string | | 93c1fb427bdae80d5a5b3c4e6a819ac02291f58a45 |
action_result.data.\*.fields.FirstName.fullFieldId | string | | |
action_result.data.\*.fields.FirstName.html | string | | |
action_result.data.\*.fields.FirstName.value | string | | Andrew |
action_result.data.\*.fields.FullName.dirty | boolean | | True False |
action_result.data.\*.fields.FullName.displayName | string | | |
action_result.data.\*.fields.FullName.fieldId | string | | 93382178280a07634f62d74fc4bc587e3b3f479776 |
action_result.data.\*.fields.FullName.fullFieldId | string | | |
action_result.data.\*.fields.FullName.html | string | | |
action_result.data.\*.fields.FullName.value | string | | Andrew Simms |
action_result.data.\*.fields.HomePhone.dirty | boolean | | True False |
action_result.data.\*.fields.HomePhone.displayName | string | | |
action_result.data.\*.fields.HomePhone.fieldId | string | | 93c1fbcac3f6333cc8cc4447daa90f76bc9c8075a9 |
action_result.data.\*.fields.HomePhone.fullFieldId | string | | |
action_result.data.\*.fields.HomePhone.html | string | | |
action_result.data.\*.fields.HomePhone.value | string | | |
action_result.data.\*.fields.Image.dirty | boolean | | True False |
action_result.data.\*.fields.Image.displayName | string | | |
action_result.data.\*.fields.Image.fieldId | string | | 93ac5024db164c79fc863e4654b158df68bcac7b63 |
action_result.data.\*.fields.Image.fullFieldId | string | | |
action_result.data.\*.fields.Image.html | string | | |
action_result.data.\*.fields.Image.value | string | | |
action_result.data.\*.fields.LanguageLocale.dirty | boolean | | True False |
action_result.data.\*.fields.LanguageLocale.displayName | string | | |
action_result.data.\*.fields.LanguageLocale.fieldId | string | | 93c1fca85acc065c5e895c4fc3af425b66d2c59f45 |
action_result.data.\*.fields.LanguageLocale.fullFieldId | string | | |
action_result.data.\*.fields.LanguageLocale.html | string | | |
action_result.data.\*.fields.LanguageLocale.value | string | | |
action_result.data.\*.fields.LanguageName.dirty | boolean | | True False |
action_result.data.\*.fields.LanguageName.displayName | string | | |
action_result.data.\*.fields.LanguageName.fieldId | string | | 93c1fca8eb44fbbe33200445b49275bad599513db5 |
action_result.data.\*.fields.LanguageName.fullFieldId | string | | |
action_result.data.\*.fields.LanguageName.html | string | | |
action_result.data.\*.fields.LanguageName.value | string | | |
action_result.data.\*.fields.LastModBy.dirty | boolean | | True False |
action_result.data.\*.fields.LastModBy.displayName | string | | |
action_result.data.\*.fields.LastModBy.fieldId | string | | 9338216b3db79f30b4f9db463bb0f90dbf87944a67 |
action_result.data.\*.fields.LastModBy.fullFieldId | string | | |
action_result.data.\*.fields.LastModBy.html | string | | |
action_result.data.\*.fields.LastModBy.value | string | | Henri Bryce |
action_result.data.\*.fields.LastModTimeStamp.dirty | boolean | | True False |
action_result.data.\*.fields.LastModTimeStamp.displayName | string | | |
action_result.data.\*.fields.LastModTimeStamp.fieldId | string | | 935d443954fe3ac992c5914c628606dad96298f661 |
action_result.data.\*.fields.LastModTimeStamp.fullFieldId | string | | |
action_result.data.\*.fields.LastModTimeStamp.html | string | | |
action_result.data.\*.fields.LastModTimeStamp.value | string | | |
action_result.data.\*.fields.LastModifiedByID.dirty | boolean | | True False |
action_result.data.\*.fields.LastModifiedByID.displayName | string | | |
action_result.data.\*.fields.LastModifiedByID.fieldId | string | | 9338216b3dc149a8b08aa64a9f988aa36a3a89b40b |
action_result.data.\*.fields.LastModifiedByID.fullFieldId | string | | |
action_result.data.\*.fields.LastModifiedByID.html | string | | |
action_result.data.\*.fields.LastModifiedByID.value | string | | 93d66d773a285704026b0d45f882c9d2ba437d406b |
action_result.data.\*.fields.LastModifiedDateTime.dirty | boolean | | True False |
action_result.data.\*.fields.LastModifiedDateTime.displayName | string | | |
action_result.data.\*.fields.LastModifiedDateTime.fieldId | string | | 9338216b3dd435ae8d47414d60aaba7cbef0a05a42 |
action_result.data.\*.fields.LastModifiedDateTime.fullFieldId | string | | |
action_result.data.\*.fields.LastModifiedDateTime.html | string | | |
action_result.data.\*.fields.LastModifiedDateTime.value | string | | 12/18/2015 2:10 AM |
action_result.data.\*.fields.LastName.dirty | boolean | | True False |
action_result.data.\*.fields.LastName.displayName | string | | |
action_result.data.\*.fields.LastName.fieldId | string | | 93c1fb88b58d34aa2c3eee44bda268e7640f28c359 |
action_result.data.\*.fields.LastName.fullFieldId | string | | |
action_result.data.\*.fields.LastName.html | string | | |
action_result.data.\*.fields.LastName.value | string | | Simms |
action_result.data.\*.fields.Manager.dirty | boolean | | True False |
action_result.data.\*.fields.Manager.displayName | string | | |
action_result.data.\*.fields.Manager.fieldId | string | | 9338217ade3a5a3a1021f547d3ac2d0b7dbbcb3f47 |
action_result.data.\*.fields.Manager.fullFieldId | string | | |
action_result.data.\*.fields.Manager.html | string | | |
action_result.data.\*.fields.Manager.value | string | | Gina Mehra |
action_result.data.\*.fields.ManagerEmail.dirty | boolean | | True False |
action_result.data.\*.fields.ManagerEmail.displayName | string | | |
action_result.data.\*.fields.ManagerEmail.fieldId | string | | 9378a8c288504f7b26ea634ed386c8836fdb5d4caf |
action_result.data.\*.fields.ManagerEmail.fullFieldId | string | | |
action_result.data.\*.fields.ManagerEmail.html | string | | |
action_result.data.\*.fields.ManagerEmail.value | string | | gina.mehra@RiverTCorp.com |
action_result.data.\*.fields.ManagerID.dirty | boolean | | True False |
action_result.data.\*.fields.ManagerID.displayName | string | | |
action_result.data.\*.fields.ManagerID.fieldId | string | | 93c30faa2f7bb23126542242aa8b6521034b8620e3 |
action_result.data.\*.fields.ManagerID.fullFieldId | string | | |
action_result.data.\*.fields.ManagerID.html | string | | |
action_result.data.\*.fields.ManagerID.value | string | | 9365b511f78906c1fe83644c3fb33e9ec1466f7d90 |
action_result.data.\*.fields.MiddleInitial.dirty | boolean | | True False |
action_result.data.\*.fields.MiddleInitial.displayName | string | | |
action_result.data.\*.fields.MiddleInitial.fieldId | string | | 93c1fb5690a2fb9f6d00724963b50e3d1140ad35f0 |
action_result.data.\*.fields.MiddleInitial.fullFieldId | string | | |
action_result.data.\*.fields.MiddleInitial.html | string | | |
action_result.data.\*.fields.MiddleInitial.value | string | | |
action_result.data.\*.fields.Office.dirty | boolean | | True False |
action_result.data.\*.fields.Office.displayName | string | | |
action_result.data.\*.fields.Office.fieldId | string | | 937897d8dcede1dede57f448b5a2a7b7417ed18a09 |
action_result.data.\*.fields.Office.fullFieldId | string | | |
action_result.data.\*.fields.Office.html | string | | |
action_result.data.\*.fields.Office.value | string | | Room 009 |
action_result.data.\*.fields.Phone.dirty | boolean | | True False |
action_result.data.\*.fields.Phone.displayName | string | | |
action_result.data.\*.fields.Phone.fieldId | string | | 93382178bc6845d204279546a9ba3d428634b125ae |
action_result.data.\*.fields.Phone.fullFieldId | string | | |
action_result.data.\*.fields.Phone.html | string | | |
action_result.data.\*.fields.Phone.value | string | | 833-898-9039 |
action_result.data.\*.fields.PostalCodeZip.dirty | boolean | | True False |
action_result.data.\*.fields.PostalCodeZip.displayName | string | | |
action_result.data.\*.fields.PostalCodeZip.fieldId | string | | 93c1faf329c6693d75e3104c5988ed2fbeab784b44 |
action_result.data.\*.fields.PostalCodeZip.fullFieldId | string | | |
action_result.data.\*.fields.PostalCodeZip.html | string | | |
action_result.data.\*.fields.PostalCodeZip.value | string | | |
action_result.data.\*.fields.ProvinceStateName.dirty | boolean | | True False |
action_result.data.\*.fields.ProvinceStateName.displayName | string | | |
action_result.data.\*.fields.ProvinceStateName.fieldId | string | | 93c1fc26a154207a0818c14ecf95c6ca53aaf12099 |
action_result.data.\*.fields.ProvinceStateName.fullFieldId | string | | |
action_result.data.\*.fields.ProvinceStateName.html | string | | |
action_result.data.\*.fields.ProvinceStateName.value | string | | |
action_result.data.\*.fields.RecID.dirty | boolean | | True False |
action_result.data.\*.fields.RecID.displayName | string | | |
action_result.data.\*.fields.RecID.fieldId | string | | 9338216b3d358c3d017f704a1fa4db7e31d7d1928a |
action_result.data.\*.fields.RecID.fullFieldId | string | | |
action_result.data.\*.fields.RecID.html | string | | |
action_result.data.\*.fields.RecID.value | string | | 9354650fbf63b8f69623cd4b179bc739dabe2716c8 |
action_result.data.\*.fields.SAMAccountName.dirty | boolean | | True False |
action_result.data.\*.fields.SAMAccountName.displayName | string | | |
action_result.data.\*.fields.SAMAccountName.fieldId | string | | 937897e026c1d118596d9749a1beffeb877d77e81d |
action_result.data.\*.fields.SAMAccountName.fullFieldId | string | | |
action_result.data.\*.fields.SAMAccountName.html | string | | |
action_result.data.\*.fields.SAMAccountName.value | string | | |
action_result.data.\*.fields.ShowInSalespersonList.dirty | boolean | | True False |
action_result.data.\*.fields.ShowInSalespersonList.displayName | string | | |
action_result.data.\*.fields.ShowInSalespersonList.fieldId | string | | 935db7d31f89e6e7e53cdb46209d4fee1f56f6f113 |
action_result.data.\*.fields.ShowInSalespersonList.fullFieldId | string | | |
action_result.data.\*.fields.ShowInSalespersonList.html | string | | |
action_result.data.\*.fields.ShowInSalespersonList.value | string | | False |
action_result.data.\*.fields.StartDate.dirty | boolean | | True False |
action_result.data.\*.fields.StartDate.displayName | string | | |
action_result.data.\*.fields.StartDate.fieldId | string | | 93b2bfe56ea8d5e0cf2a724baf99b9338e515f2374 |
action_result.data.\*.fields.StartDate.fullFieldId | string | | |
action_result.data.\*.fields.StartDate.html | string | | |
action_result.data.\*.fields.StartDate.value | string | | |
action_result.data.\*.fields.System_LDAPPath.dirty | boolean | | True False |
action_result.data.\*.fields.System_LDAPPath.displayName | string | | |
action_result.data.\*.fields.System_LDAPPath.fieldId | string | | 937897bfbf6a48b92017d2432f97deaaa00223cf7a |
action_result.data.\*.fields.System_LDAPPath.fullFieldId | string | | |
action_result.data.\*.fields.System_LDAPPath.html | string | | |
action_result.data.\*.fields.System_LDAPPath.value | string | | |
action_result.data.\*.fields.TimeZoneOffset.dirty | boolean | | True False |
action_result.data.\*.fields.TimeZoneOffset.displayName | string | | |
action_result.data.\*.fields.TimeZoneOffset.fieldId | string | | 93c1fed1cb6e5b1b19795c44dda03e348622db55da |
action_result.data.\*.fields.TimeZoneOffset.fullFieldId | string | | |
action_result.data.\*.fields.TimeZoneOffset.html | string | | |
action_result.data.\*.fields.TimeZoneOffset.value | string | | |
action_result.data.\*.fields.WebSite.dirty | boolean | | True False |
action_result.data.\*.fields.WebSite.displayName | string | | |
action_result.data.\*.fields.WebSite.fieldId | string | | 93c1fc4c859e60663d76ef46d4b0782f93ccdc493a |
action_result.data.\*.fields.WebSite.fullFieldId | string | | |
action_result.data.\*.fields.WebSite.html | string | | |
action_result.data.\*.fields.WebSite.value | string | | |
action_result.data.\*.hasError | boolean | | True False |
action_result.data.\*.lastPasswordResetDate | string | | 2013-01-28T15:07:15.117 |
action_result.data.\*.lastResetDateTime | string | | 2013-01-28T15:07:15.117 |
action_result.data.\*.ldapRequired | boolean | | True False |
action_result.data.\*.passwordNeverExpires | boolean | | True False |
action_result.data.\*.publicId | string | | Andrew Simms |
action_result.data.\*.recordId | string | `cherwell customer rec id` | 9354650fbf63b8f69623cd4b179bc739dabe2716c8 |
action_result.data.\*.securityGroupId | string | | 93373402da59635ba9e6164cf89364774a3a2bebb1 |
action_result.data.\*.shortDisplayName | string | | andrew |
action_result.data.\*.userCannotChangePassword | boolean | | True False |
action_result.data.\*.userMustResetPasswordAtNextLogin | boolean | | True False |
action_result.summary | string | | |
action_result.message | string | | Successfully retrieved the list of users |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get user'

Get information about a user

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | Customer Record ID | string | `cherwell customer rec id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | `cherwell customer rec id` | 9354650fbf63b8f69623cd4b179bc739dabe2716c8 |
action_result.data.\*.accountLocked | boolean | | True False |
action_result.data.\*.createDateTime | string | | 0001-01-01T00:00:00 |
action_result.data.\*.displayName | string | | andrew |
action_result.data.\*.errorCode | string | | |
action_result.data.\*.errorMessage | string | | |
action_result.data.\*.fields.Address.dirty | boolean | | True False |
action_result.data.\*.fields.Address.displayName | string | | |
action_result.data.\*.fields.Address.fieldId | string | | 93c1fbff092ee7ffb10d634f9f902baec611301b26 |
action_result.data.\*.fields.Address.fullFieldId | string | | |
action_result.data.\*.fields.Address.html | string | | |
action_result.data.\*.fields.Address.value | string | | |
action_result.data.\*.fields.Availability.dirty | boolean | | True False |
action_result.data.\*.fields.Availability.displayName | string | | |
action_result.data.\*.fields.Availability.fieldId | string | | 9369429dd17a7be3f91a934182b7edf1e653fd5a08 |
action_result.data.\*.fields.Availability.fullFieldId | string | | |
action_result.data.\*.fields.Availability.html | string | | |
action_result.data.\*.fields.Availability.value | string | | |
action_result.data.\*.fields.Avatar.dirty | boolean | | True False |
action_result.data.\*.fields.Avatar.displayName | string | | |
action_result.data.\*.fields.Avatar.fieldId | string | | 93d0a9e5319e3fed72a4644a5398ea78941381dfc6 |
action_result.data.\*.fields.Avatar.fullFieldId | string | | |
action_result.data.\*.fields.Avatar.html | string | | |
action_result.data.\*.fields.Avatar.value | string | | [Imported]Global;(None);Andrew_Simms |
action_result.data.\*.fields.CellPhone.dirty | boolean | | True False |
action_result.data.\*.fields.CellPhone.displayName | string | | |
action_result.data.\*.fields.CellPhone.fieldId | string | | 9338217a2c58b53c195ec0499196c39c1678430e21 |
action_result.data.\*.fields.CellPhone.fullFieldId | string | | |
action_result.data.\*.fields.CellPhone.html | string | | |
action_result.data.\*.fields.CellPhone.value | string | | 353-884-3579 |
action_result.data.\*.fields.City.dirty | boolean | | True False |
action_result.data.\*.fields.City.displayName | string | | |
action_result.data.\*.fields.City.fieldId | string | | 93c1fc1b77ec44348cae4a4dee85c6a3136b0b3577 |
action_result.data.\*.fields.City.fullFieldId | string | | |
action_result.data.\*.fields.City.html | string | | |
action_result.data.\*.fields.City.value | string | | |
action_result.data.\*.fields.Comments.dirty | boolean | | True False |
action_result.data.\*.fields.Comments.displayName | string | | |
action_result.data.\*.fields.Comments.fieldId | string | | 9338217ab731447b9333bf41bbad7ed201dc3dfc57 |
action_result.data.\*.fields.Comments.fullFieldId | string | | |
action_result.data.\*.fields.Comments.html | string | | |
action_result.data.\*.fields.Comments.value | string | | 2nd Level & Design Knowledge Team |
action_result.data.\*.fields.CreatedBy.dirty | boolean | | True False |
action_result.data.\*.fields.CreatedBy.displayName | string | | |
action_result.data.\*.fields.CreatedBy.fieldId | string | | 9338216b3d009c9ed8a3b849c287fb123b179178f6 |
action_result.data.\*.fields.CreatedBy.fullFieldId | string | | |
action_result.data.\*.fields.CreatedBy.html | string | | |
action_result.data.\*.fields.CreatedBy.value | string | | Henri Bryce |
action_result.data.\*.fields.CreatedByID.dirty | boolean | | True False |
action_result.data.\*.fields.CreatedByID.displayName | string | | |
action_result.data.\*.fields.CreatedByID.fieldId | string | | 9338216b3d0a57dc26f79d40a1927d8c4c6b286f67 |
action_result.data.\*.fields.CreatedByID.fullFieldId | string | | |
action_result.data.\*.fields.CreatedByID.html | string | | |
action_result.data.\*.fields.CreatedByID.value | string | | 9354650fbf63b8f69623cd4b179bc739dabe2716c8 |
action_result.data.\*.fields.CreatedCulture.dirty | boolean | | True False |
action_result.data.\*.fields.CreatedCulture.displayName | string | | |
action_result.data.\*.fields.CreatedCulture.fieldId | string | | 940b78b883a2b431752ffa4ad6a41859b89f8cfafd |
action_result.data.\*.fields.CreatedCulture.fullFieldId | string | | |
action_result.data.\*.fields.CreatedCulture.html | string | | |
action_result.data.\*.fields.CreatedCulture.value | string | | |
action_result.data.\*.fields.CreatedDateTime.dirty | boolean | | True False |
action_result.data.\*.fields.CreatedDateTime.displayName | string | | |
action_result.data.\*.fields.CreatedDateTime.fieldId | string | | 9338216b3d6aae467bbf5a417ea6b0faa1e5d6d01e |
action_result.data.\*.fields.CreatedDateTime.fullFieldId | string | | |
action_result.data.\*.fields.CreatedDateTime.html | string | | |
action_result.data.\*.fields.CreatedDateTime.value | string | | 1/25/2007 6:56 PM |
action_result.data.\*.fields.DefaultTeamID.dirty | boolean | | True False |
action_result.data.\*.fields.DefaultTeamID.displayName | string | | |
action_result.data.\*.fields.DefaultTeamID.fieldId | string | | 933a15d17f1f10297df7604b58a76734d6106ac428 |
action_result.data.\*.fields.DefaultTeamID.fullFieldId | string | | |
action_result.data.\*.fields.DefaultTeamID.html | string | | |
action_result.data.\*.fields.DefaultTeamID.value | string | | 93d5f9820b027f0236a27d481c94f51c9d693753fc |
action_result.data.\*.fields.DefaultTeamName.dirty | boolean | | True False |
action_result.data.\*.fields.DefaultTeamName.displayName | string | | |
action_result.data.\*.fields.DefaultTeamName.fieldId | string | | 933a15d131ff727ca7ed3f4e1c8f528d719b99b82d |
action_result.data.\*.fields.DefaultTeamName.fullFieldId | string | | |
action_result.data.\*.fields.DefaultTeamName.html | string | | |
action_result.data.\*.fields.DefaultTeamName.value | string | | 2nd Level Support |
action_result.data.\*.fields.Department.dirty | boolean | | True False |
action_result.data.\*.fields.Department.displayName | string | | |
action_result.data.\*.fields.Department.fieldId | string | | 933821787936216786fd2646b1814c466586fd87dc |
action_result.data.\*.fields.Department.fullFieldId | string | | |
action_result.data.\*.fields.Department.html | string | | |
action_result.data.\*.fields.Department.value | string | | IT |
action_result.data.\*.fields.Email.dirty | boolean | | True False |
action_result.data.\*.fields.Email.displayName | string | | |
action_result.data.\*.fields.Email.fieldId | string | | 933821793f43a638cf23e34723b907956d324ad303 |
action_result.data.\*.fields.Email.fullFieldId | string | | |
action_result.data.\*.fields.Email.html | string | | |
action_result.data.\*.fields.Email.value | string | `email` | andrew.simms@RiverTCorp.com |
action_result.data.\*.fields.EmployeeID.dirty | boolean | | True False |
action_result.data.\*.fields.EmployeeID.displayName | string | | |
action_result.data.\*.fields.EmployeeID.fieldId | string | | 937897dec8308024cd00504c048a572bd7f0dfd711 |
action_result.data.\*.fields.EmployeeID.fullFieldId | string | | |
action_result.data.\*.fields.EmployeeID.value | string | | |
action_result.data.\*.fields.EndDate.dirty | boolean | | True False |
action_result.data.\*.fields.EndDate.displayName | string | | |
action_result.data.\*.fields.EndDate.fieldId | string | | 93b2bfe601aff9ef94b15f4e2891021f91f4ac4e3e |
action_result.data.\*.fields.EndDate.fullFieldId | string | | |
action_result.data.\*.fields.EndDate.html | string | | |
action_result.data.\*.fields.EndDate.value | string | | |
action_result.data.\*.fields.FaxNumber.dirty | boolean | | True False |
action_result.data.\*.fields.FaxNumber.displayName | string | | |
action_result.data.\*.fields.FaxNumber.fieldId | string | | 9338217a6b713fbfe3dfce4a94a8d1e5dca2ffa203 |
action_result.data.\*.fields.FaxNumber.fullFieldId | string | | |
action_result.data.\*.fields.FaxNumber.html | string | | |
action_result.data.\*.fields.FaxNumber.value | string | | (838) 898-1337 x |
action_result.data.\*.fields.FirstName.dirty | boolean | | True False |
action_result.data.\*.fields.FirstName.displayName | string | | |
action_result.data.\*.fields.FirstName.fieldId | string | | 93c1fb427bdae80d5a5b3c4e6a819ac02291f58a45 |
action_result.data.\*.fields.FirstName.fullFieldId | string | | |
action_result.data.\*.fields.FirstName.html | string | | |
action_result.data.\*.fields.FirstName.value | string | | Andrew |
action_result.data.\*.fields.FullName.dirty | boolean | | True False |
action_result.data.\*.fields.FullName.displayName | string | | |
action_result.data.\*.fields.FullName.fieldId | string | | 93382178280a07634f62d74fc4bc587e3b3f479776 |
action_result.data.\*.fields.FullName.fullFieldId | string | | |
action_result.data.\*.fields.FullName.html | string | | |
action_result.data.\*.fields.FullName.value | string | | Andrew Simms |
action_result.data.\*.fields.HomePhone.dirty | boolean | | True False |
action_result.data.\*.fields.HomePhone.displayName | string | | |
action_result.data.\*.fields.HomePhone.fieldId | string | | 93c1fbcac3f6333cc8cc4447daa90f76bc9c8075a9 |
action_result.data.\*.fields.HomePhone.fullFieldId | string | | |
action_result.data.\*.fields.HomePhone.html | string | | |
action_result.data.\*.fields.HomePhone.value | string | | |
action_result.data.\*.fields.Image.dirty | boolean | | True False |
action_result.data.\*.fields.Image.displayName | string | | |
action_result.data.\*.fields.Image.fieldId | string | | 93ac5024db164c79fc863e4654b158df68bcac7b63 |
action_result.data.\*.fields.Image.fullFieldId | string | | |
action_result.data.\*.fields.Image.html | string | | |
action_result.data.\*.fields.Image.value | string | | |
action_result.data.\*.fields.LanguageLocale.dirty | boolean | | True False |
action_result.data.\*.fields.LanguageLocale.displayName | string | | |
action_result.data.\*.fields.LanguageLocale.fieldId | string | | 93c1fca85acc065c5e895c4fc3af425b66d2c59f45 |
action_result.data.\*.fields.LanguageLocale.fullFieldId | string | | |
action_result.data.\*.fields.LanguageLocale.html | string | | |
action_result.data.\*.fields.LanguageLocale.value | string | | |
action_result.data.\*.fields.LanguageName.dirty | boolean | | True False |
action_result.data.\*.fields.LanguageName.displayName | string | | |
action_result.data.\*.fields.LanguageName.fieldId | string | | 93c1fca8eb44fbbe33200445b49275bad599513db5 |
action_result.data.\*.fields.LanguageName.fullFieldId | string | | |
action_result.data.\*.fields.LanguageName.html | string | | |
action_result.data.\*.fields.LanguageName.value | string | | |
action_result.data.\*.fields.LastModBy.dirty | boolean | | True False |
action_result.data.\*.fields.LastModBy.displayName | string | | |
action_result.data.\*.fields.LastModBy.fieldId | string | | 9338216b3db79f30b4f9db463bb0f90dbf87944a67 |
action_result.data.\*.fields.LastModBy.fullFieldId | string | | |
action_result.data.\*.fields.LastModBy.html | string | | |
action_result.data.\*.fields.LastModBy.value | string | | Henri Bryce |
action_result.data.\*.fields.LastModTimeStamp.dirty | boolean | | True False |
action_result.data.\*.fields.LastModTimeStamp.displayName | string | | |
action_result.data.\*.fields.LastModTimeStamp.fieldId | string | | 935d443954fe3ac992c5914c628606dad96298f661 |
action_result.data.\*.fields.LastModTimeStamp.fullFieldId | string | | |
action_result.data.\*.fields.LastModTimeStamp.html | string | | |
action_result.data.\*.fields.LastModTimeStamp.value | string | | |
action_result.data.\*.fields.LastModifiedByID.dirty | boolean | | True False |
action_result.data.\*.fields.LastModifiedByID.displayName | string | | |
action_result.data.\*.fields.LastModifiedByID.fieldId | string | | 9338216b3dc149a8b08aa64a9f988aa36a3a89b40b |
action_result.data.\*.fields.LastModifiedByID.fullFieldId | string | | |
action_result.data.\*.fields.LastModifiedByID.html | string | | |
action_result.data.\*.fields.LastModifiedByID.value | string | | 93d66d773a285704026b0d45f882c9d2ba437d406b |
action_result.data.\*.fields.LastModifiedDateTime.dirty | boolean | | True False |
action_result.data.\*.fields.LastModifiedDateTime.displayName | string | | |
action_result.data.\*.fields.LastModifiedDateTime.fieldId | string | | 9338216b3dd435ae8d47414d60aaba7cbef0a05a42 |
action_result.data.\*.fields.LastModifiedDateTime.fullFieldId | string | | |
action_result.data.\*.fields.LastModifiedDateTime.html | string | | |
action_result.data.\*.fields.LastModifiedDateTime.value | string | | 12/18/2015 2:10 AM |
action_result.data.\*.fields.LastName.dirty | boolean | | True False |
action_result.data.\*.fields.LastName.displayName | string | | |
action_result.data.\*.fields.LastName.fieldId | string | | 93c1fb88b58d34aa2c3eee44bda268e7640f28c359 |
action_result.data.\*.fields.LastName.fullFieldId | string | | |
action_result.data.\*.fields.LastName.html | string | | |
action_result.data.\*.fields.LastName.value | string | | Simms |
action_result.data.\*.fields.Manager.dirty | boolean | | True False |
action_result.data.\*.fields.Manager.displayName | string | | |
action_result.data.\*.fields.Manager.fieldId | string | | 9338217ade3a5a3a1021f547d3ac2d0b7dbbcb3f47 |
action_result.data.\*.fields.Manager.fullFieldId | string | | |
action_result.data.\*.fields.Manager.html | string | | |
action_result.data.\*.fields.Manager.value | string | | Gina Mehra |
action_result.data.\*.fields.ManagerEmail.dirty | boolean | | True False |
action_result.data.\*.fields.ManagerEmail.displayName | string | | |
action_result.data.\*.fields.ManagerEmail.fieldId | string | | 9378a8c288504f7b26ea634ed386c8836fdb5d4caf |
action_result.data.\*.fields.ManagerEmail.fullFieldId | string | | |
action_result.data.\*.fields.ManagerEmail.html | string | | |
action_result.data.\*.fields.ManagerEmail.value | string | `email` | gina.mehra@RiverTCorp.com |
action_result.data.\*.fields.ManagerID.dirty | boolean | | True False |
action_result.data.\*.fields.ManagerID.displayName | string | | |
action_result.data.\*.fields.ManagerID.fieldId | string | | 93c30faa2f7bb23126542242aa8b6521034b8620e3 |
action_result.data.\*.fields.ManagerID.fullFieldId | string | | |
action_result.data.\*.fields.ManagerID.html | string | | |
action_result.data.\*.fields.ManagerID.value | string | | 9365b511f78906c1fe83644c3fb33e9ec1466f7d90 |
action_result.data.\*.fields.MiddleInitial.dirty | boolean | | True False |
action_result.data.\*.fields.MiddleInitial.displayName | string | | |
action_result.data.\*.fields.MiddleInitial.fieldId | string | | 93c1fb5690a2fb9f6d00724963b50e3d1140ad35f0 |
action_result.data.\*.fields.MiddleInitial.fullFieldId | string | | |
action_result.data.\*.fields.MiddleInitial.html | string | | |
action_result.data.\*.fields.MiddleInitial.value | string | | |
action_result.data.\*.fields.Office.dirty | boolean | | True False |
action_result.data.\*.fields.Office.displayName | string | | |
action_result.data.\*.fields.Office.fieldId | string | | 937897d8dcede1dede57f448b5a2a7b7417ed18a09 |
action_result.data.\*.fields.Office.fullFieldId | string | | |
action_result.data.\*.fields.Office.html | string | | |
action_result.data.\*.fields.Office.value | string | | Room 009 |
action_result.data.\*.fields.Phone.dirty | boolean | | True False |
action_result.data.\*.fields.Phone.displayName | string | | |
action_result.data.\*.fields.Phone.fieldId | string | | 93382178bc6845d204279546a9ba3d428634b125ae |
action_result.data.\*.fields.Phone.fullFieldId | string | | |
action_result.data.\*.fields.Phone.html | string | | |
action_result.data.\*.fields.Phone.value | string | | 833-898-9039 |
action_result.data.\*.fields.PostalCodeZip.dirty | boolean | | True False |
action_result.data.\*.fields.PostalCodeZip.displayName | string | | |
action_result.data.\*.fields.PostalCodeZip.fieldId | string | | 93c1faf329c6693d75e3104c5988ed2fbeab784b44 |
action_result.data.\*.fields.PostalCodeZip.fullFieldId | string | | |
action_result.data.\*.fields.PostalCodeZip.html | string | | |
action_result.data.\*.fields.PostalCodeZip.value | string | | |
action_result.data.\*.fields.ProvinceStateName.dirty | boolean | | True False |
action_result.data.\*.fields.ProvinceStateName.displayName | string | | |
action_result.data.\*.fields.ProvinceStateName.fieldId | string | | 93c1fc26a154207a0818c14ecf95c6ca53aaf12099 |
action_result.data.\*.fields.ProvinceStateName.fullFieldId | string | | |
action_result.data.\*.fields.ProvinceStateName.html | string | | |
action_result.data.\*.fields.ProvinceStateName.value | string | | |
action_result.data.\*.fields.RecID.dirty | boolean | | True False |
action_result.data.\*.fields.RecID.displayName | string | | |
action_result.data.\*.fields.RecID.fieldId | string | | 9338216b3d358c3d017f704a1fa4db7e31d7d1928a |
action_result.data.\*.fields.RecID.fullFieldId | string | | |
action_result.data.\*.fields.RecID.html | string | | |
action_result.data.\*.fields.RecID.value | string | | 9354650fbf63b8f69623cd4b179bc739dabe2716c8 |
action_result.data.\*.fields.SAMAccountName.dirty | boolean | | True False |
action_result.data.\*.fields.SAMAccountName.displayName | string | | |
action_result.data.\*.fields.SAMAccountName.fieldId | string | | 937897e026c1d118596d9749a1beffeb877d77e81d |
action_result.data.\*.fields.SAMAccountName.fullFieldId | string | | |
action_result.data.\*.fields.SAMAccountName.html | string | | |
action_result.data.\*.fields.SAMAccountName.value | string | | |
action_result.data.\*.fields.ShowInSalespersonList.dirty | boolean | | True False |
action_result.data.\*.fields.ShowInSalespersonList.displayName | string | | |
action_result.data.\*.fields.ShowInSalespersonList.fieldId | string | | 935db7d31f89e6e7e53cdb46209d4fee1f56f6f113 |
action_result.data.\*.fields.ShowInSalespersonList.fullFieldId | string | | |
action_result.data.\*.fields.ShowInSalespersonList.html | string | | |
action_result.data.\*.fields.ShowInSalespersonList.value | string | | False |
action_result.data.\*.fields.StartDate.dirty | boolean | | True False |
action_result.data.\*.fields.StartDate.displayName | string | | |
action_result.data.\*.fields.StartDate.fieldId | string | | 93b2bfe56ea8d5e0cf2a724baf99b9338e515f2374 |
action_result.data.\*.fields.StartDate.fullFieldId | string | | |
action_result.data.\*.fields.StartDate.html | string | | |
action_result.data.\*.fields.StartDate.value | string | | |
action_result.data.\*.fields.System_LDAPPath.dirty | boolean | | True False |
action_result.data.\*.fields.System_LDAPPath.displayName | string | | |
action_result.data.\*.fields.System_LDAPPath.fieldId | string | | 937897bfbf6a48b92017d2432f97deaaa00223cf7a |
action_result.data.\*.fields.System_LDAPPath.fullFieldId | string | | |
action_result.data.\*.fields.System_LDAPPath.html | string | | |
action_result.data.\*.fields.System_LDAPPath.value | string | | |
action_result.data.\*.fields.TimeZoneOffset.dirty | boolean | | True False |
action_result.data.\*.fields.TimeZoneOffset.displayName | string | | |
action_result.data.\*.fields.TimeZoneOffset.fieldId | string | | 93c1fed1cb6e5b1b19795c44dda03e348622db55da |
action_result.data.\*.fields.TimeZoneOffset.fullFieldId | string | | |
action_result.data.\*.fields.TimeZoneOffset.html | string | | |
action_result.data.\*.fields.TimeZoneOffset.value | string | | |
action_result.data.\*.fields.WebSite.dirty | boolean | | True False |
action_result.data.\*.fields.WebSite.displayName | string | | |
action_result.data.\*.fields.WebSite.fieldId | string | | 93c1fc4c859e60663d76ef46d4b0782f93ccdc493a |
action_result.data.\*.fields.WebSite.fullFieldId | string | | |
action_result.data.\*.fields.WebSite.html | string | | |
action_result.data.\*.fields.WebSite.value | string | | |
action_result.data.\*.hasError | boolean | | True False |
action_result.data.\*.lastPasswordResetDate | string | | 2013-01-28T15:07:15.117 |
action_result.data.\*.lastResetDateTime | string | | 2013-01-28T15:07:15.117 |
action_result.data.\*.ldapRequired | boolean | | True False |
action_result.data.\*.passwordNeverExpires | boolean | | True False |
action_result.data.\*.publicId | string | | Andrew Simms |
action_result.data.\*.recordId | string | `cherwell customer rec id` | 9354650fbf63b8f69623cd4b179bc739dabe2716c8 |
action_result.data.\*.securityGroupId | string | | 93373402da59635ba9e6164cf89364774a3a2bebb1 |
action_result.data.\*.shortDisplayName | string | | andrew |
action_result.data.\*.userCannotChangePassword | boolean | | True False |
action_result.data.\*.userMustResetPasswordAtNextLogin | boolean | | True False |
action_result.data.summary | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully retrieved user information |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get attachments'

List all of the attachments on a given incident

Type: **generic** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | ID of Incident | string | `cherwell incident id` |
**save_to_vault** | optional | Save Attachments To Vault | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | `cherwell incident id` | 102328 |
action_result.parameter.save_to_vault | boolean | | True False |
action_result.data.\*.attachedBusObId | string | | |
action_result.data.\*.attachedBusObRecId | string | | |
action_result.data.\*.attachmentFileId | string | | 943083f71082bbcafc5b8c44aa9f92e5f8779e70f6 |
action_result.data.\*.attachmentFileName | string | `url` | tor-logo.png |
action_result.data.\*.attachmentFileType | string | | .png |
action_result.data.\*.attachmentId | string | | 943083f7114efdfe77a9234240b6799cbc91afd934 |
action_result.data.\*.attachmentType | numeric | | 0 |
action_result.data.\*.busObId | string | `md5` | 6dd53665c0c24cab86870a21cf6434ae |
action_result.data.\*.busObRecId | string | | 94308336ffce2054555f9a4312b463b2d93833328a |
action_result.data.\*.comment | string | | |
action_result.data.\*.created | string | | 2017-11-22T01:37:44 |
action_result.data.\*.displayText | string | | tor-logo.png |
action_result.data.\*.owner | string | | |
action_result.data.\*.scope | numeric | | 0 |
action_result.data.\*.scopeOwner | string | | |
action_result.data.\*.type | numeric | | 1 |
action_result.data.\*.vault_id | string | `vault id` `sha1` | e6400081f30b3c2010605416cde61df3e840197e |
action_result.summary | string | | |
action_result.message | string | | Successfully Retrieved Attachments |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update ticket'

Update an incident

Type: **generic** \
Read only: **False**

The <b>other</b> field is used to change the <b>value</b> of some field in the incident. Any key which is returned in the incident's <b>fields</b> dictionary is okay to use. You will need to format this as a JSON object, so an example would be <code>{"Category": "Security Incident"}</code>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | ID of Incident to Update | string | `cherwell incident id` |
**file** | optional | Vault ID of File | string | `vault id` |
**other** | optional | JSON Key Pairs of other fields | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.file | string | `vault id` | e6400081f30b3c2010605416cde61df3e840197e |
action_result.parameter.id | string | `cherwell incident id` | 102328 |
action_result.parameter.other | string | | {"description": "Updated From Mission Control 2"} |
action_result.data.\*.busObPublicId | string | | 102328 |
action_result.data.\*.busObRecId | string | | 94308336ffce2054555f9a4312b463b2d93833328a |
action_result.data.\*.cacheKey | string | | |
action_result.data.\*.errorCode | string | | |
action_result.data.\*.errorMessage | string | | |
action_result.data.\*.hasError | boolean | | True False |
action_result.summary.attachment_id | string | | 94308f5eae60443524368d4995921598ca5236c949 |
action_result.message | string | | Successfully updated incident |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create ticket'

Create an incident

Type: **generic** \
Read only: **False**

Either a Public ID or a Record ID for a user must be used. When possible, try to use the Record ID over the Public ID. If both are present, the Public ID will be ignored.<br> The <b>other</b> field is used to change the <b>value</b> of some field in the incident. Any key which is returned in an incident's <b>fields</b> dictionary is okay to use. You will need to format this as a JSON object, so an example would be <code>{"Category": "Security Incident"}</code>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**description** | required | Incident Description | string | |
**priority** | required | Priority | string | |
**user_email_id** | required | Email ID of user who created ticket | string | `email` |
**other** | optional | JSON Key Pairs of other fields | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.description | string | | Created from Mission Control |
action_result.parameter.other | string | | |
action_result.parameter.priority | string | | 2 |
action_result.parameter.user_email_id | string | `email` | |
action_result.data.\*.busObPublicId | string | | 102328 |
action_result.data.\*.busObRecId | string | | 94308336ffce2054555f9a4312b463b2d93833328a |
action_result.data.\*.cacheKey | string | | |
action_result.data.\*.errorCode | string | | |
action_result.data.\*.errorMessage | string | | |
action_result.data.\*.hasError | boolean | | True False |
action_result.summary.id | string | `cherwell incident id` | |
action_result.message | string | | Successfully Created Ticket |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get ticket'

Get incident information

Type: **generic** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | ID of Incident | string | `cherwell incident id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | `cherwell incident id` | 102328 |
action_result.data.\*.busObId | string | `md5` | 6dd53665c0c24cab86870a21cf6434ae |
action_result.data.\*.busObPublicId | string | | 102328 |
action_result.data.\*.busObRecId | string | | 940d397afb64f874644d1a4126a5af80b9bd1e585c |
action_result.data.\*.errorCode | string | | |
action_result.data.\*.errorMessage | string | | |
action_result.data.\*.fields.ApprovalBlockID.dirty | boolean | | True False |
action_result.data.\*.fields.ApprovalBlockID.displayName | string | | ApprovalBlockID |
action_result.data.\*.fields.ApprovalBlockID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d57258fad7ad3979ff23442b96c4ed471fbbe2ce |
action_result.data.\*.fields.ApprovalBlockID.fullFieldId | string | | |
action_result.data.\*.fields.ApprovalBlockID.html | string | | |
action_result.data.\*.fields.ApprovalBlockID.value | string | | |
action_result.data.\*.fields.AssignedTeam.dirty | boolean | | False |
action_result.data.\*.fields.AssignedTeam.displayName | string | | Assigned Team |
action_result.data.\*.fields.AssignedTeam.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9339fc404e8d5299b7a7c64de79ab81a1c1ff4306c |
action_result.data.\*.fields.AssignedTeam.fullFieldId | string | | |
action_result.data.\*.fields.AssignedTeam.html | string | | |
action_result.data.\*.fields.AssignedTeam.value | string | | 1st Level Support |
action_result.data.\*.fields.AssignedTeamID.dirty | boolean | | False |
action_result.data.\*.fields.AssignedTeamID.displayName | string | | Assigned Team ID |
action_result.data.\*.fields.AssignedTeamID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9339fc404e312b6d43436041fc8af1c07c6197f559 |
action_result.data.\*.fields.AssignedTeamID.fullFieldId | string | | |
action_result.data.\*.fields.AssignedTeamID.html | string | | |
action_result.data.\*.fields.AssignedTeamID.value | string | | 9365b4e90592c81e3b7a024555a6c0094ba77e8773 |
action_result.data.\*.fields.AssignedTo.dirty | boolean | | False |
action_result.data.\*.fields.AssignedTo.displayName | string | | Assigned To |
action_result.data.\*.fields.AssignedTo.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9339fc404e4c93350bf5be446fb13d693b0bb7f219 |
action_result.data.\*.fields.AssignedTo.fullFieldId | string | | |
action_result.data.\*.fields.AssignedTo.html | string | | |
action_result.data.\*.fields.AssignedTo.value | string | | |
action_result.data.\*.fields.AssignedToID.dirty | boolean | | False |
action_result.data.\*.fields.AssignedToID.displayName | string | | Assigned To ID |
action_result.data.\*.fields.AssignedToID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9339fc404e39ae705648ab43969f29262e6d167606 |
action_result.data.\*.fields.AssignedToID.fullFieldId | string | | |
action_result.data.\*.fields.AssignedToID.html | string | | |
action_result.data.\*.fields.AssignedToID.value | string | | |
action_result.data.\*.fields.AssignedToManager.dirty | boolean | | False |
action_result.data.\*.fields.AssignedToManager.displayName | string | | Assigned To Manager |
action_result.data.\*.fields.AssignedToManager.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9378a8a981b9164941421e4bc6a17872b700662362 |
action_result.data.\*.fields.AssignedToManager.fullFieldId | string | | |
action_result.data.\*.fields.AssignedToManager.html | string | | |
action_result.data.\*.fields.AssignedToManager.value | string | | |
action_result.data.\*.fields.Barcode.dirty | boolean | | True False |
action_result.data.\*.fields.Barcode.displayName | string | | Barcode |
action_result.data.\*.fields.Barcode.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d732b321e7d87140ed0e452bb1c87f8675f92ea1 |
action_result.data.\*.fields.Barcode.fullFieldId | string | | |
action_result.data.\*.fields.Barcode.html | string | | |
action_result.data.\*.fields.Barcode.value | string | | |
action_result.data.\*.fields.BreachNotes.dirty | boolean | | True False |
action_result.data.\*.fields.BreachNotes.displayName | string | | Breach Notes |
action_result.data.\*.fields.BreachNotes.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938ccbf079ed406a1281c04c93bbe7db6d64a3ea80 |
action_result.data.\*.fields.BreachNotes.fullFieldId | string | | |
action_result.data.\*.fields.BreachNotes.html | string | | |
action_result.data.\*.fields.BreachNotes.value | string | | |
action_result.data.\*.fields.CICritical.dirty | boolean | | True False |
action_result.data.\*.fields.CICritical.displayName | string | | CI Critical |
action_result.data.\*.fields.CICritical.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938b8bd0b15a20714ce70247a58d6af1d3a00cdee1 |
action_result.data.\*.fields.CICritical.html | string | | |
action_result.data.\*.fields.CICritical.value | string | | False |
action_result.data.\*.fields.CIDownEndDateTime.dirty | boolean | | True False |
action_result.data.\*.fields.CIDownEndDateTime.displayName | string | | CI Down End Date/Time |
action_result.data.\*.fields.CIDownEndDateTime.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d59d10d3cb987a20f6df4aee89a329ee142b7eb0 |
action_result.data.\*.fields.CIDownEndDateTime.fullFieldId | string | | |
action_result.data.\*.fields.CIDownEndDateTime.html | string | | |
action_result.data.\*.fields.CIDownEndDateTime.value | string | | |
action_result.data.\*.fields.CIDownStartDateTime.dirty | boolean | | True False |
action_result.data.\*.fields.CIDownStartDateTime.displayName | string | | CI Down Start Date/Time |
action_result.data.\*.fields.CIDownStartDateTime.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d59d0fdc34ac19f5b86f4ff7ba7ad71426aee4e9 |
action_result.data.\*.fields.CIDownStartDateTime.fullFieldId | string | | |
action_result.data.\*.fields.CIDownStartDateTime.html | string | | |
action_result.data.\*.fields.CIDownStartDateTime.value | string | | |
action_result.data.\*.fields.CIDowntimeInMinutes.dirty | boolean | | True False |
action_result.data.\*.fields.CIDowntimeInMinutes.displayName | string | | CI Downtime in Minutes |
action_result.data.\*.fields.CIDowntimeInMinutes.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93db1f3bd38670cd4a6f114b589b2672e955901c5d |
action_result.data.\*.fields.CIDowntimeInMinutes.fullFieldId | string | | |
action_result.data.\*.fields.CIDowntimeInMinutes.html | string | | |
action_result.data.\*.fields.CIDowntimeInMinutes.value | string | | 0 |
action_result.data.\*.fields.CallSource.dirty | boolean | | False |
action_result.data.\*.fields.CallSource.displayName | string | | Call Source |
action_result.data.\*.fields.CallSource.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93670bdf8abe2cd1f92b1f490a90c7b7d684222e13 |
action_result.data.\*.fields.CallSource.fullFieldId | string | | |
action_result.data.\*.fields.CallSource.html | string | | |
action_result.data.\*.fields.CallSource.value | string | | Phone |
action_result.data.\*.fields.CartItemID.dirty | boolean | | True False |
action_result.data.\*.fields.CartItemID.displayName | string | | Cart Item ID |
action_result.data.\*.fields.CartItemID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:94008c4b2db6261ee7243243fb90b272e267eb7b7c |
action_result.data.\*.fields.CartItemID.fullFieldId | string | | |
action_result.data.\*.fields.CartItemID.html | string | | |
action_result.data.\*.fields.CartItemID.value | string | | |
action_result.data.\*.fields.Category.dirty | boolean | | True False |
action_result.data.\*.fields.Category.displayName | string | | Category |
action_result.data.\*.fields.Category.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9e0b434034e94781ab29598150f388aa |
action_result.data.\*.fields.Category.fullFieldId | string | | |
action_result.data.\*.fields.Category.html | string | | |
action_result.data.\*.fields.Category.value | string | | |
action_result.data.\*.fields.Cause.dirty | boolean | | True False |
action_result.data.\*.fields.Cause.displayName | string | | Cause |
action_result.data.\*.fields.Cause.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93da4900c37a84f3b9f43c48d1aa05b2b514bc0519 |
action_result.data.\*.fields.Cause.fullFieldId | string | | |
action_result.data.\*.fields.Cause.html | string | | |
action_result.data.\*.fields.Cause.value | string | | |
action_result.data.\*.fields.CausedByChangeRequest.dirty | boolean | | True False |
action_result.data.\*.fields.CausedByChangeRequest.displayName | string | | Caused By Change Request |
action_result.data.\*.fields.CausedByChangeRequest.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93fdb98628f9b16da86dbc4f9da6ee2e0bb5f53ab8 |
action_result.data.\*.fields.CausedByChangeRequest.html | string | | |
action_result.data.\*.fields.CausedByChangeRequest.value | string | | |
action_result.data.\*.fields.CausedByChangeRequestID.dirty | boolean | | True False |
action_result.data.\*.fields.CausedByChangeRequestID.displayName | string | | Caused By Change Request ID |
action_result.data.\*.fields.CausedByChangeRequestID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93fdb989a37a02691f853b41248a65df5c75174be1 |
action_result.data.\*.fields.CausedByChangeRequestID.html | string | | |
action_result.data.\*.fields.CausedByChangeRequestID.value | string | | |
action_result.data.\*.fields.CausedByChangeRequestLogicalField.dirty | boolean | | True False |
action_result.data.\*.fields.CausedByChangeRequestLogicalField.displayName | string | | Caused By Change Request Logical Field |
action_result.data.\*.fields.CausedByChangeRequestLogicalField.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93fdb98bc38349c47f9d504e9597502b6dd6c8d556 |
action_result.data.\*.fields.CausedByChangeRequestLogicalField.html | string | | |
action_result.data.\*.fields.CausedByChangeRequestLogicalField.value | string | | False |
action_result.data.\*.fields.CausedByChangeRequestReason.dirty | boolean | | True False |
action_result.data.\*.fields.CausedByChangeRequestReason.displayName | string | | Caused By Change Request Reason |
action_result.data.\*.fields.CausedByChangeRequestReason.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93fdb99b9074778dbde93d4375bcf9670d0c5223c5 |
action_result.data.\*.fields.CausedByChangeRequestReason.html | string | | |
action_result.data.\*.fields.CausedByChangeRequestReason.value | string | | |
action_result.data.\*.fields.CausedByLinkedChangeRequest.dirty | boolean | | True False |
action_result.data.\*.fields.CausedByLinkedChangeRequest.displayName | string | | Caused By Linked Change Request |
action_result.data.\*.fields.CausedByLinkedChangeRequest.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93fdb9a205e17af040fb7343428dfb3a61b5b279b2 |
action_result.data.\*.fields.CausedByLinkedChangeRequest.html | string | | |
action_result.data.\*.fields.CausedByLinkedChangeRequest.value | string | | |
action_result.data.\*.fields.ChangeID.dirty | boolean | | True False |
action_result.data.\*.fields.ChangeID.displayName | string | | Change Request ID |
action_result.data.\*.fields.ChangeID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93693fc5070dce3a8b2329485ea30770fd06fda4d6 |
action_result.data.\*.fields.ChangeID.fullFieldId | string | | |
action_result.data.\*.fields.ChangeID.html | string | | |
action_result.data.\*.fields.ChangeID.value | string | | |
action_result.data.\*.fields.Change_ID.dirty | boolean | | True False |
action_result.data.\*.fields.Change_ID.displayName | string | | Change_ID |
action_result.data.\*.fields.Change_ID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93fdb9a76f19cc42a92e654f849928b17662df54ee |
action_result.data.\*.fields.Change_ID.html | string | | |
action_result.data.\*.fields.Change_ID.value | string | | |
action_result.data.\*.fields.ClonedIncident.dirty | boolean | | True False |
action_result.data.\*.fields.ClonedIncident.displayName | string | | Cloned Incident |
action_result.data.\*.fields.ClonedIncident.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93daa4c522eb7f5e35a6284309afa51f08348a23a3 |
action_result.data.\*.fields.ClonedIncident.fullFieldId | string | | |
action_result.data.\*.fields.ClonedIncident.html | string | | |
action_result.data.\*.fields.ClonedIncident.value | string | | False |
action_result.data.\*.fields.ClonedIncidentID.dirty | boolean | | True False |
action_result.data.\*.fields.ClonedIncidentID.displayName | string | | Cloned IncidentID |
action_result.data.\*.fields.ClonedIncidentID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d59b02c6220ac9cad57e47ba8933451bad659965 |
action_result.data.\*.fields.ClonedIncidentID.fullFieldId | string | | |
action_result.data.\*.fields.ClonedIncidentID.html | string | | |
action_result.data.\*.fields.ClonedIncidentID.value | string | | |
action_result.data.\*.fields.CloseDescription.dirty | boolean | | True False |
action_result.data.\*.fields.CloseDescription.displayName | string | | Close Description |
action_result.data.\*.fields.CloseDescription.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93408334d3c89b364bf3b14933a74db085d0b47824 |
action_result.data.\*.fields.CloseDescription.fullFieldId | string | | |
action_result.data.\*.fields.CloseDescription.html | string | | |
action_result.data.\*.fields.CloseDescription.value | string | | |
action_result.data.\*.fields.ClosedBy.dirty | boolean | | True False |
action_result.data.\*.fields.ClosedBy.displayName | string | | Closed By |
action_result.data.\*.fields.ClosedBy.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:1ee8a71d62a247dfb23f91320a6eb911 |
action_result.data.\*.fields.ClosedBy.fullFieldId | string | | |
action_result.data.\*.fields.ClosedBy.html | string | | |
action_result.data.\*.fields.ClosedBy.value | string | | |
action_result.data.\*.fields.ClosedByID.dirty | boolean | | True False |
action_result.data.\*.fields.ClosedByID.displayName | string | | Closed By User ID |
action_result.data.\*.fields.ClosedByID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:4c361937395d4593ba0cff5b749a9356 |
action_result.data.\*.fields.ClosedByID.fullFieldId | string | | |
action_result.data.\*.fields.ClosedByID.html | string | | |
action_result.data.\*.fields.ClosedByID.value | string | | |
action_result.data.\*.fields.ClosedDateTime.dirty | boolean | | True False |
action_result.data.\*.fields.ClosedDateTime.displayName | string | | Closed Date Time |
action_result.data.\*.fields.ClosedDateTime.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:11b6961ee55048b9a7240f7e2d3a2f8d |
action_result.data.\*.fields.ClosedDateTime.fullFieldId | string | | |
action_result.data.\*.fields.ClosedDateTime.html | string | | |
action_result.data.\*.fields.ClosedDateTime.value | string | | |
action_result.data.\*.fields.ClosedOn1stCall.dirty | boolean | | True False |
action_result.data.\*.fields.ClosedOn1stCall.displayName | string | | Closed on 1st Call |
action_result.data.\*.fields.ClosedOn1stCall.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93666152f967560846b0c24439bc8d8eb3f1d92669 |
action_result.data.\*.fields.ClosedOn1stCall.fullFieldId | string | | |
action_result.data.\*.fields.ClosedOn1stCall.html | string | | |
action_result.data.\*.fields.ClosedOn1stCall.value | string | | False |
action_result.data.\*.fields.CombinedKB.dirty | boolean | | True False |
action_result.data.\*.fields.CombinedKB.displayName | string | | Combined KB |
action_result.data.\*.fields.CombinedKB.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93b23bc6cda4d63422459c4bda9198d4b6b3e81c27 |
action_result.data.\*.fields.CombinedKB.fullFieldId | string | | |
action_result.data.\*.fields.CombinedKB.html | string | | |
action_result.data.\*.fields.CombinedKB.value | string | | |
action_result.data.\*.fields.Comments.dirty | boolean | | True False |
action_result.data.\*.fields.Comments.displayName | string | | Comments |
action_result.data.\*.fields.Comments.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93db0f16a49b1f0232b5ee498ebfee566d48788088 |
action_result.data.\*.fields.Comments.fullFieldId | string | | |
action_result.data.\*.fields.Comments.html | string | | |
action_result.data.\*.fields.Comments.value | string | | |
action_result.data.\*.fields.CommentsEntry.dirty | boolean | | True False |
action_result.data.\*.fields.CommentsEntry.displayName | string | | Comments Entry |
action_result.data.\*.fields.CommentsEntry.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93db0f17616e9520ac3b0f4b6a9b721cbf221b7514 |
action_result.data.\*.fields.CommentsEntry.html | string | | |
action_result.data.\*.fields.CommentsEntry.value | string | | |
action_result.data.\*.fields.Confidence.dirty | boolean | | False |
action_result.data.\*.fields.Confidence.displayName | string | | Confidence |
action_result.data.\*.fields.Confidence.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9466bada92e1ec590066b6455ea01f78459bd9f10c |
action_result.data.\*.fields.Confidence.fullFieldId | string | | |
action_result.data.\*.fields.Confidence.html | string | | |
action_result.data.\*.fields.Confidence.value | string | | 0.39925352 |
action_result.data.\*.fields.ConfidenceLevelVerified.dirty | boolean | | False |
action_result.data.\*.fields.ConfidenceLevelVerified.displayName | string | | Confidence Level Verified |
action_result.data.\*.fields.ConfidenceLevelVerified.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9466bb18d9133efc0ba6d74d07aab222247b591996 |
action_result.data.\*.fields.ConfidenceLevelVerified.fullFieldId | string | | |
action_result.data.\*.fields.ConfidenceLevelVerified.html | string | | |
action_result.data.\*.fields.ConfidenceLevelVerified.value | string | | False |
action_result.data.\*.fields.ConfigItemDisplayName.dirty | boolean | | True False |
action_result.data.\*.fields.ConfigItemDisplayName.displayName | string | | Config Item Display Name |
action_result.data.\*.fields.ConfigItemDisplayName.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938b82597abb0a23ebc3ff459db5cdaffb4e4f5f49 |
action_result.data.\*.fields.ConfigItemDisplayName.fullFieldId | string | | |
action_result.data.\*.fields.ConfigItemDisplayName.html | string | | |
action_result.data.\*.fields.ConfigItemDisplayName.value | string | | |
action_result.data.\*.fields.ConfigItemRecID.dirty | boolean | | True False |
action_result.data.\*.fields.ConfigItemRecID.displayName | string | | ConfigItemRecID |
action_result.data.\*.fields.ConfigItemRecID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9354c1c37a136d59ef5e874940bd225039776d5778 |
action_result.data.\*.fields.ConfigItemRecID.fullFieldId | string | | |
action_result.data.\*.fields.ConfigItemRecID.html | string | | |
action_result.data.\*.fields.ConfigItemRecID.value | string | | |
action_result.data.\*.fields.ConfigItemType.dirty | boolean | | True False |
action_result.data.\*.fields.ConfigItemType.displayName | string | | Config Item Type |
action_result.data.\*.fields.ConfigItemType.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d5174bdfc03b4063def74bb98b8cfd8011133b09 |
action_result.data.\*.fields.ConfigItemType.fullFieldId | string | | |
action_result.data.\*.fields.ConfigItemType.html | string | | |
action_result.data.\*.fields.ConfigItemType.value | string | | |
action_result.data.\*.fields.ConfigItemTypeID.dirty | boolean | | True False |
action_result.data.\*.fields.ConfigItemTypeID.displayName | string | | ConfigItemTypeID |
action_result.data.\*.fields.ConfigItemTypeID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9354c1c350dd86fae5dac6438fb3956751ff65ec99 |
action_result.data.\*.fields.ConfigItemTypeID.fullFieldId | string | | |
action_result.data.\*.fields.ConfigItemTypeID.html | string | | |
action_result.data.\*.fields.ConfigItemTypeID.value | string | | |
action_result.data.\*.fields.Cost.dirty | boolean | | True False |
action_result.data.\*.fields.Cost.displayName | string | | Cost |
action_result.data.\*.fields.Cost.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9333dbdacf5dff2e347b794095a5ea2d5cb3407841 |
action_result.data.\*.fields.Cost.fullFieldId | string | | |
action_result.data.\*.fields.Cost.html | string | | |
action_result.data.\*.fields.Cost.value | string | | 0 |
action_result.data.\*.fields.CreatedBy.dirty | boolean | | True False |
action_result.data.\*.fields.CreatedBy.displayName | string | | Created By |
action_result.data.\*.fields.CreatedBy.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:290114239acc43cd92a7ee58acdc1da2 |
action_result.data.\*.fields.CreatedBy.fullFieldId | string | | |
action_result.data.\*.fields.CreatedBy.html | string | | |
action_result.data.\*.fields.CreatedBy.value | string | | Andrew Simms |
action_result.data.\*.fields.CreatedByEmail.dirty | boolean | | True False |
action_result.data.\*.fields.CreatedByEmail.displayName | string | | Created By Email |
action_result.data.\*.fields.CreatedByEmail.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9378a8aa39ca2890d9ddb84ae29d39db0ca05e425e |
action_result.data.\*.fields.CreatedByEmail.fullFieldId | string | | |
action_result.data.\*.fields.CreatedByEmail.html | string | | |
action_result.data.\*.fields.CreatedByEmail.value | string | `email` | andrew.simms@RiverTCorp.com |
action_result.data.\*.fields.CreatedByID.dirty | boolean | | True False |
action_result.data.\*.fields.CreatedByID.displayName | string | | Created By ID |
action_result.data.\*.fields.CreatedByID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:7605ee2ee7014f6999aa4f9280a9fdf9 |
action_result.data.\*.fields.CreatedByID.fullFieldId | string | | |
action_result.data.\*.fields.CreatedByID.html | string | | |
action_result.data.\*.fields.CreatedByID.value | string | `cherwell customer rec id` | 9354650fbf63b8f69623cd4b179bc739dabe2716c8 |
action_result.data.\*.fields.CreatedDateTime.dirty | boolean | | True False |
action_result.data.\*.fields.CreatedDateTime.displayName | string | | Created Date Time |
action_result.data.\*.fields.CreatedDateTime.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:c1e86f31eb2c4c5f8e8615a5189e9b19 |
action_result.data.\*.fields.CreatedDateTime.fullFieldId | string | | |
action_result.data.\*.fields.CreatedDateTime.html | string | | |
action_result.data.\*.fields.CreatedDateTime.value | string | | 11/22/2017 12:15 AM |
action_result.data.\*.fields.CreatedDuring.dirty | boolean | | True False |
action_result.data.\*.fields.CreatedDuring.displayName | string | | Created During |
action_result.data.\*.fields.CreatedDuring.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93e1db9dfb7c05a9c560b34ed09eac916a5134d385 |
action_result.data.\*.fields.CreatedDuring.fullFieldId | string | | |
action_result.data.\*.fields.CreatedDuring.html | string | | |
action_result.data.\*.fields.CreatedDuring.value | string | | |
action_result.data.\*.fields.CustomerDepartment.dirty | boolean | | False |
action_result.data.\*.fields.CustomerDepartment.displayName | string | | Customer Department |
action_result.data.\*.fields.CustomerDepartment.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:945906c8de1a7d9cfcb56c404cbf01fb1beb8636e9 |
action_result.data.\*.fields.CustomerDepartment.fullFieldId | string | | |
action_result.data.\*.fields.CustomerDepartment.html | string | | |
action_result.data.\*.fields.CustomerDepartment.value | string | | Sales & Marketing |
action_result.data.\*.fields.CustomerDisplayName.dirty | boolean | | True False |
action_result.data.\*.fields.CustomerDisplayName.displayName | string | | Customer Display Name |
action_result.data.\*.fields.CustomerDisplayName.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93734aaff77b19d1fcfd1d4b4aba1b0af895f25788 |
action_result.data.\*.fields.CustomerDisplayName.fullFieldId | string | | |
action_result.data.\*.fields.CustomerDisplayName.html | string | | |
action_result.data.\*.fields.CustomerDisplayName.value | string | | Anthony Edwards |
action_result.data.\*.fields.CustomerInformationIsNotCorrect.dirty | boolean | | True False |
action_result.data.\*.fields.CustomerInformationIsNotCorrect.displayName | string | | Customer Information is not Correct |
action_result.data.\*.fields.CustomerInformationIsNotCorrect.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93adf30981d44cbf1499044c509a979079ba3adb5f |
action_result.data.\*.fields.CustomerInformationIsNotCorrect.html | string | | |
action_result.data.\*.fields.CustomerInformationIsNotCorrect.value | string | | False |
action_result.data.\*.fields.CustomerRecID.dirty | boolean | | True False |
action_result.data.\*.fields.CustomerRecID.displayName | string | | Customer ID |
action_result.data.\*.fields.CustomerRecID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:933bd530833c64efbf66f84114acabb3e90c6d7b8f |
action_result.data.\*.fields.CustomerRecID.fullFieldId | string | | |
action_result.data.\*.fields.CustomerRecID.html | string | | |
action_result.data.\*.fields.CustomerRecID.value | string | | 9365da079bcfdb353b99df46b891e8700c456f91b9 |
action_result.data.\*.fields.CustomerSubscriptionLevel.dirty | boolean | | True False |
action_result.data.\*.fields.CustomerSubscriptionLevel.displayName | string | | Customer Subscription Level |
action_result.data.\*.fields.CustomerSubscriptionLevel.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:940040e3a88954e682a92342479a772758118abc53 |
action_result.data.\*.fields.CustomerSubscriptionLevel.fullFieldId | string | | |
action_result.data.\*.fields.CustomerSubscriptionLevel.html | string | | |
action_result.data.\*.fields.CustomerSubscriptionLevel.value | string | | |
action_result.data.\*.fields.CustomerTypeID.dirty | boolean | | True False |
action_result.data.\*.fields.CustomerTypeID.displayName | string | | Customer Type ID |
action_result.data.\*.fields.CustomerTypeID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:933bd53016ea4897701ab341abb2925340b5e8c3df |
action_result.data.\*.fields.CustomerTypeID.fullFieldId | string | | |
action_result.data.\*.fields.CustomerTypeID.html | string | | |
action_result.data.\*.fields.CustomerTypeID.value | string | | |
action_result.data.\*.fields.DefaultTeam.dirty | boolean | | True False |
action_result.data.\*.fields.DefaultTeam.displayName | string | | Default Team |
action_result.data.\*.fields.DefaultTeam.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93f730918e4f7106e1bfff420fbf8a9332a6b8d22a |
action_result.data.\*.fields.DefaultTeam.fullFieldId | string | | |
action_result.data.\*.fields.DefaultTeam.html | string | | |
action_result.data.\*.fields.DefaultTeam.value | string | | |
action_result.data.\*.fields.Description.dirty | boolean | | True False |
action_result.data.\*.fields.Description.displayName | string | | Description |
action_result.data.\*.fields.Description.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:252b836fc72c4149915053ca1131d138 |
action_result.data.\*.fields.Description.fullFieldId | string | | |
action_result.data.\*.fields.Description.html | string | | Updated From Mission Control 2 |
action_result.data.\*.fields.Description.value | string | | Updated From Mission Control 2 |
action_result.data.\*.fields.DescriptionSentimentValue.dirty | boolean | | False |
action_result.data.\*.fields.DescriptionSentimentValue.displayName | string | | Description Sentiment Value |
action_result.data.\*.fields.DescriptionSentimentValue.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:945b8ce73cffb9fc2f0e0c48fbac7739dd374476ad |
action_result.data.\*.fields.DescriptionSentimentValue.fullFieldId | string | | |
action_result.data.\*.fields.DescriptionSentimentValue.html | string | | |
action_result.data.\*.fields.DescriptionSentimentValue.value | string | | -4 |
action_result.data.\*.fields.Detail.dirty | boolean | | True False |
action_result.data.\*.fields.Detail.displayName | string | | Detail |
action_result.data.\*.fields.Detail.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9369258724d81940ae86874633864d87646f137dd8 |
action_result.data.\*.fields.Detail.html | string | | |
action_result.data.\*.fields.Detail.value | string | | |
action_result.data.\*.fields.EmailNotifications.dirty | boolean | | False |
action_result.data.\*.fields.EmailNotifications.displayName | string | | Email Notifications |
action_result.data.\*.fields.EmailNotifications.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9450a01aae6f68e1deec754425aef231f753f4a24a |
action_result.data.\*.fields.EmailNotifications.fullFieldId | string | | |
action_result.data.\*.fields.EmailNotifications.html | string | | |
action_result.data.\*.fields.EmailNotifications.value | string | | |
action_result.data.\*.fields.HasNoOpenTasks.dirty | boolean | | True False |
action_result.data.\*.fields.HasNoOpenTasks.displayName | string | | Has No Open Tasks |
action_result.data.\*.fields.HasNoOpenTasks.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d8e75db276ba562f05794dc380c30904c3089075 |
action_result.data.\*.fields.HasNoOpenTasks.html | string | | |
action_result.data.\*.fields.HasNoOpenTasks.value | string | | True |
action_result.data.\*.fields.ISMSAuditsID.dirty | boolean | | False |
action_result.data.\*.fields.ISMSAuditsID.displayName | string | | ISMS Audit ID |
action_result.data.\*.fields.ISMSAuditsID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:94257a2808fd0545bd8fde4a5bb56419bf526aab2e |
action_result.data.\*.fields.ISMSAuditsID.fullFieldId | string | | |
action_result.data.\*.fields.ISMSAuditsID.html | string | | |
action_result.data.\*.fields.ISMSAuditsID.value | string | | |
action_result.data.\*.fields.Impact.dirty | boolean | | True False |
action_result.data.\*.fields.Impact.displayName | string | | Impact |
action_result.data.\*.fields.Impact.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:ae05c132527e48bd95d063c445622df7 |
action_result.data.\*.fields.Impact.fullFieldId | string | | |
action_result.data.\*.fields.Impact.html | string | | |
action_result.data.\*.fields.Impact.value | string | | |
action_result.data.\*.fields.IncidentDurationInDays.dirty | boolean | | True False |
action_result.data.\*.fields.IncidentDurationInDays.displayName | string | | IncidentDurationInDays |
action_result.data.\*.fields.IncidentDurationInDays.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9362bc0befc77c0d2195e6456494a175b7bb8e3fc9 |
action_result.data.\*.fields.IncidentDurationInDays.fullFieldId | string | | |
action_result.data.\*.fields.IncidentDurationInDays.html | string | | |
action_result.data.\*.fields.IncidentDurationInDays.value | string | | 0 |
action_result.data.\*.fields.IncidentDurationInHours.dirty | boolean | | True False |
action_result.data.\*.fields.IncidentDurationInHours.displayName | string | | IncidentDurationInHours |
action_result.data.\*.fields.IncidentDurationInHours.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:936fb555ea6468d60b213d42d59b7221238e67b1cd |
action_result.data.\*.fields.IncidentDurationInHours.fullFieldId | string | | |
action_result.data.\*.fields.IncidentDurationInHours.html | string | | |
action_result.data.\*.fields.IncidentDurationInHours.value | string | | 0 |
action_result.data.\*.fields.IncidentID.dirty | boolean | | True False |
action_result.data.\*.fields.IncidentID.displayName | string | | Incident ID |
action_result.data.\*.fields.IncidentID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:6ae282c55e8e4266ae66ffc070c17fa3 |
action_result.data.\*.fields.IncidentID.fullFieldId | string | | |
action_result.data.\*.fields.IncidentID.html | string | | |
action_result.data.\*.fields.IncidentID.value | string | | 102328 |
action_result.data.\*.fields.IncidentType.dirty | boolean | | True False |
action_result.data.\*.fields.IncidentType.displayName | string | | Incident Type |
action_result.data.\*.fields.IncidentType.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9365a6098398ff2551e1c14dd398c466d5a201a9c7 |
action_result.data.\*.fields.IncidentType.fullFieldId | string | | |
action_result.data.\*.fields.IncidentType.html | string | | |
action_result.data.\*.fields.IncidentType.value | string | | Incident |
action_result.data.\*.fields.IncidentchildID.dirty | boolean | | False |
action_result.data.\*.fields.IncidentchildID.displayName | string | | Incident childID |
action_result.data.\*.fields.IncidentchildID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d9c675e5526fed36e03a4b5ca74dbbd5c1c9e79b |
action_result.data.\*.fields.IncidentchildID.fullFieldId | string | | |
action_result.data.\*.fields.IncidentchildID.html | string | | |
action_result.data.\*.fields.IncidentchildID.value | string | | |
action_result.data.\*.fields.IncidentchildRecID.dirty | boolean | | False |
action_result.data.\*.fields.IncidentchildRecID.displayName | string | | Incident child RecID |
action_result.data.\*.fields.IncidentchildRecID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d9c67b0ce7bea107da5242d7a2574bde0d5f3579 |
action_result.data.\*.fields.IncidentchildRecID.fullFieldId | string | | |
action_result.data.\*.fields.IncidentchildRecID.html | string | | |
action_result.data.\*.fields.IncidentchildRecID.value | string | | |
action_result.data.\*.fields.InitialITContact.dirty | boolean | | True False |
action_result.data.\*.fields.InitialITContact.displayName | string | | InitialITContact |
action_result.data.\*.fields.InitialITContact.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9378a8aad1835b5d96da4a496b9141f1ad956f954f |
action_result.data.\*.fields.InitialITContact.html | string | | |
action_result.data.\*.fields.InitialITContact.value | string | | Andrew Simms |
action_result.data.\*.fields.InitialITContactEmail.dirty | boolean | | True False |
action_result.data.\*.fields.InitialITContactEmail.displayName | string | | InitialITContactEmail |
action_result.data.\*.fields.InitialITContactEmail.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9378a8ab1eb5ae8d58c3ab4703adf2f49180a6574c |
action_result.data.\*.fields.InitialITContactEmail.html | string | | |
action_result.data.\*.fields.InitialITContactEmail.value | string | `email` | andrew.simms@RiverTCorp.com |
action_result.data.\*.fields.IsPrivate.dirty | boolean | | True False |
action_result.data.\*.fields.IsPrivate.displayName | string | | IsPrivate |
action_result.data.\*.fields.IsPrivate.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93331ee909bf8efac0faa849259ccaff4c5b41418a |
action_result.data.\*.fields.IsPrivate.html | string | | |
action_result.data.\*.fields.IsPrivate.value | string | | False |
action_result.data.\*.fields.JiraID.dirty | boolean | | True False |
action_result.data.\*.fields.JiraID.displayName | string | | Jira ID |
action_result.data.\*.fields.JiraID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9403da45167d624fba188c4bd0b54aef4fc3f338f0 |
action_result.data.\*.fields.JiraID.html | string | | |
action_result.data.\*.fields.JiraID.value | string | | 0 |
action_result.data.\*.fields.JiraIssueKey.dirty | boolean | | True False |
action_result.data.\*.fields.JiraIssueKey.displayName | string | | Jira Issue Key |
action_result.data.\*.fields.JiraIssueKey.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:940419ae30aee7ed049d29434885343cf7d85ea789 |
action_result.data.\*.fields.JiraIssueKey.html | string | | |
action_result.data.\*.fields.JiraIssueKey.value | string | | |
action_result.data.\*.fields.JiraLinkedIssueKey.dirty | boolean | | True False |
action_result.data.\*.fields.JiraLinkedIssueKey.displayName | string | | Jira Linked Issue Key |
action_result.data.\*.fields.JiraLinkedIssueKey.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:940444f3b85111a5495a1a4e64921bae33d9c6f005 |
action_result.data.\*.fields.JiraLinkedIssueKey.html | string | | |
action_result.data.\*.fields.JiraLinkedIssueKey.value | string | | |
action_result.data.\*.fields.JiraProjectKey.dirty | boolean | | True False |
action_result.data.\*.fields.JiraProjectKey.displayName | string | | Jira Project Key |
action_result.data.\*.fields.JiraProjectKey.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9403db0d1ed435a90c2fe3445b983b3f5732a5a704 |
action_result.data.\*.fields.JiraProjectKey.html | string | | |
action_result.data.\*.fields.JiraProjectKey.value | string | | |
action_result.data.\*.fields.KnowledgeArticleID.dirty | boolean | | False |
action_result.data.\*.fields.KnowledgeArticleID.displayName | string | | Knowledge Article ID |
action_result.data.\*.fields.KnowledgeArticleID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:94550eacabe006baf00e4c468eac86ed1d033c903f |
action_result.data.\*.fields.KnowledgeArticleID.fullFieldId | string | | |
action_result.data.\*.fields.KnowledgeArticleID.html | string | | |
action_result.data.\*.fields.KnowledgeArticleID.value | string | | |
action_result.data.\*.fields.LastModBy.dirty | boolean | | True False |
action_result.data.\*.fields.LastModBy.displayName | string | | Last Modified By |
action_result.data.\*.fields.LastModBy.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93543557880cda6dfd1f3c40fdb59d21ce9f9b4dd7 |
action_result.data.\*.fields.LastModBy.fullFieldId | string | | |
action_result.data.\*.fields.LastModBy.html | string | | |
action_result.data.\*.fields.LastModBy.value | string | | Andrew Simms |
action_result.data.\*.fields.LastModByID.dirty | boolean | | True False |
action_result.data.\*.fields.LastModByID.displayName | string | | Last Modified By ID |
action_result.data.\*.fields.LastModByID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9354355788388b8d9f90b94084948007c340e2190b |
action_result.data.\*.fields.LastModByID.fullFieldId | string | | |
action_result.data.\*.fields.LastModByID.html | string | | |
action_result.data.\*.fields.LastModByID.value | string | | 9354650fbf63b8f69623cd4b179bc739dabe2716c8 |
action_result.data.\*.fields.LastModTimeStamp.dirty | boolean | | True False |
action_result.data.\*.fields.LastModTimeStamp.displayName | string | | LastModTimeStamp |
action_result.data.\*.fields.LastModTimeStamp.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9334f089403f8acc055058449096cb5f0a33d48ffa |
action_result.data.\*.fields.LastModTimeStamp.fullFieldId | string | | |
action_result.data.\*.fields.LastModTimeStamp.html | string | | |
action_result.data.\*.fields.LastModTimeStamp.value | string | | |
action_result.data.\*.fields.LastModifiedByEmail.dirty | boolean | | True False |
action_result.data.\*.fields.LastModifiedByEmail.displayName | string | | Last Modified By Email |
action_result.data.\*.fields.LastModifiedByEmail.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9384dac7b7222cc7d9061f42a399307ab10d46ab02 |
action_result.data.\*.fields.LastModifiedByEmail.html | string | | |
action_result.data.\*.fields.LastModifiedByEmail.value | string | `email` | andrew.simms@RiverTCorp.com |
action_result.data.\*.fields.LastModifiedDateTime.dirty | boolean | | True False |
action_result.data.\*.fields.LastModifiedDateTime.displayName | string | | Last Modified Date Time |
action_result.data.\*.fields.LastModifiedDateTime.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93543557882ad94503745843c9a380aa0c380935c8 |
action_result.data.\*.fields.LastModifiedDateTime.fullFieldId | string | | |
action_result.data.\*.fields.LastModifiedDateTime.html | string | | |
action_result.data.\*.fields.LastModifiedDateTime.value | string | | 11/22/2017 10:23 PM |
action_result.data.\*.fields.Level2EscalationComplete.dirty | boolean | | True False |
action_result.data.\*.fields.Level2EscalationComplete.displayName | string | | Level 2 Escalation Complete |
action_result.data.\*.fields.Level2EscalationComplete.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93f72f4265297ab2b933434fd0abbf23dc33ce7872 |
action_result.data.\*.fields.Level2EscalationComplete.fullFieldId | string | | |
action_result.data.\*.fields.Level2EscalationComplete.html | string | | |
action_result.data.\*.fields.Level2EscalationComplete.value | string | | False |
action_result.data.\*.fields.Level2EscalationTeam.dirty | boolean | | True False |
action_result.data.\*.fields.Level2EscalationTeam.displayName | string | | Level 2 Escalation Team |
action_result.data.\*.fields.Level2EscalationTeam.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93f73092056e3faeadda19449fbd2fa6e895c32d03 |
action_result.data.\*.fields.Level2EscalationTeam.fullFieldId | string | | |
action_result.data.\*.fields.Level2EscalationTeam.html | string | | |
action_result.data.\*.fields.Level2EscalationTeam.value | string | | |
action_result.data.\*.fields.Level3EscalationComplete.dirty | boolean | | True False |
action_result.data.\*.fields.Level3EscalationComplete.displayName | string | | Level 3 Escalation Complete |
action_result.data.\*.fields.Level3EscalationComplete.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93f72f42d41a8e09567f3843d2bd12651a0465c20d |
action_result.data.\*.fields.Level3EscalationComplete.fullFieldId | string | | |
action_result.data.\*.fields.Level3EscalationComplete.html | string | | |
action_result.data.\*.fields.Level3EscalationComplete.value | string | | False |
action_result.data.\*.fields.Level3EscalationTeam.dirty | boolean | | True False |
action_result.data.\*.fields.Level3EscalationTeam.displayName | string | | Level 3 Escalation Team |
action_result.data.\*.fields.Level3EscalationTeam.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93f730928cf9f013a2a04147bb8d3d774c4dd37d98 |
action_result.data.\*.fields.Level3EscalationTeam.fullFieldId | string | | |
action_result.data.\*.fields.Level3EscalationTeam.html | string | | |
action_result.data.\*.fields.Level3EscalationTeam.value | string | | |
action_result.data.\*.fields.LinkedProblem.dirty | boolean | | True False |
action_result.data.\*.fields.LinkedProblem.displayName | string | | Linked Problem |
action_result.data.\*.fields.LinkedProblem.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9345e50743c7ae58b873ab4ef8b98bd09cc736daa6 |
action_result.data.\*.fields.LinkedProblem.fullFieldId | string | | |
action_result.data.\*.fields.LinkedProblem.html | string | | |
action_result.data.\*.fields.LinkedProblem.value | string | | |
action_result.data.\*.fields.LinkedSLAs.dirty | boolean | | True False |
action_result.data.\*.fields.LinkedSLAs.displayName | string | | Linked SLAs |
action_result.data.\*.fields.LinkedSLAs.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938a9f3a5930a63e41286e4ca88ae5b1b791e8b95c |
action_result.data.\*.fields.LinkedSLAs.fullFieldId | string | | |
action_result.data.\*.fields.LinkedSLAs.html | string | | |
action_result.data.\*.fields.LinkedSLAs.value | string | | , , |
action_result.data.\*.fields.LinkedToProblem.dirty | boolean | | False |
action_result.data.\*.fields.LinkedToProblem.displayName | string | | Linked to Problem |
action_result.data.\*.fields.LinkedToProblem.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9458ab93f0c6109033f84b4eeb91b184e14d5dd93f |
action_result.data.\*.fields.LinkedToProblem.fullFieldId | string | | |
action_result.data.\*.fields.LinkedToProblem.html | string | | |
action_result.data.\*.fields.LinkedToProblem.value | string | | False |
action_result.data.\*.fields.Location.dirty | boolean | | True False |
action_result.data.\*.fields.Location.displayName | string | | Location |
action_result.data.\*.fields.Location.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93bb341125a3afd2fe7c8b4c4cb856d9abae559bda |
action_result.data.\*.fields.Location.fullFieldId | string | | |
action_result.data.\*.fields.Location.html | string | | |
action_result.data.\*.fields.Location.value | string | | Colorado Springs |
action_result.data.\*.fields.MLReviewDatetime.dirty | boolean | | False |
action_result.data.\*.fields.MLReviewDatetime.displayName | string | | ML Review Datetime |
action_result.data.\*.fields.MLReviewDatetime.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:94679c2bf80ac7d6d2212541a7a9476bd20475fd7e |
action_result.data.\*.fields.MLReviewDatetime.fullFieldId | string | | |
action_result.data.\*.fields.MLReviewDatetime.html | string | | |
action_result.data.\*.fields.MLReviewDatetime.value | string | | 4/14/2022 10:22 AM |
action_result.data.\*.fields.MajorIncident.dirty | boolean | | True False |
action_result.data.\*.fields.MajorIncident.displayName | string | | Major Incident |
action_result.data.\*.fields.MajorIncident.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d74010759f36dcb8043e449785e3eab689b47ad7 |
action_result.data.\*.fields.MajorIncident.fullFieldId | string | | |
action_result.data.\*.fields.MajorIncident.html | string | | |
action_result.data.\*.fields.MajorIncident.value | string | | False |
action_result.data.\*.fields.MajorIncidentID.dirty | boolean | | True False |
action_result.data.\*.fields.MajorIncidentID.displayName | string | | Major Incident ID |
action_result.data.\*.fields.MajorIncidentID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d7400f44b2d3a890065d4cd8828d0d742531d09b |
action_result.data.\*.fields.MajorIncidentID.fullFieldId | string | | |
action_result.data.\*.fields.MajorIncidentID.html | string | | |
action_result.data.\*.fields.MajorIncidentID.value | string | | |
action_result.data.\*.fields.MajorIncidentRecID.dirty | boolean | | True False |
action_result.data.\*.fields.MajorIncidentRecID.displayName | string | | Major Incident RecID |
action_result.data.\*.fields.MajorIncidentRecID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d7400f0abe386d6d70514960ab168e25c2cd4ae6 |
action_result.data.\*.fields.MajorIncidentRecID.fullFieldId | string | | |
action_result.data.\*.fields.MajorIncidentRecID.html | string | | |
action_result.data.\*.fields.MajorIncidentRecID.value | string | | |
action_result.data.\*.fields.MatchingText.dirty | boolean | | True False |
action_result.data.\*.fields.MatchingText.displayName | string | | Matching Text |
action_result.data.\*.fields.MatchingText.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9388aaeb3e7d9b7a9b23f24996acc873f1e621b9c5 |
action_result.data.\*.fields.MatchingText.html | string | | |
action_result.data.\*.fields.MatchingText.value | string | | |
action_result.data.\*.fields.MultipleConfig.dirty | boolean | | True False |
action_result.data.\*.fields.MultipleConfig.displayName | string | | MultipleConfig |
action_result.data.\*.fields.MultipleConfig.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93694cd54559b234b626734f929b84eb9535d071d9 |
action_result.data.\*.fields.MultipleConfig.html | string | | |
action_result.data.\*.fields.MultipleConfig.value | string | | False |
action_result.data.\*.fields.NetworkEventID.dirty | boolean | | False |
action_result.data.\*.fields.NetworkEventID.displayName | string | | Network Event ID |
action_result.data.\*.fields.NetworkEventID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:942579a0f678c44aed9ca44fa2ab2fda6290a89881 |
action_result.data.\*.fields.NetworkEventID.fullFieldId | string | | |
action_result.data.\*.fields.NetworkEventID.html | string | | |
action_result.data.\*.fields.NetworkEventID.value | string | | |
action_result.data.\*.fields.NeverFixedIncident.dirty | boolean | | True False |
action_result.data.\*.fields.NeverFixedIncident.displayName | string | | Never Fixed Incident |
action_result.data.\*.fields.NeverFixedIncident.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d59b06b8fb5fc182b080466799708ba1e8968e16 |
action_result.data.\*.fields.NeverFixedIncident.html | string | | |
action_result.data.\*.fields.NeverFixedIncident.value | string | | False |
action_result.data.\*.fields.NextStatus.dirty | boolean | | True False |
action_result.data.\*.fields.NextStatus.displayName | string | | Next Status |
action_result.data.\*.fields.NextStatus.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93c24c9d7237a5e9ce37a24715b5ac4fa1703a831c |
action_result.data.\*.fields.NextStatus.fullFieldId | string | | |
action_result.data.\*.fields.NextStatus.html | string | | |
action_result.data.\*.fields.NextStatus.value | string | | Resolved |
action_result.data.\*.fields.NextStatusOneStep.dirty | boolean | | True False |
action_result.data.\*.fields.NextStatusOneStep.displayName | string | | Next Status OneStep |
action_result.data.\*.fields.NextStatusOneStep.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93c24ca88382d62a89eb4f4fb0bee7afd5ba418671 |
action_result.data.\*.fields.NextStatusOneStep.fullFieldId | string | | |
action_result.data.\*.fields.NextStatusOneStep.html | string | | |
action_result.data.\*.fields.NextStatusOneStep.value | string | | <Trebuchet>\<ActionInfoDef ID="93d969bb1308 |
action_result.data.\*.fields.NextStatusText.dirty | boolean | | True False |
action_result.data.\*.fields.NextStatusText.displayName | string | | Next Status Text |
action_result.data.\*.fields.NextStatusText.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93c24ca7c24d6f9c11a3684a1ab7509bd69e1d581a |
action_result.data.\*.fields.NextStatusText.fullFieldId | string | | |
action_result.data.\*.fields.NextStatusText.html | string | | |
action_result.data.\*.fields.NextStatusText.value | string | | Resolve |
action_result.data.\*.fields.NoOneStep.dirty | boolean | | True False |
action_result.data.\*.fields.NoOneStep.displayName | string | | NoOneStep |
action_result.data.\*.fields.NoOneStep.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93c418a4913d3e31e3af41427ab0513d695fcbbe35 |
action_result.data.\*.fields.NoOneStep.html | string | | |
action_result.data.\*.fields.NoOneStep.value | string | | False |
action_result.data.\*.fields.NoteEntry.dirty | boolean | | True False |
action_result.data.\*.fields.NoteEntry.displayName | string | | Note Entry |
action_result.data.\*.fields.NoteEntry.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9389e62015d892ebfbd4d74982a5e68c874921a998 |
action_result.data.\*.fields.NoteEntry.html | string | | |
action_result.data.\*.fields.NoteEntry.value | string | | |
action_result.data.\*.fields.Notes.dirty | boolean | | True False |
action_result.data.\*.fields.Notes.displayName | string | | Notes |
action_result.data.\*.fields.Notes.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9389e61f772cd2f7be5a0d4e1791625178cd9ebee0 |
action_result.data.\*.fields.Notes.html | string | | |
action_result.data.\*.fields.Notes.value | string | | |
action_result.data.\*.fields.OnBehalfOf.dirty | boolean | | False |
action_result.data.\*.fields.OnBehalfOf.displayName | string | | On Behalf Of |
action_result.data.\*.fields.OnBehalfOf.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9450a01dde5721fb08fef04257b82d73d320191342 |
action_result.data.\*.fields.OnBehalfOf.fullFieldId | string | | |
action_result.data.\*.fields.OnBehalfOf.html | string | | |
action_result.data.\*.fields.OnBehalfOf.value | string | | False |
action_result.data.\*.fields.OneStepPicker.dirty | boolean | | True False |
action_result.data.\*.fields.OneStepPicker.displayName | string | | One-Step Picker |
action_result.data.\*.fields.OneStepPicker.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93940af502ad52ad9039d6417d9348e4b21904d3a2 |
action_result.data.\*.fields.OneStepPicker.html | string | | |
action_result.data.\*.fields.OneStepPicker.value | string | | |
action_result.data.\*.fields.OriginalConfidence.dirty | boolean | | False |
action_result.data.\*.fields.OriginalConfidence.displayName | string | | Original Confidence |
action_result.data.\*.fields.OriginalConfidence.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9467a993dd5b55e3b635a24bdb82efbe043c7673d4 |
action_result.data.\*.fields.OriginalConfidence.fullFieldId | string | | |
action_result.data.\*.fields.OriginalConfidence.html | string | | |
action_result.data.\*.fields.OriginalConfidence.value | string | | 0 |
action_result.data.\*.fields.OriginalIncidentID.dirty | boolean | | True False |
action_result.data.\*.fields.OriginalIncidentID.displayName | string | | Original IncidentID |
action_result.data.\*.fields.OriginalIncidentID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d59b03b8c3e925cd0db44f23af491237f827e871 |
action_result.data.\*.fields.OriginalIncidentID.html | string | | |
action_result.data.\*.fields.OriginalIncidentID.value | string | | |
action_result.data.\*.fields.OutsourcedService.dirty | boolean | | True False |
action_result.data.\*.fields.OutsourcedService.displayName | string | | Outsourced Service |
action_result.data.\*.fields.OutsourcedService.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938390e0d850abec1b43a04eceace9bb2ed6007bcd |
action_result.data.\*.fields.OutsourcedService.html | string | | |
action_result.data.\*.fields.OutsourcedService.value | string | | False |
action_result.data.\*.fields.OutsourcedVendorID.dirty | boolean | | True False |
action_result.data.\*.fields.OutsourcedVendorID.displayName | string | | Outsourced Vendor ID |
action_result.data.\*.fields.OutsourcedVendorID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938390e14e876759f6f9034e6f84114ef8c6f3920e |
action_result.data.\*.fields.OutsourcedVendorID.html | string | | |
action_result.data.\*.fields.OutsourcedVendorID.value | string | | |
action_result.data.\*.fields.OutsourcedVendorName.dirty | boolean | | True False |
action_result.data.\*.fields.OutsourcedVendorName.displayName | string | | Outsourced Vendor Name |
action_result.data.\*.fields.OutsourcedVendorName.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938390e19c5d2c8a452ed8490f9ed8f100c8e5f9da |
action_result.data.\*.fields.OutsourcedVendorName.html | string | | |
action_result.data.\*.fields.OutsourcedVendorName.value | string | | |
action_result.data.\*.fields.OwnedBy.dirty | boolean | | True False |
action_result.data.\*.fields.OwnedBy.displayName | string | | Owned By |
action_result.data.\*.fields.OwnedBy.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9339fc404e4c93350bf5be446fb13d693b0bb7f219 |
action_result.data.\*.fields.OwnedBy.html | string | | |
action_result.data.\*.fields.OwnedBy.value | string | | |
action_result.data.\*.fields.OwnedByEmail.dirty | boolean | | True False |
action_result.data.\*.fields.OwnedByEmail.displayName | string | | Owned By Email |
action_result.data.\*.fields.OwnedByEmail.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:936d538f1d13d29750fc1348c495e79ff858f2ae6e |
action_result.data.\*.fields.OwnedByEmail.html | string | | |
action_result.data.\*.fields.OwnedByEmail.value | string | | |
action_result.data.\*.fields.OwnedByID.dirty | boolean | | True False |
action_result.data.\*.fields.OwnedByID.displayName | string | | Owned By ID |
action_result.data.\*.fields.OwnedByID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9339fc404e39ae705648ab43969f29262e6d167606 |
action_result.data.\*.fields.OwnedByID.html | string | | |
action_result.data.\*.fields.OwnedByID.value | string | | |
action_result.data.\*.fields.OwnedByManager.dirty | boolean | | True False |
action_result.data.\*.fields.OwnedByManager.displayName | string | | Owned By Manager |
action_result.data.\*.fields.OwnedByManager.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9378a8a981b9164941421e4bc6a17872b700662362 |
action_result.data.\*.fields.OwnedByManager.html | string | | |
action_result.data.\*.fields.OwnedByManager.value | string | | |
action_result.data.\*.fields.OwnedByManagerEmail.dirty | boolean | | True False |
action_result.data.\*.fields.OwnedByManagerEmail.displayName | string | | Owned By Manager Email |
action_result.data.\*.fields.OwnedByManagerEmail.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9378a8a9de111768e5b382449bb419b5df28efa684 |
action_result.data.\*.fields.OwnedByManagerEmail.html | string | | |
action_result.data.\*.fields.OwnedByManagerEmail.value | string | | |
action_result.data.\*.fields.OwnedByTeam.dirty | boolean | | True False |
action_result.data.\*.fields.OwnedByTeam.displayName | string | | Owned By Team |
action_result.data.\*.fields.OwnedByTeam.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9339fc404e8d5299b7a7c64de79ab81a1c1ff4306c |
action_result.data.\*.fields.OwnedByTeam.html | string | | |
action_result.data.\*.fields.OwnedByTeam.value | string | | |
action_result.data.\*.fields.OwnedByTeamID.dirty | boolean | | True False |
action_result.data.\*.fields.OwnedByTeamID.displayName | string | | Owned By Team ID |
action_result.data.\*.fields.OwnedByTeamID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9339fc404e312b6d43436041fc8af1c07c6197f559 |
action_result.data.\*.fields.OwnedByTeamID.html | string | | |
action_result.data.\*.fields.OwnedByTeamID.value | string | | |
action_result.data.\*.fields.OwnedByWorkgroup.dirty | boolean | | True False |
action_result.data.\*.fields.OwnedByWorkgroup.displayName | string | | Owned By Workgroup |
action_result.data.\*.fields.OwnedByWorkgroup.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93e47e971a991ba1c902084c30820ed50008d27293 |
action_result.data.\*.fields.OwnedByWorkgroup.html | string | | |
action_result.data.\*.fields.OwnedByWorkgroup.value | string | | |
action_result.data.\*.fields.OwnedByWorkgroupID.dirty | boolean | | True False |
action_result.data.\*.fields.OwnedByWorkgroupID.displayName | string | | Owned By Workgroup ID |
action_result.data.\*.fields.OwnedByWorkgroupID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93e47e974b6a59a8eed6234ca7b994922bed6de1cb |
action_result.data.\*.fields.OwnedByWorkgroupID.html | string | | |
action_result.data.\*.fields.OwnedByWorkgroupID.value | string | | |
action_result.data.\*.fields.ParentTicket.dirty | boolean | | True False |
action_result.data.\*.fields.ParentTicket.displayName | string | | Parent Ticket |
action_result.data.\*.fields.ParentTicket.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93b3c61818aa74b3f0280f44fc957590e6cb93eb2a |
action_result.data.\*.fields.ParentTicket.html | string | | |
action_result.data.\*.fields.ParentTicket.value | string | | False |
action_result.data.\*.fields.PendingEndDateTime.dirty | boolean | | True False |
action_result.data.\*.fields.PendingEndDateTime.displayName | string | | PendingEndDateTime |
action_result.data.\*.fields.PendingEndDateTime.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93b7c618a44242006b16f0484a8f4a5a4b2e6af280 |
action_result.data.\*.fields.PendingEndDateTime.fullFieldId | string | | |
action_result.data.\*.fields.PendingEndDateTime.html | string | | |
action_result.data.\*.fields.PendingEndDateTime.value | string | | |
action_result.data.\*.fields.PendingPreviousStatus.dirty | boolean | | True False |
action_result.data.\*.fields.PendingPreviousStatus.displayName | string | | PendingPreviousStatus |
action_result.data.\*.fields.PendingPreviousStatus.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93881bb0f2477eb889ad0547a7aed119c4e5625de0 |
action_result.data.\*.fields.PendingPreviousStatus.fullFieldId | string | | |
action_result.data.\*.fields.PendingPreviousStatus.html | string | | |
action_result.data.\*.fields.PendingPreviousStatus.value | string | | |
action_result.data.\*.fields.PendingReason.dirty | boolean | | True False |
action_result.data.\*.fields.PendingReason.displayName | string | | PendingReason |
action_result.data.\*.fields.PendingReason.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9378aba490aadc483cf364416783a48d7d63ae11aa |
action_result.data.\*.fields.PendingReason.fullFieldId | string | | |
action_result.data.\*.fields.PendingReason.html | string | | |
action_result.data.\*.fields.PendingReason.value | string | | |
action_result.data.\*.fields.PendingStartDateTime.dirty | boolean | | True False |
action_result.data.\*.fields.PendingStartDateTime.displayName | string | | PendingStartDateTime |
action_result.data.\*.fields.PendingStartDateTime.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93b7c61777c0c9eb462ccf46f5b3c37bd9d1795937 |
action_result.data.\*.fields.PendingStartDateTime.fullFieldId | string | | |
action_result.data.\*.fields.PendingStartDateTime.html | string | | |
action_result.data.\*.fields.PendingStartDateTime.value | string | | |
action_result.data.\*.fields.PhaseApprovalsStatus.dirty | boolean | | True False |
action_result.data.\*.fields.PhaseApprovalsStatus.displayName | string | | phaseApprovalsStatus |
action_result.data.\*.fields.PhaseApprovalsStatus.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93836c6c60d5d81548afc54a0fb35e0e58322d9b60 |
action_result.data.\*.fields.PhaseApprovalsStatus.html | string | | |
action_result.data.\*.fields.PhaseApprovalsStatus.value | string | | Not Required |
action_result.data.\*.fields.PhaseClassifyStatus.dirty | boolean | | True False |
action_result.data.\*.fields.PhaseClassifyStatus.displayName | string | | phaseClassifyStatus |
action_result.data.\*.fields.PhaseClassifyStatus.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93836c6a2be9ddb0e48ea245e4ae0a9106d5e897dd |
action_result.data.\*.fields.PhaseClassifyStatus.html | string | | |
action_result.data.\*.fields.PhaseClassifyStatus.value | string | | In Progress |
action_result.data.\*.fields.PhaseCloseStatus.dirty | boolean | | True False |
action_result.data.\*.fields.PhaseCloseStatus.displayName | string | | phaseCloseStatus |
action_result.data.\*.fields.PhaseCloseStatus.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93836c6bb96a9e6fd8814443c8b64c7a5e092b0e3d |
action_result.data.\*.fields.PhaseCloseStatus.html | string | | |
action_result.data.\*.fields.PhaseCloseStatus.value | string | | Required |
action_result.data.\*.fields.PhaseInvestigateStatus.dirty | boolean | | True False |
action_result.data.\*.fields.PhaseInvestigateStatus.displayName | string | | phaseInvestigateStatus |
action_result.data.\*.fields.PhaseInvestigateStatus.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93836c6ab3a46d40ee6c55472d9860979f977ef591 |
action_result.data.\*.fields.PhaseInvestigateStatus.html | string | | |
action_result.data.\*.fields.PhaseInvestigateStatus.value | string | | Required |
action_result.data.\*.fields.PhaseRFWStatus.dirty | boolean | | True False |
action_result.data.\*.fields.PhaseRFWStatus.displayName | string | | phaseRFWStatus |
action_result.data.\*.fields.PhaseRFWStatus.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93836c6b1349bea19fe6344159a51d8bdf3cc059e7 |
action_result.data.\*.fields.PhaseRFWStatus.html | string | | |
action_result.data.\*.fields.PhaseRFWStatus.value | string | | Not Required |
action_result.data.\*.fields.PhaseRecordStatus.dirty | boolean | | True False |
action_result.data.\*.fields.PhaseRecordStatus.displayName | string | | phaseRecordStatus |
action_result.data.\*.fields.PhaseRecordStatus.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93836c69dd56ffa994fcd445078fe5c96bcad3cc71 |
action_result.data.\*.fields.PhaseRecordStatus.html | string | | |
action_result.data.\*.fields.PhaseRecordStatus.value | string | | Complete |
action_result.data.\*.fields.PhaseResolveStatus.dirty | boolean | | True False |
action_result.data.\*.fields.PhaseResolveStatus.displayName | string | | phaseResolveStatus |
action_result.data.\*.fields.PhaseResolveStatus.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93836c6b64b796ecc3f1464cd0a8fabb02edfc765a |
action_result.data.\*.fields.PhaseResolveStatus.html | string | | |
action_result.data.\*.fields.PhaseResolveStatus.value | string | | Required |
action_result.data.\*.fields.PhaseSetOrder.dirty | boolean | | True False |
action_result.data.\*.fields.PhaseSetOrder.displayName | string | | phaseSetOrder |
action_result.data.\*.fields.PhaseSetOrder.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9408117848d5ca43b613bc41478d6fad110e559f33 |
action_result.data.\*.fields.PhaseSetOrder.html | string | | |
action_result.data.\*.fields.PhaseSetOrder.value | string | | 2 |
action_result.data.\*.fields.PickedUpDateTime.dirty | boolean | | False |
action_result.data.\*.fields.PickedUpDateTime.displayName | string | | Picked Up Date/Time |
action_result.data.\*.fields.PickedUpDateTime.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:945503eb5f48ff50a95cec4deba6c2a21bbcb52901 |
action_result.data.\*.fields.PickedUpDateTime.fullFieldId | string | | |
action_result.data.\*.fields.PickedUpDateTime.html | string | | |
action_result.data.\*.fields.PickedUpDateTime.value | string | | |
action_result.data.\*.fields.PortalAffectsMultipleUsers.dirty | boolean | | True False |
action_result.data.\*.fields.PortalAffectsMultipleUsers.displayName | string | | SelfServiceMultipleUsers |
action_result.data.\*.fields.PortalAffectsMultipleUsers.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93887714a1bf384aa4f4e44ef0b3b4223fe41eab42 |
action_result.data.\*.fields.PortalAffectsMultipleUsers.fullFieldId | string | | |
action_result.data.\*.fields.PortalAffectsMultipleUsers.html | string | | |
action_result.data.\*.fields.PortalAffectsMultipleUsers.value | string | | |
action_result.data.\*.fields.PortalAffectsPrimaryFunction.dirty | boolean | | True False |
action_result.data.\*.fields.PortalAffectsPrimaryFunction.displayName | string | | SelfServiceUrgent |
action_result.data.\*.fields.PortalAffectsPrimaryFunction.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93887714076e8c39fb74ae4023a2b166222ed2f9e7 |
action_result.data.\*.fields.PortalAffectsPrimaryFunction.fullFieldId | string | | |
action_result.data.\*.fields.PortalAffectsPrimaryFunction.html | string | | |
action_result.data.\*.fields.PortalAffectsPrimaryFunction.value | string | | |
action_result.data.\*.fields.PortalAltContactInfo.dirty | boolean | | True False |
action_result.data.\*.fields.PortalAltContactInfo.displayName | string | | SelfServiceAltContactInfo |
action_result.data.\*.fields.PortalAltContactInfo.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9388772fdcae3fee1e3b35436f81978a8fc033d46d |
action_result.data.\*.fields.PortalAltContactInfo.fullFieldId | string | | |
action_result.data.\*.fields.PortalAltContactInfo.html | string | | |
action_result.data.\*.fields.PortalAltContactInfo.value | string | | |
action_result.data.\*.fields.PortalRequestDescription.dirty | boolean | | True False |
action_result.data.\*.fields.PortalRequestDescription.displayName | string | | PortalRequestDescription |
action_result.data.\*.fields.PortalRequestDescription.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93df705cbf1e19d5dc2d1445ada1f1e25c0d34fe38 |
action_result.data.\*.fields.PortalRequestDescription.html | string | | |
action_result.data.\*.fields.PortalRequestDescription.value | string | | False |
action_result.data.\*.fields.PortalRequiredIncidentFields.dirty | boolean | | True False |
action_result.data.\*.fields.PortalRequiredIncidentFields.displayName | string | | PortalRequiredIncidentFields |
action_result.data.\*.fields.PortalRequiredIncidentFields.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93df8ab66f47e04e9196294b59aa142ce87918a517 |
action_result.data.\*.fields.PortalRequiredIncidentFields.html | string | | |
action_result.data.\*.fields.PortalRequiredIncidentFields.value | string | | False |
action_result.data.\*.fields.PortalUrgencyFields.dirty | boolean | | True False |
action_result.data.\*.fields.PortalUrgencyFields.displayName | string | | PortalUrgencyFields |
action_result.data.\*.fields.PortalUrgencyFields.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93df703b3eab6e7cf3653b4086be5f8b75a269ba1e |
action_result.data.\*.fields.PortalUrgencyFields.html | string | | |
action_result.data.\*.fields.PortalUrgencyFields.value | string | | False |
action_result.data.\*.fields.PortalWizardCounter.dirty | boolean | | True False |
action_result.data.\*.fields.PortalWizardCounter.displayName | string | | Portal Wizard Counter |
action_result.data.\*.fields.PortalWizardCounter.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93db95aa3a374ca2b3d8ec4dac9ce72c1d9d9e42ec |
action_result.data.\*.fields.PortalWizardCounter.html | string | | |
action_result.data.\*.fields.PortalWizardCounter.value | string | | 0 |
action_result.data.\*.fields.Priority.dirty | boolean | | True False |
action_result.data.\*.fields.Priority.displayName | string | | Priority |
action_result.data.\*.fields.Priority.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:83c36313e97b4e6b9028aff3b401b71c |
action_result.data.\*.fields.Priority.fullFieldId | string | | |
action_result.data.\*.fields.Priority.html | string | | |
action_result.data.\*.fields.Priority.value | string | | 2 |
action_result.data.\*.fields.PriorityMatrixElementRecID.dirty | boolean | | False |
action_result.data.\*.fields.PriorityMatrixElementRecID.displayName | string | | Priority Matrix Element RecID |
action_result.data.\*.fields.PriorityMatrixElementRecID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9466ebf5f84689c1e01def4f10984a349e1c011863 |
action_result.data.\*.fields.PriorityMatrixElementRecID.fullFieldId | string | | |
action_result.data.\*.fields.PriorityMatrixElementRecID.html | string | | |
action_result.data.\*.fields.PriorityMatrixElementRecID.value | string | | |
action_result.data.\*.fields.ProjectCode.dirty | boolean | | True False |
action_result.data.\*.fields.ProjectCode.displayName | string | | Project Code |
action_result.data.\*.fields.ProjectCode.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9378b6d655e4f67e3fb14d4a2a83123652281e2340 |
action_result.data.\*.fields.ProjectCode.html | string | | |
action_result.data.\*.fields.ProjectCode.value | string | | |
action_result.data.\*.fields.ReasonForBreach.dirty | boolean | | True False |
action_result.data.\*.fields.ReasonForBreach.displayName | string | | Reason for Breach |
action_result.data.\*.fields.ReasonForBreach.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938b8160d99dbc0e2116114069a7edc3a36cdd96ea |
action_result.data.\*.fields.ReasonForBreach.html | string | | |
action_result.data.\*.fields.ReasonForBreach.value | string | | |
action_result.data.\*.fields.RecID.dirty | boolean | | True False |
action_result.data.\*.fields.RecID.displayName | string | | RecID |
action_result.data.\*.fields.RecID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:fa03d51b709e4a6eb2d52885b2ef7e04 |
action_result.data.\*.fields.RecID.fullFieldId | string | | |
action_result.data.\*.fields.RecID.html | string | | |
action_result.data.\*.fields.RecID.value | string | | 94308336ffce2054555f9a4312b463b2d93833328a |
action_result.data.\*.fields.ReclassifiedML.dirty | boolean | | False |
action_result.data.\*.fields.ReclassifiedML.displayName | string | | Reclassified ML |
action_result.data.\*.fields.ReclassifiedML.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9466d3af293639b84b4dec4e6d87c943cbcf470a85 |
action_result.data.\*.fields.ReclassifiedML.fullFieldId | string | | |
action_result.data.\*.fields.ReclassifiedML.html | string | | |
action_result.data.\*.fields.ReclassifiedML.value | string | | False |
action_result.data.\*.fields.RecurringIncident.dirty | boolean | | True False |
action_result.data.\*.fields.RecurringIncident.displayName | string | | Recurring Incident |
action_result.data.\*.fields.RecurringIncident.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d59b0a4f830cf541143b4afdb4ffc17f161e6b65 |
action_result.data.\*.fields.RecurringIncident.fullFieldId | string | | |
action_result.data.\*.fields.RecurringIncident.html | string | | |
action_result.data.\*.fields.RecurringIncident.value | string | | False |
action_result.data.\*.fields.Reopened.dirty | boolean | | False |
action_result.data.\*.fields.Reopened.displayName | string | | Reopened |
action_result.data.\*.fields.Reopened.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9458d15a97e8047e5e481546488b6aa190ca68c0ce |
action_result.data.\*.fields.Reopened.fullFieldId | string | | |
action_result.data.\*.fields.Reopened.html | string | | |
action_result.data.\*.fields.Reopened.value | string | | False |
action_result.data.\*.fields.Requester.dirty | boolean | | False |
action_result.data.\*.fields.Requester.displayName | string | | Requester |
action_result.data.\*.fields.Requester.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9450a00ccdb69786a573374a7ba1b43d74e18a80bb |
action_result.data.\*.fields.Requester.fullFieldId | string | | |
action_result.data.\*.fields.Requester.html | string | | |
action_result.data.\*.fields.Requester.value | string | | |
action_result.data.\*.fields.RequesterDepartment.dirty | boolean | | True False |
action_result.data.\*.fields.RequesterDepartment.displayName | string | | Requester Department |
action_result.data.\*.fields.RequesterDepartment.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:940484fd4dad30b6c511da4f8bb0c6d3b614e28806 |
action_result.data.\*.fields.RequesterDepartment.fullFieldId | string | | |
action_result.data.\*.fields.RequesterDepartment.html | string | | |
action_result.data.\*.fields.RequesterDepartment.value | string | | Operations |
action_result.data.\*.fields.RequesterEmail.dirty | boolean | | False |
action_result.data.\*.fields.RequesterEmail.displayName | string | | Requester Email |
action_result.data.\*.fields.RequesterEmail.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9450a01476dab3b9627389482db4ccd0cb3f3bbdd4 |
action_result.data.\*.fields.RequesterEmail.fullFieldId | string | | |
action_result.data.\*.fields.RequesterEmail.html | string | | |
action_result.data.\*.fields.RequesterEmail.value | string | | |
action_result.data.\*.fields.RequesterID.dirty | boolean | | False |
action_result.data.\*.fields.RequesterID.displayName | string | | Requester ID |
action_result.data.\*.fields.RequesterID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9450a017a571fd1b157f2a42528997246adc0c2d22 |
action_result.data.\*.fields.RequesterID.fullFieldId | string | | |
action_result.data.\*.fields.RequesterID.html | string | | |
action_result.data.\*.fields.RequesterID.value | string | | |
action_result.data.\*.fields.ReviewByDeadline.dirty | boolean | | True False |
action_result.data.\*.fields.ReviewByDeadline.displayName | string | | Review By Deadline |
action_result.data.\*.fields.ReviewByDeadline.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9378aba4eb664c75b19162486199a67ac141aa8dad |
action_result.data.\*.fields.ReviewByDeadline.fullFieldId | string | | |
action_result.data.\*.fields.ReviewByDeadline.html | string | | |
action_result.data.\*.fields.ReviewByDeadline.value | string | | |
action_result.data.\*.fields.SCTFired.dirty | boolean | | True False |
action_result.data.\*.fields.SCTFired.displayName | string | | SCT Fired |
action_result.data.\*.fields.SCTFired.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:94033bef62fd3bc5380e334cb28bb77686e15dff04 |
action_result.data.\*.fields.SCTFired.fullFieldId | string | | |
action_result.data.\*.fields.SCTFired.html | string | | |
action_result.data.\*.fields.SCTFired.value | string | | False |
action_result.data.\*.fields.SCTRecID.dirty | boolean | | True False |
action_result.data.\*.fields.SCTRecID.displayName | string | | Service Catalog Template RecID |
action_result.data.\*.fields.SCTRecID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:94008c4d7e094946b49eb9495385053c0d57531d52 |
action_result.data.\*.fields.SCTRecID.fullFieldId | string | | |
action_result.data.\*.fields.SCTRecID.html | string | | |
action_result.data.\*.fields.SCTRecID.value | string | | |
action_result.data.\*.fields.SLAID.dirty | boolean | | True False |
action_result.data.\*.fields.SLAID.displayName | string | | SLA ID |
action_result.data.\*.fields.SLAID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9365b1ed358b056256368f4c76beb828111504fb9e |
action_result.data.\*.fields.SLAID.fullFieldId | string | | |
action_result.data.\*.fields.SLAID.html | string | | |
action_result.data.\*.fields.SLAID.value | string | | 938aad773b01d0140385e84d19aa5205c5acf8c839 |
action_result.data.\*.fields.SLAIDForCI.dirty | boolean | | True False |
action_result.data.\*.fields.SLAIDForCI.displayName | string | | SLA ID for CI |
action_result.data.\*.fields.SLAIDForCI.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938a9f38ea2fafdce6c9c74358b9ceec411312be5b |
action_result.data.\*.fields.SLAIDForCI.fullFieldId | string | | |
action_result.data.\*.fields.SLAIDForCI.html | string | | |
action_result.data.\*.fields.SLAIDForCI.value | string | | |
action_result.data.\*.fields.SLAIDForCustomer.dirty | boolean | | True False |
action_result.data.\*.fields.SLAIDForCustomer.displayName | string | | SLA ID for Customer |
action_result.data.\*.fields.SLAIDForCustomer.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938a9f367426b5de8e841c417a9c3cb8ae4fbf6384 |
action_result.data.\*.fields.SLAIDForCustomer.fullFieldId | string | | |
action_result.data.\*.fields.SLAIDForCustomer.html | string | | |
action_result.data.\*.fields.SLAIDForCustomer.value | string | | |
action_result.data.\*.fields.SLAIDForService.dirty | boolean | | True False |
action_result.data.\*.fields.SLAIDForService.displayName | string | | SLA ID for Service |
action_result.data.\*.fields.SLAIDForService.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938a9f379d25c69114225641ffb1b308893d59903b |
action_result.data.\*.fields.SLAIDForService.fullFieldId | string | | |
action_result.data.\*.fields.SLAIDForService.html | string | | |
action_result.data.\*.fields.SLAIDForService.value | string | | |
action_result.data.\*.fields.SLAName.dirty | boolean | | True False |
action_result.data.\*.fields.SLAName.displayName | string | | SLA Name |
action_result.data.\*.fields.SLAName.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938385efa966eac1a0cb254eed8daf0c041e3cdfa2 |
action_result.data.\*.fields.SLAName.fullFieldId | string | | |
action_result.data.\*.fields.SLAName.html | string | | |
action_result.data.\*.fields.SLAName.value | string | | Corporate |
action_result.data.\*.fields.SLANameForCI.dirty | boolean | | True False |
action_result.data.\*.fields.SLANameForCI.displayName | string | | SLA Name for CI |
action_result.data.\*.fields.SLANameForCI.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938ac6ab3735f5ba14ae82448098be78637f5b7225 |
action_result.data.\*.fields.SLANameForCI.fullFieldId | string | | |
action_result.data.\*.fields.SLANameForCI.html | string | | |
action_result.data.\*.fields.SLANameForCI.value | string | | |
action_result.data.\*.fields.SLANameForCustomer.dirty | boolean | | True False |
action_result.data.\*.fields.SLANameForCustomer.displayName | string | | SLA Name for Customer |
action_result.data.\*.fields.SLANameForCustomer.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938ac6abcd030a55b43681468ca1a5410f4de0ad55 |
action_result.data.\*.fields.SLANameForCustomer.fullFieldId | string | | |
action_result.data.\*.fields.SLANameForCustomer.html | string | | |
action_result.data.\*.fields.SLANameForCustomer.value | string | | |
action_result.data.\*.fields.SLANameForService.dirty | boolean | | True False |
action_result.data.\*.fields.SLANameForService.displayName | string | | SLA Name for Service |
action_result.data.\*.fields.SLANameForService.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938ac6ac472e27d6c19dc4491d9d4d9acc8aa40aea |
action_result.data.\*.fields.SLANameForService.fullFieldId | string | | |
action_result.data.\*.fields.SLANameForService.html | string | | |
action_result.data.\*.fields.SLANameForService.value | string | | |
action_result.data.\*.fields.SLAResolutionWarning.dirty | boolean | | True False |
action_result.data.\*.fields.SLAResolutionWarning.displayName | string | | SLA Resolution Warning |
action_result.data.\*.fields.SLAResolutionWarning.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93b64514a233576673c3b14b34b6b458c8f96e7d2b |
action_result.data.\*.fields.SLAResolutionWarning.fullFieldId | string | | |
action_result.data.\*.fields.SLAResolutionWarning.html | string | | |
action_result.data.\*.fields.SLAResolutionWarning.value | string | | 11/24/2017 12:00 AM |
action_result.data.\*.fields.SLAResolveByDeadline.dirty | boolean | | True False |
action_result.data.\*.fields.SLAResolveByDeadline.displayName | string | | SLA Resolve By Deadline |
action_result.data.\*.fields.SLAResolveByDeadline.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9365b4209be3fff3623a4a4d6ab76991c2f01ea109 |
action_result.data.\*.fields.SLAResolveByDeadline.fullFieldId | string | | |
action_result.data.\*.fields.SLAResolveByDeadline.html | string | | |
action_result.data.\*.fields.SLAResolveByDeadline.value | string | | 11/24/2017 12:15 AM |
action_result.data.\*.fields.SLARespondByDeadline.dirty | boolean | | True False |
action_result.data.\*.fields.SLARespondByDeadline.displayName | string | | SLA Respond By Deadline |
action_result.data.\*.fields.SLARespondByDeadline.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9365b1db4ecb560c538b474ad58f51bf1fb6b101a5 |
action_result.data.\*.fields.SLARespondByDeadline.fullFieldId | string | | |
action_result.data.\*.fields.SLARespondByDeadline.html | string | | |
action_result.data.\*.fields.SLARespondByDeadline.value | string | | 11/22/2017 1:15 AM |
action_result.data.\*.fields.SLAResponseWarning.dirty | boolean | | True False |
action_result.data.\*.fields.SLAResponseWarning.displayName | string | | SLA Response Warning |
action_result.data.\*.fields.SLAResponseWarning.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93b64513d03b32250dc65642e7bd19ea3b9989b984 |
action_result.data.\*.fields.SLAResponseWarning.fullFieldId | string | | |
action_result.data.\*.fields.SLAResponseWarning.html | string | | |
action_result.data.\*.fields.SLAResponseWarning.value | string | | 11/22/2017 1:00 AM |
action_result.data.\*.fields.SLATargetTimeID.dirty | boolean | | True False |
action_result.data.\*.fields.SLATargetTimeID.displayName | string | | SLA Target Time ID |
action_result.data.\*.fields.SLATargetTimeID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d9ba0cb631686d7e326b4f5cb793a516e2525537 |
action_result.data.\*.fields.SLATargetTimeID.fullFieldId | string | | |
action_result.data.\*.fields.SLATargetTimeID.html | string | | |
action_result.data.\*.fields.SLATargetTimeID.value | string | | |
action_result.data.\*.fields.SLA_Key.dirty | boolean | | True False |
action_result.data.\*.fields.SLA_Key.displayName | string | | SLA_Key |
action_result.data.\*.fields.SLA_Key.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93c69d66e8a43f7cc8f25e44aeb52130ee477c3fff |
action_result.data.\*.fields.SLA_Key.fullFieldId | string | | |
action_result.data.\*.fields.SLA_Key.html | string | | |
action_result.data.\*.fields.SLA_Key.value | string | | \_Incident |
action_result.data.\*.fields.SSSection1Complete.dirty | boolean | | True False |
action_result.data.\*.fields.SSSection1Complete.displayName | string | | SS Section 1 Complete |
action_result.data.\*.fields.SSSection1Complete.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93adf2d7c3d0c4923fbcd4432b8ae670ec3868b5fb |
action_result.data.\*.fields.SSSection1Complete.html | string | | |
action_result.data.\*.fields.SSSection1Complete.value | string | | False |
action_result.data.\*.fields.SSSection2Complete.dirty | boolean | | True False |
action_result.data.\*.fields.SSSection2Complete.displayName | string | | SS Section 2 Complete |
action_result.data.\*.fields.SSSection2Complete.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93adf2d84ef0fa83e5f7ab436ea4e7fb4eac13f0f6 |
action_result.data.\*.fields.SSSection2Complete.html | string | | |
action_result.data.\*.fields.SSSection2Complete.value | string | | False |
action_result.data.\*.fields.SSSection3Complete.dirty | boolean | | True False |
action_result.data.\*.fields.SSSection3Complete.displayName | string | | SS Section 3 Complete |
action_result.data.\*.fields.SSSection3Complete.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93adf2e48b6b2a993f6b63457c92a9ad16fa85216c |
action_result.data.\*.fields.SSSection3Complete.html | string | | |
action_result.data.\*.fields.SSSection3Complete.value | string | | False |
action_result.data.\*.fields.SSSection4Complete.dirty | boolean | | True False |
action_result.data.\*.fields.SSSection4Complete.displayName | string | | SS Section 4 Complete |
action_result.data.\*.fields.SSSection4Complete.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93adf2e512a7c372ea027c466e9a5c18b1973ba565 |
action_result.data.\*.fields.SSSection4Complete.html | string | | |
action_result.data.\*.fields.SSSection4Complete.value | string | | False |
action_result.data.\*.fields.STCTimeInMinutes.dirty | boolean | | True False |
action_result.data.\*.fields.STCTimeInMinutes.displayName | string | | STCTimeInMinutes |
action_result.data.\*.fields.STCTimeInMinutes.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93b7c62bb497986b83199247aa940930eabdc5fb8d |
action_result.data.\*.fields.STCTimeInMinutes.fullFieldId | string | | |
action_result.data.\*.fields.STCTimeInMinutes.html | string | | |
action_result.data.\*.fields.STCTimeInMinutes.value | string | | 0 |
action_result.data.\*.fields.SecurityEventID.dirty | boolean | | False |
action_result.data.\*.fields.SecurityEventID.displayName | string | | Security Event ID |
action_result.data.\*.fields.SecurityEventID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:94255f78cefd978fbb6f854c53866ece5eb14fca84 |
action_result.data.\*.fields.SecurityEventID.fullFieldId | string | | |
action_result.data.\*.fields.SecurityEventID.html | string | | |
action_result.data.\*.fields.SecurityEventID.value | string | | |
action_result.data.\*.fields.SelectedStatus.dirty | boolean | | True False |
action_result.data.\*.fields.SelectedStatus.displayName | string | | SelectedStatus |
action_result.data.\*.fields.SelectedStatus.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93c25a4423de524e6ad18f412aa49c782358dcc1ca |
action_result.data.\*.fields.SelectedStatus.html | string | | |
action_result.data.\*.fields.SelectedStatus.value | string | | |
action_result.data.\*.fields.SelfServiceContactInfoCorrect.dirty | boolean | | True False |
action_result.data.\*.fields.SelfServiceContactInfoCorrect.displayName | string | | SelfServiceContactInfoCorrect |
action_result.data.\*.fields.SelfServiceContactInfoCorrect.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938877339165eb5f083e454d81aee1f4eb5b9bec8c |
action_result.data.\*.fields.SelfServiceContactInfoCorrect.html | string | | |
action_result.data.\*.fields.SelfServiceContactInfoCorrect.value | string | | False |
action_result.data.\*.fields.Service.dirty | boolean | | True False |
action_result.data.\*.fields.Service.displayName | string | | Service |
action_result.data.\*.fields.Service.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:936725cd10c735d1dd8c5b4cd4969cb0bd833655f4 |
action_result.data.\*.fields.Service.fullFieldId | string | | |
action_result.data.\*.fields.Service.html | string | | |
action_result.data.\*.fields.Service.value | string | | |
action_result.data.\*.fields.ServiceCartID.dirty | boolean | | True False |
action_result.data.\*.fields.ServiceCartID.displayName | string | | Service Cart ID |
action_result.data.\*.fields.ServiceCartID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:94007ee8679939f2fbdbfc409bbc3bc686d7c9609c |
action_result.data.\*.fields.ServiceCartID.fullFieldId | string | | |
action_result.data.\*.fields.ServiceCartID.html | string | | |
action_result.data.\*.fields.ServiceCartID.value | string | | |
action_result.data.\*.fields.ServiceCatalogTemplateName.dirty | boolean | | False True |
action_result.data.\*.fields.ServiceCatalogTemplateName.displayName | string | | Service Catalog Template Name |
action_result.data.\*.fields.ServiceCatalogTemplateName.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9411f5f0a548a580737d4f488588d9da1de8ffbac0 |
action_result.data.\*.fields.ServiceCatalogTemplateName.fullFieldId | string | | |
action_result.data.\*.fields.ServiceCatalogTemplateName.html | string | | |
action_result.data.\*.fields.ServiceCatalogTemplateName.value | string | | |
action_result.data.\*.fields.ServiceCustomerIsEntitled.dirty | boolean | | True False |
action_result.data.\*.fields.ServiceCustomerIsEntitled.displayName | string | | Service Customer is Entitled |
action_result.data.\*.fields.ServiceCustomerIsEntitled.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:939802c2f2de6a9b91c072465ebe11b3361a83ae28 |
action_result.data.\*.fields.ServiceCustomerIsEntitled.fullFieldId | string | | |
action_result.data.\*.fields.ServiceCustomerIsEntitled.html | string | | |
action_result.data.\*.fields.ServiceCustomerIsEntitled.value | string | | False |
action_result.data.\*.fields.ServiceEntitlements.dirty | boolean | | True False |
action_result.data.\*.fields.ServiceEntitlements.displayName | string | | Service Entitlements |
action_result.data.\*.fields.ServiceEntitlements.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93980292c5e7b84a15ee4e4c88aec8748e67a44701 |
action_result.data.\*.fields.ServiceEntitlements.fullFieldId | string | | |
action_result.data.\*.fields.ServiceEntitlements.html | string | | |
action_result.data.\*.fields.ServiceEntitlements.value | string | | |
action_result.data.\*.fields.ServiceID.dirty | boolean | | True False |
action_result.data.\*.fields.ServiceID.displayName | string | | ServiceID |
action_result.data.\*.fields.ServiceID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93881a00214afe7688b3774234a103f7d94fb27002 |
action_result.data.\*.fields.ServiceID.fullFieldId | string | | |
action_result.data.\*.fields.ServiceID.html | string | | |
action_result.data.\*.fields.ServiceID.value | string | | |
action_result.data.\*.fields.ShortDescription.dirty | boolean | | True False |
action_result.data.\*.fields.ShortDescription.displayName | string | | Short Description |
action_result.data.\*.fields.ShortDescription.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93e8ea93ff67fd95118255419690a50ef2d56f910c |
action_result.data.\*.fields.ShortDescription.html | string | | |
action_result.data.\*.fields.ShortDescription.value | string | | |
action_result.data.\*.fields.ShowAllServices.dirty | boolean | | True False |
action_result.data.\*.fields.ShowAllServices.displayName | string | | Show all services |
action_result.data.\*.fields.ShowAllServices.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:939645f6f7cc1dc0bf86274e84bfab6c91773d5667 |
action_result.data.\*.fields.ShowAllServices.fullFieldId | string | | |
action_result.data.\*.fields.ShowAllServices.html | string | | |
action_result.data.\*.fields.ShowAllServices.value | string | | False |
action_result.data.\*.fields.ShowContactInformation.dirty | boolean | | True False |
action_result.data.\*.fields.ShowContactInformation.displayName | string | | Show Contact Information |
action_result.data.\*.fields.ShowContactInformation.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93964e0f873d35e0f2ad80407491b6b02c0d26ce53 |
action_result.data.\*.fields.ShowContactInformation.fullFieldId | string | | |
action_result.data.\*.fields.ShowContactInformation.html | string | | |
action_result.data.\*.fields.ShowContactInformation.value | string | | False |
action_result.data.\*.fields.SkillID.dirty | boolean | | False |
action_result.data.\*.fields.SkillID.displayName | string | | Skill ID |
action_result.data.\*.fields.SkillID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9454dd19ad378f8fcfea9446b48313bb6ab85006ad |
action_result.data.\*.fields.SkillID.fullFieldId | string | | |
action_result.data.\*.fields.SkillID.html | string | | |
action_result.data.\*.fields.SkillID.value | string | | |
action_result.data.\*.fields.SmartClassifySearchString.dirty | boolean | | True False |
action_result.data.\*.fields.SmartClassifySearchString.displayName | string | | Smart Classify Search String |
action_result.data.\*.fields.SmartClassifySearchString.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93ceccc608a0356e1b9a7d424c828a9fc3169749cd |
action_result.data.\*.fields.SmartClassifySearchString.fullFieldId | string | | |
action_result.data.\*.fields.SmartClassifySearchString.html | string | | |
action_result.data.\*.fields.SmartClassifySearchString.value | string | | |
action_result.data.\*.fields.SmartUXGeocodedLocation.dirty | boolean | | False |
action_result.data.\*.fields.SmartUXGeocodedLocation.displayName | string | | SmartUX Geocoded Location |
action_result.data.\*.fields.SmartUXGeocodedLocation.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:945c13eba06550cc5431d644ac8e18f2c1178d0e53 |
action_result.data.\*.fields.SmartUXGeocodedLocation.fullFieldId | string | | |
action_result.data.\*.fields.SmartUXGeocodedLocation.html | string | | |
action_result.data.\*.fields.SmartUXGeocodedLocation.value | string | | |
action_result.data.\*.fields.SmartUXLatitude.dirty | boolean | | False |
action_result.data.\*.fields.SmartUXLatitude.displayName | string | | SmartUX Latitude |
action_result.data.\*.fields.SmartUXLatitude.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:945ad3b02b41f61b8d7c664b83bda95dbec27edc8b |
action_result.data.\*.fields.SmartUXLatitude.fullFieldId | string | | |
action_result.data.\*.fields.SmartUXLatitude.html | string | | |
action_result.data.\*.fields.SmartUXLatitude.value | string | | 0 |
action_result.data.\*.fields.SmartUXLongitude.dirty | boolean | | False |
action_result.data.\*.fields.SmartUXLongitude.displayName | string | | SmartUX Longitude |
action_result.data.\*.fields.SmartUXLongitude.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:945ad3a686ca7b705a3f1c400c9aabf87a5ba098b1 |
action_result.data.\*.fields.SmartUXLongitude.fullFieldId | string | | |
action_result.data.\*.fields.SmartUXLongitude.html | string | | |
action_result.data.\*.fields.SmartUXLongitude.value | string | | 0 |
action_result.data.\*.fields.Source.dirty | boolean | | True False |
action_result.data.\*.fields.Source.displayName | string | | Call Source |
action_result.data.\*.fields.Source.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93670bdf8abe2cd1f92b1f490a90c7b7d684222e13 |
action_result.data.\*.fields.Source.html | string | | |
action_result.data.\*.fields.Source.value | string | | Phone |
action_result.data.\*.fields.SpecificsTypeId.dirty | boolean | | True False |
action_result.data.\*.fields.SpecificsTypeId.displayName | string | | SpecificsTypeId |
action_result.data.\*.fields.SpecificsTypeId.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:933a6388b180f3fb13e37f4bbcbc283c183579c5a8 |
action_result.data.\*.fields.SpecificsTypeId.fullFieldId | string | | |
action_result.data.\*.fields.SpecificsTypeId.html | string | | |
action_result.data.\*.fields.SpecificsTypeId.value | string | | |
action_result.data.\*.fields.Stat_24x7ElapsedTime.dirty | boolean | | True False |
action_result.data.\*.fields.Stat_24x7ElapsedTime.displayName | string | | stat_24x7ElapsedTime |
action_result.data.\*.fields.Stat_24x7ElapsedTime.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93843c46302264bb2a5758456e899b3129e1c7a453 |
action_result.data.\*.fields.Stat_24x7ElapsedTime.fullFieldId | string | | |
action_result.data.\*.fields.Stat_24x7ElapsedTime.html | string | | |
action_result.data.\*.fields.Stat_24x7ElapsedTime.value | string | | 0 |
action_result.data.\*.fields.Stat_DateTimeAssigned.dirty | boolean | | True False |
action_result.data.\*.fields.Stat_DateTimeAssigned.displayName | string | | stat_Date Time Assigned |
action_result.data.\*.fields.Stat_DateTimeAssigned.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d316c4fac1324cca581945b397a49be3ab19f4a2 |
action_result.data.\*.fields.Stat_DateTimeAssigned.fullFieldId | string | | |
action_result.data.\*.fields.Stat_DateTimeAssigned.html | string | | |
action_result.data.\*.fields.Stat_DateTimeAssigned.value | string | | |
action_result.data.\*.fields.Stat_DateTimeClosed.dirty | boolean | | True False |
action_result.data.\*.fields.Stat_DateTimeClosed.displayName | string | | stat_Date Time Closed |
action_result.data.\*.fields.Stat_DateTimeClosed.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d316d3b7efb91be6561a4935b11eea8eb5149b40 |
action_result.data.\*.fields.Stat_DateTimeClosed.fullFieldId | string | | |
action_result.data.\*.fields.Stat_DateTimeClosed.html | string | | |
action_result.data.\*.fields.Stat_DateTimeClosed.value | string | | |
action_result.data.\*.fields.Stat_DateTimeInProgress.dirty | boolean | | True False |
action_result.data.\*.fields.Stat_DateTimeInProgress.displayName | string | | stat_Date Time In Progress |
action_result.data.\*.fields.Stat_DateTimeInProgress.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d316cfe84bd564456fcd48438c1d4db920f301ce |
action_result.data.\*.fields.Stat_DateTimeInProgress.fullFieldId | string | | |
action_result.data.\*.fields.Stat_DateTimeInProgress.html | string | | |
action_result.data.\*.fields.Stat_DateTimeInProgress.value | string | | 11/22/2017 12:15 AM |
action_result.data.\*.fields.Stat_DateTimeReOpened.dirty | boolean | | True False |
action_result.data.\*.fields.Stat_DateTimeReOpened.displayName | string | | stat_Date Time ReOpened |
action_result.data.\*.fields.Stat_DateTimeReOpened.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d316e0df00c363989e1e48eeaee9d24e659de9dc |
action_result.data.\*.fields.Stat_DateTimeReOpened.fullFieldId | string | | |
action_result.data.\*.fields.Stat_DateTimeReOpened.html | string | | |
action_result.data.\*.fields.Stat_DateTimeReOpened.value | string | | |
action_result.data.\*.fields.Stat_DateTimeResolved.dirty | boolean | | True False |
action_result.data.\*.fields.Stat_DateTimeResolved.displayName | string | | stat_Date Time Resolved |
action_result.data.\*.fields.Stat_DateTimeResolved.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93b63c949c847642f72c0c43beb901d6806e74901a |
action_result.data.\*.fields.Stat_DateTimeResolved.fullFieldId | string | | |
action_result.data.\*.fields.Stat_DateTimeResolved.html | string | | |
action_result.data.\*.fields.Stat_DateTimeResolved.value | string | | |
action_result.data.\*.fields.Stat_DateTimeResponded.dirty | boolean | | True False |
action_result.data.\*.fields.Stat_DateTimeResponded.displayName | string | | stat_DateTime Responded |
action_result.data.\*.fields.Stat_DateTimeResponded.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93843c5730fc45cfb91e404bafaae5ad5978ebdb22 |
action_result.data.\*.fields.Stat_DateTimeResponded.fullFieldId | string | | |
action_result.data.\*.fields.Stat_DateTimeResponded.html | string | | |
action_result.data.\*.fields.Stat_DateTimeResponded.value | string | | 11/22/2017 12:15 AM |
action_result.data.\*.fields.Stat_FirstCallResolution.dirty | boolean | | True False |
action_result.data.\*.fields.Stat_FirstCallResolution.displayName | string | | stat_First Call Resolution |
action_result.data.\*.fields.Stat_FirstCallResolution.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93843c2574a1eeea9c06a240259f9a91bfa3e2c4eb |
action_result.data.\*.fields.Stat_FirstCallResolution.fullFieldId | string | | |
action_result.data.\*.fields.Stat_FirstCallResolution.html | string | | |
action_result.data.\*.fields.Stat_FirstCallResolution.value | string | | False |
action_result.data.\*.fields.Stat_IncidentEscalated.dirty | boolean | | True False |
action_result.data.\*.fields.Stat_IncidentEscalated.displayName | string | | stat_Incident Escalated |
action_result.data.\*.fields.Stat_IncidentEscalated.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93843c4494a6c4048312344ef79a2764f7a03974b4 |
action_result.data.\*.fields.Stat_IncidentEscalated.fullFieldId | string | | |
action_result.data.\*.fields.Stat_IncidentEscalated.html | string | | |
action_result.data.\*.fields.Stat_IncidentEscalated.value | string | | False |
action_result.data.\*.fields.Stat_IncidentReopened.dirty | boolean | | True False |
action_result.data.\*.fields.Stat_IncidentReopened.displayName | string | | stat_Incident Reopened |
action_result.data.\*.fields.Stat_IncidentReopened.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93843c51c65c4feef225de469c9389729162bc750e |
action_result.data.\*.fields.Stat_IncidentReopened.fullFieldId | string | | |
action_result.data.\*.fields.Stat_IncidentReopened.html | string | | |
action_result.data.\*.fields.Stat_IncidentReopened.value | string | | False |
action_result.data.\*.fields.Stat_NumberOfEscalations.dirty | boolean | | True False |
action_result.data.\*.fields.Stat_NumberOfEscalations.displayName | string | | stat_Number Of Escalations |
action_result.data.\*.fields.Stat_NumberOfEscalations.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93843c454f073f3f574df84a7c8c8d7767e08039af |
action_result.data.\*.fields.Stat_NumberOfEscalations.fullFieldId | string | | |
action_result.data.\*.fields.Stat_NumberOfEscalations.html | string | | |
action_result.data.\*.fields.Stat_NumberOfEscalations.value | string | | 0 |
action_result.data.\*.fields.Stat_NumberOfTouches.dirty | boolean | | True False |
action_result.data.\*.fields.Stat_NumberOfTouches.displayName | string | | stat_Number Of Touches |
action_result.data.\*.fields.Stat_NumberOfTouches.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93843c2301c27644faed9e48328310bffaf04250bc |
action_result.data.\*.fields.Stat_NumberOfTouches.fullFieldId | string | | |
action_result.data.\*.fields.Stat_NumberOfTouches.html | string | | |
action_result.data.\*.fields.Stat_NumberOfTouches.value | string | | 11 |
action_result.data.\*.fields.Stat_ResponseTime.dirty | boolean | | True False |
action_result.data.\*.fields.Stat_ResponseTime.displayName | string | | stat_Response Time |
action_result.data.\*.fields.Stat_ResponseTime.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93843c57daea0dbfee32164b058d81dfc03d7e66fd |
action_result.data.\*.fields.Stat_ResponseTime.fullFieldId | string | | |
action_result.data.\*.fields.Stat_ResponseTime.html | string | | |
action_result.data.\*.fields.Stat_ResponseTime.value | string | | 0 |
action_result.data.\*.fields.Stat_SLAResolutionBreached.dirty | boolean | | True False |
action_result.data.\*.fields.Stat_SLAResolutionBreached.displayName | string | | stat_SLA Resolution Breached |
action_result.data.\*.fields.Stat_SLAResolutionBreached.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93843c5c8ce8b2a364be704baa8149b4c7312f0eb3 |
action_result.data.\*.fields.Stat_SLAResolutionBreached.fullFieldId | string | | |
action_result.data.\*.fields.Stat_SLAResolutionBreached.html | string | | |
action_result.data.\*.fields.Stat_SLAResolutionBreached.value | string | | False |
action_result.data.\*.fields.Stat_SLAResolutionGood.dirty | boolean | | True False |
action_result.data.\*.fields.Stat_SLAResolutionGood.displayName | string | | stat_SLA Resolution Good |
action_result.data.\*.fields.Stat_SLAResolutionGood.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93b63a8d4d1a8900db9e2a4eb58cf8fb54d9850559 |
action_result.data.\*.fields.Stat_SLAResolutionGood.fullFieldId | string | | |
action_result.data.\*.fields.Stat_SLAResolutionGood.html | string | | |
action_result.data.\*.fields.Stat_SLAResolutionGood.value | string | | False |
action_result.data.\*.fields.Stat_SLAResolutionWarning.dirty | boolean | | True False |
action_result.data.\*.fields.Stat_SLAResolutionWarning.displayName | string | | stat_SLA Resolution Warning |
action_result.data.\*.fields.Stat_SLAResolutionWarning.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93b63a8963786a6d8fca7f4c7b9443ae3c6424dd7d |
action_result.data.\*.fields.Stat_SLAResolutionWarning.fullFieldId | string | | |
action_result.data.\*.fields.Stat_SLAResolutionWarning.html | string | | |
action_result.data.\*.fields.Stat_SLAResolutionWarning.value | string | | False |
action_result.data.\*.fields.Stat_SLAResponseBreached.dirty | boolean | | True False |
action_result.data.\*.fields.Stat_SLAResponseBreached.displayName | string | | stat_SLA Response Breached |
action_result.data.\*.fields.Stat_SLAResponseBreached.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93843c5c02e98315b4b8d3487f8398c7943f4e6440 |
action_result.data.\*.fields.Stat_SLAResponseBreached.fullFieldId | string | | |
action_result.data.\*.fields.Stat_SLAResponseBreached.html | string | | |
action_result.data.\*.fields.Stat_SLAResponseBreached.value | string | | False |
action_result.data.\*.fields.Stat_SLAResponseGood.dirty | boolean | | True False |
action_result.data.\*.fields.Stat_SLAResponseGood.displayName | string | | stat_SLA Response Good |
action_result.data.\*.fields.Stat_SLAResponseGood.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93b63a8dbb977db61759b54d24857d61ebfc824b68 |
action_result.data.\*.fields.Stat_SLAResponseGood.fullFieldId | string | | |
action_result.data.\*.fields.Stat_SLAResponseGood.html | string | | |
action_result.data.\*.fields.Stat_SLAResponseGood.value | string | | True |
action_result.data.\*.fields.Stat_SLAResponseWarning.dirty | boolean | | True False |
action_result.data.\*.fields.Stat_SLAResponseWarning.displayName | string | | stat_SLA Response Warning |
action_result.data.\*.fields.Stat_SLAResponseWarning.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93b63a8ca52ab6af7d64ad479fb995031290f3d41a |
action_result.data.\*.fields.Stat_SLAResponseWarning.fullFieldId | string | | |
action_result.data.\*.fields.Stat_SLAResponseWarning.html | string | | |
action_result.data.\*.fields.Stat_SLAResponseWarning.value | string | | False |
action_result.data.\*.fields.Stat_TotalDLHOfIncident.dirty | boolean | | True False |
action_result.data.\*.fields.Stat_TotalDLHOfIncident.displayName | string | | stat_TotalDLHOfIncident |
action_result.data.\*.fields.Stat_TotalDLHOfIncident.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93843c5d73adf5d36c38b448939683c7f01174014a |
action_result.data.\*.fields.Stat_TotalDLHOfIncident.html | string | | |
action_result.data.\*.fields.Stat_TotalDLHOfIncident.value | string | | 0 |
action_result.data.\*.fields.Status.dirty | boolean | | True False |
action_result.data.\*.fields.Status.displayName | string | | Status |
action_result.data.\*.fields.Status.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:5eb3234ae1344c64a19819eda437f18d |
action_result.data.\*.fields.Status.fullFieldId | string | | |
action_result.data.\*.fields.Status.html | string | | |
action_result.data.\*.fields.Status.value | string | | In Progress |
action_result.data.\*.fields.StatusDesc.dirty | boolean | | True False |
action_result.data.\*.fields.StatusDesc.displayName | string | | Status Description |
action_result.data.\*.fields.StatusDesc.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:20d1e9c67a3c440b8912ee9f83be15f9 |
action_result.data.\*.fields.StatusDesc.fullFieldId | string | | |
action_result.data.\*.fields.StatusDesc.html | string | | |
action_result.data.\*.fields.StatusDesc.value | string | | |
action_result.data.\*.fields.StatusID.dirty | boolean | | True False |
action_result.data.\*.fields.StatusID.displayName | string | | Status ID |
action_result.data.\*.fields.StatusID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93c73b428f2fbdfe68f8724ce9bcaaa4ff0ed57ce9 |
action_result.data.\*.fields.StatusID.fullFieldId | string | | |
action_result.data.\*.fields.StatusID.html | string | | |
action_result.data.\*.fields.StatusID.value | string | | 93ac5b5ea0dbf7c1695cb64a1791de030505574b1a |
action_result.data.\*.fields.StatusOrder.dirty | boolean | | False |
action_result.data.\*.fields.StatusOrder.displayName | string | | Status Order |
action_result.data.\*.fields.StatusOrder.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:94592d2f88ac4006370ce24184b3512b7a36ee23f4 |
action_result.data.\*.fields.StatusOrder.fullFieldId | string | | |
action_result.data.\*.fields.StatusOrder.html | string | | |
action_result.data.\*.fields.StatusOrder.value | string | | 1 |
action_result.data.\*.fields.Subcategory.dirty | boolean | | True False |
action_result.data.\*.fields.Subcategory.displayName | string | | Subcategory |
action_result.data.\*.fields.Subcategory.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:1163fda7e6a44f40bb94d2b47cc58f46 |
action_result.data.\*.fields.Subcategory.fullFieldId | string | | |
action_result.data.\*.fields.Subcategory.html | string | | |
action_result.data.\*.fields.Subcategory.value | string | | |
action_result.data.\*.fields.SubcategoryID.dirty | boolean | | True False |
action_result.data.\*.fields.SubcategoryID.displayName | string | | Subcategory ID |
action_result.data.\*.fields.SubcategoryID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93cec0404a97942d8e4d294260b1a3a6146b7f7db5 |
action_result.data.\*.fields.SubcategoryID.html | string | | |
action_result.data.\*.fields.SubcategoryID.value | string | | |
action_result.data.\*.fields.SubcategoryRecID.dirty | boolean | | False |
action_result.data.\*.fields.SubcategoryRecID.displayName | string | | Subcategory RecID |
action_result.data.\*.fields.SubcategoryRecID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93cec0404a97942d8e4d294260b1a3a6146b7f7db5 |
action_result.data.\*.fields.SubcategoryRecID.fullFieldId | string | | |
action_result.data.\*.fields.SubcategoryRecID.html | string | | |
action_result.data.\*.fields.SubcategoryRecID.value | string | | 94662639503c1d2351325445f3ace4fe18a7b51aa5 |
action_result.data.\*.fields.SubmitOnBehalfOf.dirty | boolean | | True False |
action_result.data.\*.fields.SubmitOnBehalfOf.displayName | string | | Submit On Behalf Of |
action_result.data.\*.fields.SubmitOnBehalfOf.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93f69ce4e406293245cf26483484ceb1771494fee6 |
action_result.data.\*.fields.SubmitOnBehalfOf.html | string | | |
action_result.data.\*.fields.SubmitOnBehalfOf.value | string | | |
action_result.data.\*.fields.SubmitOnBehalfOfEmail.dirty | boolean | | True False |
action_result.data.\*.fields.SubmitOnBehalfOfEmail.displayName | string | | Submit On Behalf Of Email |
action_result.data.\*.fields.SubmitOnBehalfOfEmail.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93f69ce98dce1f287fdd9944a48dc106a13dd8b27e |
action_result.data.\*.fields.SubmitOnBehalfOfEmail.html | string | | |
action_result.data.\*.fields.SubmitOnBehalfOfEmail.value | string | | |
action_result.data.\*.fields.SubmitOnBehalfOfEnableEmailNotifications.dirty | boolean | | True False |
action_result.data.\*.fields.SubmitOnBehalfOfEnableEmailNotifications.displayName | string | | Submit On Behalf Of Enable Email Notifications |
action_result.data.\*.fields.SubmitOnBehalfOfEnableEmailNotifications.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93f69cfa1fb2bd1574ad9743609939e72782c94e12 |
action_result.data.\*.fields.SubmitOnBehalfOfEnableEmailNotifications.html | string | | |
action_result.data.\*.fields.SubmitOnBehalfOfEnableEmailNotifications.value | string | | |
action_result.data.\*.fields.SubmitOnBehalfOfID.dirty | boolean | | True False |
action_result.data.\*.fields.SubmitOnBehalfOfID.displayName | string | | Submit On Behalf Of ID |
action_result.data.\*.fields.SubmitOnBehalfOfID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93f69ced30154e31f9dc664590ae6e192be65768e7 |
action_result.data.\*.fields.SubmitOnBehalfOfID.html | string | | |
action_result.data.\*.fields.SubmitOnBehalfOfID.value | string | | |
action_result.data.\*.fields.SubmitOnBehalfOfPhone.dirty | boolean | | True False |
action_result.data.\*.fields.SubmitOnBehalfOfPhone.displayName | string | | Submit On Behalf Of Phone |
action_result.data.\*.fields.SubmitOnBehalfOfPhone.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93f69cef834157846746b045ca89cab113a6f89801 |
action_result.data.\*.fields.SubmitOnBehalfOfPhone.html | string | | |
action_result.data.\*.fields.SubmitOnBehalfOfPhone.value | string | | |
action_result.data.\*.fields.SubmitOnBehalfOfSLAID.dirty | boolean | | True False |
action_result.data.\*.fields.SubmitOnBehalfOfSLAID.displayName | string | | Submit On Behalf Of SLA ID |
action_result.data.\*.fields.SubmitOnBehalfOfSLAID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93f69cf1b1adcdbe4d5e82468eb93c1680bbefe42c |
action_result.data.\*.fields.SubmitOnBehalfOfSLAID.html | string | | |
action_result.data.\*.fields.SubmitOnBehalfOfSLAID.value | string | | |
action_result.data.\*.fields.SubmitOnBehalfOfTitle.dirty | boolean | | True False |
action_result.data.\*.fields.SubmitOnBehalfOfTitle.displayName | string | | Submit On Behalf Of Title |
action_result.data.\*.fields.SubmitOnBehalfOfTitle.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93f69cf644c5b948a833ef427d9a8239397c77b28b |
action_result.data.\*.fields.SubmitOnBehalfOfTitle.html | string | | |
action_result.data.\*.fields.SubmitOnBehalfOfTitle.value | string | | |
action_result.data.\*.fields.Task.dirty | boolean | | True False |
action_result.data.\*.fields.Task.displayName | string | | Task |
action_result.data.\*.fields.Task.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9378b6d68c08017e385f2d43ae8ab367442312d3be |
action_result.data.\*.fields.Task.html | string | | |
action_result.data.\*.fields.Task.value | string | | |
action_result.data.\*.fields.TaskClosedCount.dirty | boolean | | True False |
action_result.data.\*.fields.TaskClosedCount.displayName | string | | Task Closed Count |
action_result.data.\*.fields.TaskClosedCount.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:940276a6c3d39150eb372b48f692bc42ec2064afc9 |
action_result.data.\*.fields.TaskClosedCount.fullFieldId | string | | |
action_result.data.\*.fields.TaskClosedCount.html | string | | |
action_result.data.\*.fields.TaskClosedCount.value | string | | 0 |
action_result.data.\*.fields.TasksClosed.dirty | boolean | | True False |
action_result.data.\*.fields.TasksClosed.displayName | string | | Tasks Closed |
action_result.data.\*.fields.TasksClosed.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:94024cee20421108e0fea744f0a66021ff5710a8e0 |
action_result.data.\*.fields.TasksClosed.fullFieldId | string | | |
action_result.data.\*.fields.TasksClosed.html | string | | |
action_result.data.\*.fields.TasksClosed.value | string | | False |
action_result.data.\*.fields.TasksInProgress.dirty | boolean | | True False |
action_result.data.\*.fields.TasksInProgress.displayName | string | | Tasks In Progress |
action_result.data.\*.fields.TasksInProgress.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:94022727d9c89a9acc0c8e43c4978e29919a29ced0 |
action_result.data.\*.fields.TasksInProgress.fullFieldId | string | | |
action_result.data.\*.fields.TasksInProgress.html | string | | |
action_result.data.\*.fields.TasksInProgress.value | string | | False |
action_result.data.\*.fields.TasksOnHold.dirty | boolean | | True False |
action_result.data.\*.fields.TasksOnHold.displayName | string | | Tasks On Hold |
action_result.data.\*.fields.TasksOnHold.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:940311fef665f9ba7400b6476b912e2170277bed75 |
action_result.data.\*.fields.TasksOnHold.fullFieldId | string | | |
action_result.data.\*.fields.TasksOnHold.html | string | | |
action_result.data.\*.fields.TasksOnHold.value | string | | False |
action_result.data.\*.fields.Temp_Accepted.dirty | boolean | | True False |
action_result.data.\*.fields.Temp_Accepted.displayName | string | | temp_Accepted |
action_result.data.\*.fields.Temp_Accepted.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938737b9b9ac00442ac729437f9064f08990641a8d |
action_result.data.\*.fields.Temp_Accepted.html | string | | |
action_result.data.\*.fields.Temp_Accepted.value | string | | False |
action_result.data.\*.fields.Temp_Active.dirty | boolean | | True False |
action_result.data.\*.fields.Temp_Active.displayName | string | | temp_Active |
action_result.data.\*.fields.Temp_Active.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938737b8b8d52a8095824d44b0983dcfeed948a149 |
action_result.data.\*.fields.Temp_Active.html | string | | |
action_result.data.\*.fields.Temp_Active.value | string | | False |
action_result.data.\*.fields.Temp_Assigned.dirty | boolean | | True False |
action_result.data.\*.fields.Temp_Assigned.displayName | string | | temp_Assigned |
action_result.data.\*.fields.Temp_Assigned.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938737dc76ee0e561f46aa400c8dd7d1e8b209c775 |
action_result.data.\*.fields.Temp_Assigned.html | string | | |
action_result.data.\*.fields.Temp_Assigned.value | string | | False |
action_result.data.\*.fields.Temp_Dependency.dirty | boolean | | True False |
action_result.data.\*.fields.Temp_Dependency.displayName | string | | temp_Dependency |
action_result.data.\*.fields.Temp_Dependency.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93bb61861a74af043aa61a411cb69538172dc6c7a9 |
action_result.data.\*.fields.Temp_Dependency.html | string | | |
action_result.data.\*.fields.Temp_Dependency.value | string | | False |
action_result.data.\*.fields.Temp_Resolved.dirty | boolean | | True False |
action_result.data.\*.fields.Temp_Resolved.displayName | string | | temp_Resolved |
action_result.data.\*.fields.Temp_Resolved.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938737ba5d26bdb84c4048462bb8153ebdad3df282 |
action_result.data.\*.fields.Temp_Resolved.html | string | | |
action_result.data.\*.fields.Temp_Resolved.value | string | | False |
action_result.data.\*.fields.Temp_childID.dirty | boolean | | True False |
action_result.data.\*.fields.Temp_childID.displayName | string | | temp_childID |
action_result.data.\*.fields.Temp_childID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d9c675e5526fed36e03a4b5ca74dbbd5c1c9e79b |
action_result.data.\*.fields.Temp_childID.html | string | | |
action_result.data.\*.fields.Temp_childID.value | string | | |
action_result.data.\*.fields.Temp_childRecID.dirty | boolean | | True False |
action_result.data.\*.fields.Temp_childRecID.displayName | string | | temp_childRecID |
action_result.data.\*.fields.Temp_childRecID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d9c67b0ce7bea107da5242d7a2574bde0d5f3579 |
action_result.data.\*.fields.Temp_childRecID.html | string | | |
action_result.data.\*.fields.Temp_childRecID.value | string | | |
action_result.data.\*.fields.Temp_open.dirty | boolean | | True False |
action_result.data.\*.fields.Temp_open.displayName | string | | temp_open |
action_result.data.\*.fields.Temp_open.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93871342b0c74b0c90e44e4c69bc9ad9ecf233431d |
action_result.data.\*.fields.Temp_open.html | string | | |
action_result.data.\*.fields.Temp_open.value | string | | False |
action_result.data.\*.fields.Temp_pending.dirty | boolean | | True False |
action_result.data.\*.fields.Temp_pending.displayName | string | | temp_pending |
action_result.data.\*.fields.Temp_pending.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:9387132831cb94ec1b33bf40f199d652e9ed17e595 |
action_result.data.\*.fields.Temp_pending.html | string | | |
action_result.data.\*.fields.Temp_pending.value | string | | False |
action_result.data.\*.fields.Temp_reopen.dirty | boolean | | True False |
action_result.data.\*.fields.Temp_reopen.displayName | string | | temp_reopen |
action_result.data.\*.fields.Temp_reopen.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93871327faa0dd54a8b50d4b6d952713c30084c01d |
action_result.data.\*.fields.Temp_reopen.html | string | | |
action_result.data.\*.fields.Temp_reopen.value | string | | False |
action_result.data.\*.fields.Temp_showSLAInfo.dirty | boolean | | True False |
action_result.data.\*.fields.Temp_showSLAInfo.displayName | string | | TEMP_show SLA stuff |
action_result.data.\*.fields.Temp_showSLAInfo.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938ac7c91e2f5c6d1be2a8465cad9919bb25297043 |
action_result.data.\*.fields.Temp_showSLAInfo.html | string | | |
action_result.data.\*.fields.Temp_showSLAInfo.value | string | | False |
action_result.data.\*.fields.Temp_status_set.dirty | boolean | | True False |
action_result.data.\*.fields.Temp_status_set.displayName | string | | temp_status_set |
action_result.data.\*.fields.Temp_status_set.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938713e23db3fc03864ddb44f7933a310f072c5449 |
action_result.data.\*.fields.Temp_status_set.html | string | | |
action_result.data.\*.fields.Temp_status_set.value | string | | False |
action_result.data.\*.fields.Temp_taskDetails.dirty | boolean | | True False |
action_result.data.\*.fields.Temp_taskDetails.displayName | string | | temp_taskDetails |
action_result.data.\*.fields.Temp_taskDetails.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93e71017bbf5b0ea8065164d6f94e26f388bb9e485 |
action_result.data.\*.fields.Temp_taskDetails.html | string | | |
action_result.data.\*.fields.Temp_taskDetails.value | string | | |
action_result.data.\*.fields.Temp_taskTime.dirty | boolean | | True False |
action_result.data.\*.fields.Temp_taskTime.displayName | string | | temp_taskTime |
action_result.data.\*.fields.Temp_taskTime.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93e710176d39c4147d8bb048c9931bd6c3b757009d |
action_result.data.\*.fields.Temp_taskTime.html | string | | |
action_result.data.\*.fields.Temp_taskTime.value | string | | 0 |
action_result.data.\*.fields.TotalSTCTimeInMinutes.dirty | boolean | | True False |
action_result.data.\*.fields.TotalSTCTimeInMinutes.displayName | string | | TotalSTCTimeInMinutes |
action_result.data.\*.fields.TotalSTCTimeInMinutes.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93b7c62c826d949055f19249e6a403307a50ff6972 |
action_result.data.\*.fields.TotalSTCTimeInMinutes.fullFieldId | string | | |
action_result.data.\*.fields.TotalSTCTimeInMinutes.html | string | | |
action_result.data.\*.fields.TotalSTCTimeInMinutes.value | string | | 0 |
action_result.data.\*.fields.TotalTaskTime.dirty | boolean | | True False |
action_result.data.\*.fields.TotalTaskTime.displayName | string | | Total Task Time |
action_result.data.\*.fields.TotalTaskTime.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d38dcafc0b8fcfcd2fa64353a02977143597fb45 |
action_result.data.\*.fields.TotalTaskTime.fullFieldId | string | | |
action_result.data.\*.fields.TotalTaskTime.html | string | | |
action_result.data.\*.fields.TotalTaskTime.value | string | | 0 |
action_result.data.\*.fields.TotalTasks.dirty | boolean | | True False |
action_result.data.\*.fields.TotalTasks.displayName | string | | Total Tasks |
action_result.data.\*.fields.TotalTasks.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93b4fa20417c19e57b58e847b5a109abe721c95e0a |
action_result.data.\*.fields.TotalTasks.fullFieldId | string | | |
action_result.data.\*.fields.TotalTasks.html | string | | |
action_result.data.\*.fields.TotalTasks.value | string | | 0 |
action_result.data.\*.fields.Urgency.dirty | boolean | | True False |
action_result.data.\*.fields.Urgency.displayName | string | | Urgency |
action_result.data.\*.fields.Urgency.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:29d741aae8bf461f8aafa3c9eb4dc822 |
action_result.data.\*.fields.Urgency.fullFieldId | string | | |
action_result.data.\*.fields.Urgency.html | string | | |
action_result.data.\*.fields.Urgency.value | string | | |
action_result.data.\*.fields.VendorID.dirty | boolean | | True False |
action_result.data.\*.fields.VendorID.displayName | string | | Vendor ID |
action_result.data.\*.fields.VendorID.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938b78655951a1a331b7fb4ce489c93c0e1fd77be8 |
action_result.data.\*.fields.VendorID.html | string | | |
action_result.data.\*.fields.VendorID.value | string | | |
action_result.data.\*.fields.VendorName.dirty | boolean | | True False |
action_result.data.\*.fields.VendorName.displayName | string | | Vendor Name |
action_result.data.\*.fields.VendorName.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:938b7865063a90d65b21d94c5bbae5c686297c3feb |
action_result.data.\*.fields.VendorName.html | string | | |
action_result.data.\*.fields.VendorName.value | string | | |
action_result.data.\*.fields.WaitTime.dirty | boolean | | False |
action_result.data.\*.fields.WaitTime.displayName | string | | Wait Time |
action_result.data.\*.fields.WaitTime.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:945503f0beaf7e5b9891b743d491def3925a78d32d |
action_result.data.\*.fields.WaitTime.fullFieldId | string | | |
action_result.data.\*.fields.WaitTime.html | string | | |
action_result.data.\*.fields.WaitTime.value | string | | 0 |
action_result.data.\*.fields.WalkUpSupportLocation.dirty | boolean | | False |
action_result.data.\*.fields.WalkUpSupportLocation.displayName | string | | Walk-Up Support Location |
action_result.data.\*.fields.WalkUpSupportLocation.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:945503e6c7ee29a849e74f4b9087d49d59d822dbd4 |
action_result.data.\*.fields.WalkUpSupportLocation.fullFieldId | string | | |
action_result.data.\*.fields.WalkUpSupportLocation.html | string | | |
action_result.data.\*.fields.WalkUpSupportLocation.value | string | | |
action_result.data.\*.fields.WasCIDown.dirty | boolean | | True False |
action_result.data.\*.fields.WasCIDown.displayName | string | | Was CI Down |
action_result.data.\*.fields.WasCIDown.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93d59cdbce9c360fb88f014a1d9d1df8abdc9e9978 |
action_result.data.\*.fields.WasCIDown.fullFieldId | string | | |
action_result.data.\*.fields.WasCIDown.html | string | | |
action_result.data.\*.fields.WasCIDown.value | string | | False |
action_result.data.\*.fields.Withdraw.dirty | boolean | | True False |
action_result.data.\*.fields.Withdraw.displayName | string | | Withdraw |
action_result.data.\*.fields.Withdraw.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93eb71eaa716390d447f274f35ad9e41ccbfcef59f |
action_result.data.\*.fields.Withdraw.fullFieldId | string | | |
action_result.data.\*.fields.Withdraw.html | string | | |
action_result.data.\*.fields.Withdraw.value | string | | False |
action_result.data.\*.fields.WrkflwCurrentPhase.dirty | boolean | | True False |
action_result.data.\*.fields.WrkflwCurrentPhase.displayName | string | | wrkflwCurrentPhase |
action_result.data.\*.fields.WrkflwCurrentPhase.fieldId | string | | BO:6dd53665c0c24cab86870a21cf6434ae,FI:93837cb8d6004fb6d675254efe854b8c1494f14ddf |
action_result.data.\*.fields.WrkflwCurrentPhase.html | string | | |
action_result.data.\*.fields.WrkflwCurrentPhase.value | string | | |
action_result.data.\*.hasError | boolean | | True False |
action_result.summary | string | | |
action_result.message | string | | Successfully Listed Tickets |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list tickets'

Get a list of incidents

Type: **generic** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.busObId | string | `md5` | 6dd53665c0c24cab86870a21cf6434ae |
action_result.data.\*.busObRecId | string | | 9430df3c11b4e320235525476ab4d45a83e694ee3f |
action_result.data.\*.docRepositoryItemId | string | | |
action_result.data.\*.galleryImage | string | | |
action_result.data.\*.publicId | string | `cherwell incident id` | 102332 |
action_result.data.\*.scope | string | | |
action_result.data.\*.scopeOwner | string | | |
action_result.data.\*.subTitle | string | | Last Modified 11:46 PM by Andrew Simms |
action_result.data.\*.text | string | | Update From Playbook Ticket 102332 |
action_result.data.\*.title | string | | 102332, In Progress, Andrew Simms |
action_result.summary | string | | |
action_result.message | string | | Successfully Listed Tickets |
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
