# Splunk Add-On for _Keycloak_

by [NEXTPART Security Intelligence GmbH](https://nextpart.io)

This extension for [Splunk®](https://www.splunk.com/) allows you to retrieve data from the
[public API](https://www.keycloak.org/docs-api/19.0.3/rest-api/index.html) of
[Keycloak](https://www.keycloak.org/) and integrate this data into your log management. With the
setting of the inputs the data of the different [endpoints] are fetched and indexed. You can then
use the lookup tables and logs to create various evaluations, audits, reports or alerts.

## Author information

- Author: _Nextpart Security Intelligence GmbH_
- Version: `0.1.1` (dynamic)
- Creation: August, 2023

## Using this Application

- Sourcetype:
  - `keycloak:audit`
  - `keycloak:events`
  - `keycloak:users`
  - `keycloak:realms`

## Configuration

On your Splunk instance navigate to `/app/KeycloakAPI_nxtp` to perform the configuration.

## Copyright & License

Copyright © Nextpart Security Intelligence GmbH
