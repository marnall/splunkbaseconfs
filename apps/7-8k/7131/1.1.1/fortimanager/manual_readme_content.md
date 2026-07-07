## ADOM Locking/Unlocking

Every write action in this connector performs a lock on the Administrative Domain (ADOM) specified in the action parameters before updating or creating a resource on the FortiManager asset. If the locking attempt fails, then the entire action will fail because a lock on the ADOM could not be obtained. This is either because another user or session is actively holding the lock on the ADOM or the ADOM specified in action parameters may be invalid. FortiManager requires ADOM locking before every write operation to ensure no two administrators can make changes simultaneously.

If the locking attempt is successful, then the API call to FortiManager will execute. Afterwards, as part of the action run, the ADOM lock will be released regardless of whether the action succeeds, fails, or exits on an exception.

## Asset Configuration

The two authentication schemes allowed by the connector are either Basic Auth (username and password) or API key. The steps to generate an API key through the FortiManager UI are as follows:

1. Log into the FortiManager UI using an administrator account.
1. Select an ADOM other than 'Global', such as 'root'.
1. Click on 'System Settings' in the left pane.
1. Click on 'Administrators' and click the 'Create New' button.
1. Select 'REST API Admin' in the dropdown of the button.
1. Enter the User Name and any other pertinent information. A trusted host entry is required. Select the Admin Profile and the type of JSON API Access. For SOAR, this would most likely be 'Read-Write' access.
1. Click the 'OK' Button.
1. After the User has been created, click on the user now listed under 'REST API Administrator' to see the user details. Click on 'Regenerate' in the 'Regenerate API Key' form value, then click the 'Generate' button. Copy the generated key and use that value as the API key in the asset configuration. For this authentication scheme, only the base URL and API key are required.
