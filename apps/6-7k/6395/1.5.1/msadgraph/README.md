# MS Graph for Active Directory

Publisher: Splunk <br>
Connector Version: 1.5.1 <br>
Product Vendor: Microsoft <br>
Product Name: MS Graph for Active Directory <br>
Minimum Product Version: 6.4.0

Connects to Microsoft Active Directory using MS Graph REST API services to support various generic and investigative actions

## Prerequisites

Before configuring this connector, ensure you have:

- **Azure AD Administrator Access**: Global Administrator or Privileged Role Administrator role
- **SOAR Platform Access**: Administrator privileges in Splunk SOAR
- **Network Connectivity**: SOAR instance can reach `https://graph.microsoft.com` and `https://login.microsoftonline.com`

## Azure AD Admin Role Requirements

### Required Roles for Setup

The following Azure AD roles can perform the initial setup and grant admin consent:

| **Role** | **Can Grant Admin Consent** | **Least Privilege Option** |
|----------|----------------------------|---------------------------|
| **Global Administrator** | Yes | Not recommended for production |
| **Privileged Role Administrator** | Yes | **Recommended** |
| **Cloud Application Administrator** | Limited | Only for apps they manage |
| **Application Administrator** | Limited | Only for apps they manage |

**Recommendation**: Use **Privileged Role Administrator** as it provides the necessary permissions without the broad access of Global Administrator.

### Operational Role Requirements

For ongoing operations, specific actions require different privilege levels:

- **Reset Password**: User Administrator role minimum
- **Enable/Disable Users**: Privileged Authentication Administrator role minimum
- **Manage Groups**: Groups Administrator role minimum
- **Read-only Operations**: Directory Readers role sufficient

### Reset Password Limitations

The **reset password** action calls the Microsoft Graph Update user API and updates the user's `passwordProfile`
property. This property contains the new temporary password and whether the user must change the password at next
sign-in. Microsoft documents in the Update user API request body properties that `passwordProfile` cannot be used for
federated users. For federated users, Microsoft Entra ID can return the error "Password cannot be changed for federated
users." Password management for federated users should be handled through the federation provider instead.

