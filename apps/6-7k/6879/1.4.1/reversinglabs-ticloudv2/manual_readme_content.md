### Configuration Variables

The below configuration variables are required for this Connector to operate. These variables are specified when configuring a TitaniumCloud asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**url** | required | string | TitaniumCloud URL
**username** | required | string | TitaniumCloud username
**password** | required | password | TitaniumCloud password

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration\
[advanced search](#action-advanced-search) - TCA-0320 - Search for hashes using multi-part search criteria\
[analyze url](#action-analyze-url) - TCA-0404 - Analyze a given URL\
[av scanners](#action-av-scanners) - TCA-0103 - Retrieve AV Scanner data from TitaniumCloud\
[customer daily usage](#action-customer-daily-usage) - TCA-9999 - Check daily usage of ReversingLabs API\
[customer dayrange usage](#action-customer-dayrange-usage) - TCA-9999 - Check ReversingLabs API usage for specified time range (in days)\
[customer month range usage](#action-customer-month-range-usage) - TCA-9999 - Check ReversingLabs API usage for specified time range (in months)\
[customer monthly usage](#action-customer-monthly-usage) - TCA-9999 - Check Monthly usage of ReversingLabs API\
[customer quota limits](#action-customer-quota-limits) - TCA-9999 - Returns current quota limits for APIs accessible to the authenticated user or users belonging to the authenticated user's company.\
[customer yara api usage](#action-customer-yara-api-usage) - TCA-9999 - Check Yara usage on ReversingLabs API\
[dynamic analysis results](#action-dynamic-analysis-results) - TCA-0106 - Retrieve a file dynamic analysis results\
[dynamic url analysis results](#action-dynamic-url-analysis-results) - TCA-0106 - Retrieve an url dynamic analysis results\
[file analysis](#action-file-analysis) - TCA-0104 - Retrieve File Analysis by hash data from TitaniumCloud\
[file reputation](#action-file-reputation) - TCA-0101 - Queries for file reputation info\
[file reputation user override](#action-file-reputation-user-override) - TCA-0102 - File Reputation User Override\
[functional similarity](#action-functional-similarity) - TCA-0301 - Retrieve a list of functionally similar hashes to the provided one\
[get domain downloaded files](#action-get-domain-downloaded-files) - TCA-0405 - Retrieve a list of files downloaded from the submitted domain\
[get domain report](#action-get-domain-report) - TCA-0405 - API returns threat intelligence data for the submitted domain
[get downloaded files](#action-get-downloaded-files) - TCA-0403 - Get files downloaded from url\
[get file](#action-get-file) - TCA-0201 - Download a sample from TitaniumCloud\
[get ip downloaded files](#action-get-ip-downloaded-files) - TCA-0406 - Retrieve a list of files downloaded from the submitted IP address
[get ip report](#action-get-ip-report) - TCA-0406 - API returns threat intelligence data for the submitted ip address
[get latest url analysis feed](#action-get-latest-url-analysis-feed) - TCA - 0403 - Get latest url analysis feed\
[get list user overrides](#action-get-list-user-overrides) - TCA-0408 - Get user URL classification overrides\
[get list user overrides aggregated](#action-get-list-user-overrides-aggregated) - TCA-0408 - Get user URL classification overrides aggregated\
[get network reputation](#action-get-network-reputation) - TCA-0407 - Get reputation of a requested URL, domain or IP address\
[get related domains](#action-get-related-domains) - TCA-0405 - API provides a list of domains that have the same top parent domain as the requested domain
[get resolutions from domain](#action-get-resolutions-from-domains) - TCA-0405 - API provides a list of domain-to-IP mappings for the requested domain
[get resolutions from ip](#action-get-resolutions-from-ip) - TCA-0406 - API provides a list of IP-to-domain mappings for the requested IP address
[get url analysis feed from date](#action-get-url-analysis-feed-from-date) - TCA-0403 - Get url analysis feed from date\
[get urls from domain](#action-get-urls-from-domain) - TCA-0405 - API provides a list of URLs associated with the requested domain
[get urls from ip](#action-get-urls-from-ip) - TCA-0406 - API provides a list of URLs associated with the requested IP address
[get yara matches](#action-get-yara-matches) - TCA-0303 - Get a recordset of YARA ruleset matches in the specified time range\
[get yara retro matches](#action-get-yara-retro-matches) - TCA-0319 - Get a recordset of YARA ruleset matches in the specified time range\
[imphash similarity](#action-imphash-similarity) - TCA-0302 - Get a a list of all available SHA1 hashes for files sharing the same import hash (imphash)\
[list active file reputation user overrides](#action-list-active-file-reputation-user-overrides) - TCA-0102 - List Active File Reputation User Overrides
[network reputation user override](#action-network-reputation-user-override) - TCA-0408 - Override user network location reputation\
[reanalyze file](#action-reanalyze-file) - TCA-0205 - Reanalyze sample\
[submit for dynamic analysis](#action-submit-for-dynamic-analysis) - TCA-0207 - Submit an existing sample for dynamic analysis\
[submit url for dynamic analysis](#action-submit-url-for-dynamic-analysis) - TCA-0207 - Submit an existing url sample for dynamic analysis\
[upload file](#action-upload-file) - TCA-0202 - Upload file to TitaniumCloud\
[uri index](#action-uri-index) - TCA-0401 - Retrieve a list of all available file hashes associated with a given URI\
[uri statistics](#action-uri-statistics) - TCA-0402 - Retrieve the number of MALICIOUS, SUSPICIOUS and KNOWN files associated with a specific URI\
[url reputation](#action-url-reputation) - TCA-0403 - Queries URL Threat Intelligence\
[yara create ruleset](#action-yara-create-ruleset) - TCA-0303 - Create a new YARA ruleset\
[yara delete ruleset](#action-yara-delete-ruleset) - TCA-0303 - Delete YARA ruleset\
[yara get ruleset info](#action-yara-get-ruleset-info) - TCA-0303 - Get YARA ruleset info\
[yara get ruleset text](#action-yara-get-ruleset-text) - TCA-0303 - Get YARA ruleset text\
[yara retro enable hunt](#action-yara-retro-enable-hunt) - TCA-0319 - Enable YARA retro hunt\
[yara retro start hunt](#action-yara-retro-start-hunt) - TCA-0319 - Start YARA retro hunt for the specified ruleset\
[yara retro check status](#action-yara-retro-check-status) - TCA-0319 - Check the retro hunt status for the specified ruleset\
[yara retro cancel hunt](#action-yara-retro-cancel-hunt) - TCA-0319 - Cancel the retro hunt for the specified ruleset

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test**\
Read only: **True**

Validate the asset configuration for connectivity using supplied configuration.

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'advanced search'

TCA-0320 - Search for hashes using multi-part search criteria

Type: **investigate**\
Read only: **False**

TCA-0320 - Search for hashes using multi-part search criteria. Supported criteria include more than 60 keywords, 35 antivirus vendors, 137 sample types and subtypes, and 283 tags that enable creating 510 unique search expressions with support for Boolean operators and case-insensitive wildcard matching. A number of search keywords support relational operators '\<=' and '>='.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query** | required | Advanced Search query | string |
**limit** | optional | Maximum number of results | numeric |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.limit | numeric | |\
action_result.parameter.query | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'analyze url'

TCA-0404 - Analyze a given URL

Type: **investigate**\
Read only: **False**

TCA-0404 - This service allows users to submit a URL for analysis.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL to analyze | string | `url`

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.url | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'av scanners'

TCA-0103 - Retrieve AV Scanner data from TitaniumCloud

Type: **investigate**\
Read only: **False**

TCA-0103 - Provides AV vendor cross-reference data for a desired sample from multiple AV scanners.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | File hash | string | `sha1` `sha256` `md5`

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.hash | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'customer daily usage'

TCA-9999 - Check daily usage of ReversingLabs API

Type: **generic**\
Read only: **False**

TCA-9999 - API allows ReversingLabs customers to track the usage of TitaniumCloud services provisioned to all accounts in a company

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**date** | required | Specifies the date for which customer usage information should be returned | string | |
**company** | optional | When this parameter is checked, the API will return usage for all accounts within the company | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.*.date | Date | | YYYY-MM-DD
action_result.data.*.usage_report.*.product | string | |
action_result.data.*.usage_report.*.number_of_queries | string | |
action_result.data.*.usage_report.\*.used_bytes | string | |
action_result.status | string | | success or failed
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'customer dayrange usage'

TCA-9999 - Check ReversingLabs API usage for specified time range (in days)

Type: **generic**\
Read only: **False**

TCA-9999 - API allows ReversingLabs customers to track the usage of TitaniumCloud services provisioned to all accounts in a company

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**from_date** | required | Specifies the from date for which customer usage information should be returned. Users can submit one value per request in the YYYY-MM-DD format. | string | |
**to_date** | required | Specifies the to date for which customer usage information should be returned. Users can submit one value per request in the YYYY-MM-DD format. | string | |
**company** | optional | When this parameter is checked, the API will return usage for all accounts within the company | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'customer month range usage'

TCA-9999 - Check ReversingLabs API usage for specified time range (in months)

Type: **generic**\
Read only: **False**

TCA-9999 - API allows ReversingLabs customers to track the usage of TitaniumCloud services provisioned to all accounts in a company

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**from_month** | required | Specifies the from date for which customer usage information should be returned. Users can submit one value per request in the YYYY-MM format. | string | |
**to_month** | required | Specifies the to date for which customer usage information should be returned. Users can submit one value per request in the YYYY-MM format. | string | |
**company** | optional | When this parameter is checked, the API will return usage for all accounts within the company | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'customer monthly usage'

TCA-9999 - Check Monthly usage of ReversingLabs API

Type: **generic**\
Read only: **False**

TCA-9999 - API allows ReversingLabs customers to track the usage of TitaniumCloud services provisioned to all accounts in a company

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**month** | required | Specifies the month for which customer usage information should be returned. Users can submit one value per request in the YYYY-MM format. | string | |
**company** | optional | When this parameter is checked, the API will return usage for all accounts within the company | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.*.month | string | | YYYY-MM
action_result.data.*.usage_report.*.product | string |\
action_result.data.*.usage_report.*.number_of_queries | string |
action_result.data.*.usage_report.\*.used_bytes | string |
action_result.status | string | | success or failed
action_result.message | string | |
summary.total_objects | numeric | |
summary.total_objects_successful | numeric | |

## action: 'customer quota limits'

TCA-9999 - Returns current quota limits for APIs accessible to the authenticated user or users belonging to the authenticated user's company.

Type: **generic**\
Read only: **False**

TCA-9999 - API allows ReversingLabs customers to track quota limits of TitaniumCloud services provisioned to all accounts in a company

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**company** | optional | When this parameter is checked, the API will return usage for all accounts within the company | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.*.limits.*.limit | numeric | |
action_result.data.*limits.*.limit_type | string | |
action_result.data.*limits.*.limit_exceeded | boolean | |
action_result.data.*limits.*.products | string | |
action_result.data.*limits.*.users | string | |
action_result.status | string | | success or failed
action_result.message | string | |
summary.total_objects | numeric | |
summary.total_objects_successful | numeric | |

## action: 'customer yara api usage'

TCA-9999 - Check Yara usage on ReversingLabs API.

Type: **generic**\
Read only: **False**

TCA-9999 - This query returns information about the number of active YARA rulesets for the TitaniumCloud account that sent the request.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**format** | optional | Specify the response format. Supported values are xml and json. The default is JSON. | string | json |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.*.product | string | |
action_result.data.*.number_of_active_rulesets | string | |
action_result.status | string | | success or failed
action_result.message | string | |\
summary.total_objects | numeric | |
summary.total_objects_successful | numeric | |

## action: 'dynamic analysis results'

TCA-0106 - Retrieve dynamic analysis results

Type: **generic**\
Read only: **False**

TCA-0106 - This service allows users to retrieve dynamic analysis results for a file that was submitted for dynamic analysis.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**sha1** | required | Selected sample's SHA-1 hash | string | `sha1`
**analysis_id** | optional | Return only the results of this analysis | string |
**latest** | optional | Return only the latest analysis results | boolean |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.analysis_id | string | |\
action_result.parameter.latest | boolean | |\
action_result.parameter.sha1 | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'dynamic url analysis results'

TCA-0106 - Retrieve dynamic analysis results for url

Type: **investigate**\
Read only: **true**

TCA-0106 - This service allows users to retrieve dynamic analysis results for an url that was submitted for dynamic analysis.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | Provide one of the following: sha1, base64 or url | string | `sha1` `url` |
**analysis_id** | optional | Return only the results of this analysis | string |
**latest** | optional | Return only the latest analysis results | boolean |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.analysis_id | string | |\
action_result.parameter.data.0.requested_sha1_url | string | |

## action: 'file analysis'

TCA-0104 - Retrieve File Analysis by hash data from TitaniumCloud

Type: **investigate**\
Read only: **False**

TCA-0104 - Provides file analysis data on hashes. Metadata can include relevant portions of static analysis, AV scan information, file sources and any related IP/domain information.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | File hash | string | `sha1` `sha256` `md5` `vault id`

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.hash | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'file reputation'

TCA-0101 - Queries for file reputation info

Type: **investigate**\
Read only: **True**

TCA-0101 - Queries for file reputation info.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | File hash to query | string | `hash` `sha256` `sha1` `md5`

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.hash | string | `hash` `sha256` `sha1` `md5` |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'file reputation user override'

TCA-0102 - File Reputation User Override

Type: **generic**\
Read only: **False**

TCA-0102 - The File Reputation User Override service enables File sample classification overrides.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**override_samples** | required | List of samples to override structured in JSON format. Visit documentation for guidance. | string |
**remove_overrides** | optional | List of samples whose classification override needs to be removed structured in JSON format. Visit documentation for guidance | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.override_samples | string | |
action_result.parameter.remove_overrides | string | |
action_result.status | string | | success or failed
action_result.parameter.hash | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'functional similarity'

TCA-0301 - Retrieve a list of functionally similar hashes to the provided one

Type: **investigate**\
Read only: **False**

TCA-0301 - Provides a list of SHA1 hashes of files that are functionally similar to the provided file (SHA1 hash) at the selected precision level.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | File hash | string | `sha1`
**limit** | optional | Maximum number of results | numeric |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.hash | string | |\
action_result.parameter.limit | numeric | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get domain downloaded files'

TCA-0405 - Retrieve a list of files downloaded from the submitted domain

Type: **generic**\
Read only: **False**

TCA-0405 - The response will contain metadata for files downloaded from the submitted domain. Empty fields are not included in the response.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | The domain for which to retrieve the downloaded files | string | domain
**extended** | optional | Chose whether you want extended result data set | boolean |\
**limit** | optional | The number of files to return in the response. Default is 1000 | numeric |\
**classification** | optional | Return only samples that match the requested classification for given domain | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get domain report'

TCA-0405 - API returns threat intelligence data for the submitted domain

Type: **generic**\
Read only: **False**

TCA-0405 - The report contains domain reputation from various reputation sources, classification statistics for files downloaded from the domain, the most common threats found on the domain DNS information about the domain, and parent domain information.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | The domain for which to retrieve the report | string | `domain`

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get downloaded files'

TCA - 0403 - Get files downloaded from url

Type: **generic**\
Read only: **False**

Accepts a URL string and returns a list of downloaded files aggregated through multiple pages of results.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL string | string |
**extended** | optional | Return extended report | boolean |
**classification** | optional | Return only files of this classification | string |
**last_analysis** | optional | Return only files from the last analysis | boolean |
**analysis_id** | optional | Return only files from this analysis | string |
**results_per_page** | optional | Number of results to be returned in one page, maximum value is 1000 | numeric |
**max_results** | optional | Maximum results to be returned in the list | numeric |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.url | string | |\
action_result.parameter.extended | boolean | |\
action_result.parameter.classification | string | |\
action_result.parameter.last_analysis | boolean | |\
action_result.parameter.analysis_id | string | |\
action_result.parameter.results_per_page | numeric | |\
action_result.parameter.max_results | numeric | |\
action_result.status | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get file'

TCA-0201 - Download a sample from TitaniumCloud

Type: **investigate**\
Read only: **True**

TCA-0201 - Download a sample from TitaniumCloud and add it to the vault.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash of file/sample to download | string | `md5` `sha1` `sha256`

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.hash | string | `md5` `sha1` `sha256` |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get ip downloaded files'

TCA-0406 - Retrieve a list of files downloaded from the submitted IP address

Type: **generic**\
Read only: **True**

TCA-0406 - The response will contain metadata for files downloaded from the submitted IP address. Empty fields are not included in the response.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_address** | required | The IP address for which to retrieve the downloaded files | string | `ip`
**extended** | optional | Chose whether you want extended result data set | boolean |\
**page** | optional | String representing a page of results | string |\
**limit** | optional | The number of files to return in the response. Default is 1000 | numeric |\
**classification** | optional | Return only samples that match the requested classification for given domain | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get ip report'

TCA-0406 - API returns threat intelligence data for the submitted ip address

Type: **generic**\
Read only: **True**

TCA-0406 - The report contains IP reputation from various reputation sources, classification statistics for files downloaded from the IP, and the top threats hosted on the submitted IP.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_address** | required | The IP address for which to retrieve the report | string | `ip`

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get latest url analysis feed'

TCA - 0403 - Get latest url analysis feed

Type: **generic**\
Read only: **False**

Returns the latest URL analyses reports aggregated as list.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**results_per_page** | optional | Number of results to be returned in one page, maximum value is 1000 | numeric |
**max_results** | optional | Maximum results to be returned in the list | numeric |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.results_per_page | numeric | |\
action_result.parameter.max_results | numeric | |\
action_result.status | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get list user overrides'

TCA-0408 - Get user URL classification overrides

Type: **generic**\
Read only: **False**

TCA-0408 - Get user URL classification overrides

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**next_page_sha1** | optional | Optional parameter used for pagination | string | `sha1`

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.*.user_override.network_locations.*.network_location | string | `url` `domain` `ip` |\
action_result.data.*.user_override.network_locations.*.type | string | `url` `domain` `ip` |\
action_result.status | string | | success or failed
action_result.message | string | |
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get list user overrides aggregated'

TCA-0408 - Get user URL classification overrides aggregated

Type: **generic**\
Read only: **False**

This API automatically handles paging and returns a list of results instead of a Response object.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**max_results** | optional | | numeric |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.*.*.network_location | string | `url` `domain` `ip` |\
action_result.data.*.*.type | string | `url` `domain` `ip` |\
action_result.status | string | | success or failed
action_result.message | string | |
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get network reputation'

TCA-0407 - Get reputation of a requested URL, domain or IP address

Type: **investigate**\
Read only: **False**

Service provides information regarding the reputation of a requested URL, domain or IP address.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**network_locations** | required | domain, url or ip | string | `domain` `url` `ip`

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get related domains'

TCA - 0405 - API provides a list of domains that have the same top parent domain as the requested domain

Type: **investigate**\
Read only: **False**

TCA - 0405 - API provides a list of domains that have the same top parent domain as the requested domain. If the requested domain is a top parent domain, the API will return all subdomains.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | The domain for which to retrieve the downloaded files | string | `domain`
**page** | optional | String representing a page of results | string |
**limit** | optional | The number of files to return in the response. Default is 1000 | numeric |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.*.requested_domain | string | `domain` |\
action_result.data.*.related_domains.\*.domain | string | `domain` |\
action_result.status | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get resolutions from domain'

TCA - 0405 - API provides a list of domain-to-IP mappings for the requested domain

Type: **investigate**\
Read only: **False**

TCA - 0405 - API provides a list of domain-to-IP mappings for the requested domain.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | The domain for which to retrieve the domain to IP mappings | string | `domain`
**page** | optional | String representing a page of results | string |
**limit** | optional | The number of files to return in the response. Default is 1000 | numeric |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.*.requested_domain | string | `domain` |\
action_result.data.*.resolutions.*.record_type | string | |\
action_result.data.*.resolutions.*.answer | string | |\
action_result.data.*.resolutions.*.last_resolution_time | string | |\
action_result.data.*.resolutions.\*.provider | string | |\
action_result.status | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get resolutions from ip'

TCA - 0406 - API provides a list of IP-to-domain mappings for the requested IP address

Type: **investigate**\
Read only: **False**

TCA - 0406 - API provides a list of IP-to-domain mappings for the requested IP address

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_address** | required | The IP address for which to retrieve resolutions | string | `ip`
**page** | optional | String representing a page of results | string |
**limit** | optional | The number of files to return in the response. Default is 1000 | numeric |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.*.requested_ip | string | `ip` |\
action_result.data.*.resolutions.*.host_name | string | `domain` |\
action_result.data.*.resolutions.*.last_resolution_time | string | |\
action_result.data.*.resolutions.\*.provider | string | |\
action_result.status | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get url analysis feed from date'

TCA - 0403 - Get url analysis feed from date

Type: **generic**\
Read only: **False**

Accepts time format and a start time and returns URL analyses reports from that defined time onward aggregated as a list.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**time_format** | required | Possible values: 'utc' or 'timestamp' | string |
**start_time** | required | Time from which to retrieve results onwards | string |
**results_per_page** | optional | Number of results to be returned in one page, maximum value is 1000 | numeric |
**max_results** | optional | Maximum results to be returned in the list | numeric |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.time_format | string | |\
action_result.parameter.start_time | string | |\
action_result.parameter.results_per_page | numeric | |\
action_result.parameter.max_results | numeric | |\
action_result.status | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get urls from domain'

TCA - 0405 - API provides a list of URLs associated with the requested domain.

Type: **investigate**\
Read only: **False**

TCA - 0405 - API provides a list of URLs associated with the requested domain.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | The domain for which to retrieve the resolved IP addresses | string | `domain`
**page** | optional | String representing a page of results | string |
**limit** | optional | The number of files to return in the response. Default is 1000 | numeric |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.*.requested_domain | string | `domain` |\
action_result.data.*.urls.\*.url | string | `url` |\
action_result.status | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get urls from ip'

TCA - 0406 - API provides a list of URLs associated with the requested IP address.

Type: **investigate**\
Read only: **False**

TCA - 0406 - API provides a list of URLs associated with the requested IP address.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_address** | required | The IP for which to retrieve the domain resolutions | string | `ip`
**page** | optional | String representing a page of results | string |
**limit** | optional | The number of files to return in the response. Default is 1000 | numeric |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.*.requested_ip | string | `ip` |\
action_result.data.*.urls.\*.url | string | `url` |\
action_result.status | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get yara matches'

TCA-0303 - Get a recordset of YARA ruleset matches in the specified time range

Type: **generic**\
Read only: **False**

TCA-0303 - Get a recordset of YARA ruleset matches in the specified time range.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**time_format** | required | 'utc' or 'timestamp' | string |
**time_value** | required | 'YYYY-MM-DDThh:mm:ss' or Unix timestamp string | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.time_format | string | |\
action_result.parameter.time_value | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get yara retro matches'

TCA-0319 - Get a recordset of YARA ruleset matches in the specified time range

Type: **generic**\
Read only: **False**

TCA-0319 - Get a recordset of YARA ruleset matches in the specified time range.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**time_format** | required | 'utc' or 'timestamp' | string |
**time_value** | required | 'YYYY-MM-DDThh:mm:ss' or Unix timestamp string | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.data.*.rl.feed.name | string | |\
action_result.data.*.rl.feed.time_range.from | string | |\
action_result.data.*.rl.feed.time_range.to | string | |\
action_result.data.*.rl.feed.last_timestamp | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'imphash similarity'

TCA-0302 - Get a a list of all available SHA1 hashes for files sharing the same import hash (imphash)

Type: **investigate**\
Read only: **True**

TCA-0302 - Imphash Index provides a list of all available SHA1 hashes for files sharing the same import hash (imphash). An imphash is a hash calculated from a string which contains the libraries imported by a Windows Portable Executable (PE) file.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**imphash** | required | Imphash | string | `hash`
**limit** | optional | Maximum number of results | numeric |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.imphash | string | |\
action_result.parameter.limit | numeric | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'list active file reputation user overrides'

TCA-0102 - List Active File Reputation User Overrides

Type: **generic**\
Read only: **False**

TCA-0102 - The File Reputation User Override service enables sample classification overrides. Any sample can be overridden to malicious, suspicious, or known.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash_type** | required | Required parameter that defines the type of hash | string | `sha1` `sha256` `md5`
**start_hash** | optional | When this parameter is present, the API will return up to 1000 hashes with a classification override starting from the start_hash value | string | `sha1` `sha256` `md5`

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.user_override.hash_values | string | `sha1` `sha256` `md5` |
action_result.status | string | | success or failed
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'network reputation user override'

TCA-0408 - Override user network location reputation

Type: **generic**\
Read only: **False**

The Network Reputation User OVerride service enables URL classification overrides

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**override_list** | required | List of network locations which classification needs to be overriden | string |
**remove_overrides_list** | optional | List of network locations which classification override needs to be removed | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.override_list | string | | { "network_location": "http://example.com", "type": "url", "classification": "malicious", "categories": ["phishing"] }
action_result.parameter.remove_overrides_list | string | | { "network_location": "http://example.com", "type": "url" }
action_result.message | string | |
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'reanalyze file'

TCA-0205 - Reanalyze sample

Type: **investigate**\
Read only: **False**

TCA-0205 - This query sends a sample with the requested hash for rescanning.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | File hash | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.hash | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'submit for dynamic analysis'

TCA-0207 - Submit an existing sample for dynamic analysis

Type: **investigate**\
Read only: **False**

TCA-0207 - This service allows users to detonate a file in the ReversingLabs TitaniumCloud sandbox. To submit a file for analysis, it must exist in TitaniumCloud.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**sha1** | required | Selected sample's SHA-1 hash | string | `sha1` `vault id`
**platform** | required | Selected platform on which the analysis will be performed. See TCA-0207 API documentation for available options | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.platform | string | |\
action_result.parameter.sha1 | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'submit url for dynamic analysis'

TCA-0207 - Submit an existing URL sample for dynamic analysis

Type: **investigate**\
Read only: **False**

TCA-0207 - This service allows users to detonate an URL in the ReversingLabs TitaniumCloud sandbox. To submit an url for analysis, it must exist in TitaniumCloud.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**sha1** | required | Selected sample's url string | string | `url` `domain`
**platform** | required | Selected platform on which the analysis will be performed. See TCA-0207 API documentation for available options | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.*.rl.url | string | url |\
action_result.data.*.rl.sha1 | string | sha1 |\
action_result.data.*.rl.status | string | |\
action_result.data.*.rl.url_base64 | string | |\
action_result.data.\*.rl.analysis_id | string | |

## action: 'upload file'

TCA-0202 - Upload file to TitaniumCloud

Type: **generic**\
Read only: **False**

TCA-0202 - Upload file to TitaniumCloud.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault_id** | required | Vault ID of file to upload | string | `vault id`
**file_name** | optional | Filename to use | string | `file name`

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.file_name | string | `file name` |\
action_result.parameter.vault_id | string | `pe file` `pdf` `flash` `apk` `jar` `doc` `xls` `ppt` |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'uri index'

TCA-0401 - Retrieve a list of all available file hashes associated with a given URI

Type: **generic**\
Read only: **False**

TCA-0401 - Provides a list of all available file hashes associated with a given URI (domain, IP address, email or URL) regardless of file classification.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**uri** | required | Desired URI string | string | `url` `domain`
**limit** | optional | Maximum number of results | numeric |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.limit | numeric | |\
action_result.parameter.uri | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'uri statistics'

TCA-0402 - Retrieve the number of MALICIOUS, SUSPICIOUS and KNOWN files associated with a specific URI

Type: **generic**\
Read only: **False**

TCA-0402 - Provides the number of MALICIOUS, SUSPICIOUS and KNOWN files associated with a specific URI (domain, IP address, email or URL).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**uri** | required | Uri | string | `sha1`

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.uri | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'url reputation'

TCA-0403 - Queries URL Threat Intelligence

Type: **investigate**\
Read only: **True**

TCA-0403 - Queries URL Threat Intelligence.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL to query | string | `url`

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.url | string | `url` |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'yara create ruleset'

TCA-0304 - Create a new YARA ruleset

Type: **generic**\
Read only: **False**

TCA-0304 - Create a new YARA ruleset.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ruleset_name** | required | YARA ruleset name | string |
**ruleset_text** | required | Stringified YARA ruleset / a Unicode string | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.ruleset_name | string | |\
action_result.parameter.ruleset_text | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'yara delete ruleset'

TCA-0303 - Delete YARA ruleset

Type: **generic**\
Read only: **False**

TCA-0303 - Delete YARA ruleset.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ruleset_name** | required | YARA ruleset name | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.ruleset_name | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'yara get ruleset info'

TCA-0303 - Get YARA ruleset info

Type: **generic**\
Read only: **False**

TCA-0303 - Get information for a specific YARA ruleset or all YARA rulesets in the collection.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ruleset_name** | optional | YARA ruleset name | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.data.*.ruleset_name | string | |\
action_result.data.*.valid | string | |\
action_result.data.\*.approved | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'yara get ruleset text'

TCA-0303 - Get YARA ruleset text

Type: **generic**\
Read only: **False**

TCA-0303 - Get the text of a YARA ruleset.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ruleset_name** | required | YARA ruleset name | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.ruleset_name | string | |\
action_result.data.\*.text | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'yara retro cancel hunt'

TCA-0319 - Cancel the retro hunt for the specified ruleset

Type: **generic**\
Read only: **False**

TCA-0319 - Cancel the retro hunt for the specified ruleset.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ruleset_name** | required | YARA ruleset name | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.ruleset_name | string | |\
action_result.data.\*.ruleset_sha1 | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'yara retro check status'

TCA-0319 - Check the retro hunt status for the specified ruleset

Type: **generic**\
Read only: **False**

TCA-0319 - Check the retro hunt status for the specified ruleset.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ruleset_name** | required | YARA ruleset name | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.ruleset_name | string | |\
action_result.data.*.retro_status | string | |\
action_result.data.*.start_time | string | |\
action_result.data.*.finish_time | string | |\
action_result.data.*.reason | string | |\
action_result.data.*.progress | string | |\
action_result.data.*.estimated_finish_time | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'yara retro enable hunt'

TCA-0319 - Enable YARA retro hunt

Type: **generic**\
Read only: **False**

TCA-0319 - Enable the retro hunt for the specified ruleset that has been submitted to TitaniumCloud prior to deployment of YARA retro.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ruleset_name** | required | YARA ruleset name | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.ruleset_name | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'yara retro start hunt'

TCA-0319 - Start YARA retro hunt for the specified ruleset

Type: **generic**\
Read only: **False**

TCA-0319 - Start YARA retro hunt for the specified ruleset.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ruleset_name** | required | YARA ruleset name | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success or failed
action_result.parameter.ruleset_name | string | |\
action_result.data.\*.ruleset_sha1 | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |
