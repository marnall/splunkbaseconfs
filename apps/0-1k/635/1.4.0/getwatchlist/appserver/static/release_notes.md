# Release notes

## Version 1.4.0

- Enhanced Error handling for more graceful and information error messages

- Added Credential Management for Profiles.

- Graphical Interface for profiles

- Reviewed default profiles for the correct operation of settings

- Various bug fixes

- Validated for Splunk Python 3.13

- Added a `file://` support.

  - **JAILED**: This input is jailed to the `$SPLUNK_HOME/etc/apps/getwatchlist/watchlists` directory.

## Version 1.3.5

- Upgraded `splunk-sdk` to version 2.1.0

## Version 1.3.4

- Upgraded `splunk-sdk` to version 2.0.2

## Version 1.3.3

- Updated url parsing to allow datetime relative calculations in the url.

  - example: `url=https://my.api.com?last_event={{dt:-1d@d:%Y-%m-%d}}`

  - Renders (assuming *today* is 2023-12-18): `url=https://my.api.com?last_event=2023-12-17`

  - Double braces indicate replacement.

  - `dt` is only "operation" currently supported.

  - `{{dt:<relative_time_modifier>:<time_format>}}`

  - Defaults

    - `time_format`: `%Y-%m-%dT%H:%M:%SZ`

  - Special Relative Time modifiers (for readability/ease of use)

    - `now`: `-1s`

    - `yesterday`: `-1d@d`

    - `tomorrow`: `+1d@d`

    - `today`: `@d`

- Multi-level `dataKey` extraction

  - assumes `json` type

  - "key.second_key" for data that is represented as a list of objects

  - example: `{"vulns": [{"cve": {"id": "CVE-001"}}, {"cve": {"id: "CVE-002"}}]}`

  - `autoExtract=1 dataKey="vulns.cve"`

- Flatten Json for `json` type

  - `flattenJson=1` converts and flattens the json object.

## Version 1.3.2

- Updated the `gz` extraction path to allow for better handling of compressed streams.

- Added a `Settings` page, to enable debug logging as needed.

## Version 1.3.1

- Updated extraction of parameters with `=` in the string.

- Added `pipe` delimiter keyword.

## Version 1.3.0

- Added new file type support: `archive` and `gz`.

## Version 1.2.0

- Removed `getwatchlist_orig.py` for Cloud compat

- CSV, TXT, JSON, XLSX formats are supported directly using profiles.

- Enhanced auto-parsing of CSV, JSON, XLSX formats.

## Version 1.1.7

- Fixed issue with App Setup Configuration being forced

## Version 1.1.6

- Fix issue where URLs would not be called without a profile name.

- Fix issue with pass-through field names and values.

## Version 1.1.5

- Fix issue when URL is specified with parameters in search bar

## Version 1.1.3

- Fix invalid stanza on startup

## Version 1.1.2

- Remove unnecessary files

## Version 1.1.1

- Updated to Python 3 for Splunk 8 and above.

## Version 1.0.0

Added:

- Better error handling and output in Splunk

- The ability to add values from other columns in the fetched list.

Changed:

- The configuration file has been made more Splunk-like. An example file is in /default/ and custom profiles or configs can be added to a getwatchlist.conf in the /local/ directory.

- The URL for Malware Domains has been updated as from 8/1/11 the domains.txt file will only be available from mirrors

Security:

- Note that a potential security vulnerability was found in version 0.7. Users are urged to update.
