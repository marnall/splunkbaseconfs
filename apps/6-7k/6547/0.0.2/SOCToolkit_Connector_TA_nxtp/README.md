# Splunk Add-On for _SOC-Toolkit_

by [NEXTPART Security Intelligence GmbH](https://nextpart.io)

This extension for [Splunk®](https://www.splunk.com/) allows you to directly link Splunk to
[SOC Toolkit](https://www.nextpart.io/#soc-toolkit) and enables the forwarding of events and running
investigations to include in the incident response process or to take them over from Enterprise
Security for further enrichment, graph-based analysis, etc.

## Author information

- Author: _Nextpart Security Intelligence GmbH_
- Version: `0.0.2` (dynamic)
- Creation: July, 2022

## Configuration

On your Splunk instance navigate to `/app/SOCToolkit_Connector_TA_nxtp` to perform the
configuration.

**Add-on Settings**:

- **IAM**: The domain name of the identity and access management service.
- **Realm**: The user management container at the IAM service resp. the name of your tenant
- **Domain**: The domain address of the SOC-Toolkit instance to interact with.
- **OAuth Client ID**: The alpha-numeric ID string that is used in OIDC requests to identify the
  client.
- **OAuth Client Secret**: The secret key to access the API endpoints.

## Audit Log

- Source: `api.guardia.at` (or the hostname of the instance)
- Sourcetype: `soctoolkit:audit`

Create a new input in which you configure the start time for the fetch of the audit logs and
activate it, if this is not already done automatically.

## Alert Action

There are different approaches how to create an investigation in soc-toolkit based on one or more
events in Splunk:

- **Create an investigation from search:**

  ```
  | makeresults
  | eval field="michael@nextpart.io"
  | sendalert send_to_soc_toolkit
      param.case_name="case from splunk"
      param.playbook="indicator_playbook"
      param.integrations="HAVEIBEENPWNED"
  ```

- **Create an investigation from enterprise security a noteable event:**

  ```
  | makeresults
  | eval field="michael@nextpart.io"
  | sendalert noteable
  ```

  - Navigate to the "Enterprise Security" app and go to the "Incident Review" tab.
  - Select the "Adaptive Response Action" option for the desired Event and select "_Send to
    SOC-Toolkit_".
  - Enter a **case name** under which the new case should be created in the SOC Toolkit and select
    the analysis **playbook** and the **integrations** used for it. You can get the list of
    integrations directly from the application. These are written in capital letters and all the
    integrations you have configured for your tenant are available.

## Copyright & License

Copyright © 2022 Nextpart Security Intelligence GmbH
