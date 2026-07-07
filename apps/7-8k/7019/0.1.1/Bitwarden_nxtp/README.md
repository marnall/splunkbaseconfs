# Splunk Add-On for _Bitwarden - Password Manager_

This extension for [Splunk®](https://www.splunk.com/) allows you to retrieve data from the
[public API](https://bitwarden.com/help/public-api/) of the
[Bitwarden password manager](https://bitwarden.com/) and integrate this data into your log
management. With the setting of the inputs the data of the different
[endpoints](https://bitwarden.com/help/api/) are fetched and indexed. You can then use the lookup
tables and logs to create various evaluations, audits, reports or alerts.

## Author information

- Author: Nextpart Security Intelligence GmbH
- Version: `0.1.1` (dynamic)
- Creation: July, 2022

## Using this Application

- Source: `bitwarden`
- Sourcetype:
  - `bitwarden:audit`
  - `bitwarden:users`
  - `bitwarden:groups`
  - `bitwarden:collections`

## Setup

1. After you have installed and activated the app, create an index (e.g. "bitwarden").

2. If you name the index differently, make sure to also change the makro accordingly.

3. Then you can configure and activate the inputs for the different endpoints.

4. In the report section you will find two searches that provide a lookup table for better data
   quality in the audit log. These searches should be configured to run on a scheduled basis, but
   you can trigger them once initially to get started.

## Copyright & License

Copyright © 2022 Nextpart Security Intelligence GmbH
