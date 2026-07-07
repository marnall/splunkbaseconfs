![app-version](https://img.shields.io/badge/irflow--splunk--app-v2.1.0-brightgreen.svg)
![splunk6-version](https://img.shields.io/badge/splunk-v6.6%2B-blue.svg)
![splunk7-version](https://img.shields.io/badge/splunk-v7.0%2B-blue.svg)
![splunk-cim](https://img.shields.io/badge/splunk--cim-v4.7%2B-blue.svg)


# Splunk IR-Flow Integration #

The IR-Flow app for Splunk is supported by email during business hours for IR-Flow users.
- This is a developer supported app.
- Email support during US Eastern Time business hours support@syncurity.net

The IR-Flow integration with Splunk uses the _sendalert_ function in Splunk.  In order to use the app, one must assure that appropriate permissions are deployed to the alert in the permissions page for the app.  See _Settings->Apps->Splunk_IR-Flow->Permissions_ for details.

When a search is run, all results will be inserted into _separate_ IR-Flow Alerts.  The IR-Flow search must expect all Splunk fields and must be named the same as the Splunk search name.

Configuration instructions are in the IR-Flow Splunk Action Setup Guide.pdf file in the root directory of this app, as well as on splunk base.splu

This app uses code from the requests and splunklib projects. These projects are licensed under the Apache License,
Version 2.0. A copy of this license is included in the root directory of this app in a file called COPYRIGHTS

Requests version: v2.14.2
Splunklib version: v1.6.2
Dateutil version: v:2.7.3

Requests on GitHub: https://github.com/requests/requests
SplunkLib on GitHub: https://github.com/splunk/splunk-sdk-python
Dateutil on Github: https://github.com/dateutil/dateutil


# Adaptive Response

Adaptive Response for ES is optional, but in order to use it, you must configure a `irflow_actions` index. This is where ES will look for the response actions. You must also import this app to ES. See setup guide for more info.

# Auto Field Translation

The IR-Flow Splunk App allows integration with the Syncurity IR-Flow system. Both Splunk and Syncurity use a Common language within their products. To account for these disparities, Syncurity has provided an auto-translation portion of the alert action. Pass in the Splunk CIM fields, and they will be translated to the Syncurity fields that are required. This also provides you the ability to map your own fields.

## Extending the Field translation

The required fields for the lookup are: id, field_name, and field_splunk. id should be a unique identifier for the field. This will help in debugging if needed.
The lookup needs to be placed in the lookups folder in this App, and must start with irflow_.