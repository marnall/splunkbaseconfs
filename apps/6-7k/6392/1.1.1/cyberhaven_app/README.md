# Overview

This is cyberhaven splunk application, after running you should specify host and credentials
Then you'll get list of incidents in your splunk instance and will be able to search and analyze data
Get auth token for staging:

https://deployment-staging.cyberhaven.io/api-tokens

or

https://{{HOST}}/api-tokens

# How to run application locally ?

1. Install splunk locally https://docs.splunk.com/Documentation/SplunkCloud/latest/SearchTutorial/InstallSplunk
2. move cyperhaven_app/cyperhaven_app folder to `Splunk/etc/apps `folder
3. Run splunk and configure application

# Setup Page Entry Point

Splunk will automatically try to redirect the user to the setup page if the `app.conf`'s `[install]` stanza has its `is_configured` property set to false.

# Program Flow

This program starts in the `app.conf`, where the `[install]` stanza's `is_configured` property is set to `false`. This causes Splunk to redirect to it's setup page that is specified so that an admin/user can configure it for use.

In the `app.conf`'s, `[ui]` stanza there is a `setup_page` property that points to which resource should be used for the setup page. In this case it's pointing to `default/data/ui/views/setup_page_dashboard.xml`.

The dashboard view specifies its CSS and JavaScript resources and points to `appserver/static/javascript/setup_page.js`.

And finally the `setup_page.js` imports a React app from `appserver/static/javascript/views/app.js`.

# Resources

- Splunk apps store
  https://splunkbase.splunk.com/apps/#/product/splunk/

- Splunk Techniques Used
  - Splunk Dashboards
    - [API Documentation](http://docs.splunk.com/Documentation/SplunkCloud/latest/Viz/PanelreferenceforSimplifiedXML) (docs.splunk.com)
  - Splunk Setup Page
    - [app.conf Specification](http://docs.splunk.com/Documentation/Splunk/6.6.3/admin/Appconf#.5Bui.5D)
  - Splunk Web Framework
    - [Main Website](https://dev.splunk.com/enterprise/docs/developapps/webframework) (dev.splunk.com)
- Technology Used
  - CSS
  - HTML
  - JavaScript
    - React
      - [Main Website](https://reactjs.org/)
      - [On GitHub](https://github.com/facebook/react)
    - Splunk JavaScript Software Development Kit
      - [Main Website](https://dev.splunk.com/enterprise/docs/javascript/sdk-javascript) (dev.splunk.com)
      - [On GitHub](https://github.com/splunk/splunk-sdk-javascript)

# Ho to deploy

1. Do all steps from "How to run application locally" above

2. Create app archive
   `cd /Applications/Splunk/etc/apps/cyberhaven_app && find . | grep -E "(/__pycache__$|\.pyc$|\.pyo$)" | xargs rm -rf && cd /Applications/Splunk/bin && ./splunk package app cyberhaven_app`
   Package will be at Splunk/share/splunk/app_packages

3. Upload new version to splunk store

   3.1. Get credentials on our github page

   3.2 Go to https://splunkbase.splunk.com and login

   3.3 Go to https://splunkbase.splunk.com/app/6392/edit/#/hosting and click “New Version”
