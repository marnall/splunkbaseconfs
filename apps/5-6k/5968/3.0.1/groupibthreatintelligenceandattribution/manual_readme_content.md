## Asset configuration

1). Find **Group IB Threat Intelligence** app, click **CONFIGURE NEW ASSET** button, in **Asset
Settings** tab enter your credentials and configure necessary collections.

- **Group-IB API URL** is https://tap.group-ib.com/api/v2/
- **Username** is the login for the Group-IB TI portal.
- **Verify server certificate** - Whether to allow connections without verifying SSL certificates
  validity.
- **API key** can be manually generated in the portal:\
  The old version of the portal: log in to the TI -> click on your name in the right upper corner
  -> choose the **Profile** option -> click on the **Go to my setting** button under your name ->
  under the **Change password** button you will see **API KEY generator** . **Do not forget to
  save the API key** .\
  The new version of the portal: log in to the TI -> click on your name in the right upper corner
  -> choose the **Profile** option -> click on **Security and Access** tab -> click on **Personal
  token** tab -> click on **Generate new token** button -> enter your password, copy token and
  click **Save** button.
- Every collection has a poll starting date and enable checkbox.

2). If you are using a proxy to connect to the Group IB TI server, you can specify the appropriate
settings. You need to expand the **Advanced** section on the bottom, find the **Environment**
section and click **+ Variable** . **NAME** must be HTTPS_PROXY, **VALUE** is your proxy server.

3). In the **Ingest settings** tab choose the polling interval you need.

## SDK and SDK Licensing details for the app

#### cyberintegrations

This app uses the cyberintegrations module, which is licensed under the MIT License (MIT), Copyright (c) 2023-24
Group-IB.
