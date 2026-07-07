## Authentication

You will first need to create an application on the Azure AD Admin Portal. Follow the steps outlined
below to do this:

- Navigate to <https://portal.azure.com> in a browser and log in with a Microsoft account

- Select **Azure Active Directory** from the left side menu

- From the left panel, select **App Registrations**

- At the top of the middle section, select **New registration**

- On the next page, give your application a name and select **Register**

- Once the app is created, the below steps need to be taken on the next page:

  - Under **Certificates & secrets** select **New client secret** . Note down this key somewhere
    secure, as it cannot be retrieved after closing the window.

  - Under **Authentication** , select **Add a platform** . In the **Add a platform** window,
    select **Web** . The **Redirect URLs** should be filled right here. We will get **Redirect
    URLs** from the Phantom asset we create below in the section titled **Phantom Asset for
    SharePoint** . This step is required only if you are a non-admin user.

  - Under **API Permissions** Click on **Add a permission** .

  - Under the **Microsoft API** section, select **Microsoft Graph** .

  - There are two ways to gives the Application and Delegated permissions to the app.

    1. Permissive mode

       - Sites.Read.All
       - Files.Read.All
       - Files.ReadWrite.All
       - Sites.ReadWrite.All

    1. Restrictive mode

       - Sites.Selected (only Application permission)

       The user will have to configure permissions for each of the sites that they are working
       with. You can find more information
       [here](https://devblogs.microsoft.com/microsoft365dev/controlling-app-access-on-specific-sharepoint-site-collections/)
       . Also, while using this mode 'list sites' action will return the empty list.\
       **Note:** You need **Sites.FullControl.All** Application permission while using the site
       permission endpoint.

  - After making these changes, click **Add permissions** at the bottom of the screen.

- If you are an admin user, then click **Grant admin consent for Phantom** and provide admin
  consent. And configure asset configuration parameter **Admin Consent Already Provided** with
  value **True** .

- If you are a non-admin user, then follow the steps listed below to grant admin consent:

  - Configure an asset configuration parameter **Admin Consent Already Provided** with value
    **False** .
  - You must have configured the **Redirect URLs** mentioned in the above steps.To configure
    **Redirect URLs** , checkout the section titled **Phantom Asset for SharePoint** below.
  - Run the **Test Connectivity** .
  - You will be asked to open a link in a new tab. Open the link in the same browser so that you
    are logged into Splunk Phantom for the redirect. If you wish to use a different browser, log
    in to the Splunk Phantom first, and then open the provided link.
  - Proceed to log in to the Microsoft site with the admin user.
  - You will be prompted to agree to the permissions requested by the App.
  - If all goes well the browser should instruct you to close the tab.
  - Now go back and check the message on the Test Connectivity dialog box, it should say **Test
    Connectivity Passed** .

## Phantom Asset for SharePoint

When creating an asset for the **MS Graph for SharePoint** app, place the **Application ID** and
**Client secret** of the app created during the previous step in the **Client/Application ID** and
**Client Secret** fields respectively. You can also find **Tenant ID** on the application overview
page. After filling in all the required values, click **SAVE** .

After saving, a new field will appear in the **Asset Settings** tab. Take the URL found in the
**POST incoming for MS Graph for SharePoint to this location** field and place it in the **Redirect
URLs** field mentioned in a previous step. After doing so the URL should look something like:

https://\<phantom_host>/rest/handler/msgraphforsharepoint_7963f3ef-b527-40e5-a704-392c56f0a88d/\<asset_name>

Additionally, updating the Base URL in the Company Settings is also required. Navigate to
**Administration > Company Settings > Info** to configure the **Base URL For Splunk SOAR** . Then,
select **Save Changes** .

For the asset configuration parameter **SharePoint Site ID** , it should be in the format
**{Hostname},{SPSite-id},{SPWeb-id}** . You can get the **SharePoint Site ID** by running the
**'list site'** action. For more information check out the [Microsoft
documentation](https://docs.microsoft.com/en-us/graph/api/resources/sharepoint?view=graph-rest-1.0#note-for-existing-sharepoint-developers)
.

## Restrictions and Limitations

Some special characters aren't allowed as a SharePoint **list name** and **file/folder name** . If
you have created the list/files with these special characters, SharePoint API will not allow us to
retrieve the list information. For more information about limitations check out the [Microsoft
documentation](https://support.microsoft.com/en-us/kb/905231) .\
As a workaround for lists, we can use the list_id instead of the list_name. Run the 'list lists'
action to get the list_id.

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Microsoft servers. Below are the
default ports used by Splunk SOAR.

|         Service Name | Transport Protocol | Port |
|----------------------|--------------------|------|
|         http | tcp | 80 |
|         https | tcp | 443 |
