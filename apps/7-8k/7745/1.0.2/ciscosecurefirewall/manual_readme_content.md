This connector supports both cloud and on-prem delivered FMC. Below are the steps for connecting to both

## Connecting to a cloud delivered FMC

1. On Cisco Security Cloud Control navigate to User Management
1. Create a new Api Only User with an Admin role
1. Copy the Api key and enter it in the "Api key for cloud delivered FMC" input box in the SOAR Asset Settings page
1. Specfiy Cloud for the type of FMC you are connecting to
1. Specify your region in the "Region your Cisco Security Cloud Control is deployed in" input box and click Save

## Connecting to an on-prem delivered FMC

1. On the SOAR asset setting page select On-prem for the type of FMC you are connecting to
1. Specify the device ip/hostname of your on-prem FMC along with the username and password used to login to FMC

**Note** that you can optionally specify a default firepower domain that will be queried. You can override this domain when running an action. In addition, cloud versions of FMC only support the default domain. To achieve multi tenancy you must use separate tenants.
