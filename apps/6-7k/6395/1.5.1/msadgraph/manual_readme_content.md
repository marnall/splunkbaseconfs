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
