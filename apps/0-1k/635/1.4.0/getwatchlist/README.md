# PAVO GetWatchList Documentation

Getwatchlist is a custom search command for Splunk which will return a CSV formatted list from a URL

## About PAVO GetWatchList

|                           |                                                |
|---------------------------|------------------------------------------------|
| Author                    | Aplura, LLC                                    |
| App Version               | 1.4.0                                          |
| App Build                 | 122                                            |
| Vendor Products           |                                                |
| Has index-time operations | false                                          |
| Creates an index          | false                                          |
| Implements summarization  | Currently, the app does not generate summaries |

# Scripts and binaries

This App provides the following scripts:

- getwatchlist.py

  - Fetches different watchlists for processing and output.

- version.py

  - Holds the version information for logging purposes.

- Utilities.py

  - Provides Splunk Utilities for scripts.

- Diag.py

  - Provides customized Diag access.

- app_properties.py

  - Provides generated properties to use in python scripts.

## About PAVO GetWatchList

**NOTE**  
If you were using a previous version, please make sure to read about the changes in the configuration file locations, and backup any custom configurations you may have prior to upgrading!

## Requirements

This custom command has been tested on Splunk 8 and higher. If you want to pull down lists off of the internet, your search head will need to have internet access.

## Usage

### Credential Update

With 1.4.0, credential management is more secure, and allows for multiple authentication types. Navigate to the configuration page of the App, and add a new credential using the button found there. Use the list below and enter the credentials as documented.

- `Basic`

  - This is in plaintext, and will be base64 encoded on POST.

  - This can be used for both FTP and HTTP types.

  - **Example**: `<username>:<password>`

- `Header`

  - This is in plaintext, and will be added to the `Authorization` header, **as-is**.

  - **Example**: `Bearer <token>`

- `Query`

  - This is an URL param, and needs to have the field name along with the token, and added to the query params **as-is**

  - **Example**: `apikey=<token>`

### Original Instructions

Options for `getwatchlist` can be supplied via the search options passed in the search box, a configuration file, or a combination of the two. The first argument passed to `getwatchlist` is the name of a profile in the configuration file. If a profile exists, it will be loaded first, and then options passed via the search command will be used to overwrite the stored settings. If the profile does not exist, default settings are used.

Options are passed in a `key=value` fashion. Arguments that are passed and are not known arguments will be appended as custom fields. So if I add a field of:

    spam=tasty

Each line of the CSV which is returned will have a column named "spam", with a value of "tasty".

If there are additional columns in the list which you would like to be output as well, you can tell the command which column, and what the name if it should be. To do this, use an integer (the column number you would like to include), and give it a name for the column. To include column 3 of a list, and name the column "enddate", you would add `3=enddate` to your command parameters or configuration.

Here are options which can be passed, or used in the configuration file:

- categoryCol

  - The column number of any category field in the fetched file.