For more information, see the Microsoft Graph
[Update user API request body](https://learn.microsoft.com/en-us/graph/api/user-update?view=graph-rest-1.0#request-body).

## Configuration Overview

The MS Graph for Active Directory connector supports two authentication modes:

1. **Delegated Permissions** (Interactive): Acts on behalf of a signed-in user
1. **Application Permissions** (Non-interactive): Acts with its own identity

## Step-by-Step Setup Guide

### Step 1: Create Azure Application Registration

1. Navigate to [Azure Portal](https://portal.azure.com)
1. Go to **Azure Active Directory** → **App registrations**
1. Click **+ New registration**
1. Configure the application:
   - **Name**: `SOAR-MSGraph-Connector` (or your preferred name)
   - **Supported account types**: Select appropriate option for your organization
   - **Redirect URI**: Leave blank for now (will be configured later)
1. Click **Register**
1. **Save the Application (client) ID** - you'll need this for the SOAR asset configuration

### Step 2: Create Client Secret

1. In your app registration, go to **Certificates & secrets**
1. Click **+ New client secret**
1. Add a description and set expiration (24 months recommended)
1. Click **Add**
1. **Immediately copy and securely store the secret value** - it cannot be retrieved later

### Step 3: Configure API Permissions

Choose **either** Delegated OR Application permissions based on your use case:

#### Option A: Delegated Permissions (Recommended for most use cases)

1. Go to **API permissions** → **+ Add a permission**
1. Select **Microsoft Graph** → **Delegated permissions**
1. Add the following permissions:
   - `User.ReadWrite.All`
   - `Directory.ReadWrite.All`
   - `Directory.AccessAsUser.All`
   - `User.ManageIdentities.All`
   - `Group.ReadWrite.All`
   - `GroupMember.ReadWrite.All`
   - `RoleManagement.ReadWrite.Directory`
   - `Policy.Read.All`
   - `Policy.ReadWrite.ConditionalAccess`
   - `offline_access`
1. Click **Add permissions**
1. Click **Grant admin consent for [Your Organization]**

#### Note: **reset password** and **disable user** action is required minimun User Administrator role to be run with Delegated permissions

#### Option B: Application Permissions (For automated scenarios)

1. Go to **API permissions** → **+ Add a permission**
1. Select **Microsoft Graph** → **Application permissions**
1. Add the following permissions:
   - `User.ReadWrite.All`
   - `Directory.ReadWrite.All`
   - `User.ManageIdentities.All`
   - `Group.ReadWrite.All`
   - `GroupMember.ReadWrite.All`
   - `RoleManagement.ReadWrite.Directory`
   - `Policy.Read.All`
   - `Policy.ReadWrite.ConditionalAccess`
   - `User-PasswordProfile.ReadWrite.All`
1. Click **Add permissions**
1. Click **Grant admin consent for [Your Organization]**

#### Note: `User-PasswordProfile.ReadWrite.All` is required only for **reset password** action to be run with Application permissions

### Step 4: Configure SOAR Asset

1. In Splunk SOAR, go to **Apps** → **MS Graph for Active Directory**
1. Click **+ ASSET**
1. Configure the asset with the following information:

## Asset Configuration

### Configuration Fields Explained

| **SOAR Field** | **Azure Portal Equivalent** | **Description** | **Required** |
|----------------|----------------------------|-----------------|--------------|
| **Tenant** | Directory (tenant) ID | Your Azure AD tenant identifier | Yes |
| **Application ID** | Application (client) ID | The app registration's unique identifier | Yes |
| **Client Secret** | Client secret value | The secret created in Step 2 | Yes |
| **Microsoft AD Region** | N/A | Select your Microsoft cloud environment | No (defaults to Global) |
| **Admin Access Required** | N/A | Check if using Application permissions | No |
| **Admin Consent Already Provided** | N/A | Check if admin consent was granted in Azure | No |

### Region Options

| **Region** | **Endpoint** | **Use Case** |
|------------|--------------|--------------|
| **Global** | `graph.microsoft.com` | Most organizations |
| **US Gov L4** | `graph.microsoft.us` | US Government |
| **US Gov L5 (DOD)** | `dod-graph.microsoft.us` | US Department of Defense |
| **Germany** | `graph.microsoft.de` | Microsoft Cloud Germany |
| **China (21Vianet)** | `microsoftgraph.chinacloudapi.cn` | Microsoft Cloud China |

### Step 5: Update Redirect URI

1. After saving the SOAR asset, note the **POST incoming for MS Graph to this location** URL
1. Return to your Azure app registration
1. Go to **Authentication** → **+ Add a platform** → **Web**
1. Add the redirect URI: `[SOAR_URL]/result`
   - Example: `https://<phantom_host>/rest/handler/msgraphforactivedirectory_f2a239df-acb2-47d6-861c-726a435cfe76/<asset_name>/result`
1. Click **Configure**

## Understanding Consent Types

### Azure Admin Consent vs SOAR Test Connectivity

There are **two different consent processes** that serve different purposes:

#### 1. Azure Admin Consent

- **Where**: Azure Portal → App registrations → API permissions
- **Purpose**: Grants the application permission to access Microsoft Graph APIs
- **Who**: Azure AD administrator (Global Admin or Privileged Role Admin)
- **When**: During initial setup in Azure Portal
- **What it grants**: API access permissions to the application

#### 2. SOAR Test Connectivity Consent

- **Where**: SOAR platform → Asset → Test Connectivity
- **Purpose**: Establishes the authentication flow and obtains access tokens
- **Who**: User with appropriate Azure AD permissions for the requested operations
- **When**: During SOAR asset configuration and testing
- **What it grants**: Actual authentication tokens for API calls

**Both consents are required** for the connector to function properly.

### Simplified Consent Flow

The traditional three-step process can be optimized:

#### Traditional Flow (Can be simplified)

1. Admin grants consent in Azure Portal
1. Uncheck "Admin Consent Already Provided" in SOAR
1. Run Test Connectivity with functional account

#### Optimized Flow (Recommended)

1. Admin grants consent in Azure Portal
1. **Check "Admin Consent Already Provided" in SOAR**
1. Run Test Connectivity - it will use application permissions directly

**Recommendation**: Use the optimized flow by checking "Admin Consent Already Provided" after granting consent in Azure Portal.

## Permissions Reference

### Action-Specific Permissions

The following table shows the minimum required permissions for each action:

| **Action** | **Minimum Delegated Permission** | **Minimum Application Permission** | **Azure AD Role Required** |
|------------|----------------------------------|-----------------------------------|---------------------------|
| **Test Connectivity** | `User.Read` | `User.Read.All` | Directory Readers |
| **List Users** | `User.Read.All` | `User.Read.All` | Directory Readers |
| **Reset Password** | `User.ReadWrite.All` | `User-PasswordProfile.ReadWrite.All` | User Administrator |
| **Disable Tokens** | `User.RevokeSessions.All` | `User.RevokeSessions.All` | Directory Readers |
| **Enable/Disable User** | `User.ReadWrite.All` | `User.ReadWrite.All` | Privileged Authentication Administrator |
| **List User Devices** | `User.Read` | `Directory.Read.All` | Directory Readers |
| **List User Attributes** | `User.Read.All` | `User.Read.All` | Directory Readers |
| **Set User Attribute** | `User.ReadWrite.All` | `User.ReadWrite.All` | User Administrator |
| **Add/Remove User (Group)** | `GroupMember.ReadWrite.All` | `GroupMember.ReadWrite.All` | Groups Administrator |
| **List Groups** | `Group.Read.All` | `Group.Read.All` | Directory Readers |
| **Get Group** | `Group.Read.All` | `Group.Read.All` | Directory Readers |
| **List Group Members** | `GroupMember.Read.All` | `GroupMember.Read.All` | Directory Readers |
| **Validate Group** | `User.Read.All` | `User.Read.All` | Directory Readers |
| **List Directory Roles** | `RoleManagement.Read.Directory` | `RoleManagement.Read.Directory` | Directory Readers |
| **List Named Locations** | `Policy.Read.All` | `Policy.Read.All` | Conditional Access Administrator |
| **Add CIDR to Named Location** | `Policy.Read.All`, `Policy.ReadWrite.ConditionalAccess` | `Policy.Read.All`, `Policy.ReadWrite.ConditionalAccess` | Conditional Access Administrator |
| **Remove CIDR from Named Location** | `Policy.Read.All`, `Policy.ReadWrite.ConditionalAccess` | `Policy.Read.All`, `Policy.ReadWrite.ConditionalAccess` | Conditional Access Administrator |

### Full vs Minimum Permissions

**Current Configuration** (Full permissions - maximum capability):

- `User.ReadWrite.All`, `Directory.ReadWrite.All`, `User.ManageIdentities.All`
- `Group.ReadWrite.All`, `GroupMember.ReadWrite.All`, `RoleManagement.ReadWrite.Directory`
- `Policy.Read.All`, `Policy.ReadWrite.ConditionalAccess`

**Minimum Required** (For read-only operations):

- `User.Read.All`, `Group.Read.All`, `GroupMember.Read.All`

## Test Connectivity

### For Delegated Permissions

1. Click **TEST CONNECTIVITY** on the asset
1. A popup will display a URL - click to open in a new tab
1. Sign in with an account that has the necessary Azure AD permissions
1. Review and accept the permission request
1. Close the browser tab and return to SOAR
1. The test should complete successfully

### For Application Permissions

1. Ensure **Admin Access Required** and **Admin Consent Already Provided** are checked
1. Click **TEST CONNECTIVITY**
1. The test will authenticate using the application's own identity
1. No interactive login is required

## User Permissions Setup

To complete the authorization process, this app needs permission to view assets, which is not granted by default.

1. **Check Asset User**

   - Navigate to **Asset Settings > Advanced**
   - Note the user listed under **Select a user on behalf of which automated actions can be executed**
   - Default user is typically **automation**

1. **Create Asset Viewer Role**

   - Go to **Administration > User Management > Roles & Permissions > + ROLE**
   - **Name**: "Asset Viewer" (or similar)
   - **Users tab**: Add the user from step 1
   - **Permissions tab**: Grant **View Assets** privilege
   - Click **SAVE**

## State File Permissions

The connector stores authentication tokens in a state file that requires proper permissions:

### File Locations

- **Root Install**: `/opt/phantom/local_data/app_states/f2a239df-acb2-47d6-861c-726a435cfe76/{asset_id}_state.json`
- **Non-Root Install**: `/<PHANTOM_HOME_DIRECTORY>/local_data/app_states/f2a239df-acb2-47d6-861c-726a435cfe76/{asset_id}_state.json`

### Required Permissions

- **File Rights**: `rw-rw-r--` (664) (The SOAR user should have read and write access for the state file)
- **File Owner**: Appropriate SOAR user
- **Access**: SOAR user must have read and write access

## Port Details

The app uses HTTP/ HTTPS protocol for communicating with the Microsoft Graph server. Below are the
default ports used by the Splunk SOAR Connector.

| Service Name | Transport Protocol | Port |
|--------------|--------------------|------|
| https | tcp | 443 |

## Microsoft Documentation References

- [Microsoft Graph Permissions Overview](https://learn.microsoft.com/en-us/graph/permissions-overview)
- [Microsoft Graph Permissions Reference](https://learn.microsoft.com/en-us/graph/permissions-reference)
- [Azure AD Built-in Roles](https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/permissions-reference)
- [Microsoft Graph API Documentation](https://learn.microsoft.com/en-us/graph/)
- [Application vs Delegated Permissions](https://learn.microsoft.com/en-us/graph/auth/auth-concepts#delegated-and-application-permissions)

### Configuration variables

This table lists the configuration variables required to operate MS Graph for Active Directory. These variables are specified when configuring a MS Graph for Active Directory asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**tenant_id** | required | string | Tenant (Tenant ID or Tenant Name) |
**client_id** | required | string | Application ID |
**client_secret** | required | password | Client Secret |
**region** | optional | string | Microsoft AD Region |
**admin_access_required** | optional | boolean | Admin Access Required |
**admin_access_granted** | optional | boolean | Admin Consent Already Provided |

### Supported Actions

[test connectivity](#action-test-connectivity) - Use supplied credentials to generate a token with MS Graph <br>
[list users](#action-list-users) - Get a list of users <br>
[reset password](#action-reset-password) - Reset or set a user's password in a Microsoft AD environment <br>
[disable tokens](#action-disable-tokens) - Invalidate all active refresh tokens for a user in a Microsoft AD environment <br>
[enable user](#action-enable-user) - Enable a user <br>
[disable user](#action-disable-user) - Disable a user <br>
[list user devices](#action-list-user-devices) - List devices for a specified user <br>
[list user attributes](#action-list-user-attributes) - List attributes for all or a specified user <br>
[set user attribute](#action-set-user-attribute) - Set an attribute for a user <br>
[remove user](#action-remove-user) - Remove a user from a specified group <br>
[add user](#action-add-user) - Add a user to a specified group <br>
[list groups](#action-list-groups) - List groups in the organization <br>
[get group](#action-get-group) - Get information about a group <br>
[list group members](#action-list-group-members) - List the members in a group <br>
[validate group](#action-validate-group) - Returns true if a user is in a group; otherwise, false <br>
[list directory roles](#action-list-directory-roles) - List the directory roles that are activated in the tenant <br>
[list named locations](#action-list-named-locations) - List named locations in Entra Conditional Access <br>
[add cidr to named location](#action-add-cidr-to-named-location) - Add a CIDR range to an IP-based named location in Entra Conditional Access <br>
[remove cidr from named location](#action-remove-cidr-from-named-location) - Remove a CIDR range from an IP-based named location in Entra Conditional Access <br>
[generate token](#action-generate-token) - Generate a token

## action: 'test connectivity'

Use supplied credentials to generate a token with MS Graph

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list users'

Get a list of users

Type: **investigate** <br>
Read only: **True**

For more information on using the filter_string, select_string and expand_string parameters, refer to https://docs.microsoft.com/en-us/graph/query-parameters. By default, only a limited set of properties are returned, to return an alternative property set use $select query parameter.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**filter_string** | optional | Filter string to apply to user listing | string | |
**select_string** | optional | Select string to get additional user properties. Separate multiple values with commas | string | |
**expand_string** | optional | Expand string to get a resource or collection referenced by a single relationship | string | |
**use_advanced_query** | optional | Use advanced query capabilities | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.expand_string | string | | manager |
action_result.parameter.filter_string | string | | startswith(displayName,'User') |
action_result.parameter.select_string | string | | displayName |
action_result.parameter.use_advanced_query | boolean | | True False |
action_result.data.\*.accountEnabled | boolean | | True False |
action_result.data.\*.ageGroup | string | | |
action_result.data.\*.assignedLicenses.\*.skuId | string | | 189a915c-fe4f-4ffa-bde4-85b9628d07a0 |
action_result.data.\*.assignedPlans.\*.assignedTimestamp | string | | 2017-08-29T02:31:40Z |
action_result.data.\*.assignedPlans.\*.capabilityStatus | string | | Enabled |
action_result.data.\*.assignedPlans.\*.service | string | | OfficeForms |
action_result.data.\*.assignedPlans.\*.servicePlanId | string | | e212cbc7-0961-4c40-9825-01117710dcb1 |
action_result.data.\*.city | string | | Palo Alto |
action_result.data.\*.companyName | string | | |
action_result.data.\*.consentProvidedForMinor | string | | |
action_result.data.\*.country | string | | US |
action_result.data.\*.createdDateTime | string | | 2019-05-21T22:27:20Z |
action_result.data.\*.creationType | string | | |
action_result.data.\*.deletionTimestamp | string | | |
action_result.data.\*.department | string | | Sales |
action_result.data.\*.dirSyncEnabled | string | | |
action_result.data.\*.displayName | string | | User |
action_result.data.\*.employeeId | string | | |
action_result.data.\*.facsimileTelephoneNumber | string | | |
action_result.data.\*.givenName | string | | testuser |
action_result.data.\*.id | string | `user id` | e4c722ac-3b83-478d-8f52-c388885dc30f |
action_result.data.\*.immutableId | string | | |
action_result.data.\*.isCompromised | string | | |
action_result.data.\*.jobTitle | string | | Sales Manager |
action_result.data.\*.lastDirSyncTime | string | | |
action_result.data.\*.legalAgeGroupClassification | string | | |
action_result.data.\*.mail | string | `email` | user@test.com |
action_result.data.\*.mailNickname | string | | testmail |
action_result.data.\*.mobile | string | | +1 5556378688 |
action_result.data.\*.mobilePhone | string | | |
action_result.data.\*.objectType | string | | User |
action_result.data.\*.odata.type | string | | test.DirectoryServices.User |
action_result.data.\*.officeLocation | string | | |
action_result.data.\*.onPremisesDistinguishedName | string | | |
action_result.data.\*.onPremisesSecurityIdentifier | string | | |
action_result.data.\*.otherMails | string | `email` | user.test@outlook.com |
action_result.data.\*.passwordPolicies | string | | None |
action_result.data.\*.passwordProfile | string | | |
action_result.data.\*.passwordProfile.enforceChangePasswordPolicy | boolean | | True False |
action_result.data.\*.passwordProfile.forceChangePasswordNextLogin | boolean | | True False |
action_result.data.\*.passwordProfile.password | string | | |
action_result.data.\*.physicalDeliveryOfficeName | string | | |
action_result.data.\*.postalCode | string | | 94303 |
action_result.data.\*.preferredLanguage | string | | en-US |
action_result.data.\*.provisionedPlans.\*.capabilityStatus | string | | Enabled |
action_result.data.\*.provisionedPlans.\*.provisioningStatus | string | | Success |
action_result.data.\*.provisionedPlans.\*.service | string | | exchange |
action_result.data.\*.proxyAddresses | string | | SMTP:user1@test.com |
action_result.data.\*.refreshTokensValidFromDateTime | string | | 2017-09-27T22:54:59Z |
action_result.data.\*.showInAddressList | string | | |
action_result.data.\*.sipProxyAddress | string | `email` | user@test.com |
action_result.data.\*.state | string | | CA |
action_result.data.\*.streetAddress | string | | 2479 E. Bayshore Rd. |
action_result.data.\*.surname | string | | Test_surname |
action_result.data.\*.telephoneNumber | string | | |
action_result.data.\*.thumbnailPhoto@odata.mediaEditLink | string | | directoryObjects/6132ca31-7a09-434f-a269-abe836d0c01e/test.DirectoryServices.User/thumbnailPhoto |
action_result.data.\*.usageLocation | string | | US |
action_result.data.\*.userPrincipalName | string | `user id` | user@test.com |
action_result.data.\*.userState | string | | |
action_result.data.\*.userStateChangedOn | string | | |
action_result.data.\*.userType | string | | Member |
action_result.summary.num_users | numeric | | 8 |
action_result.summary.result_found | boolean | | True False |
action_result.summary.total_results | numeric | | 7 |
action_result.message | string | | Successfully listed users |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'reset password'

Reset or set a user's password in a Microsoft AD environment

Type: **contain** <br>
Read only: **False**

Password reset updates the user's passwordProfile property. This property cannot be used for federated users; manage those passwords through the federation provider. For more information, refer to https://learn.microsoft.com/en-us/graph/api/user-update?view=graph-rest-1.0#request-body.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user_id** | required | User ID to change password - can be user principal name or object ID | string | `user id` |
**force_change** | optional | Force user to change password on next login | boolean | |
**temp_password** | required | Temporary password for user | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.force_change | boolean | | True False |
action_result.parameter.temp_password | string | | Temp_PA$$w0rd |
action_result.parameter.user_id | string | `user id` | ee3dc4f2-70f9-446f-a19e-6b4e95ba030d user@test.com |
action_result.data | string | | |
action_result.summary.status | string | | Successfully reset user password |
action_result.message | string | | Status: Successfully reset user password |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'disable tokens'

Invalidate all active refresh tokens for a user in a Microsoft AD environment

Type: **contain** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user_id** | required | User ID to disable tokens of - can be user principal name or object ID | string | `user id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.user_id | string | `user id` | ee3dc4f2-70f9-446f-a19e-6b4e95ba030d user@test.com |
action_result.data | string | | |
action_result.data.\*.@odata.context | string | | https://graph.test.com/v1.0/$metadata#Edm.Boolean |
action_result.data.\*.odata.metadata | string | `url` | https://graph.windows.net/1t309est-db6c-4tes-t1d2-12bf3456d78d/$metadata#Edm.Null |
action_result.data.\*.odata.null | boolean | | True False |
action_result.data.\*.value | boolean | | True False |
action_result.summary.status | string | | Successfully disabled tokens |
action_result.message | string | | Successfully invalidated tokens Status: Successfully disabled tokens |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'enable user'

Enable a user

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user_id** | required | User ID to enable - can be user principal name or object ID | string | `user id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.user_id | string | `user id` | user@test.com |
action_result.data | string | | |
action_result.summary.status | string | | Successfully enabled user user@test.com |
action_result.message | string | | Status: Successfully enabled user user@test.com |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'disable user'

Disable a user

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user_id** | required | User ID to disable - can be user principal name or object ID | string | `user id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.user_id | string | `user id` | user@test.com |
action_result.data | string | | |
action_result.summary.status | string | | Successfully disabled user user@test.com |
action_result.message | string | | Status: Successfully disabled user user@test.com |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list user devices'

List devices for a specified user

Type: **investigate** <br>
Read only: **True**

By default, only a limited set of properties are returned, to return an alternative property set use $select query parameter. For more information on using the select_string parameter, refer to <a href='https://docs.microsoft.com/en-us/graph/query-parameters#select-parameter' target='_blank'>this</a> documentation.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user_id** | required | User ID - can be user principal name or object ID | string | `user id` |
**select_string** | optional | Select string to get additional user properties. Separate multiple values with commas | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.select_string | string | | displayName |
action_result.parameter.user_id | string | `user id` | user@test.com |
action_result.data.\*.@odata.type | string | | #test.graph.device |
action_result.data.\*.accountEnabled | boolean | | True False |
action_result.data.\*.alternativeSecurityIds.\*.identityProvider | string | | |
action_result.data.\*.alternativeSecurityIds.\*.key | string | | WAA1ADAAOQA6ADwAUwBIAEEAMQAtAFQAUAAtAFAAVQBCAEsARQBZAD4AOQA5AEEARQAwADgAOABDAEUANAA1ADgAMABCADcAQgBGAEEARQA2ADEAQQBCADYANAA3ADYANgA5ADUAOAAzAEQANABFAEYARQA5ADYAOAAyAHkAcQBSAEIANwBrAGEAMQA4AEoATAByACsAegB4AE8AYwB6AE8AYgBNAFEANQBZAEgAbgB0AFQAdgBOAG0AbgA5AEQAZQA2AFgAVQBUAGgAcwBFAD0A |
action_result.data.\*.alternativeSecurityIds.\*.type | numeric | | 2 |
action_result.data.\*.approximateLastSignInDateTime | string | | 2019-09-26T03:42:15Z |
action_result.data.\*.complianceExpirationDateTime | string | | |
action_result.data.\*.createdDateTime | string | | 2019-09-26T03:42:15Z |
action_result.data.\*.deletedDateTime | string | | |
action_result.data.\*.deviceCategory | string | | |
action_result.data.\*.deviceId | string | | |
action_result.data.\*.deviceMetadata | string | | |
action_result.data.\*.deviceOwnership | string | | |
action_result.data.\*.deviceVersion | numeric | | |
action_result.data.\*.displayName | string | | |
action_result.data.\*.domainName | string | | |
action_result.data.\*.enrollmentProfileName | string | | |
action_result.data.\*.enrollmentType | string | | |
action_result.data.\*.extensionAttributes.extensionAttribute1 | string | | |
action_result.data.\*.extensionAttributes.extensionAttribute10 | string | | |
action_result.data.\*.extensionAttributes.extensionAttribute11 | string | | |
action_result.data.\*.extensionAttributes.extensionAttribute12 | string | | |
action_result.data.\*.extensionAttributes.extensionAttribute13 | string | | |
action_result.data.\*.extensionAttributes.extensionAttribute14 | string | | |
action_result.data.\*.extensionAttributes.extensionAttribute15 | string | | |
action_result.data.\*.extensionAttributes.extensionAttribute2 | string | | |
action_result.data.\*.extensionAttributes.extensionAttribute3 | string | | |
action_result.data.\*.extensionAttributes.extensionAttribute4 | string | | |
action_result.data.\*.extensionAttributes.extensionAttribute5 | string | | |
action_result.data.\*.extensionAttributes.extensionAttribute6 | string | | |
action_result.data.\*.extensionAttributes.extensionAttribute7 | string | | |
action_result.data.\*.extensionAttributes.extensionAttribute8 | string | | |
action_result.data.\*.extensionAttributes.extensionAttribute9 | string | | |
action_result.data.\*.externalSourceName | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.isCompliant | boolean | | |
action_result.data.\*.isManaged | boolean | | |
action_result.data.\*.isRooted | string | | |
action_result.data.\*.managementType | string | | |
action_result.data.\*.manufacturer | string | | |
action_result.data.\*.mdmAppId | string | | |
action_result.data.\*.model | string | | |
action_result.data.\*.onPremisesLastSyncDateTime | string | | |
action_result.data.\*.onPremisesSyncEnabled | boolean | | |
action_result.data.\*.operatingSystem | string | | Windows |
action_result.data.\*.operatingSystemVersion | string | | 10.0.18362.0 |
action_result.data.\*.profileType | string | | RegisteredDevice |
action_result.data.\*.registrationDateTime | string | | 2019-09-26T03:42:15Z |
action_result.data.\*.sourceType | string | | |
action_result.data.\*.trustType | string | | Workplace |
action_result.summary | string | | |
action_result.summary.status | string | | Successfully retrieved owned devices for user test@user.test.com |
action_result.message | string | | Status: Successfully retrieved owned devices for user test@user.test.com |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list user attributes'

List attributes for all or a specified user

Type: **investigate** <br>
Read only: **True**

By default, only a limited set of properties are returned, to return an alternative property set use $select query parameter. For more information on using the select_string and expand_string parameters, refer to https://docs.microsoft.com/en-us/graph/query-parameters.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user_id** | optional | User ID - can be user principal name or object ID | string | `user id` |
**select_string** | optional | Select string to get additional user properties. Separate multiple values with commas | string | |
**expand_string** | optional | Expand string to get a resource or collection referenced by a single relationship | string | |
**use_advanced_query** | optional | Use advanced query capabilities | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.expand_string | string | | manager |
action_result.parameter.select_string | string | | displayName |
action_result.parameter.use_advanced_query | boolean | | True False |
action_result.parameter.user_id | string | `user id` | user@test.com |
action_result.data.\*.@odata.context | string | | https://graph.test.com/v1.0/$metadata#users/$entity |
action_result.data.\*.accountEnabled | boolean | | True False |
action_result.data.\*.ageGroup | string | | |
action_result.data.\*.assignedLicenses.\*.skuId | string | | f30db892-07e9-47e9-837c-80727f46fd3d |
action_result.data.\*.assignedPlans.\*.assignedTimestamp | string | | 2019-04-26T07:21:18Z |
action_result.data.\*.assignedPlans.\*.capabilityStatus | string | | Enabled |
action_result.data.\*.assignedPlans.\*.service | string | | exchange |
action_result.data.\*.assignedPlans.\*.servicePlanId | string | | 33c4f319-9bdd-48d6-9c4d-410b750a4a5a |
action_result.data.\*.city | string | | |
action_result.data.\*.companyName | string | | |
action_result.data.\*.consentProvidedForMinor | string | | |
action_result.data.\*.country | string | | |
action_result.data.\*.createdDateTime | string | | 2019-05-02T20:27:59Z |
action_result.data.\*.creationType | string | | |
action_result.data.\*.deletionTimestamp | string | | |
action_result.data.\*.department | string | | Sales |
action_result.data.\*.dirSyncEnabled | string | | |
action_result.data.\*.displayName | string | | Test User |
action_result.data.\*.employeeId | string | | |
action_result.data.\*.facsimileTelephoneNumber | string | | |
action_result.data.\*.givenName | string | | |
action_result.data.\*.id | string | `user id` | 7d55d7e6-cf5a-4dd2-a176-57a3c33b7fa9 |
action_result.data.\*.identities.\*.issuer | string | | test.com |
action_result.data.\*.identities.\*.issuerAssignedId | string | | test2@user.test.com |
action_result.data.\*.identities.\*.signInType | string | | userPrincipalName |
action_result.data.\*.immutableId | string | | |
action_result.data.\*.isCompromised | string | | |
action_result.data.\*.jobTitle | string | | |
action_result.data.\*.lastDirSyncTime | string | | |
action_result.data.\*.legalAgeGroupClassification | string | | |
action_result.data.\*.mail | string | `email` | |
action_result.data.\*.mailNickname | string | | test |
action_result.data.\*.mobile | string | | |
action_result.data.\*.mobilePhone | string | | |
action_result.data.\*.objectId | string | | 59f51194-1998-4932-a8ac-468e59374edc |
action_result.data.\*.objectType | string | | User |
action_result.data.\*.odata.metadata | string | | https://graph.windows.net/1t309est-db6c-4tes-t1d2-12bf3456d78d/$metadata#directoryObjects/@Element |
action_result.data.\*.odata.type | string | | test.DirectoryServices.User |
action_result.data.\*.officeLocation | string | | |
action_result.data.\*.onPremisesDistinguishedName | string | | |
action_result.data.\*.onPremisesSecurityIdentifier | string | | |
action_result.data.\*.otherMails | string | `email` | user@test.com |
action_result.data.\*.passwordPolicies | string | | |
action_result.data.\*.passwordProfile | string | | |
action_result.data.\*.passwordProfile.enforceChangePasswordPolicy | boolean | | True False |
action_result.data.\*.passwordProfile.forceChangePasswordNextLogin | boolean | | True False |
action_result.data.\*.passwordProfile.password | string | | |
action_result.data.\*.physicalDeliveryOfficeName | string | | |
action_result.data.\*.postalCode | string | | |
action_result.data.\*.preferredLanguage | string | | |
action_result.data.\*.provisionedPlans.\*.capabilityStatus | string | | Enabled |
action_result.data.\*.provisionedPlans.\*.provisioningStatus | string | | Success |
action_result.data.\*.provisionedPlans.\*.service | string | | exchange |
action_result.data.\*.proxyAddresses | string | | SMTP:test_shared_mailbox@test.com |
action_result.data.\*.refreshTokensValidFromDateTime | string | | 2019-05-16T19:54:18Z |
action_result.data.\*.showInAddressList | string | | |
action_result.data.\*.sipProxyAddress | string | `email` | |
action_result.data.\*.state | string | | |
action_result.data.\*.streetAddress | string | | |
action_result.data.\*.surname | string | | |
action_result.data.\*.telephoneNumber | string | | |
action_result.data.\*.thumbnailPhoto@odata.mediaEditLink | string | | directoryObjects/59f12345-1998-4932-a8ac-468e59374edc/test.DirectoryServices.User/thumbnailPhoto |
action_result.data.\*.usageLocation | string | | US |
action_result.data.\*.userPrincipalName | string | `user id` | user@test.com |
action_result.data.\*.userState | string | | |
action_result.data.\*.userStateChangedOn | string | | |
action_result.data.\*.userType | string | | Member |
action_result.summary.status | string | | Successfully retrieved user attributes Successfully retrieved attributes for user user@test.com |
action_result.message | string | | Status: Successfully retrieved user attributes Status: Successfully retrieved attributes for user user@test.com, User enabled: False |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'set user attribute'

Set an attribute for a user

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user_id** | required | User ID - can be user principal name or object ID | string | `user id` |
**attribute** | required | Attribute to set | string | |
**attribute_value** | required | Value of attribute to set | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.attribute | string | | department |
action_result.parameter.attribute_value | string | | Sales |
action_result.parameter.user_id | string | `user id` | user@test.com |
action_result.data | string | | |
action_result.data.\*.classification | string | | |
action_result.data.\*.createdDateTime | string | | 2021-03-25T18:40:53Z |
action_result.data.\*.deletedDateTime | string | | |
action_result.data.\*.deletionTimestamp | string | | |
action_result.data.\*.description | string | | This is for testing purpose |
action_result.data.\*.dirSyncEnabled | string | | |
action_result.data.\*.displayName | string | | Test-site |
action_result.data.\*.expirationDateTime | string | | |
action_result.data.\*.id | string | `user id` | 2a201c95-101b-42d9-a7af-9a2fdf8193f1 |
action_result.data.\*.isAssignableToRole | string | | |
action_result.data.\*.lastDirSyncTime | string | | |
action_result.data.\*.mail | string | `email` | Test-site@test.com |
action_result.data.\*.mailEnabled | boolean | | True False |
action_result.data.\*.mailNickname | string | | Test-site |
action_result.data.\*.membershipRule | string | | |
action_result.data.\*.membershipRuleProcessingState | string | | |
action_result.data.\*.objectType | string | | Group |
action_result.data.\*.odata.type | string | | test.DirectoryServices.Group |
action_result.data.\*.onPremisesDomainName | string | `domain` | |
action_result.data.\*.onPremisesLastSyncDateTime | string | | |
action_result.data.\*.onPremisesNetBiosName | string | | |
action_result.data.\*.onPremisesSamAccountName | string | | |
action_result.data.\*.onPremisesSecurityIdentifier | string | | |
action_result.data.\*.onPremisesSyncEnabled | string | | |
action_result.data.\*.preferredDataLocation | string | | |
action_result.data.\*.preferredLanguage | string | | |
action_result.data.\*.proxyAddresses | string | | SMTP:test-h@test.com |
action_result.data.\*.renewedDateTime | string | | 2021-03-25T18:40:53Z |
action_result.data.\*.securityEnabled | boolean | | True False |
action_result.data.\*.securityIdentifier | string | | S-1-12-1-294681889-1319597617-672379543-28952017 |
action_result.data.\*.theme | string | | |
action_result.data.\*.visibility | string | | Private |
action_result.summary.status | string | | Successfully enabled user user@test.com |
action_result.message | string | | Status: Successfully enabled user user@test.com |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.ph_0 | ph | | |

## action: 'remove user'

Remove a user from a specified group

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**group_object_id** | required | Object ID of group | string | `group object id` |
**user_id** | required | User ID to remove from group | string | `user id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.group_object_id | string | `group object id` | ddb876b3-603a-437b-9814-2d46a2219a1e |
action_result.parameter.user_id | string | `user id` | 17be76d0-35ed-4881-ab62-d2eb73c2ebe3 |
action_result.data | string | | |
action_result.summary.status | string | | Successfully removed user from group User not in group |
action_result.message | string | | Status: Successfully removed user from group Status: User not in group |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add user'

Add a user to a specified group

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**group_object_id** | required | Object ID of group | string | `group object id` |
**user_id** | required | User ID to add to group | string | `user id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.group_object_id | string | `group object id` | ddb876b3-603a-437b-9814-2d46a2219a1e |
action_result.parameter.user_id | string | `user id` | 17be76d0-35ed-4881-ab62-d2eb73c2ebe3 |
action_result.data | string | | |
action_result.summary.status | string | | Successfully added user to group User already in group |
action_result.message | string | | Status: Successfully added user to group Status: User already in group |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list groups'

List groups in the organization

Type: **investigate** <br>
Read only: **True**

By default, only a limited set of properties are returned, to return an alternative property set use $select query parameter. For more information on using the select_string and expand_string parameters, refer to https://docs.microsoft.com/en-us/graph/query-parameters.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**filter_string** | optional | Filter string to apply to group listing | string | |
**select_string** | optional | Select string to get additional group properties. Separate multiple values with commas | string | |
**expand_string** | optional | Expand string to get a resource or collection referenced by a single relationship | string | |
**use_advanced_query** | optional | Use advanced query capabilities | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.expand_string | string | | members |
action_result.parameter.filter_string | string | | createdDateTime ge '2014-01-01T00:00:00Z' |
action_result.parameter.select_string | string | | displayName |
action_result.parameter.use_advanced_query | boolean | | True False |
action_result.data.\*.classification | string | | |
action_result.data.\*.createdDateTime | string | | 2021-03-25T18:40:53Z |
action_result.data.\*.deletedDateTime | string | | |
action_result.data.\*.deletionTimestamp | string | | |
action_result.data.\*.description | string | | This is for testing purpose |
action_result.data.\*.dirSyncEnabled | string | | |
action_result.data.\*.displayName | string | | Test-site |
action_result.data.\*.expirationDateTime | string | | |
action_result.data.\*.id | string | `group object id` | 2a201c95-101b-42d9-a7af-9a2fdf8193f1 |
action_result.data.\*.isAssignableToRole | string | | |
action_result.data.\*.lastDirSyncTime | string | | |
action_result.data.\*.mail | string | `email` | Test-site@test.com |
action_result.data.\*.mailEnabled | boolean | | True False |
action_result.data.\*.mailNickname | string | | Test-site |
action_result.data.\*.membershipRule | string | | |
action_result.data.\*.membershipRuleProcessingState | string | | |
action_result.data.\*.objectType | string | | Group |
action_result.data.\*.odata.type | string | | test.DirectoryServices.Group |
action_result.data.\*.onPremisesDomainName | string | `domain` | |
action_result.data.\*.onPremisesLastSyncDateTime | string | | |
action_result.data.\*.onPremisesNetBiosName | string | | |
action_result.data.\*.onPremisesSamAccountName | string | | |
action_result.data.\*.onPremisesSecurityIdentifier | string | | |
action_result.data.\*.onPremisesSyncEnabled | string | | |
action_result.data.\*.preferredDataLocation | string | | |
action_result.data.\*.preferredLanguage | string | | |
action_result.data.\*.proxyAddresses | string | | SMTP:test-h@test.com |
action_result.data.\*.renewedDateTime | string | | 2021-03-25T18:40:53Z |
action_result.data.\*.securityEnabled | boolean | | True False |
action_result.data.\*.securityIdentifier | string | | S-1-12-1-294681889-1319597617-672379543-28952017 |
action_result.data.\*.theme | string | | |
action_result.data.\*.visibility | string | | Private |
action_result.summary.num_groups | numeric | | 7 |
action_result.message | string | | Num groups: 7 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get group'

Get information about a group

Type: **investigate** <br>
Read only: **True**

By default, only a limited set of properties are returned, to return an alternative property set use $select query parameter. For more information on using the select_string and expand_string parameters, refer to https://docs.microsoft.com/en-us/graph/query-parameters.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**object_id** | required | Object ID of group | string | `group object id` |
**select_string** | optional | Select string to get additional group properties. Separate multiple values with commas | string | |
**expand_string** | optional | Expand string to get a resource or collection referenced by a single relationship | string | |
**use_advanced_query** | optional | Use advanced query capabilities | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.expand_string | string | | members |
action_result.parameter.object_id | string | `group object id` | ddb876b3-603a-437b-9814-2d46a2219a1e |
action_result.parameter.select_string | string | | displayName |
action_result.parameter.use_advanced_query | boolean | | True False |
action_result.data.\*.@odata.context | string | | https://graph.test.com/v1.0/$metadata#groups(id,displayName)/$entity |
action_result.data.\*.classification | string | | |
action_result.data.\*.createdDateTime | string | | 2020-08-05T11:59:49Z |
action_result.data.\*.deletedDateTime | string | | |
action_result.data.\*.deletionTimestamp | string | | |
action_result.data.\*.description | string | | This is the office 365 group |
action_result.data.\*.dirSyncEnabled | string | | |
action_result.data.\*.displayName | string | | o365group |
action_result.data.\*.expirationDateTime | string | | |
action_result.data.\*.id | string | `group object id` | ddb876b3-603a-437b-9814-2d46a2219a1e |
action_result.data.\*.isAssignableToRole | string | | |
action_result.data.\*.lastDirSyncTime | string | | |
action_result.data.\*.mail | string | `email` | bc7f9cabe@test.com |
action_result.data.\*.mailEnabled | boolean | | True False |
action_result.data.\*.mailNickname | string | | bc7f9cabe |
action_result.data.\*.membershipRule | string | | |
action_result.data.\*.membershipRuleProcessingState | string | | |
action_result.data.\*.objectType | string | | Group |
action_result.data.\*.odata.metadata | string | | https://graph.windows.net/1t309est-db6c-4tes-t1d2-12bf3456d78d/$metadata#directoryObjects/@Element |
action_result.data.\*.odata.type | string | | test.DirectoryServices.Group |
action_result.data.\*.onPremisesDomainName | string | `domain` | |
action_result.data.\*.onPremisesLastSyncDateTime | string | | |
action_result.data.\*.onPremisesNetBiosName | string | | |
action_result.data.\*.onPremisesSamAccountName | string | | |
action_result.data.\*.onPremisesSecurityIdentifier | string | | |
action_result.data.\*.onPremisesSyncEnabled | string | | |
action_result.data.\*.preferredDataLocation | string | | |
action_result.data.\*.preferredLanguage | string | | |
action_result.data.\*.proxyAddresses | string | | SMTP:bc7f9cabe@test.com |
action_result.data.\*.renewedDateTime | string | | 2020-08-05T11:59:49Z |
action_result.data.\*.securityEnabled | boolean | | True False |
action_result.data.\*.securityIdentifier | string | | S-1-12-1-909260723-1083662375-1952945031-2402852259 |
action_result.data.\*.theme | string | | |
action_result.data.\*.visibility | string | | |
action_result.summary.display_name | string | | o365group |
action_result.summary.status | string | | Successfully retrieved group 104d4576-1544-48b5-bb7e-9f8f871aa824 |
action_result.message | string | | Display name: o365group |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list group members'

List the members in a group

Type: **investigate** <br>
Read only: **True**

By default, only a limited set of properties are returned, to return an alternative property set use $select query parameter. For more information on using the select_string and expand_string parameters, refer to https://docs.microsoft.com/en-us/graph/query-parameters.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**group_object_id** | required | Object ID of group | string | `group object id` |
**select_string** | optional | Select string to get additional properties. Separate multiple values with commas | string | |
**expand_string** | optional | Expand string to get a resource or collection referenced by a single relationship | string | |
**use_advanced_query** | optional | Use advanced query capabilities | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.expand_string | string | | manager |
action_result.parameter.group_object_id | string | `group object id` | ebcd3130-55a1-4cbf-81b2-86408ff21203 |
action_result.parameter.select_string | string | | displayName |
action_result.parameter.use_advanced_query | boolean | | True False |
action_result.data.\*.@odata.type | string | | #test.graph.user |
action_result.data.\*.accountEnabled | boolean | | True |
action_result.data.\*.ageGroup | string | | |
action_result.data.\*.assignedLicenses.\*.skuId | string | | 189a915c-fe4f-4ffa-bde4-85b9628d07a0 |
action_result.data.\*.assignedPlans.\*.assignedDateTime | string | | 2022-11-03T15:12:28Z |
action_result.data.\*.assignedPlans.\*.capabilityStatus | string | | Deleted |
action_result.data.\*.assignedPlans.\*.service | string | | AADPremiumService |
action_result.data.\*.assignedPlans.\*.servicePlanId | string | | eec0eb4f-6444-4f95-aba0-50c24d67f998 |
action_result.data.\*.city | string | | Palo Alto |
action_result.data.\*.companyName | string | | |
action_result.data.\*.consentProvidedForMinor | string | | |
action_result.data.\*.country | string | | US |
action_result.data.\*.createdDateTime | string | | 2016-06-09T18:33:27Z |
action_result.data.\*.creationType | string | | |
action_result.data.\*.deletedDateTime | string | | |
action_result.data.\*.department | string | | |
action_result.data.\*.displayName | string | | Firstname Lastname |
action_result.data.\*.employeeHireDate | string | | |
action_result.data.\*.employeeId | string | | |
action_result.data.\*.employeeOrgData | string | | |
action_result.data.\*.employeeType | string | | |
action_result.data.\*.externalUserState | string | | |
action_result.data.\*.externalUserStateChangeDateTime | string | | |
action_result.data.\*.faxNumber | string | | |
action_result.data.\*.givenName | string | | |
action_result.data.\*.id | string | `user id` | 17be76d0-35ed-4881-ab62-d2eb73c2ebe3 |
action_result.data.\*.identities.\*.issuer | string | | test.com |
action_result.data.\*.identities.\*.issuerAssignedId | string | | test@user.test.com |
action_result.data.\*.identities.\*.signInType | string | | userPrincipalName |
action_result.data.\*.isResourceAccount | string | | |
action_result.data.\*.jobTitle | string | | |
action_result.data.\*.legalAgeGroupClassification | string | | |
action_result.data.\*.mail | string | | |
action_result.data.\*.mailNickname | string | | User |
action_result.data.\*.mobilePhone | string | | |
action_result.data.\*.officeLocation | string | | |
action_result.data.\*.onPremisesDistinguishedName | string | | |
action_result.data.\*.onPremisesDomainName | string | | |
action_result.data.\*.onPremisesExtensionAttributes.extensionAttribute1 | string | | |
action_result.data.\*.onPremisesExtensionAttributes.extensionAttribute10 | string | | |
action_result.data.\*.onPremisesExtensionAttributes.extensionAttribute11 | string | | |
action_result.data.\*.onPremisesExtensionAttributes.extensionAttribute12 | string | | |
action_result.data.\*.onPremisesExtensionAttributes.extensionAttribute13 | string | | |
action_result.data.\*.onPremisesExtensionAttributes.extensionAttribute14 | string | | |
action_result.data.\*.onPremisesExtensionAttributes.extensionAttribute15 | string | | |
action_result.data.\*.onPremisesExtensionAttributes.extensionAttribute2 | string | | |
action_result.data.\*.onPremisesExtensionAttributes.extensionAttribute3 | string | | |
action_result.data.\*.onPremisesExtensionAttributes.extensionAttribute4 | string | | |
action_result.data.\*.onPremisesExtensionAttributes.extensionAttribute5 | string | | |
action_result.data.\*.onPremisesExtensionAttributes.extensionAttribute6 | string | | |
action_result.data.\*.onPremisesExtensionAttributes.extensionAttribute7 | string | | |
action_result.data.\*.onPremisesExtensionAttributes.extensionAttribute8 | string | | |
action_result.data.\*.onPremisesExtensionAttributes.extensionAttribute9 | string | | |
action_result.data.\*.onPremisesImmutableId | string | | |
action_result.data.\*.onPremisesLastSyncDateTime | string | | |
action_result.data.\*.onPremisesSamAccountName | string | | |
action_result.data.\*.onPremisesSecurityIdentifier | string | | |
action_result.data.\*.onPremisesSyncEnabled | string | | |
action_result.data.\*.onPremisesUserPrincipalName | string | | |
action_result.data.\*.passwordPolicies | string | | |
action_result.data.\*.passwordProfile | string | | |
action_result.data.\*.postalCode | string | | 94303 |
action_result.data.\*.preferredDataLocation | string | | |
action_result.data.\*.preferredLanguage | string | | |
action_result.data.\*.provisionedPlans.\*.capabilityStatus | string | | Enabled |
action_result.data.\*.provisionedPlans.\*.provisioningStatus | string | | Success |
action_result.data.\*.provisionedPlans.\*.service | string | | testCommunicationsOnline |
action_result.data.\*.refreshTokensValidFromDateTime | string | | 2022-08-08T13:00:58Z |
action_result.data.\*.showInAddressList | string | | |
action_result.data.\*.signInSessionsValidFromDateTime | string | | 2022-08-08T13:00:58Z |
action_result.data.\*.state | string | | CA |
action_result.data.\*.streetAddress | string | | 2479 E. Bayshore Rd. |
action_result.data.\*.surname | string | | |
action_result.data.\*.usageLocation | string | | US |
action_result.data.\*.userPrincipalName | string | | ews_retest@test.com |
action_result.data.\*.userType | string | | Member |
action_result.summary.num_members | numeric | `user id` | 3 |
action_result.summary.num_users | numeric | | 3 |
action_result.message | string | | Num members: 3 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'validate group'

Returns true if a user is in a group; otherwise, false

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**group_object_id** | required | Object ID of group | string | `group object id` |
**user_id** | required | User ID to validate | string | `user id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.group_object_id | string | `group object id` | ebcd3130-55a1-4cbf-81b2-86408ff21203 |
action_result.parameter.user_id | string | `user id` | user@test.com |
action_result.data.\*.@odata.context | string | | https://graph.test.com/v1.0/$metadata#directoryObjects |
action_result.data.\*.user_in_group | string | | |
action_result.data.\*.value.\*.@odata.type | string | | #test.graph.group |
action_result.data.\*.value.\*.classification | string | | |
action_result.data.\*.value.\*.createdDateTime | string | | 2022-02-25T12:05:22Z |
action_result.data.\*.value.\*.deletedDateTime | string | | |
action_result.data.\*.value.\*.description | string | | Test group for MSGraph |
action_result.data.\*.value.\*.displayName | string | | Test group for MSGraph |
action_result.data.\*.value.\*.expirationDateTime | string | | |
action_result.data.\*.value.\*.id | string | `user id` | 49233413-24c6-4516-a9e1-4d5f87fe34fd |
action_result.data.\*.value.\*.isAssignableToRole | string | | |
action_result.data.\*.value.\*.mail | string | | test@user.test.com |
action_result.data.\*.value.\*.mailEnabled | boolean | | True |
action_result.data.\*.value.\*.mailNickname | string | | TestgroupforMSGraph |
action_result.data.\*.value.\*.membershipRule | string | | |
action_result.data.\*.value.\*.membershipRuleProcessingState | string | | |
action_result.data.\*.value.\*.onPremisesDomainName | string | | |
action_result.data.\*.value.\*.onPremisesLastSyncDateTime | string | | |
action_result.data.\*.value.\*.onPremisesNetBiosName | string | | |
action_result.data.\*.value.\*.onPremisesSamAccountName | string | | |
action_result.data.\*.value.\*.onPremisesSecurityIdentifier | string | | |
action_result.data.\*.value.\*.onPremisesSyncEnabled | string | | |
action_result.data.\*.value.\*.preferredDataLocation | string | | |
action_result.data.\*.value.\*.preferredLanguage | string | | |
action_result.data.\*.value.\*.renewedDateTime | string | | 2022-02-25T12:05:22Z |
action_result.data.\*.value.\*.securityEnabled | boolean | | True |
action_result.data.\*.value.\*.securityIdentifier | string | | S-1-12-1-1227043859-1159079110-1598939561-4248108679 |
action_result.data.\*.value.\*.theme | string | | |
action_result.data.\*.value.\*.visibility | string | | Private |
action_result.summary.message | string | | User is member of group |
action_result.summary.user_in_group | string | | |
action_result.message | string | | User in group: True |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list directory roles'

List the directory roles that are activated in the tenant

Type: **investigate** <br>
Read only: **True**

<p>Pagination is not implemented for this action as this endpoint does not support pagination. Here is the <b><a href='https://docs.microsoft.com/en-us/graph/paging' target='_blank'>Documentation</a></b> for the same.</p>

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.deletedDateTime | string | | |
action_result.data.\*.deletionTimestamp | string | | |
action_result.data.\*.description | string | | Can read basic directory information. For granting access to applications, not intended for users. |
action_result.data.\*.displayName | string | | Directory Readers |
action_result.data.\*.id | string | `directory object id` | 02b238cb-0d15-454b-aae6-0e94993a3207 |
action_result.data.\*.isSystem | boolean | | True False |
action_result.data.\*.objectType | string | | Role |
action_result.data.\*.odata.type | string | | test.DirectoryServices.DirectoryRole |
action_result.data.\*.roleTemplateId | string | `role template id` | 88d8e3e3-8f55-4a1e-953a-9b9898b8876b |
action_result.summary.num_directory_roles | numeric | | 9 |
action_result.message | string | | Num directory roles: 9 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list named locations'

List named locations in Entra Conditional Access

Type: **investigate** <br>
Read only: **True**

For more information on using the filter and select parameters, refer to https://learn.microsoft.com/en-us/graph/filter-query-parameter and https://learn.microsoft.com/en-us/graph/query-parameters#select-parameter.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**location_type** | optional | Type of named locations to return | string | |
**filter** | optional | Optional OData filter, for example contains(displayName,'Blocked') | string | |
**select** | optional | Optional select string to get specific properties. Separate multiple values with commas | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.location_type | string | | all ip country |
action_result.parameter.filter | string | | contains(displayName,'Blocked') |
action_result.parameter.select | string | | id,displayName |
action_result.data.\*.@odata.type | string | | #microsoft.graph.ipNamedLocation #microsoft.graph.countryNamedLocation |
action_result.data.\*.id | string | `directory object id` | 0c0c6d27-93e7-4fd7-88a4-952c6d61a697 |
action_result.data.\*.displayName | string | | Named locations to be blocked |
action_result.data.\*.createdDateTime | string | `datetime` | 2021-03-23T04:59:25.8014022Z |
action_result.data.\*.modifiedDateTime | string | `datetime` | 2021-03-23T08:05:02.1027085Z |
action_result.data.\*.isTrusted | boolean | | True False |
action_result.data.\*.ipRanges.\*.@odata.type | string | | #microsoft.graph.iPv6CidrRange #microsoft.graph.iPv4CidrRange |
action_result.data.\*.ipRanges.\*.cidrAddress | string | `ip` `cidr` | 127.0.0.1/32 2001:8000::/20 |
action_result.data.\*.countriesAndRegions.\* | string | | US CA |
action_result.data.\*.countryLookupMethod | string | | clientIpAddress authenticatorAppGps |
action_result.data.\*.includeUnknownCountriesAndRegions | boolean | | True False |
action_result.summary.num_named_locations | numeric | | 2 |
action_result.message | string | | Successfully listed named locations |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add cidr to named location'

Add a CIDR range to an IP-based named location in Entra Conditional Access

Type: **contain** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**cidr_range** | required | IPv4 or IPv6 CIDR range, for example 1.1.1.0/24 or 2001:db8::/32 | string | `ip` `cidr` |
**location_id** | required | Object ID of the IP-based named location | string | `directory object id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.cidr_range | string | `ip` `cidr` | 1.1.1.0/24 2001:db8::/32 |
action_result.parameter.location_id | string | `directory object id` | 0c0c6d27-93e7-4fd7-88a4-952c6d61a697 |
action_result.summary.status | string | | Successfully added 1.1.1.0/24 CIDR already present |
action_result.message | string | | Successfully added 1.1.1.0/24 CIDR already present in named location |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remove cidr from named location'

Remove a CIDR range from an IP-based named location in Entra Conditional Access

Type: **correct** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**cidr_range** | required | IPv4 or IPv6 CIDR range, for example 1.1.1.0/24 or 2001:db8::/32 | string | `ip` `cidr` |
**location_id** | required | Object ID of the IP-based named location | string | `directory object id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.cidr_range | string | `ip` `cidr` | 1.1.1.0/24 2001:db8::/32 |
action_result.parameter.location_id | string | `directory object id` | 0c0c6d27-93e7-4fd7-88a4-952c6d61a697 |
action_result.summary.status | string | | Successfully removed 1.1.1.0/24 CIDR not present |
action_result.message | string | | Successfully removed 1.1.1.0/24 CIDR not present in named location |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'generate token'

Generate a token

Type: **generic** <br>
Read only: **False**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Token generated |
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
