## Authentication

### Microsoft Azure Application creation

This app requires creating a Microsoft Azure Application. To do so, navigate to [https://portal.azure.com](https://portal.azure.com) in a browser and log in with a Microsoft account, then select **Azure Active Directory**.

1. Go to **App Registrations** and click on **+ New registration**.
1. Give the app an appropriate name.
1. Select a supported account type (configure the application to be multitenant).
1. Click on the **Register**.

- Under **Certificates & secrets**, add **New client secret**. Note this key somewhere secure, as it cannot be retrieved after closing the window.
- Under **Redirect URIs** we will be updating the entry of https://phantom.local to reflect the actual redirect URI. We will get this from the SOAR asset we create below in the section titled "Configure the MS Graph for Active Directory SOAR app Asset"

### Delegated Permissions configuration

Use this procedure to provide non-admin permissions to the app. To do so, navigate to [https://portal.azure.com](https://portal.azure.com) in a browser and log in with a Microsoft account, then navigate to the previously created app configuration.

1. Under **API Permissions**, click on **Add a permission**.
1. Go to **Microsoft Graph Permissions**, the following **Delegated Permissions** need to be added:
   - DeviceManagementManagedDevices.Read.All
   - DeviceManagementManagedDevices.ReadWrite.All
   - offline_access
1. Click on the **Add permissions**.
1. After making these changes, click on **Grant admin consent**.

### Application Permissions configuration

Use this procedure to provide admin permissions to the app. To do so, navigate to [https://portal.azure.com](https://portal.azure.com) in a browser and log in with a Microsoft account, then navigate to the previously created app configuration.

1. Under **API Permissions**, click on **Add a permission**.
1. Go to **Microsoft Graph Permissions**, the following **Application Permissions** need to be added:
   - DeviceManagementManagedDevices.Read.All
   - DeviceManagementManagedDevices.ReadWrite.All
1. Click on the **Add permissions**.
1. After making these changes, click on **Grant admin consent**.

#### Note: **reset password** action is not supported with Application permissions

## Configure the MS Graph for Active Directory SOAR app Asset

When creating an asset for the **MS Graph for Active Directory** app, place the **Application ID** of the app created during the previous step in the **Client ID** field and place the password generated during the app creation process in the **Client Secret** field. Then, after filling out the **Tenant** field, click **SAVE**.

After saving, a new field will appear in the **Asset Settings** tab. Take the URL found in the **POST incoming for MS Graph to this location** field and place it in the **Redirect URIs** field of the Azure Application configuration page. To this URL, add **/result**. After doing so the URL should look something like:

https://\<phantom_host>/rest/handler/msgraphforactivedirectory_f2a239df-acb2-47d6-861c-726a435cfe76/\<asset_name>/result

Once again, click on Save.

## Enable Application Permissions

If you have received admin consent to use application permissions, make sure to check the **Admin Access Required** and **Admin Consent Already Provided** checkboxes on the asset.

## User Permissions

To complete the authorization process, this app needs permission to view assets, which is not granted by default. First, under **asset settings**, check which user is listed under **Select a user on behalf of which automated actions can be executed**. By default, the user will be **automation**, but this user can be changed by clicking **EDIT** at the bottom of the window. To give this user permission to view assets, follow these steps:

- In the main drop-down menu, select **Administration**, then select the **User Management**, and under that tab, select **Roles**. Finally, click **+ ROLE**.
- In the **Add Role** wizard, give the role a name (e.g **Asset Viewer**), and provide a description. Subsequently, under **Available Users**, add the user assigned to the asset viewed earlier. Then click the **Permissions** tab.
- On the permission tab, under **Available Privileges**, give the role the **View Assets** privilege. Then click **SAVE**.

## Method to Run Test Connectivity (for delegated permissions)

After setting up the asset and user, click the **TEST CONNECTIVITY** button. A window should pop up and display a URL. Navigate to this URL in a separate browser tab. This new tab will redirect to a Microsoft login page. Log in to a Microsoft account with administrator privileges to the Microsoft AD environment. After logging in, review the requested permissions listed, then click **Accept**. Finally, close that tab. The test connectivity window should show a success.

The app should now be ready to use.

## State File Permissions

Please check the permissions for the state file as mentioned below.

#### State Filepath

- For Root Install Instance: /opt/phantom/local_data/app_states/f2a239df-acb2-47d6-861c-726a435cfe76/{asset_id}\_state.json
- For Non-Root Install Instance: /\<PHANTOM_HOME_DIRECTORY>/local_data/app_states/f2a239df-acb2-47d6-861c-726a435cfe76/{asset_id}\_state.json

#### State File Permissions

- File Rights: rw-rw-r-- (664) (The SOAR user should have read and write access for the state file)
- File Owner: appropriate SOAR user

## Port Details

The app uses HTTP/ HTTPS protocol for communicating with the Microsoft Graph server. Below are the
default ports used by the Splunk SOAR Connector.

| Service Name | Transport Protocol | Port |
|--------------|--------------------|------|
| https | tcp | 443 |