- comment (default: \#)

  - The character which is used to denote a commented out line .

- dateCol

  - The column number of any date field in the file which you would like to use for reference.

- delimiter (default: \t)

  - The delimiter field of the fetched file.

  - Special values: `space`, `tab`, `comma`, `pipe`. These will be converted to the correctly escaped value.

- ignoreFirstLine (default: False)

  - Some watchlists contain a header which is not commented out. If this is set to "True" this line will be ignored.

- relevantFieldCol (default: 1)

  - The column number (starting at 1) which contains the key value you would like to use .

- relevantFieldName (default: ip_address)

  - What you would like the field to be named in the CSV output (not the name in the fetched CSV) .

- referenceCol

  - The column number of any reference field in the fetched CSV.

- url

  - The URL of the file to be retrieved (HTTP, HTTPS or FTP).

- fieldNames

  - A semicolon list of field names to prepend to the data. The semicolons will be replaced with the delimiter during processing.

- fileName

  - Used with tgz, tar, and zip files. Provide to target a file in an archive. If not provided, the first file found will be used.

- sheetIndex

  - Used with xlsx files.

- authUser

  - Username to use for authentication (HTTP Basic or FTP)

- authPassword

  - Password to use for authentication (HTTP Basic or FTP)

- proxyHost

  - Hostname or IP of the HTTP proxy to be used for HTTP and HTTPS connections

- proxyPort

  - Port for the HTTP proxy

## Configuration File

Configurations are kept in files named `getwatchlist.conf`. An example of this file is in the `/default/` directory of the application. It contains example profiles which are ready to use. Any custom configuration items in the /local/ version of the .conf file will override or add on to any settings in the /default/ file, much like normal Splunk configuration. Additionally, settings entered via the search command will override both the /default/ and /local/ settings.

The "globals" section of the configuration file can be used for proxy configuration. By using the globals section, the command will use those settings by default, but can be overridden using command or profile settings.

## Event Generator

PAVO GetWatchList does not include an event generator.

## Acceleration

- Summary Indexing: No

- Data Model Acceleration: No

- Report Acceleration: No

## Third Party

Version 1.4.0 of PAVO GetWatchList incorporates the following Third-party software or third-party services.

- pylightxl

- splunklib

- tld

# Examples

Splunk Searches to output a watchlist

## Spamhaus DROP list from config file

    |getwatchlist spamhaus

## Spamhaus DROP list via URL

    |getwatchlist spamhaus url=https://www.spamhaus.org/drop/drop.lasso delimiter=; relevantFieldName=’sourceRange’ relevantFieldCol=1 referenceCol=2 ignoreFirstLine=True comment=;

## Generic URL

    |getwatchlist default url=https://www.google.com/robots.txt spam=tasty relevantFieldName=action

    |getwatchlist txt url=https://www.team-cymru.org/Services/Bogons/fullbogons-ipv4.txt relevantFieldName=src_ip

## XLSX Document

    | getwatchlist xlsx url=https://www.tn.gov/content/dam/tn/health/documents/cedep/novel-coronavirus/datasets/Public-Dataset-Data-Dictionary.xlsx sheetIndex=1 autoExtract=1 ignoreFirstLine=1

    | getwatchlist xlsx url=https://www.cdc.gov/vaccines/programs/iis/downloads/Preview-Posting-of-COVID-19-Vaccine-Codes-and-Crosswalk-20220831.xlsx sheetIndex=1 ignoreFirstLine=1

## CSV Document

    | getwatchlist csv url=https://corgis-edu.github.io/corgis/datasets/csv/billionaires/billionaires.csv

## XLS Document

XLS Documents ARE NOT Supported due to out-of-date protocols. Convert to XLSX, CSV, or JSON.

## JSON Document

This example uses an encoded url to make sure parameters are sent to the endpoint correctly. Encoded URLs are automatically unencoded. The JSON profile with `autoExtract` set as false, will return the response in a `_raw` field, that can be used for further processing with commands.

    | getwatchlist json url=https%3A%2F%2Fqrng.anu.edu.au%2FAPI%2FjsonI.php%3Flength%3D100%26type%3Duint8 autoExtract=0 | extract reload=true

This example uses an encoded url, but also includes a `dataKey` to target a list of data to use for the rows in the response.

    | getwatchlist json url=https%3A%2F%2Fservices1.arcgis.com%2FFjPcSmEFuDYlIdKC%2Farcgis%2Frest%2Fservices%2FEelgrass_2006_Points_Beds%2FFeatureServer%2F1%3Ff%3Dpjson dataKey=fields

This example uses Splunk to encode the URL:

    | makeresults | eval url="https://services1.arcgis.com/FjPcSmEFuDYlIdKC/arcgis/rest/services/Eelgrass_2006_Points_Beds/FeatureServer/1?f=pjson" | `urlencode("url")` | map [ getwatchlist json url=$url$ dataKey=fields]

The `expandObjects` command flag can be used when the source data is an Object with Keys, and those keys are objects that have the fields located within in them.

Sample Data (served locally on 5555):

    { "0": {"field1": "value1", "field2": "value2"}, "something": {"field1": "value2", "field2": "value3"}}

Example:

    | getwatchlist json url=http://localhost:5555/ expandObjects=1

Example output:

|        |        |
|--------|--------|
| field1 | field2 |
| value1 | value2 |
| value2 | value3 |

The `dictKeys` command flag can be used to pull a column that is an object, and make it a row with the headers added to the table.

Example:

    | getwatchlist json url=https%3A%2F%2Fservices1.arcgis.com%2FFjPcSmEFuDYlIdKC%2Farcgis%2Frest%2Fservices%2FEelgrass_2006_Points_Beds%2FFeatureServer%2F1%3Ff%3Dpjson dictKeys="extent,geometryProperties,advancedQueryAnalyticCapabilities" { fields spatialReference xmin ymax supportsLinearRegression shape*

## gz files

This example pulls a local file from a server, that is g-zipped. The delimiter of the data is a tab, and contains three different fields. This format supports ONLY "csv" style data, not JSON or other file types.

    |getwatchlist gz url=https://epss.cyentia.com/epss_scores-2023-11-30.csv.gz delimiter=comma autoExtract=1 ignoreLines=2 fieldNames=cve;epss;percentile

## tar, tgz files

This example pulls a local file from a server, that is a tarball, either gzipped or not. The delimiter of the data is a tab, and contains three different fields. This format supports ONLY "csv" style data, not JSON or other file types.

    |getwatchlist archive url=http://localhost:5555/test.tar.gz delimiter=\t fieldNames=src_ip;subnet;ip_count autoExtract=1

## zip files

This example pulls a local file from a server, that is zipped. The delimiter of the data is a tab, and contains three different fields. This format supports ONLY "csv" style data, not JSON or other file types.

    |getwatchlist archive url=http://localhost:5555/test.zip delimiter=\t fieldNames=src_ip;subnet;ip_count autoExtract=1

## Configuration File Examples

Examples can be found in the `$APP_HOME/default/getwatchlist.conf`

## Splunk Searches using saved lookups

Using a subsearch from the CSV: `index="webproxy" [}inputlookup phishtank.csv | fields uri]`

Using a configured lookup: `index="webproxy" | lookup phishtank uri | search isbad=true`

# Inputs

- ptag_upgrader

  - ptag_upgrader://d0a05452-cb76-4a4e-b374-f3b881900b26

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

# Installation

To install, copy the downloaded tarball to the `$SPLUNK_HOME/etc/apps` directory and expand. This will create a directory named getwatchlist which contains the sample configuration file, the `command.conf` to enable the command, as well as permissions to enable usage of the command globally in Splunk. Splunk will need to be restarted for the new application and configuration to take.

# Support and Resources

## Questions and answers

Access questions and answers specific to PAVO GetWatchList at <https://answers.splunk.com/>. Be sure to tag your question with the App.

## Support

- Support Email: <customersupport@aplura.com>

- Support Offered: Splunk Answers

For further inspection in the logs, set the `DEBUG` flag on the loggers in `default/apl_logging.conf`

Diag can be generated via `$SPLUNK_HOME/bin/splunk diag --collect=app:getwatchlist`
