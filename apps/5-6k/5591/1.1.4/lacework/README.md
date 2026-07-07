# Lacework
Enable API calls to Lacework through custom search command and view vulnerability data through built-in dashboards.

## Before you start
The Alerts page only works for those who have a Lacework connector set up (see [here](https://support.lacework.com/hc/en-us/articles/360007889274-Splunk)). However, you can still use all other existing dashboards in the App without this page if you do not need it.

If you wish to use the alert page: Currently, the app only accepts index=lacework for the alerts data input.
Additional feature to change the index is coming up soon.

## How to use
- Upon installation, navigate to the app and finish setup by completing the setup form. This will help us fetch your Lacework API token and enable all functionalities of the app.
- The custom search command "lacework" sends a GET request to a Lacework endpoint.
    - Example: `| lacework target="/api/v1/..."`

## <a id="custom_endpoints"></a>Supported custom endpoints
The following endpoint allows you to get or update the current domain without going through the setup page. This is useful in case the setup page does not work and direct modification on configuration files is not viable.

__Note: Make sure you provide username and password in Basic Authorization.__

`GET https://localhost:PORT/services/apiDomain/APIDomainHandler` has an optional parameter of `domain`
- `GET https://localhost:PORT/services/apiDomain/APIDomainHandler` gets the current domain
- `GET https://localhost:PORT/services/apiDomain/APIDomainHandler?domain=exampleDomain` to update the current domain to `exampleDomain.lacework.net`

## Version support
Splunk 8.2 version

## Troubleshooting
#### **Q: My dashboard is showing empty results/ no accounts found/ no CVE IDs found**

A:
- Re-do your setup from the setupage ("Manage Apps" -> "Lacework" -> "Set up") to ensure that the credentials are valid.
- Refresh the page to reload your dashboard. 
- If this still does not work, please restart the server OR the `setupReload.sh` script from "Settings" -> "Data Inputs" -> "Scripts" by toggling the Enable/Disable status buttons. This script will reload your setup configuration.
- _Note: Dashboards may also take a while to load, so please give it up to a minute to load the data in._

#### **Q: How do I change my setup credentials outside of setup page?**

A: You can either modify the file(s) directly as an admin, or use Splunk's endpoint and our EAI endpoint.
- For keyId and secret, please use Splunk's storage passwords endpoints to modify the passwords.conf file.
- For API domain, please use the `https://localhost:PORT/services/apiDomain/APIDomainHandler` endpoint. See [Supported custom endpoitns](#custom_endpoints).

#### **Q: How do I change the index that stores the logs from the scripts?**

A: "Settings" -> "Data Inputs" -> "Scripts" -> Find `setupReload.sh` -> Click on the name -> Change fields from the "Source type" section.
