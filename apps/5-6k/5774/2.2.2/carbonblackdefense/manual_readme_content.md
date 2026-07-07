There are four different sets of credentials for this app - a SIEM key, a Custom API Key, an
Organization Key, and an API key. The action **get notifications** uses the SIEM key. This means the
**siem_connector_id** and the **siem_key** asset configuration parameters are required to run the
**get notifications** action. The actions **list processes** , **get event** , **list events** ,
**list devices** , **update device** , and **get alert** requires Custom API Key along with
Organization Key meaning the **custom_api_connecter_id** , **custom_api_key** , and **org_key** are
required to run these actions. All other actions use the API key, meaning that the
**api_connector_id** and **api_key** asset configuration parameters are required for those
actions.

**NOTE:** Test connectivity will only check the API credentials, it will NOT check the SIEM Key
credentials, Organization Key, and Custom Key credentials.

**To Generate Keys**\
To get started with the Carbon black Defense API to integrate with Phantom, log into the Carbon
black Defense web portal and go to Settings then API Access. From here you can retrieve ORG KEY, API
ID which is used as API Connector ID in Phantom app asset, and API Secret Key which is used as API
Key in Phantom app asset. To Generate SIEM Connector ID and SIEM Key select SIEM in the **Access
Level type** . To Generate API Connector ID and API Key select Live Response in the **Access Level
type** . To Generate Custom API Connector ID and Custom API Key select Custom in the **Access Level
type** and accordingly select **Custom Access Level** which has appropriate permissions.

**Custom Access Levels required the following permissions**

- For 'org.search.events' allow permission to 'CREATE' and 'READ'.
- For 'device' allow permissions for 'READ'.
- For 'device.policy' allow permissions for 'UPDATE'.
- For 'device.bg-scan' allow permissions for 'EXECUTE'.
- For 'device.bypass' allow permissions for 'EXECUTE'.
- For 'device.quarantine' allow permissions for 'EXECUTE'.
- For 'org.kits' allow permissions for 'EXECUTE'.
- For 'device.uninstall' allow permissions for 'EXECUTE'.
- For 'device.deregistered' allow permissions for 'DELETE'.
- For 'org.alerts' allow permissions for 'READ'.
- For 'org.alerts.dismiss' allow permissions for 'EXECUTE'.
- For 'org.alerts.notes' allow permissions for 'CREATE', 'READ', and 'DELETE'.
- For 'org.search.events', allow permission for 'CREATE' and 'READ'.

## Port Information

The app uses HTTP/HTTPS protocol for communicating with the Carbon Black Defense Server. Below are
the default ports used by Splunk SOAR.

| Service Name | Transport Protocol | Port |
|--------------|--------------------|------|
| http | tcp | 80 |
| https | tcp | 443 |
