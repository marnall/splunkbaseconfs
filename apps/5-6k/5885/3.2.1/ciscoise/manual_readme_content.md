## Asset Configuration For Authentication

- ERS uses HTTPS port 9060 which is closed by default. Clients trying to access this port without
  enabling ERS first will face a timeout from the server. Therefore, the first requirement is to
  enable ERS from the Cisco ISE admin UI. Go to Administration > Settings > ERS Settings and
  enable the Enable ERS for Read/Write radio button
- Go to Administration > System > Admin Users. Now add an account by clicking Add > Create an
  admin user. Then enter name and password and select ERS Admin in Admin Group and then press
  save.
- Go to Administration > System > Admin Users. Now add an account by clicking Add > Create an
  admin user. Then enter name and password and select MnT Admin in Admin Group and then press
  save.
- Configurations expect user with MnT Admin Access group in username/password fields and user in
  ERS Admin group in ERS username/password fields or user with both MnT Admin or ERS Admin access
  group in username/password field.
- Also, you can add both MnT Admin and ERS Admin Access groups to a user and use that credentials
  in username/password. The App will use username/password if ERS username/password is not
  provided

## Note

1. The actions "quarantine system" and "unquarantine system" are removed in the version 3.0.0.
   Users are advised to use "apply policy" and "clear policy" actions to achieve the same objective
1. ERS credentials are required for actions
   - list endpoints
   - get device info
   - update device info
   - get resources
   - delete resource
   - create resource
   - update resource
   - apply policy
   - create policy
1. If resource is **Guest User** in resource related actions, it is required to use **Sponsor Account** credentials to access the GuestAPI, For creating sponsor account refer this document: [Set Up Admin and Sponsor Account for ERS](https://www.cisco.com/c/en/us/support/docs/security/identity-services-engine/215476-configure-ise-guest-accounts-with-rest-a.html)
1. Once you have internal user created from step #3, Add username and password in **ers_username** and **ers_password** in asset configuration respectively.
1. An ISE node can assume any or all of the following personas: Administration, Policy Service, and
   Monitoring. For detailed info: [Types of
   nodes](https://www.cisco.com/en/US/docs/security/ise/1.0/user_guide/ise10_dis_deploy.html#wp1123452)
   - All actions can run on Administration node.
   - Actions create resource, update resource, delete resource, list resource, get resources,
     list sessions, update device info, get device info, and list endpoints can run on Monitoring
     node
   - Actions quarantine device, unquarantine device, apply policy, clear policy, and terminate
     session can run on Policy Service node
1. For create resource action, user needs to provide valid json with required fields of that
   specified resource (For more details head over to [API
   Reference](https://developer.cisco.com/docs/identity-services-engine/v1/#!endpoint) ). Examples
   as below
   - Endpoint

     ```
     {
         "ERSEndPoint": {
             "name": "name",
             "description": "MyEndpoint",
             "mac": "11:22:33:44:55:66"
         }
     }
     ```

   - Endpoint identity groups

     ```
     {
         "EndPointGroup": {
             "name": "Cisco-Meraki-Device",
             "description": "Identity Group for Profile: Cisco-Meraki-Device",
             "systemDefined": "true"
         }
     }
     ```

   - Guest users

     ```
     {
         "GuestUser": {
             "name": "guestUser",
             "guestInfo": {
               "userName": "DS3ewdsa34wWE",
               "password": "asdlkj324ew", # pragma: allowlist secret
               "enabled": true
             },
             "guestAccessInfo": {
                 "validDays": 90
             }
         }
     }
     ```

   - User identity groups

     ```
     {
         "IdentityGroup": {
             "name": "GuestType_Weekly (default)",
             "parent": "NAC Group:NAC:IdentityGroups:User Identity Groups"
         }
     }
     ```

   - Internal users

     ```
     {
         "InternalUser": {
             "name": "name",
             "enabled": true,
             "password": "*******",
             "changePassword": true,
             "passwordIDStore": "Internal Users" # pragma: allowlist secret
         }
     }
     ```

   - Network devices

     ```
     {
           "NetworkDevice": {
                 "name": "ISE_EST_Local_Host",
                 "authenticationSettings": {
                     "enableKeyWrap": true,
                     "enableMultiSecret": true,
                     "keyEncryptionKey": 1234567890123456,
                     "keyInputFormat": "ASCII"
                 },
                 "coaPort": 0,
                 "snmpsettings": {
                     "pollingInterval": 3600,
                     "linkTrapQuery": true,
                     "macTrapQuery": true,
                     "originatingPolicyServicesNode": "Auto"
                 },
                 "trustsecsettings": {
                     "deviceAuthenticationSettings": {},
                     "sgaNotificationAndUpdates": {},
                     "deviceConfigurationDeployment": {},
                     "pushIdSupport": false
                 },
                 "tacacsSettings": {
                     "sharedSecret": "aaa" # pragma: allowlist secret
                 },
                 "profileName": "Cisco",
                 "NetworkDeviceIPList": [
                     {
                         "ipaddress": "127.0.0.1",
                         "mask": 32
                     }
                 ]
           }
     }
     ```

   - Network device groups

     ```
     {
         "NetworkDeviceGroup": {
             "name": "Device Type#All Device Types"
         }
     }
     ```

   - Security groups

     ```
     {
         "Sgt": {
             "name": "Employees",
             "value": 4
         }
     }
     ```

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Cisco ISE server. Below are the default
ports used by Splunk SOAR.

| Service Name | Transport Protocol | Port |
|--------------|--------------------|------|
| http | tcp | 80 |
| https | tcp | 443 |
