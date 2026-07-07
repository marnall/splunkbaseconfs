# Flashpoint

Publisher: Flashpoint <br>
Connector Version: 3.0.1 <br>
Product Vendor: Flashpoint <br>
Product Name: Flashpoint <br>
Minimum Product Version: 6.2.1

This app implements the investigative actions for the Flashpoint on the Phantom Platform

## Explanation of Asset Configuration Parameters

The asset configuration parameters affect [test connectivity] and all the other actions of the
application. Below are the explanation and usage of all those parameters.

- **Base URL -** The URL to connect to the Flashpoint server.
- **API Token -** The API token of the user.
- **Retry Wait Period (in seconds) -** The value of this parameter defines the waiting period in
  seconds for which to hold the current execution of the action on receiving the “500 Internal
  Server Error” and then, retry the same API call after the waiting period is exhausted. This
  ensures that the integration provides a mechanism of attempting to overcome the intermittent
  “500 Internal Server Error”. It allows only non-zero positive integer values as input. The
  default value is 5 seconds.
- **Number Of Retries -** The value of this parameter defines the number of attempts for which the
  action will keep on retrying if the Flashpoint API continuously returns the “500 Internal Server
  Error”. If the intermittent error gets eliminated before the number of retries gets exhausted,
  then, the action execution will continue along its workflow with the next set of API calls and
  if the intermittent error is still persistent and all the number of retries are exhausted, then,
  the action will fail with the latest error message being displayed. It allows only zero or
  positive integer values as input. The default value is 1 retry.
- **Session Timeout -** This is an optional asset configuration parameter. The value of this
  parameter will be used as the session timeout value in the ‘Get Compromised Credentials’ and
  ‘Run Query’ actions while using the session scrolling pagination. The default value is 2 minutes
  and the maximum allowed value is 60 minutes.

## Steps to generate API Token

1. Go to [Flashpoint](https://fp.tools/) .
1. Select **APIs & Integrations** from the left side panel.
1. Under the **FLASHPOINT API** section, select **Manage API Tokens** .
1. Click on the **GENERATE TOKEN** .
1. Enter a **Token Label** and your current FPTools credentials in the **Username** and
   **Password** fields in the appeared **Generate API Token** prompt.
1. Click on the **GENERATE** button.
1. This will generate a new API token and will display it in the **GENERATE API TOKEN** section on
   the page.

**Note-** Save your generated API token somewhere secure, as you will no longer be able to
retrieve this key after leaving this page.

## Explanation of Flashpoint Actions' Parameters

1. ### Test Connectivity (Action Workflow Details)
   - This action will test the connectivity of the Phantom server to the Flashpoint instance by
     making an initial API call to the Indicators API using the provided asset configuration
     parameters.
   - The action validates the provided asset configuration parameters. Based on the API call
     response, the appropriate success and failure message will be displayed when the action gets
     executed.
1. ### List Indicators
   - **<u>Action Parameter</u> ​ - Attribute Types**

     - This parameter enables search by attribute types. It is an optional action parameter. It
       supports the comma-separated list of attribute types values. Each value from the
       provided comma-separated list must correspond to one of the MISP types, a list of which
       can be found [here](https://www.circl.lu/doc/misp/categories-and-types/#types) .
     - **Examples:**
       - Get recent md5, sha1, or source IP indicators
         - Attribute Types = md5,sha1,ip-src

   - **<u>Action Parameter</u> ​ - Query**

     - This parameter will be used for free text searching. It is an optional parameter. You
       can also provide different queries to filter out indicators results.
     - **Examples:**
       - Filtering results based on the field value
         - Query = category:”Payload Delivery”
       - Free text search(when using multiple words, use a + instead of space, and for
         specific word search use “test text” (inverted double quotes) in the query action
         parameter.)
         - Query = gandcrab+ransomware
         - Query = “test text”

   - **<u>Action Parameter</u> - Limit**

     - This parameter is used to limit the number of indicator results. The default value
       is 500. If the limit is not provided, it will fetch by default 500 indicator results.

   - **<u>Notes</u> -** The user will have to provide URL value in the "Attribute Types" action
     parameter and the URL value enclosed in double-quotes in the "Query" parameter if they want
     to search for an IoC having a specific URL value. This does not work correctly if the user
     provides the URL value without double-quotes in the "Query" parameter. This is based on the
     current API behavior of the Flashpoint.
1. ### Search Indicators
   - **<u>Action Parameter</u> ​ - Attribute Type and Attribute Value**

     - These parameters are required parameters. They will be used to retrieve specific
       indicator results based on the provided values.
     - **Examples:**
       - Get indicator matching a specific hash value

         - Attribute Type = md5 (any of md5,sha1,sha256, etc.)
         - Attribute Value= 16139ce9025274a388a4281fef65049e

       - Get indicator matching a specific filename

         - Attribute Type = filename
         - Attribute Value= "PLEASE-CHECK”

         <u>Note</u> - In the above example, without the double quotes around the filename,
         it will search for every filename that matches 'PLEASE'. The hyphen/space will be
         considered as the end of the search value and it will search for indicators matching
         the value until the first encountered hyphen/space.

       - Get indicator matching a specific source IP Address

         - Attribute Type = ip-src
         - Attribute Value = 111.255.198.92

       - Get indicator matching a specific URL value

         - Attribute Type = url
         - Attribute Value=
           http://ww1.gadmobs.com/?subid1=bf5b0786-272c-11e9-b8c7-e15edf920d61

         <u>Note</u> - Internally, this URL value passed within the inverted comma(for ad-hoc
         fixation) in the request parameters. Because without the inverted comma, the server
         responded with the Internal Server Error unnecessarily.

   - **<u>Action Parameter</u> ​ - Limit**

     - This parameter is used to limit the number of indicator results. The default value
       is 500. If the limit is not provided, it will fetch by default 500 indicator results.

   - **<u>Notes</u> -** This action is not working with the valid value of IoC type which
     consists of pipe symbol(|) in its name. In case of searching the IoC of that type, you can
     use [run query] or [list indicators] actions by providing an appropriate query in the
     "Query" action parameter. Below are the examples:

     <u>For [run query] action</u> :

     Search for IoC value which consists of pipe symbol(|) in the IoC attribute type

     - <u>Usage</u> :

     - Query = +basetypes:indicator_attribute +type:"\<ioc_type>" +value.\\\*:\<ioc_value>

     - <u>Example</u> :

     - Query = +basetypes:indicator_attribute +type:"ip-dst|port" +value.\\\*:5.79.68.110|80

     <u>For [list indicators] action</u> :

     Search for IoC value which consists of pipe symbol(|) in the IoC attribute type

     - <u>Usage</u> :

     - Attribute Types = \<ioc_type>

     - Query = +value.\\\*:\<ioc_value>

     - <u>Example</u> :

     - Attribute Types = ip-dst|port

     - Query = +value.\\\*:"5.79.68.110|80"
1. ### List Reports
   - **<u>Action Parameter</u> ​ - Limit**

     - This is an optional parameter. It is used to limit the number of fetched intelligence
       reports. The default value is 500. If the limit is not provided, it will fetch by
       default 500 intelligence reports.

     **<u>Note</u> -** Based on the current API analysis, the endpoint for this action fetches a
     huge set of data. Hence, the action run might take more time for a larger limit value.
1. ### Get Report
   - **<u>Action Parameter</u> ​ - Report ID**
     - This is a required parameter. It is a Flashpoint intelligence report ID.
     - **Examples:**
       - Fetch an intelligence report having the provided report ID value
         - Report ID = wrh9BCZETzu3AO3CUopOlw
1. ### List Related Reports
   - **<u>Action Parameter</u> ​ - Report ID**

     - This is a required parameter. It is a Flashpoint intelligence report ID.
     - **Examples:**
       - Fetch default 500 related intelligence reports for the provided report ID
         - Report ID = wrh9BCZETzu3AO3CUopOlw
         - Limit = Keep it empty

   - **<u>Action Parameter</u> ​ - Limit**

     - This is an optional parameter. It is used to limit the number of fetched intelligence
       reports. The default value is 500. If the limit is not provided, it will fetch by
       default 500 intelligence reports.

     **<u>Note</u> -** Based on the current API analysis, the endpoint for this action fetches a
     huge set of data. Hence, the action run might take more time for a larger limit value.
1. ### Get Compromised Credentials
   - **<u>Action Parameter</u> ​ - Filter**

     - This parameter will be used for filtering the data of credentials sightings on the
       Flashpoint instance. It is an optional parameter. If not given, it will get all the
       compromised credentials. A few sample values of the filter action parameter are listed
       below.
       - +is_fresh:true (search for only new credential sightings)
       - +breach.first_observed_at.date-time:[now-30d TO now] (search for credential
         sightings which are discovered in the last month based on the date provided from the
         source of this credential sightings data)
       - +breach.fpid:nIbeDs_VXyKedBmuhFEaGQ (search for all credential sightings in a
         Breach)
       - +email:username (search for a username)
       - +email.keyword:username@domain.com (search for an email address)
       - +domain.keyword:domain.com (search for credentials sightings data of a particular
         domain)
     - **Examples:**
       - Search for credential sightings of the given domain and that are discovered in the
         last month based on the date provided from the source of this credential sightings
         data
         - Filter = +domain.keyword:domain.com+breach.first_observed_at.date-time:\[now-30d
           TO now\]
       - Search for credential sightings of the given domain and that are discovered in the
         last month based on the date of indexing of the data into the Flashpoint server
         - Filter = +domain.keyword:domain.com+header\_.indexed_at:[now-30d TO now]
       - Search for credential sightings which are discovered in the last month based on the
         date of indexing of the data into the Flashpoint server
         - Filter = +header\_.indexed_at:[now-30d TO now]
       - Search for credential sightings which are discovered in between the provided
         timestamps based on the date provided from the source of this credential sightings
         data
         - Filter = +breach.first_observed_at.timestamp:[1234567890 TO 1234567890]
     - **Usage:**
       - For making filter parameter value

         - Query= +basetypes:credential-sighting\<filter>

         Here, the filter is any supported values by the search API endpoint.

   - **<u>Action Parameter</u> ​ - Limit**

     - This parameter is used to limit the number of fetched compromised credentials. The
       default value is 500. If the limit is not provided, it will fetch by default 500
       compromised credentials. The internal pagination logic for fetching a large number of
       compromised credentials implements the scrolling session-based Credentials All Search
       APIs.
1. ### Run Query
   - **<u>Action Parameter</u> ​ - Query**

     - This parameter will be used to search across all fields in the marketplace data by
       appending terms to it or limit searches to individual fields by appending \<field
       name>:\<value> to the ‘Query’ parameter. The queries supported by action are listed
       below.
       - Credential breach queries (+basetypes:breach)
       - CVE queries (+basetypes:cve)
       - Card queries (+basetypes:card)
       - Paste queries (+basetypes:paste)
       - Chat queries (+basetypes:generic-product)
       - Indicator attribute queries (+basetypes:indicator_attribute)
       - Credential sightings queries (+basetypes:credential-sighting)
       - Vulnerability queries (+basetypes:vulnerability)
       - Conversation queries (+basetypes:conversation)
       - Chan queries (+basetypes:chan)
       - Blog queries (+basetypes:blog)
       - Reddit queries (+basetypes:reddit)
       - Forum queries (+basetypes:forum)
     - **Examples:**
       - Search for "Analyst Research" breaches
         - Query= +basetypes:breach+source_type:"Analyst Research"
       - Search for "testing" across all free-form fields (message body, channel profile,
         channel name, and user name) for chat queries
         - Query = +basetypes:chat+testing
       - Search for credential sightings of the given domain and that are discovered in the
         last month based on the date provided from the source of this credential sightings
         data
         - Filter =
           +basetypes:credential-sighting+domain.keyword:domain.com+breach.first_observed_at.date-time:\[now-30d
           TO now\]
       - Search for all search results which are discovered in the last month based on the
         date of indexing of the data into the Flashpoint server
         - Filter = +header\_.indexed_at:[now-30d TO now]
       - Filter all search results by ISO date/time range based on the date provided from the
         source of this search data
         - Query = +created_at.date-time:\["2018-10-24T10:05:10+00:00" TO
           "2018-10-26T10:05:10+00:00"\]
       - Filter results by Unix time for all paste results based on the date provided from
         the source of this paste search data
         - Query = +basetypes:paste+created_at.timestamp:[1234567890 TO 1234567890]
     - **Usage:**
       - For making query parameter value

         - Query= \<basetypes_query>\<search_filter>

         Here, basetypes_query and search_filter are any supported values by the search API
         endpoint.

   - **<u>Action Parameter</u> ​ - Limit**

     - This parameter is used to limit the number of fetched all search data. The default value
       is 500. If the limit is not provided, it will fetch by default 500 search items. The
       internal pagination logic for fetching a large number of search items implements the
       scrolling session-based All Search APIs.

### Configuration variables

This table lists the configuration variables required to operate Flashpoint. These variables are specified when configuring a Flashpoint asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Base URL |
**api_token** | required | password | API Token |
**wait_timeout_period** | optional | numeric | Retry Wait Period(in seconds) |
**no_of_retries** | optional | numeric | Number Of Retries |
**session_timeout** | optional | numeric | Session Timeout(in minutes) |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[list reports](#action-list-reports) - Fetch a list of all the intelligence reports from the Flashpoint Platform <br>
[get report](#action-get-report) - Fetch a specific intelligence report from the Flashpoint Platform for the provided report ID <br>
[list related reports](#action-list-related-reports) - Fetch a list of all the related intelligence reports from the Flashpoint Platform for the provided report ID <br>
[get compromised credentials](#action-get-compromised-credentials) - Fetch a list of all the Credential Sightings from the Flashpoint Platform <br>
[run query](#action-run-query) - Fetch the data by performing a universal search from the Flashpoint Platform <br>
[list indicators](#action-list-indicators) - Fetch a list of IoCs that occur in the context of an event from the Flashpoint Platform <br>
[search indicators](#action-search-indicators) - Fetch an IoC value of a specific attribute type from the list of available IoCs on the Flashpoint Platform

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list reports'

Fetch a list of all the intelligence reports from the Flashpoint Platform

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**limit** | optional | Maximum number of reports to be fetched (default: 500) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.limit | numeric | | 501 |
action_result.data.\*.asset_ids | string | | JEfvV_RvTFC68FCg-ZFaCw |
action_result.data.\*.assets | string | | /assets/JEfvV_RvTFC68FCg-ZFaCw |
action_result.data.\*.body | string | | <html><head></head><body>This is a sample body</body></html> |
action_result.data.\*.id | string | `fp report id` | KtHHUswTTSG1IjhreK3ipg |
action_result.data.\*.ingested_at | string | | 2020-02-18T22:56:38.092+00:00 |
action_result.data.\*.is_featured | boolean | | True False |
action_result.data.\*.notified_at | string | | 2020-02-18T22:56:38.092+00:00 |
action_result.data.\*.platform_url | string | `url` | https://fp.tools/home/intelligence/reports/report/KtHHUswTTSG1IjhreK3ipg#detail |
action_result.data.\*.posted_at | string | | 2020-02-18T22:56:38.092+00:00 |
action_result.data.\*.processed_body | string | | This is a processed body |
action_result.data.\*.processed_summary | string | | This is a processed summary |
action_result.data.\*.published_status | string | | published |
action_result.data.\*.sources.\*.original | string | `url` | https://fp.tools/home/ddw/chats/channels/Pg2nv9-CUGm7OQwsvyRIiQ?id=1581881510&fpid=Rk4a-CEeW4Ku4zssexy_kg&limit=&skip=#detail |
action_result.data.\*.sources.\*.platform_url | string | `url` | |
action_result.data.\*.sources.\*.source | string | | |
action_result.data.\*.sources.\*.source_id | string | | |
action_result.data.\*.sources.\*.title | string | `url` | https://fp.tools/home/ddw/chats/channels/Pg2nv9-CUGm7OQwsvyRIiQ?id=1581881510&fpid=Rk4a-CEeW4Ku4zssexy_kg&limit=&skip=#detail |
action_result.data.\*.sources.\*.type | string | | External |
action_result.data.\*.summary | string | | This is a summary message |
action_result.data.\*.tags | string | | North America |
action_result.data.\*.title | string | | Test Title |
action_result.data.\*.title_asset | string | | /assets/YvrgXc0zQGK8rKLYLvZKEw |
action_result.data.\*.title_asset_id | string | | YvrgXc0zQGK8rKLYLvZKEw |
action_result.data.\*.updated_at | string | | 2020-02-18T22:56:38.092+00:00 |
action_result.data.\*.version_posted_at | string | | 2020-02-18T22:56:38.092+00:00 |
action_result.status | string | | success failed |
action_result.message | string | | Total reports: 501 |
action_result.summary.total_reports | numeric | | 501 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get report'

Fetch a specific intelligence report from the Flashpoint Platform for the provided report ID

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**report_id** | required | Flashpoint intelligence report ID | string | `fp report id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.report_id | string | `fp report id` | 6a_iIe1CQK2-Rjb_wRcKuw |
action_result.data.\*.asset_ids | string | | FIYUJy1-RuaFoJw1FstX8g |
action_result.data.\*.assets | string | | /assets/FIYUJy1-RuaFoJw1FstX8g |
action_result.data.\*.body | string | | <html><head></head><body>This is a sample body</body></html> |
action_result.data.\*.id | string | `fp report id` | 6a_iIe1CQK2-Rjb_wRcKuw |
action_result.data.\*.ingested_at | string | | 2020-02-13T21:10:50.521+00:00 |
action_result.data.\*.is_featured | boolean | | True False |
action_result.data.\*.notified_at | string | | 2020-02-13T21:13:24.735+00:00 |
action_result.data.\*.platform_url | string | `url` | https://fp.tools/home/intelligence/reports/report/6a_iIe1CQK2-Rjb_wRcKuw#detail |
action_result.data.\*.posted_at | string | | 2020-02-13T21:10:50.521+00:00 |
action_result.data.\*.processed_body | string | | This is a processed body |
action_result.data.\*.processed_summary | string | | This is a processed summary |
action_result.data.\*.published_status | string | | published |
action_result.data.\*.sources.\*.original | string | `url` | https://fp.tools/home/technical_data/cves/items/IPFW6CIyXzSsPpo4UxBhKw |
action_result.data.\*.sources.\*.platform_url | string | `url` | |
action_result.data.\*.sources.\*.source | string | | |
action_result.data.\*.sources.\*.source_id | string | | |
action_result.data.\*.sources.\*.title | string | `url` | https://fp.tools/home/technical_data/cves/items/IPFW6CIyXzSsPpo4UxBhKw |
action_result.data.\*.sources.\*.type | string | | External |
action_result.data.\*.summary | string | | This is a summary message |
action_result.data.\*.tags | string | | Global |
action_result.data.\*.title | string | | Test Title |
action_result.data.\*.title_asset | string | | /assets/koILoloySXqHVHcdka76hg |
action_result.data.\*.title_asset_id | string | | koILoloySXqHVHcdka76hg |
action_result.data.\*.updated_at | string | | 2020-02-13T21:13:24.735+00:00 |
action_result.data.\*.version_posted_at | string | | 2020-02-13T21:13:24.735+00:00 |
action_result.status | string | | success failed |
action_result.message | string | | Successfully fetched report |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list related reports'

Fetch a list of all the related intelligence reports from the Flashpoint Platform for the provided report ID

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**report_id** | required | Flashpoint intelligence report ID | string | `fp report id` |
**limit** | optional | Maximum number of reports to be fetched (default: 500) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.limit | numeric | | 50 |
action_result.parameter.report_id | string | `fp report id` | 6a_iIe1CQK2-Rjb_wRcKuw |
action_result.data.\*.asset_ids | string | | GH1tAvocTjGM67O8I_FflQ |
action_result.data.\*.assets | string | | /assets/GH1tAvocTjGM67O8I_FflQ |
action_result.data.\*.body | string | | <html><head></head><body>This is test body</body></html> |
action_result.data.\*.id | string | `fp report id` | 2EtSXz6HRX23Bb4ZvrFoHA |
action_result.data.\*.ingested_at | string | | 2020-02-12T22:35:11.579+00:00 |
action_result.data.\*.is_featured | boolean | | True False |
action_result.data.\*.notified_at | string | | 2020-02-12T22:42:57.323+00:00 |
action_result.data.\*.platform_url | string | `url` | https://fp.tools/home/intelligence/reports/report/2EtSXz6HRX23Bb4ZvrFoHA#detail |
action_result.data.\*.posted_at | string | | 2020-02-12T22:35:11.579+00:00 |
action_result.data.\*.processed_body | string | | This is a processed body |
action_result.data.\*.processed_summary | string | | This is a processed summary |
action_result.data.\*.published_status | string | | published |
action_result.data.\*.sources.\*.original | string | `url` | https://fp.tools/home/technical_data/cves/items/W69B9eS4WUK8sGcGi0m8AA |
action_result.data.\*.sources.\*.platform_url | string | `url` | |
action_result.data.\*.sources.\*.source | string | | |
action_result.data.\*.sources.\*.source_id | string | | |
action_result.data.\*.sources.\*.title | string | `url` | https://fp.tools/home/technical_data/cves/items/W69B9eS4WUK8sGcGi0m8AA |
action_result.data.\*.sources.\*.type | string | | External |
action_result.data.\*.summary | string | | This is a summary message |
action_result.data.\*.tags | string | | North America |
action_result.data.\*.title | string | | Test Title |
action_result.data.\*.title_asset | string | | /assets/19xWABeWTXGJuFz6Xh4phQ |
action_result.data.\*.title_asset_id | string | | 19xWABeWTXGJuFz6Xh4phQ |
action_result.data.\*.updated_at | string | | 2020-02-12T22:42:57.323+00:00 |
action_result.data.\*.version_posted_at | string | | 2020-02-12T22:42:57.323+00:00 |
action_result.status | string | | success failed |
action_result.message | string | | Total related reports: 50 |
action_result.summary.total_related_reports | numeric | | 50 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get compromised credentials'

Fetch a list of all the Credential Sightings from the Flashpoint Platform

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**filter** | optional | Filtering the data of credentials sightings | string | |
**limit** | optional | Maximum number of reports to be fetched (default: 500) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.filter | string | | +is_fresh:true +breach.fpid:nIbeDs_VXyKedBmuhFEaGQ +domain.keyword:domain.com+is_fresh:true |
action_result.parameter.limit | numeric | | 500 |
action_result.data.\*.\_id | string | | AvnahLkdXU6p-ahsDMr_JQ |
action_result.data.\*.\_source.basetypes | string | `fp query basetypes` | credential-sighting |
action_result.data.\*.\_source.body.raw | string | | user.name@domain.com:ya29.GlsrBvzMY9_HL-d7nCA0jlgC0cFUnTtpzrHU94xGiY0OM_sS-0nExZ9y-xWMapu7QKmAml3xkbi4wqE9e58D7XoZ8rF8qYbDNTTEqX4B7X1DMIBzmhT2LcLHpfq4 |
action_result.data.\*.\_source.breach.basetypes | string | `fp query basetypes` | breach |
action_result.data.\*.\_source.breach.breach_type | string | | credential |
action_result.data.\*.\_source.breach.created_at.date-time | string | | 2019-04-01T12:00:00Z |
action_result.data.\*.\_source.breach.created_at.timestamp | numeric | | 1554120000 |
action_result.data.\*.\_source.breach.first_observed_at.date-time | string | | 2019-09-20T03:14:00Z |
action_result.data.\*.\_source.breach.first_observed_at.timestamp | numeric | | 1568949240 |
action_result.data.\*.\_source.breach.fpid | string | | Z8VbElXPWHCguJBX6goxRg |
action_result.data.\*.\_source.breach.source | string | | Analyst Research |
action_result.data.\*.\_source.breach.source_type | string | | Analyst Research |
action_result.data.\*.\_source.breach.title | string | | Compromised Users from example.com Apr012019 |
action_result.data.\*.\_source.breach.victim | string | | www.example.com |
action_result.data.\*.\_source.credential_record_fpid | string | | qOpTj49MUeCXD5VXxKaJZA |
action_result.data.\*.\_source.customer_id | string | | 0011N00001sDj4A |
action_result.data.\*.\_source.domain | string | `fp attribute value` `domain` | domain.com |
action_result.data.\*.\_source.email | string | `fp attribute value` `email` | user.name@domain.com |
action_result.data.\*.\_source.extraction_id | string | | tXfm1PGDXRqTmcB57L9-eA |
action_result.data.\*.\_source.extraction_record_id | string | | dhaaFUx8X4G229qg67jrtA |
action_result.data.\*.\_source.fpid | string | | AvnahLkdXU6p-ahsDMr_JQ |
action_result.data.\*._source.header_.indexed_at | numeric | | 1581371433 |
action_result.data.\*.\_source.is_fresh | boolean | | True False |
action_result.data.\*.\_source.last_observed_at.date-time | string | | 2019-09-20T03:14:00Z |
action_result.data.\*.\_source.last_observed_at.timestamp | numeric | | 1568949240 |
action_result.data.\*.\_source.password | string | | thisapassword |
action_result.data.\*.\_source.password_complexity.has_lowercase | boolean | | True False |
action_result.data.\*.\_source.password_complexity.has_number | boolean | | True False |
action_result.data.\*.\_source.password_complexity.has_symbol | boolean | | True False |
action_result.data.\*.\_source.password_complexity.has_uppercase | boolean | | True False |
action_result.data.\*.\_source.password_complexity.length | numeric | | 129 |
action_result.data.\*.\_source.password_complexity.probable_hash_algorithms | string | | bcrypt |
action_result.data.\*.\_source.times_seen | numeric | | 1 |
action_result.data.\*.\_type | string | | \_doc |
action_result.status | string | | success failed |
action_result.message | string | | Total results: 4 |
action_result.summary.total_results | numeric | | 4 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'run query'

Fetch the data by performing a universal search from the Flashpoint Platform

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query** | required | Search across all fields in the marketplace or free text search | string | `fp query basetypes` |
**limit** | optional | Maximum number of reports to be fetched (default: 500) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.limit | numeric | | 478 |
action_result.parameter.query | string | `fp query basetypes` | +basetypes:card +basetypes:breach +basetypes:cve +basetypes:paste +basetypes:generic-product +basetypes:indicator_attribute +basetypes:credential-sighting +basetypes:vulnerability +basetypes:conversation +basetypes:chan +basetypes:blog +basetypes:reddit +basetypes:forum +basetypes:indicator_attribute+type:"ip-dst|port"+value.\\\*:5.79.68.110|80 |
action_result.data.\*.\_id | string | | 8dKFsRoeV0mP8zOY1uYcLQ |
action_result.data.\*.\_source.Event.Galaxy.\*.GalaxyCluster.\*.authors | string | | TESTAUTHORS |
action_result.data.\*.\_source.Event.Galaxy.\*.GalaxyCluster.\*.description | string | | This is a test description |
action_result.data.\*.\_source.Event.Galaxy.\*.GalaxyCluster.\*.galaxy_id | string | | 22 |
action_result.data.\*.\_source.Event.Galaxy.\*.GalaxyCluster.\*.id | string | | 11086 |
action_result.data.\*.\_source.Event.Galaxy.\*.GalaxyCluster.\*.meta.external_id | string | | T1192 |
action_result.data.\*.\_source.Event.Galaxy.\*.GalaxyCluster.\*.meta.kill_chain | string | | test-attack:enterprise-attack:initial-access |
action_result.data.\*.\_source.Event.Galaxy.\*.GalaxyCluster.\*.meta.mitre_data_sources | string | | Mail server |
action_result.data.\*.\_source.Event.Galaxy.\*.GalaxyCluster.\*.meta.mitre_platforms | string | | macOS |
action_result.data.\*.\_source.Event.Galaxy.\*.GalaxyCluster.\*.meta.refs | string | `url` | https:/testdomainlink.com/test |
action_result.data.\*.\_source.Event.Galaxy.\*.GalaxyCluster.\*.source | string | `url` | https://testdomainlink.com/test |
action_result.data.\*.\_source.Event.Galaxy.\*.GalaxyCluster.\*.tag_id | string | | 270 |
action_result.data.\*.\_source.Event.Galaxy.\*.GalaxyCluster.\*.tag_name | string | | misp-galaxy:test-enterprise-attack-attack-pattern="Exfiltration Over Command and Control Channel - T1041" |
action_result.data.\*.\_source.Event.Galaxy.\*.GalaxyCluster.\*.type | string | | test-enterprise-attack-attack-pattern |
action_result.data.\*.\_source.Event.Galaxy.\*.GalaxyCluster.\*.uuid | string | | fb2242d8-1707-11e8-ab20-6fa7448c3640 |
action_result.data.\*.\_source.Event.Galaxy.\*.GalaxyCluster.\*.value | string | | Exfiltration Over Command and Control Channel - T1041 |
action_result.data.\*.\_source.Event.Galaxy.\*.GalaxyCluster.\*.version | string | | 4 |
action_result.data.\*.\_source.Event.Galaxy.\*.description | string | | This is a test description |
action_result.data.\*.\_source.Event.Galaxy.\*.icon | string | | map |
action_result.data.\*.\_source.Event.Galaxy.\*.id | string | | 22 |
action_result.data.\*.\_source.Event.Galaxy.\*.name | string | | Test Name - Example |
action_result.data.\*.\_source.Event.Galaxy.\*.type | string | | mitre-enterprise-attack-attack-pattern |
action_result.data.\*.\_source.Event.Galaxy.\*.uuid | string | | fa7016a8-1707-11e8-82d0-1b73d76eb204 |
action_result.data.\*.\_source.Event.Galaxy.\*.version | string | | 4 |
action_result.data.\*.\_source.Event.Org.id | string | | 1 |
action_result.data.\*.\_source.Event.Org.name | string | | FP-SME-INT |
action_result.data.\*.\_source.Event.Org.uuid | string | | 5af24c91-8c9c-4b8d-8a59-620c0a640c05 |
action_result.data.\*.\_source.Event.Orgc.id | string | | 1 |
action_result.data.\*.\_source.Event.Orgc.name | string | | FP-SME-INT |
action_result.data.\*.\_source.Event.Orgc.uuid | string | | 5af24c91-8c9c-4b8d-8a59-620c0a640c05 |
action_result.data.\*.\_source.Event.RelatedEvent.\*.Event.Org.id | string | | 1 |
action_result.data.\*.\_source.Event.RelatedEvent.\*.Event.Org.name | string | | FP-SME-INT |
action_result.data.\*.\_source.Event.RelatedEvent.\*.Event.Org.uuid | string | | 5af24c91-8c9c-4b8d-8a59-620c0a640c05 |
action_result.data.\*.\_source.Event.RelatedEvent.\*.Event.Orgc.id | string | | 1 |
action_result.data.\*.\_source.Event.RelatedEvent.\*.Event.Orgc.name | string | | FP-SME-INT |
action_result.data.\*.\_source.Event.RelatedEvent.\*.Event.Orgc.uuid | string | | 5af24c91-8c9c-4b8d-8a59-620c0a640c05 |
action_result.data.\*.\_source.Event.RelatedEvent.\*.Event.analysis | string | | 0 |
action_result.data.\*.\_source.Event.RelatedEvent.\*.Event.date | string | | 2019-02-05 |
action_result.data.\*.\_source.Event.RelatedEvent.\*.Event.distribution | string | | 3 |
action_result.data.\*.\_source.Event.RelatedEvent.\*.Event.id | string | | 3472 |
action_result.data.\*.\_source.Event.RelatedEvent.\*.Event.info | string | | 2018-11-26 21:40:00: Nodistribute - nodistribute.com |
action_result.data.\*.\_source.Event.RelatedEvent.\*.Event.org_id | string | | 1 |
action_result.data.\*.\_source.Event.RelatedEvent.\*.Event.orgc_id | string | | 1 |
action_result.data.\*.\_source.Event.RelatedEvent.\*.Event.published | boolean | | True False |
action_result.data.\*.\_source.Event.RelatedEvent.\*.Event.threat_level_id | string | | 2 |
action_result.data.\*.\_source.Event.RelatedEvent.\*.Event.timestamp | string | | 1549411296 |
action_result.data.\*.\_source.Event.RelatedEvent.\*.Event.uuid | string | | 5c5a23e0-a67c-4270-ba6e-12600a640c05 |
action_result.data.\*.\_source.Event.Tag.\*.colour | string | | #b9b062 |
action_result.data.\*.\_source.Event.Tag.\*.exportable | boolean | | True False |
action_result.data.\*.\_source.Event.Tag.\*.hide_tag | boolean | | True False |
action_result.data.\*.\_source.Event.Tag.\*.id | string | | 488 |
action_result.data.\*.\_source.Event.Tag.\*.name | string | `file name` | Nodistribute |
action_result.data.\*.\_source.Event.Tag.\*.user_id | boolean | | True False |
action_result.data.\*.\_source.Event.analysis | string | | 0 |
action_result.data.\*.\_source.Event.attribute_count | string | | 1 |
action_result.data.\*.\_source.Event.date | string | | 2019-02-05 |
action_result.data.\*.\_source.Event.disable_correlation | boolean | | True False |
action_result.data.\*.\_source.Event.distribution | string | | 3 |
action_result.data.\*.\_source.Event.event_creator_email | string | `email` | extxvbhjx@testdomainlink.com |
action_result.data.\*.\_source.Event.extends_uuid | string | | |
action_result.data.\*.\_source.Event.fpid | string | | tJjXjAb-Un6HJ1fGwChZ7g |
action_result.data.\*.\_source.Event.id | string | | 5070 |
action_result.data.\*.\_source.Event.info | string | | 2018-12-04 13:10:00: Nodistribute - nodistribute.com |
action_result.data.\*.\_source.Event.locked | boolean | | True False |
action_result.data.\*.\_source.Event.org_id | string | | 1 |
action_result.data.\*.\_source.Event.orgc_id | string | | 1 |
action_result.data.\*.\_source.Event.proposal_email_lock | boolean | | True False |
action_result.data.\*.\_source.Event.publish_timestamp | string | | 1549413013 |
action_result.data.\*.\_source.Event.published | boolean | | True False |
action_result.data.\*.\_source.Event.sharing_group_id | string | | 0 |
action_result.data.\*.\_source.Event.threat_level_id | string | | 2 |
action_result.data.\*.\_source.Event.timestamp | string | | 1549413013 |
action_result.data.\*.\_source.Event.uuid | string | | 5c5a2a95-4b88-4db4-a065-124a0a640c05 |
action_result.data.\*.\_source.Tag.\*.colour | string | | #000000 |
action_result.data.\*.\_source.Tag.\*.exportable | boolean | | True False |
action_result.data.\*.\_source.Tag.\*.hide_tag | boolean | | True False |
action_result.data.\*.\_source.Tag.\*.id | string | | 7 |
action_result.data.\*.\_source.Tag.\*.name | string | | malware:destructive:wiper |
action_result.data.\*.\_source.Tag.\*.user_id | boolean | | True False |
action_result.data.\*.\_source.account_domain | string | | testdomainlink.com |
action_result.data.\*.\_source.account_holder_information.full_name | string | | Name |
action_result.data.\*.\_source.account_holder_information.location.address | string | | Waterbury United States |
action_result.data.\*.\_source.account_holder_information.location.country.raw | string | | US |
action_result.data.\*.\_source.account_organization | string | | Organization |
action_result.data.\*.\_source.account_type | string | | Personal |
action_result.data.\*.\_source.balance | numeric | | 936 |
action_result.data.\*.\_source.bank_name | string | | Discover Bank |
action_result.data.\*.\_source.base.basetypes | string | `fp query basetypes` | base |
action_result.data.\*.\_source.base.fpid | string | | 17Oc0omBXUe0HltX8Yk0hw |
action_result.data.\*.\_source.base.native_id | string | | 20151 |
action_result.data.\*.\_source.base.raw | string | | This is a test base raw |
action_result.data.\*.\_source.base.release_date.date-time | string | | 2019-04-22T00:00:00+00:00 |
action_result.data.\*.\_source.base.release_date.raw | string | | 2019-04-22 |
action_result.data.\*.\_source.base.release_date.timestamp | numeric | | 1555891200 |
action_result.data.\*.\_source.base.title | string | | Test Title |
action_result.data.\*.\_source.basetypes | string | `fp query basetypes` | cvv breach advisory post generic-product indicator_attribute credential-sighting vulnerability message aggregation |
action_result.data.\*.\_source.bin | numeric | | 601100 |
action_result.data.\*.\_source.board.name | string | | pol |
action_result.data.\*.\_source.board.native_id | string | | pol |
action_result.data.\*.\_source.board.site.behavior | string | | replace |
action_result.data.\*.\_source.board.site.href | string | | urn:fp:type:resource.qualified.site:Ra2dBSXnXjKqoLS7wJPWgw |
action_result.data.\*.\_source.board.site.target | string | | $.site |
action_result.data.\*.\_source.board.title | string | | pol |
action_result.data.\*.\_source.board.type | string | | board |
action_result.data.\*.\_source.body.enrichments.cves | string | | CVE-2016-7266 |
action_result.data.\*.\_source.body.enrichments.domains | string | `fp attribute value` `domain` | chaxxe-xx-fall-bxxinx.html www.testdomainlink.va |
action_result.data.\*.\_source.body.enrichments.hashtags | string | | #HASHTAG |
action_result.data.\*.\_source.body.enrichments.language | string | | en ar |
action_result.data.\*.\_source.body.enrichments.links.\*.href | string | `url` | https://schemas.testdomainlink.com/2017/resxxrce/collexxxons/daxxxxse_row.json |
action_result.data.\*.\_source.body.enrichments.social_media_handles | string | | @blxxfatxxxer |
action_result.data.\*.\_source.body.raw | string | `url` | This is a test body |
action_result.data.\*.\_source.body.text/html+sanitized | string | `url` | This is a test body |
action_result.data.\*.\_source.body.text/html-sanitized | string | | |
action_result.data.\*.\_source.body.text/plain | string | `url` | This is test body text/plan |
action_result.data.\*.\_source.breach.basetypes | string | | breach |
action_result.data.\*.\_source.breach.breach_type | string | | credential |
action_result.data.\*.\_source.breach.created_at.date-time | string | | 2019-04-01T12:00:00Z |
action_result.data.\*.\_source.breach.created_at.timestamp | numeric | | 1554120000 |
action_result.data.\*.\_source.breach.first_observed_at.date-time | string | | 2019-09-20T03:14:00Z |
action_result.data.\*.\_source.breach.first_observed_at.timestamp | numeric | | 1568949240 |
action_result.data.\*.\_source.breach.fpid | string | | ZxVbExxxfghuxBX6goxxg |
action_result.data.\*.\_source.breach.source | string | | Analyst Research |
action_result.data.\*.\_source.breach.source_type | string | | Analyst Research |
action_result.data.\*.\_source.breach.title | string | | Compromised Users from example.com Apr012019 |
action_result.data.\*.\_source.breach.victim | string | | www.example.com |
action_result.data.\*.\_source.breach_intersections.\*.count | numeric | | 7167 |
action_result.data.\*.\_source.breach_intersections.\*.dump | string | | en6DWDl_VKyuLUvCsHk_EQ |
action_result.data.\*.\_source.breach_intersections.\*.title | string | | Compromised Users from example.com Sept2015 |
action_result.data.\*.\_source.breach_intersections.count | numeric | | 2 |
action_result.data.\*.\_source.breach_intersections.dump | string | | b7klT43iV-SLtY1sE-\_vYg |
action_result.data.\*.\_source.breach_intersections.title | string | | Compromised Users from test: File "1234" Jan052020 |
action_result.data.\*.\_source.card_number | string | | 4147342xxxxxxx442 |
action_result.data.\*.\_source.card_type | string | | Discover Bank Discover Platinum Credit |
action_result.data.\*.\_source.cardholder_information.date_of_birth.raw | string | | NULL |
action_result.data.\*.\_source.cardholder_information.email | string | | yes |
action_result.data.\*.\_source.cardholder_information.first | string | | Firstname |
action_result.data.\*.\_source.cardholder_information.full_name | string | | Full Name |
action_result.data.\*.\_source.cardholder_information.is_date_of_birth_available | boolean | | True False |
action_result.data.\*.\_source.cardholder_information.is_email_available | boolean | | True False |
action_result.data.\*.\_source.cardholder_information.is_mothers_maiden_name_available | boolean | | True False |
action_result.data.\*.\_source.cardholder_information.is_phone_number_available | boolean | | True False |
action_result.data.\*.\_source.cardholder_information.is_social_security_number_available | boolean | | True False |
action_result.data.\*.\_source.cardholder_information.last | string | | LAST NAME |
action_result.data.\*.\_source.cardholder_information.location.address | string | | 1245M 2026 |
action_result.data.\*.\_source.cardholder_information.location.city | string | | City |
action_result.data.\*.\_source.cardholder_information.location.country.abbreviation | string | | AB |
action_result.data.\*.\_source.cardholder_information.location.country.full_name | string | | Country Name |
action_result.data.\*.\_source.cardholder_information.location.country.raw | string | | AB |
action_result.data.\*.\_source.cardholder_information.location.raw | string | | 1104 |
action_result.data.\*.\_source.cardholder_information.location.region.abbreviation | string | | UNKNOWN |
action_result.data.\*.\_source.cardholder_information.location.region.full_name | string | | NY |
action_result.data.\*.\_source.cardholder_information.location.region.raw | string | | NC |
action_result.data.\*.\_source.cardholder_information.location.zip_code | string | | 28904 |
action_result.data.\*.\_source.cardholder_information.phone_number | string | | 81392026 |
action_result.data.\*.\_source.cardholder_information.social_security_number.full | string | | 2013 |
action_result.data.\*.\_source.category | string | | Money Payload delivery |
action_result.data.\*.\_source.container.admins_count | numeric | | 0 |
action_result.data.\*.\_source.container.basetypes | string | | container |
action_result.data.\*.\_source.container.body.enrichments.domains | string | `fp attribute value` `domain` | 15g2q4s6kj931.png |
action_result.data.\*.\_source.container.body.enrichments.language | string | | en |
action_result.data.\*.\_source.container.body.enrichments.links.\*.href | string | `url` `ip` | https://example.com/test.gif |
action_result.data.\*.\_source.container.body.raw | string | `url` | https://example.com/test.gif |
action_result.data.\*.\_source.container.body.text/html+sanitized | string | `url` | https://example.com/test.gif |
action_result.data.\*.\_source.container.body.text/plain | string | `url` | https://example.com/test.gif |
action_result.data.\*.\_source.container.category | string | | Uncategorized |
action_result.data.\*.\_source.container.container.basetypes | string | | container |
action_result.data.\*.\_source.container.container.body.enrichments.bins | string | | 397466 |
action_result.data.\*.\_source.container.container.body.enrichments.bitcoin_addresses | string | | 3xvP5WbQNw4HPyEYvwtKC6aubQ |
action_result.data.\*.\_source.container.container.body.enrichments.domains | string | `fp attribute value` `domain` | testdomainlink.com |
action_result.data.\*.\_source.container.container.body.enrichments.email_addresses | string | `fp attribute value` `email` | kulture@kulturemedia.org |
action_result.data.\*.\_source.container.container.body.enrichments.facebook_urls | string | | groups |
action_result.data.\*.\_source.container.container.body.enrichments.hashtags | string | | #hashtag |
action_result.data.\*.\_source.container.container.body.enrichments.language | string | | en |
action_result.data.\*.\_source.container.container.body.enrichments.links.\*.href | string | `url` `ip` | https://www.testdomainlink.com/en |
action_result.data.\*.\_source.container.container.body.enrichments.pans | string | | 3974663043 |
action_result.data.\*.\_source.container.container.body.enrichments.partial_cards | string | | 3974663043 |
action_result.data.\*.\_source.container.container.body.enrichments.social_media_handles | string | | @txxxxls |
action_result.data.\*.\_source.container.container.body.raw | string | | This is a test body |
action_result.data.\*.\_source.container.container.body.text/html+sanitized | string | | This is a test body |
action_result.data.\*.\_source.container.container.body.text/plain | string | | This is a test body |
action_result.data.\*.\_source.container.container.created_at.date-time | string | | 2010-09-09T14:30:26+00:00 |
action_result.data.\*.\_source.container.container.created_at.raw | string | | 2010-09-09 14:30:26+00:00 |
action_result.data.\*.\_source.container.container.created_at.timestamp | numeric | | 1284042626 |
action_result.data.\*.\_source.container.container.enrichments.language | string | | vi |
action_result.data.\*.\_source.container.container.first_observed_at.date-time | string | | 2014-04-21T22:22:00.462230+00:00 |
action_result.data.\*.\_source.container.container.first_observed_at.raw | string | | 2014-04-21 22:22:00.462230+00:00 |
action_result.data.\*.\_source.container.container.first_observed_at.timestamp | numeric | | 1398118920 |
action_result.data.\*.\_source.container.container.fpid | string | | IiHLxxxxUTSAM--a-b2qNw |
action_result.data.\*.\_source.container.container.icon_url | string | | https://example.com/icons/541672061005856769/f38df3477629c0103733dfffc4541f3b.jpg |
action_result.data.\*.\_source.container.container.is_deleted | boolean | | True False |
action_result.data.\*.\_source.container.container.last_observed_at.date-time | string | | 2019-07-15T02:27:07+00:00 |
action_result.data.\*.\_source.container.container.last_observed_at.raw | string | | 1563157627.517987 |
action_result.data.\*.\_source.container.container.last_observed_at.timestamp | numeric | | 1563157627 |
action_result.data.\*.\_source.container.container.legacy_fpid | string | | sfiwvykIWsiOYbzKFVm-8w |
action_result.data.\*.\_source.container.container.name | string | | Container Name |
action_result.data.\*.\_source.container.container.native_id | string | | Native ID |
action_result.data.\*.\_source.container.container.num_subscribers | numeric | | 1076809 |
action_result.data.\*.\_source.container.container.region | string | | eu_central |
action_result.data.\*.\_source.container.container.server_owner.id | string | | 303560006810776586 |
action_result.data.\*.\_source.container.container.server_owner.username | string | | Grenus#9357 |
action_result.data.\*.\_source.container.container.source_uri | string | `url` | https://testdomainlink.com/source/ |
action_result.data.\*.\_source.container.container.title | string | | pol |
action_result.data.\*.\_source.container.container.type | string | | board |
action_result.data.\*.\_source.container.container.url | string | `fp attribute value` `url` | https://testdomainlink.com/r/ |
action_result.data.\*.\_source.container.container.verification_level | string | | 4 |
action_result.data.\*.\_source.container.created_at.date-time | string | | 2019-07-14T16:04:12+00:00 |
action_result.data.\*.\_source.container.created_at.raw | string | | 1464629880 2013-01-31 18:03:58+00:00 2019-07-14 16:04:12+00:00 |
action_result.data.\*.\_source.container.created_at.timestamp | numeric | | 1563120252 |
action_result.data.\*.\_source.container.description | string | `url` | Test Description |
action_result.data.\*.\_source.container.enrichments.domains | string | `fp attribute value` `domain` | testdomainlink.com |
action_result.data.\*.\_source.container.enrichments.language | string | | en |
action_result.data.\*.\_source.container.enrichments.links.\*.href | string | `url` `ip` | http://testdomainlink.com |
action_result.data.\*.\_source.container.first_observed_at.date-time | string | | 2014-04-23T03:08:24.610332+00:00 |
action_result.data.\*.\_source.container.first_observed_at.raw | string | | 2014-04-23 03:08:24.610332+00:00 |
action_result.data.\*.\_source.container.first_observed_at.timestamp | numeric | | 1398222504 |
action_result.data.\*.\_source.container.fpid | string | | U_jW3cTZUpKMrHKBVZY0Dw |
action_result.data.\*.\_source.container.is_deleted | boolean | | True False |
action_result.data.\*.\_source.container.kicked_count | numeric | | 0 |
action_result.data.\*.\_source.container.last_observed_at.date-time | string | | 2019-07-15T02:26:04+00:00 |
action_result.data.\*.\_source.container.last_observed_at.raw | string | | 1563157564.722768 |
action_result.data.\*.\_source.container.last_observed_at.timestamp | numeric | | 1563157564 |
action_result.data.\*.\_source.container.legacy_fpid | string | | 8AWJcntPVYeklC4n5273uw |
action_result.data.\*.\_source.container.name | string | `url` | Test Name |
action_result.data.\*.\_source.container.native_id | string | | cd4npa |
action_result.data.\*.\_source.container.num_replies | numeric | | 838 |
action_result.data.\*.\_source.container.participants_count | numeric | | 382 |
action_result.data.\*.\_source.container.permission_overrides.\*.overrides | string | | {'embed_links': False, 'read_message_history': True, 'mention_everyone': False, 'add_reactions': True, 'attach_files': False, 'send_tts_messages': False} |
action_result.data.\*.\_source.container.permission_overrides.\*.role.id | string | | 541672061005856769 |
action_result.data.\*.\_source.container.permission_overrides.\*.role.name | string | | @everyone |
action_result.data.\*.\_source.container.raw_href | string | `url` | https://testdomainlink.com/test |
action_result.data.\*.\_source.container.reputation.number_of_downvotes | numeric | | 581 |
action_result.data.\*.\_source.container.reputation.number_of_upvotes | numeric | | 582 |
action_result.data.\*.\_source.container.site_actor.avatar_uri.href | string | | https://testdomainlink.com/user/123e3e.jpg |
action_result.data.\*.\_source.container.site_actor.basetypes | string | | site_actor |
action_result.data.\*.\_source.container.site_actor.flair.flair_text | string | | Cringetopia Overlord |
action_result.data.\*.\_source.container.site_actor.fpid | string | | vhGyvSzrW6WTl3QrJJWudg 3tWg7NpuVZ2yBBBrz1FLAA |
action_result.data.\*.\_source.container.site_actor.is_admin | boolean | | True False |
action_result.data.\*.\_source.container.site_actor.last_observed_at.date-time | string | | 2019-07-15T02:19:23+00:00 |
action_result.data.\*.\_source.container.site_actor.last_observed_at.raw | string | | 1563157163.299181 |
action_result.data.\*.\_source.container.site_actor.last_observed_at.timestamp | numeric | | 1563157163 |
action_result.data.\*.\_source.container.site_actor.names.aliases | string | | vxxtax |
action_result.data.\*.\_source.container.site_actor.names.handle | string | | testname cam130894 |
action_result.data.\*.\_source.container.site_actor.native_id | string | | x_ertxxx_ty |
action_result.data.\*.\_source.container.site_actor.site.base_uris | string | `url` | https://www.testdomainlink.com |
action_result.data.\*.\_source.container.site_actor.site.basetypes | string | | site |
action_result.data.\*.\_source.container.site_actor.site.created_at.date-time | string | | 2017-01-25T17:25:41 |
action_result.data.\*.\_source.container.site_actor.site.description.raw | string | | This is an example description |
action_result.data.\*.\_source.container.site_actor.site.fpid | string | | kGh8HzrbVM6HA83csB8D8Q |
action_result.data.\*.\_source.container.site_actor.site.site_type | string | | Example |
action_result.data.\*.\_source.container.site_actor.site.source_uri | string | | testdomainlink.com |
action_result.data.\*.\_source.container.site_actor.site.tags.\*.name | string | | Language |
action_result.data.\*.\_source.container.site_actor.site.tags.\*.parent_tag.name | string | | Language |
action_result.data.\*.\_source.container.site_actor.site.title | string | | Test Title |
action_result.data.\*.\_source.container.site_actor.site.updated_at.date-time | string | | 2019-05-28T15:25:06 |
action_result.data.\*.\_source.container.site_actor.source_uri | string | `url` | https://testdomainlink.com/r/?ref=xxxdnext |
action_result.data.\*.\_source.container.site_actor.url | string | `fp attribute value` `url` | https://testdomainlink.com/user/xxx130894 |
action_result.data.\*._source.container.source_uri | string | `url` | https://testdomainlink.com |
action_result.data.\*._source.container.title | string | `url` | Test Title |
action_result.data.\*._source.container.topic | string | | \<a:tru:533929657473564672> \<a:tru2:533929657834274816> \<a:tru3:533929656999739395> \<a:tru4:533929657486278667> \<a:tru5:533929656735367168> \<a:tru6:533929870561116173> \<a:tru2:533929657834274816>\<a:t_:409863142827622400>\<a:o_:409863139417391115> \<:d:535397902550302722> \<:y:535401467981332480> \<:d:535397902550302722> \<:d:535397902550302722> \<:y_:535401467729805323> \<a:testo:400377695403245569>\*\*Support Our Server - \<#412449213960683530>\<a:giflove:399339112890630165> Check Out Our Website- https://test.me \<a:test:432612759981522944>Invite link https://discord.gg/ABCDEF \*\*\<a:AmbitiousMistyHoopoesmall:400381611083956245> |
action_result.data.\*.\_source.container.type | string | | channel |
action_result.data.\*.\_source.container.url | string | `fp attribute value` `url` | https://example.com/test.gif |
action_result.data.\*.\_source.container.username | string | `url` `user name` | username |
action_result.data.\*.\_source.container_position.index_number | numeric | | 1 |
action_result.data.\*.\_source.created_at.date-time | string | | 2019-07-14T19:56:37+00:00 |
action_result.data.\*.\_source.created_at.raw | string | | 2019-07-14 19:56:37+00:00 |
action_result.data.\*.\_source.created_at.timestamp | numeric | | 1563134197 |
action_result.data.\*.\_source.credential_record_fpid | string | | qOpTj49MUeCXD5VXxKaJZA |
action_result.data.\*.\_source.credit_cards.\*.raw | string | | || |
action_result.data.\*.\_source.customer_id | string | | 0011N00001sDj4A |
action_result.data.\*.\_source.cve.basetypes | string | | vulnerability |
action_result.data.\*.\_source.cve.fpid | string | | V1hUGZkyUgmd-uLt5diIdw |
action_result.data.\*.\_source.cve.last_observed_at.date-time | string | | 2020-03-03T19:00:02+00:00 |
action_result.data.\*.\_source.cve.last_observed_at.raw | string | | 2020-03-03T19:00:02 |
action_result.data.\*.\_source.cve.last_observed_at.timestamp | numeric | | 1583262002 |
action_result.data.\*.\_source.cve.mitre.basetypes | string | | mitre |
action_result.data.\*.\_source.cve.mitre.body.enrichments.cves | string | | CVE-2016-7266 |
action_result.data.\*.\_source.cve.mitre.body.enrichments.links.\*.href | string | `url` | https://schemas.testdomainlink.com/2017/resource/collections/database_row.json |
action_result.data.\*.\_source.cve.mitre.body.raw | string | | This is a test body raw |
action_result.data.\*.\_source.cve.mitre.body.text/html-sanitized | string | | This is a test body text/html-sanitized |
action_result.data.\*.\_source.cve.mitre.body.text/plain | string | | This is a test body text/plain |
action_result.data.\*.\_source.cve.mitre.created_at.date-time | string | | 2016-09-09T00:00:00+00:00 |
action_result.data.\*.\_source.cve.mitre.created_at.raw | string | | 20160909 |
action_result.data.\*.\_source.cve.mitre.created_at.timestamp | numeric | | 1473379200 |
action_result.data.\*.\_source.cve.mitre.fpid | string | | EcUGRaNNXPevq6Jo2yo8og |
action_result.data.\*.\_source.cve.mitre.last_observed_at.date-time | string | | 2020-03-03T19:00:02+00:00 |
action_result.data.\*.\_source.cve.mitre.last_observed_at.raw | string | | 2020-03-03T19:00:02 |
action_result.data.\*.\_source.cve.mitre.last_observed_at.timestamp | numeric | | 1583262002 |
action_result.data.\*.\_source.cve.mitre.native_id | string | | [28355, 'CVE-2016-7232'] |
action_result.data.\*.\_source.cve.mitre.phase | string | | Assigned (20160909) |
action_result.data.\*.\_source.cve.mitre.site.base_uris | string | `url` | http://testdomainlink.org |
action_result.data.\*.\_source.cve.mitre.site.basetypes | string | | site |
action_result.data.\*.\_source.cve.mitre.site.created_at.date-time | string | | 2019-02-14T17:21:27.064334 |
action_result.data.\*.\_source.cve.mitre.site.description.raw | string | | This is a test description. |
action_result.data.\*.\_source.cve.mitre.site.fpid | string | | YJKOYduNWE2PVi1WiTEMOg |
action_result.data.\*.\_source.cve.mitre.site.site_type | string | | Site Type |
action_result.data.\*.\_source.cve.mitre.site.source_uri | string | | testdomainlink.org |
action_result.data.\*.\_source.cve.mitre.site.tags.\*.name | string | | Security |
action_result.data.\*.\_source.cve.mitre.site.tags.\*.parent_tag.name | string | | Cyber Threat |
action_result.data.\*.\_source.cve.mitre.site.title | string | | MITRE |
action_result.data.\*.\_source.cve.mitre.site.updated_at.date-time | string | | 2019-02-14T17:26:05.741343 |
action_result.data.\*.\_source.cve.mitre.status | string | | Candidate |
action_result.data.\*.\_source.cve.mitre.title | string | | CVE-2016-7232 |
action_result.data.\*.\_source.cve.native_id | string | | CVE-2016-7232 |
action_result.data.\*.\_source.cve.nist.assigner | string | `email` | cve@mitre.org |
action_result.data.\*.\_source.cve.nist.basetypes | string | | nist |
action_result.data.\*.\_source.cve.nist.body.enrichments.cves | string | | CVE-2016-7266 |
action_result.data.\*.\_source.cve.nist.body.enrichments.links.\*.href | string | `url` | https://schemas.testdomainlink.com/2017/resource/colxxxxions/daxxbxxe_row.json |
action_result.data.\*.\_source.cve.nist.body.raw | string | | This is a test body |
action_result.data.\*.\_source.cve.nist.body.text/html-sanitized | string | | This is a test body text/html-sanitized |
action_result.data.\*.\_source.cve.nist.body.text/plain | string | | This is a test body text/plain |
action_result.data.\*.\_source.cve.nist.configurations.\*.cpe23_uri | string | | cpe:2.3:a:microsoft:office:2010:sp2:\*:\*:\*:\*:\*:\* |
action_result.data.\*.\_source.cve.nist.configurations.\*.version_end_including | string | | 2.3.34 |
action_result.data.\*.\_source.cve.nist.created_at.date-time | string | | 2016-11-10T06:59:00+00:00 |
action_result.data.\*.\_source.cve.nist.created_at.raw | string | | 2016-11-10T06:59Z |
action_result.data.\*.\_source.cve.nist.created_at.timestamp | numeric | | 1478761140 |
action_result.data.\*.\_source.cve.nist.cvssv2.access_complexity | string | | MEDIUM |
action_result.data.\*.\_source.cve.nist.cvssv2.access_vector | string | | NETWORK |
action_result.data.\*.\_source.cve.nist.cvssv2.authentication | string | | NONE |
action_result.data.\*.\_source.cve.nist.cvssv2.availability_impact | string | | COMPLETE |
action_result.data.\*.\_source.cve.nist.cvssv2.base_score | numeric | | 9.3 |
action_result.data.\*.\_source.cve.nist.cvssv2.confidentiality_impact | string | | COMPLETE |
action_result.data.\*.\_source.cve.nist.cvssv2.exploitability_score | numeric | | 8.6 |
action_result.data.\*.\_source.cve.nist.cvssv2.impact_score | numeric | | 10 |
action_result.data.\*.\_source.cve.nist.cvssv2.integrity_impact | string | | COMPLETE |
action_result.data.\*.\_source.cve.nist.cvssv2.severity | string | | HIGH |
action_result.data.\*.\_source.cve.nist.cvssv2.vector_string | string | | AV:N/AC:M/Au:N/C:C/I:C/A:C |
action_result.data.\*.\_source.cve.nist.cvssv3.attack_complexity | string | | LOW |
action_result.data.\*.\_source.cve.nist.cvssv3.attack_vector | string | | LOCAL |
action_result.data.\*.\_source.cve.nist.cvssv3.availability_impact | string | | HIGH |
action_result.data.\*.\_source.cve.nist.cvssv3.base_score | numeric | | 7.8 |
action_result.data.\*.\_source.cve.nist.cvssv3.confidentiality_impact | string | | HIGH |
action_result.data.\*.\_source.cve.nist.cvssv3.exploitability_score | numeric | | 1.8 |
action_result.data.\*.\_source.cve.nist.cvssv3.impact_score | numeric | | 5.9 |
action_result.data.\*.\_source.cve.nist.cvssv3.integrity_impact | string | | HIGH |
action_result.data.\*.\_source.cve.nist.cvssv3.privileges_required | string | | NONE |
action_result.data.\*.\_source.cve.nist.cvssv3.scope | string | | UNCHANGED |
action_result.data.\*.\_source.cve.nist.cvssv3.severity | string | | HIGH |
action_result.data.\*.\_source.cve.nist.cvssv3.user_interaction | string | | REQUIRED |
action_result.data.\*.\_source.cve.nist.cvssv3.vector_string | string | | CVSS:3.0/AV:L/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:H |
action_result.data.\*.\_source.cve.nist.fpid | string | | D_2yAYSFVaWo7aGXsGN9LQ |
action_result.data.\*.\_source.cve.nist.last_observed_at.date-time | string | | 2020-03-02T19:00:02+00:00 |
action_result.data.\*.\_source.cve.nist.last_observed_at.raw | string | | 2020-03-02T19:00:02 |
action_result.data.\*.\_source.cve.nist.last_observed_at.timestamp | numeric | | 1583175602 |
action_result.data.\*.\_source.cve.nist.native_id | string | | [28350, 'CVE-2016-7232'] |
action_result.data.\*.\_source.cve.nist.products.\*.product_name | string | | office |
action_result.data.\*.\_source.cve.nist.products.\*.vendor_name | string | | microsoft |
action_result.data.\*.\_source.cve.nist.references.\*.name | string | `url` | 94005 |
action_result.data.\*.\_source.cve.nist.references.\*.refsource | string | | BID |
action_result.data.\*.\_source.cve.nist.references.\*.tags | string | | VDB Entry |
action_result.data.\*.\_source.cve.nist.references.\*.url | string | `fp attribute value` `url` | http://www.testdomainlink.com/bid/94005 |
action_result.data.\*.\_source.cve.nist.site.base_uris | string | `url` | http://testdomainlink.com |
action_result.data.\*.\_source.cve.nist.site.basetypes | string | | site |
action_result.data.\*.\_source.cve.nist.site.created_at.date-time | string | | 2019-02-14T16:51:17.949358 |
action_result.data.\*.\_source.cve.nist.site.description.raw | string | | The NIST National Vulnerability Database provides a feed of known vulnerabilities (CVEs) and related information. |
action_result.data.\*.\_source.cve.nist.site.fpid | string | | IPp5rJZgXhuvZYu2PXMW3Q |
action_result.data.\*.\_source.cve.nist.site.site_type | string | | Site Type |
action_result.data.\*.\_source.cve.nist.site.source_uri | string | | testdomainlink.com |
action_result.data.\*.\_source.cve.nist.site.tags.\*.name | string | | Tag Name |
action_result.data.\*.\_source.cve.nist.site.title | string | | Test Site Title |
action_result.data.\*.\_source.cve.nist.site.updated_at.date-time | string | | 2019-02-14T16:51:18.230655 |
action_result.data.\*.\_source.cve.nist.title | string | | CVE-2016-7232 |
action_result.data.\*.\_source.cve.nist.updated_at.date-time | string | | 2018-10-12T22:14:00+00:00 |
action_result.data.\*.\_source.cve.nist.updated_at.raw | string | | 2018-10-12T22:14Z |
action_result.data.\*.\_source.cve.nist.updated_at.timestamp | numeric | | 1539382440 |
action_result.data.\*.\_source.cve.nist.vulnerability_types | string | | CWE-20 |
action_result.data.\*.\_source.cve.title | string | | CVE-2016-7232 |
action_result.data.\*.\_source.cvv | numeric | | 285 |
action_result.data.\*.\_source.deleted | boolean | | True False |
action_result.data.\*.\_source.disable_correlation | boolean | | True False |
action_result.data.\*.\_source.distribution | string | | 5 |
action_result.data.\*.\_source.domain | string | `fp attribute value` `domain` | domain.com |
action_result.data.\*.\_source.email | string | `fp attribute value` `email` | user.name@domain.com |
action_result.data.\*.\_source.email_domain | string | `fp attribute value` `domain` | testdomainlink.ax.xb |
action_result.data.\*.\_source.enrichments.domains | string | `fp attribute value` `domain` | change-or-fall-behind.html |
action_result.data.\*.\_source.enrichments.hashtags | string | | #HASHTAG |
action_result.data.\*.\_source.enrichments.language | string | | en |
action_result.data.\*.\_source.enrichments.links.\*.href | string | `url` | http://testdomainlink.com/test |
action_result.data.\*.\_source.enrichments.social_media_handles | string | | @69 |
action_result.data.\*.\_source.expiration | string | | 06/2024 |
action_result.data.\*.\_source.expires_at.date-time | string | | 1970-01-01T22:00:00+00:00 |
action_result.data.\*.\_source.expires_at.raw | string | | Never |
action_result.data.\*.\_source.expires_at.timestamp | numeric | | 180 |
action_result.data.\*.\_source.extraction_id | string | | tXfm1PGDXRqTmcB57L9-eA |
action_result.data.\*.\_source.extraction_record_id | string | | dhaaFUx8X4G229qg67jrtA |
action_result.data.\*.\_source.first_observed_at.date-time | string | | 2019-05-24T18:11:15Z |
action_result.data.\*.\_source.first_observed_at.raw | string | | 2019-05-24T18:11:15Z |
action_result.data.\*.\_source.first_observed_at.timestamp | numeric | | 1558721475 |
action_result.data.\*.\_source.fpid | string | | 8dKFsRoeV0mP8zOY1uYcLQ |
action_result.data.\*.\_source.has_credit_card | boolean | | True False |
action_result.data.\*.\_source.has_email_access | boolean | | True False |
action_result.data.\*._source.header_.collected_fpid | string | | pXpjocaLQ8u72VAtHZXrKQ |
action_result.data.\*._source.header_.indexed_at | numeric | | 1571442668 |
action_result.data.\*._source.header_.ingested_at | numeric | | 1519149743 |
action_result.data.\*._source.header_.is_visible | boolean | | True False |
action_result.data.\*._source.header_.observed_at | numeric | | 1552989386 |
action_result.data.\*._source.header_.source | string | `url` | https://testdomainlink.org/thread/1234.json |
action_result.data.\*._source.header_.source_fpid | string | | bGWFKCynXQSmEgWy4nPYtQ |
action_result.data.\*._source.header_.source_keyword | string | | pastebin 4chan |
action_result.data.\*._source.header_.source_uri | string | | https://testdomainlink.com/posts/1234 |
action_result.data.\*.\_source.id | string | | 33925 |
action_result.data.\*.\_source.is_cvv_available | boolean | | True False |
action_result.data.\*.\_source.is_deleted | boolean | | True False |
action_result.data.\*.\_source.is_edited | boolean | | True False |
action_result.data.\*.\_source.is_fresh | boolean | | True False |
action_result.data.\*.\_source.is_media | boolean | | True False |
action_result.data.\*.\_source.is_pin_available | boolean | | True False |
action_result.data.\*.\_source.is_track1_available | boolean | | True False |
action_result.data.\*.\_source.is_verified | boolean | | True False |
action_result.data.\*.\_source.is_verified_by_visa | boolean | | True False |
action_result.data.\*.\_source.last4 | string | | 442 |
action_result.data.\*.\_source.last_checked_at.date-time | string | | 2020-02-29T00:00:00+00:00 |
action_result.data.\*.\_source.last_checked_at.raw | string | | 29-02-2020 |
action_result.data.\*.\_source.last_checked_at.timestamp | numeric | | 1582934400 |
action_result.data.\*.\_source.last_observed_at.date-time | string | | 2019-10-18T23:51:05+00:00 |
action_result.data.\*.\_source.last_observed_at.raw | string | | 1571442665.596432 |
action_result.data.\*.\_source.last_observed_at.timestamp | numeric | | 1571442665 |
action_result.data.\*.\_source.legacy_fpid | string | | Rh_TO57eVzutV_uAW-kcGw |
action_result.data.\*.\_source.level | string | | Platinum |
action_result.data.\*.\_source.location.country.abbreviation | string | | US |
action_result.data.\*.\_source.location.country.full_name | string | | Country Name |
action_result.data.\*.\_source.media.author | string | `url` | Author |
action_result.data.\*.\_source.media.basetypes | string | | media |
action_result.data.\*.\_source.media.body.raw | string | | https://testdomainlink.com/test |
action_result.data.\*.\_source.media.created_at.date-time | string | | 2018-12-30T10:26:04+00:00 |
action_result.data.\*.\_source.media.created_at.raw | string | | 2018-12-30 10:26:04+00:00 |
action_result.data.\*.\_source.media.created_at.timestamp | numeric | | 1546165564 |
action_result.data.\*.\_source.media.description | string | | description |
action_result.data.\*.\_source.media.filename | string | | test.mp3 |
action_result.data.\*.\_source.media.fpid | string | | BdSDO5vKV2StpBbHvfJIKQ |
action_result.data.\*.\_source.media.last_observed_at.date-time | string | | 2019-01-08T14:37:36+00:00 |
action_result.data.\*.\_source.media.last_observed_at.raw | string | | 1546958256 |
action_result.data.\*.\_source.media.last_observed_at.timestamp | numeric | | 1546958256 |
action_result.data.\*.\_source.media.mime_type | string | | image/webp |
action_result.data.\*.\_source.media.native_id | string | | unknown_id |
action_result.data.\*.\_source.media.phash | string | | c03e3f553fc29ac0 |
action_result.data.\*.\_source.media.sha1 | string | `fp attribute value` `sha1` | c4d73272dccaa140f3001bb46043439315de733a |
action_result.data.\*.\_source.media.site.created_at.date-time | string | | 2016-10-24T14:04:35 |
action_result.data.\*.\_source.media.site.description.raw | string | | The Test Site Description |
action_result.data.\*.\_source.media.site.fpid | string | | PKA2rDMoWSCQk2uFD_gzaA |
action_result.data.\*.\_source.media.site.site_type | string | | Site Type |
action_result.data.\*.\_source.media.site.source_uri | string | | web.testdomainlink.org |
action_result.data.\*.\_source.media.site.tags.\*.name | string | | Tag Name |
action_result.data.\*.\_source.media.site.tags.\*.parent_tag.name | string | | Parent Tag Name |
action_result.data.\*.\_source.media.site.title | string | | Site Title |
action_result.data.\*.\_source.media.site.updated_at.date-time | string | | 2018-12-18T22:03:20 |
action_result.data.\*.\_source.media.size | numeric | | 13824 |
action_result.data.\*.\_source.media.source_uri | string | | urn:fp:resource:qualified:conversation:chat:telegram:media:unknown_id |
action_result.data.\*.\_source.media.storage_uri | string | | xs://testdomainlink/ab123.jpg |
action_result.data.\*.\_source.media.title | string | | title |
action_result.data.\*.\_source.media.type | string | | document |
action_result.data.\*.\_source.message_count.count | numeric | | 56765 |
action_result.data.\*.\_source.message_count.first_resource.container.fpid | string | | oCV-K3_yU2KPmdvyNhw4HA |
action_result.data.\*.\_source.message_count.first_resource.created_at.date-time | string | | 2017-01-20T17:46:08+00:00 |
action_result.data.\*.\_source.message_count.first_resource.first_observed_at.date-time | string | | 2018-04-22T12:18:56.127552+00:00 |
action_result.data.\*.\_source.message_count.first_resource.fpid | string | | gWSgwUHzV6exZYPVd-prsA |
action_result.data.\*.\_source.message_count.first_resource.site_actor.fpid | string | | KHXTQDjDWe6qk2t7cZGYbw |
action_result.data.\*.\_source.message_count.first_resource.site_actor.names.handle | string | | Emu |
action_result.data.\*.\_source.message_count.first_resource.site_actor.native_id | string | | 633735-emu |
action_result.data.\*.\_source.message_count.last_resource.container.container.first_observed_at.date-time | string | | 2015-11-17T18:59:58.384479+00:00 |
action_result.data.\*.\_source.message_count.last_resource.container.container.first_observed_at.raw | string | | 2015-11-17 18:59:58.384479+00:00 |
action_result.data.\*.\_source.message_count.last_resource.container.container.first_observed_at.timestamp | numeric | | 1447786798 |
action_result.data.\*.\_source.message_count.last_resource.container.container.fpid | string | | 3tFp3L-qVEaiS3w60OY5cg |
action_result.data.\*.\_source.message_count.last_resource.container.container.last_observed_at.date-time | string | | 2018-09-27T06:14:27.770185+00:00 |
action_result.data.\*.\_source.message_count.last_resource.container.container.last_observed_at.raw | string | | 2018-09-27 06:14:27.770185+00:00 |
action_result.data.\*.\_source.message_count.last_resource.container.container.last_observed_at.timestamp | numeric | | 1538028867 |
action_result.data.\*.\_source.message_count.last_resource.container.container.legacy_fpid | string | | LL09S4ejV1KIyEol2WulKg |
action_result.data.\*.\_source.message_count.last_resource.container.container.native_id | string | | 66-example |
action_result.data.\*.\_source.message_count.last_resource.container.container.source_uri | string | | https://www.testdomainlink.com/test |
action_result.data.\*.\_source.message_count.last_resource.container.container.title | string | | Test Title |
action_result.data.\*.\_source.message_count.last_resource.container.fpid | string | | oCV-K3_yU2KPmdvyNhw4HA |
action_result.data.\*.\_source.message_count.last_resource.container.legacy_fpid | string | | h0eTQng6VsOj96P53w4siA |
action_result.data.\*.\_source.message_count.last_resource.container.native_id | string | | 215544-2440x-oce-accounts-emu-style |
action_result.data.\*.\_source.message_count.last_resource.container.source_uri | string | | https://www.testdomainlink.com/test |
action_result.data.\*.\_source.message_count.last_resource.container.title | string | | 2440x OCE accounts, Emu style |
action_result.data.\*.\_source.message_count.last_resource.created_at.date-time | string | | 2017-10-22T08:34:39+00:00 |
action_result.data.\*.\_source.message_count.last_resource.first_observed_at.date-time | string | | 2018-04-22T12:21:44.708966+00:00 |
action_result.data.\*.\_source.message_count.last_resource.fpid | string | | dp8jDkN0WOCq0cSck8syIA |
action_result.data.\*.\_source.message_count.last_resource.site.created_at.date-time | string | | 2016-11-15T17:57:00 |
action_result.data.\*.\_source.message_count.last_resource.site.description.raw | string | | This is an example description |
action_result.data.\*.\_source.message_count.last_resource.site.fpid | string | | vPX7DFoGWC-AOiA5qvBzlA |
action_result.data.\*.\_source.message_count.last_resource.site.legacy_fpid | string | | D11tFq1XWKyAyxWTwScsHQ |
action_result.data.\*.\_source.message_count.last_resource.site.site_type | string | | Forum |
action_result.data.\*.\_source.message_count.last_resource.site.source_uri | string | | www.testdomainlink.com |
action_result.data.\*.\_source.message_count.last_resource.site.tags.\*.name | string | | Tag Name |
action_result.data.\*.\_source.message_count.last_resource.site.tags.\*.parent_tag.name | string | | Parent Tag Name |
action_result.data.\*.\_source.message_count.last_resource.site.title | string | | Site Title |
action_result.data.\*.\_source.message_count.last_resource.site.updated_at.date-time | string | | 2018-09-21T23:57:26 |
action_result.data.\*.\_source.message_count.last_resource.site_actor.fpid | string | | 5lauqgEyXjmm-EZbwSOUvQ |
action_result.data.\*.\_source.message_count.last_resource.site_actor.names.handle | string | | mantq |
action_result.data.\*.\_source.message_count.last_resource.site_actor.native_id | string | | 1195854-mantq |
action_result.data.\*.\_source.mitre.basetypes | string | | mitre |
action_result.data.\*.\_source.mitre.body.enrichments.cves | string | | CVE-2019-14743 |
action_result.data.\*.\_source.mitre.body.enrichments.links.\*.href | string | `url` `ip` | https://schemas.testdomainlink.com/2017/resource/collections/database_row.json |
action_result.data.\*.\_source.mitre.body.raw | string | | This is a test body |
action_result.data.\*.\_source.mitre.body.text/html-sanitized | string | | This is a test body text/html-sanitized |
action_result.data.\*.\_source.mitre.body.text/plain | string | | This is a test body test/plain |
action_result.data.\*.\_source.mitre.created_at.date-time | string | | 2019-04-03T00:00:00+00:00 |
action_result.data.\*.\_source.mitre.created_at.raw | string | | 20190403 |
action_result.data.\*.\_source.mitre.created_at.timestamp | numeric | | 1554249600 |
action_result.data.\*.\_source.mitre.fpid | string | | DoJqrFGjX7GZL3GzCIKiZw |
action_result.data.\*.\_source.mitre.last_observed_at.date-time | string | | 2020-03-02T19:00:02+00:00 |
action_result.data.\*.\_source.mitre.last_observed_at.raw | string | | 2020-03-02T19:00:02 |
action_result.data.\*.\_source.mitre.last_observed_at.timestamp | numeric | | 1583175602 |
action_result.data.\*.\_source.mitre.native_id | string | | [28355, 'CVE-2019-10802'] |
action_result.data.\*.\_source.mitre.phase | string | | Assigned (20190403) |
action_result.data.\*.\_source.mitre.site.base_uris | string | `url` | http://mitre.org |
action_result.data.\*.\_source.mitre.site.basetypes | string | | site |
action_result.data.\*.\_source.mitre.site.created_at.date-time | string | | 2019-02-14T17:21:27.064334 |
action_result.data.\*.\_source.mitre.site.description.raw | string | | This is a test description |
action_result.data.\*.\_source.mitre.site.fpid | string | | YJKOYduNWE2PVi1WiTEMOg |
action_result.data.\*.\_source.mitre.site.site_type | string | | Site Type |
action_result.data.\*.\_source.mitre.site.source_uri | string | | testdomainlink.org |
action_result.data.\*.\_source.mitre.site.tags.\*.name | string | | Tag Name |
action_result.data.\*.\_source.mitre.site.tags.\*.parent_tag.name | string | | Parent Tag Name |
action_result.data.\*.\_source.mitre.site.title | string | | Site Title |
action_result.data.\*.\_source.mitre.site.updated_at.date-time | string | | 2019-02-14T17:26:05.741343 |
action_result.data.\*.\_source.mitre.status | string | | Candidate |
action_result.data.\*.\_source.mitre.title | string | | CVE-2019-10802 |
action_result.data.\*.\_source.native_id | string | `md5` | 378494454 [28356, 'CVE-2016-7232'] |
action_result.data.\*.\_source.new_records | numeric | | 0 |
action_result.data.\*.\_source.nist.assigner | string | `email` | cve@testdomainlink.org |
action_result.data.\*.\_source.nist.basetypes | string | | nist |
action_result.data.\*.\_source.nist.body.enrichments.cves | string | | CVE-2019-14743 |
action_result.data.\*.\_source.nist.body.enrichments.links.\*.href | string | `url` `ip` | https://schemas.testdomainlink.com/2017/resource/collections/database_row.json |
action_result.data.\*.\_source.nist.body.raw | string | | This is a test body |
action_result.data.\*.\_source.nist.body.text/html-sanitized | string | | This is a test body test/html-sanitized |
action_result.data.\*.\_source.nist.body.text/plain | string | | This is a test body test/plain |
action_result.data.\*.\_source.nist.configurations.\*.cpe23_uri | string | | cpe:2.3:o:grandstream:gwn7610_firmware:\*:\*:\*:\*:\*:\*:\*:\* |
action_result.data.\*.\_source.nist.configurations.\*.version_end_including | string | `ip` | 11.2 |
action_result.data.\*.\_source.nist.created_at.date-time | string | | 2019-03-30T17:29:00+00:00 |
action_result.data.\*.\_source.nist.created_at.raw | string | | 2019-03-30T17:29Z |
action_result.data.\*.\_source.nist.created_at.timestamp | numeric | | 1553966940 |
action_result.data.\*.\_source.nist.cvssv2.access_complexity | string | | LOW |
action_result.data.\*.\_source.nist.cvssv2.access_vector | string | | NETWORK |
action_result.data.\*.\_source.nist.cvssv2.authentication | string | | SINGLE |
action_result.data.\*.\_source.nist.cvssv2.availability_impact | string | | NONE |
action_result.data.\*.\_source.nist.cvssv2.base_score | numeric | | 4 |
action_result.data.\*.\_source.nist.cvssv2.confidentiality_impact | string | | PARTIAL |
action_result.data.\*.\_source.nist.cvssv2.exploitability_score | numeric | | 8 |
action_result.data.\*.\_source.nist.cvssv2.impact_score | numeric | | 2.9 |
action_result.data.\*.\_source.nist.cvssv2.integrity_impact | string | | NONE |
action_result.data.\*.\_source.nist.cvssv2.severity | string | | MEDIUM |
action_result.data.\*.\_source.nist.cvssv2.vector_string | string | | AV:N/AC:L/Au:S/C:P/I:N/A:N |
action_result.data.\*.\_source.nist.cvssv3.attack_complexity | string | | LOW |
action_result.data.\*.\_source.nist.cvssv3.attack_vector | string | | NETWORK |
action_result.data.\*.\_source.nist.cvssv3.availability_impact | string | | NONE |
action_result.data.\*.\_source.nist.cvssv3.base_score | numeric | | 6.5 |
action_result.data.\*.\_source.nist.cvssv3.confidentiality_impact | string | | HIGH |
action_result.data.\*.\_source.nist.cvssv3.exploitability_score | numeric | | 2.8 |
action_result.data.\*.\_source.nist.cvssv3.impact_score | numeric | | 3.6 |
action_result.data.\*.\_source.nist.cvssv3.integrity_impact | string | | NONE |
action_result.data.\*.\_source.nist.cvssv3.privileges_required | string | | LOW |
action_result.data.\*.\_source.nist.cvssv3.scope | string | | UNCHANGED |
action_result.data.\*.\_source.nist.cvssv3.severity | string | | MEDIUM |
action_result.data.\*.\_source.nist.cvssv3.user_interaction | string | | NONE |
action_result.data.\*.\_source.nist.cvssv3.vector_string | string | | CVSS:3.0/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N |
action_result.data.\*.\_source.nist.fpid | string | | O42mIpMpVIycfzwmBkoPCA |
action_result.data.\*.\_source.nist.last_observed_at.date-time | string | | 2020-02-24T19:00:02+00:00 |
action_result.data.\*.\_source.nist.last_observed_at.raw | string | | 2020-02-24T19:00:02 |
action_result.data.\*.\_source.nist.last_observed_at.timestamp | numeric | | 1582570802 |
action_result.data.\*.\_source.nist.native_id | string | | [28350, 'CVE-2019-10657'] |
action_result.data.\*.\_source.nist.products.\*.product_name | string | | gwn7000_firmware |
action_result.data.\*.\_source.nist.products.\*.vendor_name | string | | testname |
action_result.data.\*.\_source.nist.references.\*.name | string | `url` | https://testdomainlink.com/test |
action_result.data.\*.\_source.nist.references.\*.refsource | string | | MISC |
action_result.data.\*.\_source.nist.references.\*.tags | string | | Refernece Tags |
action_result.data.\*.\_source.nist.references.\*.url | string | `fp attribute value` `url` | https://testdomainlink.com/test |
action_result.data.\*.\_source.nist.site.base_uris | string | `url` | http://testdomainlink.com |
action_result.data.\*.\_source.nist.site.basetypes | string | | site |
action_result.data.\*.\_source.nist.site.created_at.date-time | string | | 2019-02-14T16:51:17.949358 |
action_result.data.\*.\_source.nist.site.description.raw | string | | This is a test description. |
action_result.data.\*.\_source.nist.site.fpid | string | | IPp5rJZgXhuvZYu2PXMW3Q |
action_result.data.\*.\_source.nist.site.site_type | string | | Site Type |
action_result.data.\*.\_source.nist.site.source_uri | string | | testdomainlink.com |
action_result.data.\*.\_source.nist.site.tags.\*.name | string | | Tag Name |
action_result.data.\*.\_source.nist.site.title | string | | Site Title |
action_result.data.\*.\_source.nist.site.updated_at.date-time | string | | 2019-02-14T16:51:18.230655 |
action_result.data.\*.\_source.nist.title | string | | CVE-2019-10657 |
action_result.data.\*.\_source.nist.updated_at.date-time | string | | 2019-04-12T18:29:00+00:00 |
action_result.data.\*.\_source.nist.updated_at.raw | string | | 2019-04-12T18:29Z |
action_result.data.\*.\_source.nist.updated_at.timestamp | numeric | | 1555093740 |
action_result.data.\*.\_source.nist.vulnerability_types | string | | CWE-264 |
action_result.data.\*.\_source.num_replies | numeric | | 1 |
action_result.data.\*.\_source.object_id | string | | 0 |
action_result.data.\*.\_source.object_relation | string | | |
action_result.data.\*.\_source.old_records | numeric | | 0 |
action_result.data.\*.\_source.parent_comment.native_id | string | | 209360561 |
action_result.data.\*.\_source.parent_comment.site.behavior | string | | replace |
action_result.data.\*.\_source.parent_comment.site.href | string | | urn:fp:type:resource.qualified.site:Ra2dBSXnXjKqoLS7wJPWgw |
action_result.data.\*.\_source.parent_comment.site.target | string | | $.site |
action_result.data.\*.\_source.parent_comment.type | string | | parent_comment |
action_result.data.\*.\_source.parent_message.basetypes | string | | message |
action_result.data.\*.\_source.parent_message.fpid | string | | 1IIVq-rPXIG7LdX3FFauuw |
action_result.data.\*.\_source.parent_message.native_id | string | `url` | etrmp5y |
action_result.data.\*.\_source.parent_message.num_replies | numeric | | 3 |
action_result.data.\*.\_source.parent_message.site_actor.avatar_uri.href | string | | https://testdomainlink.com/media/user/ab-1234.jpeg |
action_result.data.\*.\_source.parent_message.site_actor.fpid | string | | e7xy1LSvVHaDEj_jTDmL0g |
action_result.data.\*.\_source.parent_message.site_actor.names.handle | string | | Test Handle |
action_result.data.\*.\_source.parent_message.site_actor.native_id | string | | text1234 |
action_result.data.\*.\_source.parent_message.site_actor.url | string | `fp attribute value` `url` | https://testdomainlink.com/test1234 |
action_result.data.\*.\_source.parent_message.type | string | | parent_message |
action_result.data.\*.\_source.password | string | | ya29.GlsrBvzMY9_HL-d7nCA0jlgC0cFUnTtpzrHU94xGiY0OM_sS-0nExZ9y-xWMapu7QKmAml3xkbi4wqE9e58D7XoZ8rF8qYbDNTTEqX4B7X1DMIBzmhT2LcLHpfq4 |
action_result.data.\*.\_source.password_complexity.has_lowercase | boolean | | True False |
action_result.data.\*.\_source.password_complexity.has_number | boolean | | True False |
action_result.data.\*.\_source.password_complexity.has_symbol | boolean | | True False |
action_result.data.\*.\_source.password_complexity.has_uppercase | boolean | | True False |
action_result.data.\*.\_source.password_complexity.length | numeric | | 129 |
action_result.data.\*.\_source.password_complexity.probable_hash_algorithms | string | | bcrypt |
action_result.data.\*.\_source.payment_method | string | | credit |
action_result.data.\*.\_source.previous_message | string | | 206826987 |
action_result.data.\*.\_source.prices.\*.currency.abbreviation | string | | $ |
action_result.data.\*.\_source.prices.\*.currency.raw | string | | $ |
action_result.data.\*.\_source.prices.\*.raw | string | | $5 300 EUR (0.038673 BTC) |
action_result.data.\*.\_source.prices.\*.value | numeric | | 3 15 |
action_result.data.\*.\_source.quantity.available.raw | string | | more than 25 pcs in stock |
action_result.data.\*.\_source.quantity.sold.raw | string | | 20 sold since May 7, 2015 |
action_result.data.\*.\_source.raw_href | string | `url` | http://testdomainlink.com/ab1cd234 |
action_result.data.\*.\_source.reputation.number_of_downvotes | numeric | | 4 |
action_result.data.\*.\_source.reputation.number_of_upvotes | numeric | | 5 |
action_result.data.\*.\_source.reputation.score | string | | 1 |
action_result.data.\*.\_source.resource_fpid | string | | cVDJlMvXVYeuBT_QTBe_Hg |
action_result.data.\*.\_source.room_count.count | numeric | | 10 |
action_result.data.\*.\_source.service_code | numeric | | 201 |
action_result.data.\*.\_source.sharing_group_id | string | | 0 |
action_result.data.\*.\_source.shipping.\*.raw | string | | Test Shipping ( Croatia, Australia, New Zealand, Cambodia, South Africa) |
action_result.data.\*.\_source.ships_from | string | | Finland |
action_result.data.\*.\_source.ships_to | string | | Worldwide |
action_result.data.\*.\_source.site.base_uris | string | `url` | https://testdomainlink.link |
action_result.data.\*.\_source.site.basetypes | string | | site |
action_result.data.\*.\_source.site.created_at.date-time | string | | 2016-10-19T20:57:50.738121 |
action_result.data.\*.\_source.site.description.raw | string | | This is an example description |
action_result.data.\*.\_source.site.fpid | string | | EGxvMDp8VBeqjYc0jkKbeg |
action_result.data.\*.\_source.site.is_deleted | boolean | | True False |
action_result.data.\*.\_source.site.legacy_fpid | string | | HOJ9wN7rXFm6HaWp-xGcow |
action_result.data.\*.\_source.site.site_type | string | | Card Shop |
action_result.data.\*.\_source.site.source_uri | string | | testdomainlink.com |
action_result.data.\*.\_source.site.tags.\*.name | string | | Carding Security |
action_result.data.\*.\_source.site.tags.\*.parent_tag.name | string | | Parent Tag Name |
action_result.data.\*.\_source.site.title | string | | Site Title |
action_result.data.\*.\_source.site.type | string | | test service |
action_result.data.\*.\_source.site.updated_at.date-time | string | | 2019-09-24T17:54:21.503860 2019-05-28T15:25:06 |
action_result.data.\*.\_source.site_actor.\_header.collected_fpid | string | | vreB-nCASfukTGsj6OdU_A |
action_result.data.\*.\_source.site_actor.\_header.observed_at | numeric | | 1575671142 |
action_result.data.\*.\_source.site_actor.activity.name | string | | Custom Status |
action_result.data.\*.\_source.site_actor.activity.type | numeric | | 4 |
action_result.data.\*.\_source.site_actor.avatar_uri.href | string | `url` | https://testdomainlink.com/img/example123.gif |
action_result.data.\*.\_source.site_actor.avatar_url | string | | https://testdomainlink.com/avatars/test/123ab.webp?size=1024 |
action_result.data.\*.\_source.site_actor.basetypes | string | | site_actor user |
action_result.data.\*.\_source.site_actor.body.enrichments.language | string | | en |
action_result.data.\*.\_source.site_actor.body.enrichments.links.\*.href | string | | https://testdomainlink.com/test |
action_result.data.\*.\_source.site_actor.body.raw | string | | <p>"This is a test body"<br /><br /><a href="https://testdomainlink.com/test" class="mention hashtag" rel="tag">#<span>Test</span></a></p> |
action_result.data.\*.\_source.site_actor.body.text/html+sanitized | string | | <p>"This is a test body text/html+sanitized"<br> (https://testdomainlink.com/test) #Test</p> |
action_result.data.\*.\_source.site_actor.body.text/plain | string | | "This is a test body test/plain" #Test |
action_result.data.\*.\_source.site_actor.bot | boolean | | True False |
action_result.data.\*.\_source.site_actor.comment_reputation.number_of_upvotes | numeric | | 1071 |
action_result.data.\*.\_source.site_actor.created_at.date-time | string | | 2016-06-03T00:00:00+00:00 |
action_result.data.\*.\_source.site_actor.created_at.raw | string | | 2016-06-03 00:00:00+00:00 |
action_result.data.\*.\_source.site_actor.created_at.timestamp | numeric | | 1464912000 |
action_result.data.\*.\_source.site_actor.description | string | | Test Description |
action_result.data.\*.\_source.site_actor.discriminator | string | | 9044 |
action_result.data.\*.\_source.site_actor.enrichments.language | string | | en |
action_result.data.\*.\_source.site_actor.enrichments.links.\*.href | string | | https://www.testdomainlink.com/test |
action_result.data.\*.\_source.site_actor.first_name | string | | first name |
action_result.data.\*.\_source.site_actor.first_observed_at.date-time | string | | 2014-04-22T21:15:38.417619+00:00 |
action_result.data.\*.\_source.site_actor.first_observed_at.raw | string | | 2014-04-22 21:15:38.417619+00:00 |
action_result.data.\*.\_source.site_actor.first_observed_at.timestamp | numeric | | 1398201338 |
action_result.data.\*.\_source.site_actor.flair.flair_text | string | | flair text |
action_result.data.\*.\_source.site_actor.fpid | string | | QSRLfKc-VJaqaSIcgAUNiA |
action_result.data.\*.\_source.site_actor.is_admin | boolean | | True False |
action_result.data.\*.\_source.site_actor.is_deleted | boolean | | True False |
action_result.data.\*.\_source.site_actor.is_donor | boolean | | True False |
action_result.data.\*.\_source.site_actor.is_investor | boolean | | True False |
action_result.data.\*.\_source.site_actor.is_premium | boolean | | True False |
action_result.data.\*.\_source.site_actor.is_private | boolean | | True False |
action_result.data.\*.\_source.site_actor.is_pro | boolean | | True False |
action_result.data.\*.\_source.site_actor.is_verified | boolean | | True False |
action_result.data.\*.\_source.site_actor.joined_at.date-time | string | | 2019-12-07T18:49:28.780462+00:00 |
action_result.data.\*.\_source.site_actor.joined_at.raw | string | | 1575744568.780462 |
action_result.data.\*.\_source.site_actor.joined_at.timestamp | numeric | | 1575744568 |
action_result.data.\*.\_source.site_actor.last_active_at.date-time | string | | 2019-07-31T03:23:09+00:00 |
action_result.data.\*.\_source.site_actor.last_active_at.raw | string | | 2019-07-31 03:23:09+00:00 |
action_result.data.\*.\_source.site_actor.last_active_at.timestamp | numeric | | 1564543389 |
action_result.data.\*.\_source.site_actor.last_name | string | | Test Name |
action_result.data.\*.\_source.site_actor.last_observed_at.date-time | string | | 2019-07-15T02:19:23+00:00 |
action_result.data.\*.\_source.site_actor.last_observed_at.raw | string | | 1563157163.299181 |
action_result.data.\*.\_source.site_actor.last_observed_at.timestamp | numeric | | 1563157163 |
action_result.data.\*.\_source.site_actor.legacy_fpid | string | | 1jLzGo5DX5qNUT5y1dFXrQ |
action_result.data.\*.\_source.site_actor.name | string | | name |
action_result.data.\*.\_source.site_actor.names.aliases | string | | aliasname |
action_result.data.\*.\_source.site_actor.names.handle | string | | name |
action_result.data.\*.\_source.site_actor.native_id | string | `url` `md5` | testid |
action_result.data.\*.\_source.site_actor.nick | string | | nick name |
action_result.data.\*.\_source.site_actor.number_following | numeric | | 1751 |
action_result.data.\*.\_source.site_actor.number_of_followers | numeric | | 3223 |
action_result.data.\*.\_source.site_actor.number_of_messages | numeric | | 33486 |
action_result.data.\*.\_source.site_actor.pgp_key_public | string | | -----BEGIN PGP PUBLIC KEY BLOCK----- PGPxKeyxPublic -----END PGP PUBLIC KEY BLOCK----- |
action_result.data.\*.\_source.site_actor.post_reputation.number_of_upvotes | numeric | | 1 |
action_result.data.\*.\_source.site_actor.reputation.count_ratings | string | | 50 |
action_result.data.\*.\_source.site_actor.reputation.negative_feedback | string | | -1 |
action_result.data.\*.\_source.site_actor.reputation.positive_feedback | string | | 0 |
action_result.data.\*.\_source.site_actor.reputation.score | string | | 100 |
action_result.data.\*.\_source.site_actor.reputation.site_actor_rating | string | | Level 1 |
action_result.data.\*.\_source.site_actor.roles.\*.id | string | | 276516314170916864 |
action_result.data.\*.\_source.site_actor.roles.\*.name | string | | @everyone |
action_result.data.\*.\_source.site_actor.sales.total_transactions | numeric | | 5000 |
action_result.data.\*.\_source.site_actor.server.created_at.date-time | string | | 2017-02-02T00:57:06.723000+00:00 |
action_result.data.\*.\_source.site_actor.server.created_at.raw | string | | 1485997026.723 |
action_result.data.\*.\_source.site_actor.server.created_at.timestamp | numeric | | 1485997026 |
action_result.data.\*.\_source.site_actor.server.fpid | string | | 1xVN9lLjUPC7SMwbLv_0RQ |
action_result.data.\*.\_source.site_actor.server.icon_url | string | | https://testdomainlink.com/icons/1234.jpg |
action_result.data.\*.\_source.site_actor.server.is_deleted | boolean | | True False |
action_result.data.\*.\_source.site_actor.server.last_observed_at.date-time | string | | 2020-01-08T17:42:10.080020+00:00 |
action_result.data.\*.\_source.site_actor.server.last_observed_at.raw | string | | 1578505330.08002 |
action_result.data.\*.\_source.site_actor.server.last_observed_at.timestamp | numeric | | 1578505330 |
action_result.data.\*.\_source.site_actor.server.name | string | | Super Club Penguin |
action_result.data.\*.\_source.site_actor.server.native_id | string | | 276516314170916864 |
action_result.data.\*.\_source.site_actor.server.region | string | | us_central |
action_result.data.\*.\_source.site_actor.server.server_owner.id | string | | 272944155205042177 |
action_result.data.\*.\_source.site_actor.server.server_owner.username | string | | Mate#5386 |
action_result.data.\*.\_source.site_actor.server.site.fpid | string | | 6-JEBtwCWXmpUgPo1ZtoRQ |
action_result.data.\*.\_source.site_actor.server.site.is_deleted | boolean | | True False |
action_result.data.\*.\_source.site_actor.server.site.site_type | string | | Site Type |
action_result.data.\*.\_source.site_actor.server.site.source_uri | string | | urn:fp:resource:qualified:site:27891 |
action_result.data.\*.\_source.site_actor.server.site.title | string | | Site Title |
action_result.data.\*.\_source.site_actor.server.source_uri | string | | urn:fp:resource:qualified:conversation:chat:discord:server:276516314170916864 |
action_result.data.\*.\_source.site_actor.server.title | string | | Server Title |
action_result.data.\*.\_source.site_actor.server.verification_level | string | | 4 |
action_result.data.\*.\_source.site_actor.site_actor.\_header.collected_fpid | string | | RK6nDJJbRAmmInesId8lqA |
action_result.data.\*.\_source.site_actor.site_actor.\_header.observed_at | numeric | | 1559420203 |
action_result.data.\*.\_source.site_actor.site_actor.avatar_uri.href | string | | https://testdomainlink.com/media/user/1234.jpg |
action_result.data.\*.\_source.site_actor.site_actor.body.enrichments.language | string | | en |
action_result.data.\*.\_source.site_actor.site_actor.body.raw | string | | This is a test body |
action_result.data.\*.\_source.site_actor.site_actor.body.text/html+sanitized | string | | This is a test body text/html+sanitized |
action_result.data.\*.\_source.site_actor.site_actor.body.text/plain | string | | This is a test body text/plain |
action_result.data.\*.\_source.site_actor.site_actor.created_at.date-time | string | | 2016-12-01T00:00:00+00:00 |
action_result.data.\*.\_source.site_actor.site_actor.created_at.raw | string | | December 2016 |
action_result.data.\*.\_source.site_actor.site_actor.created_at.timestamp | numeric | | 1480550400 |
action_result.data.\*.\_source.site_actor.site_actor.fpid | string | | eE9alofZWZuS0Ef5HiirIA |
action_result.data.\*.\_source.site_actor.site_actor.is_donor | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.is_investor | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.is_premium | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.is_private | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.is_pro | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.is_verified | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.names.handle | string | | dankemp |
action_result.data.\*.\_source.site_actor.site_actor.native_id | string | | dankemp |
action_result.data.\*.\_source.site_actor.site_actor.number_following | numeric | | 2304 |
action_result.data.\*.\_source.site_actor.site_actor.number_of_followers | numeric | | 1703 |
action_result.data.\*.\_source.site_actor.site_actor.number_of_messages | numeric | | 9610 |
action_result.data.\*.\_source.site_actor.site_actor.site.created_at.date-time | string | | 2018-05-03T13:35:05 |
action_result.data.\*.\_source.site_actor.site_actor.site.description.raw | string | | This is an example description |
action_result.data.\*.\_source.site_actor.site_actor.site.fpid | string | | \_tI5K2qyXYeqD3rUhkxMzg |
action_result.data.\*.\_source.site_actor.site_actor.site.site_type | string | | Social Network |
action_result.data.\*.\_source.site_actor.site_actor.site.source_uri | string | | testdomainlink.com |
action_result.data.\*.\_source.site_actor.site_actor.site.tags.\*.name | string | | Tag Name |
action_result.data.\*.\_source.site_actor.site_actor.site.tags.\*.parent_tag.name | string | | Parent Tag Name |
action_result.data.\*.\_source.site_actor.site_actor.site.title | string | | Site Title |
action_result.data.\*.\_source.site_actor.site_actor.site.updated_at.date-time | string | | 2019-03-27T15:59:59 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.\_header.collected_fpid | string | | RK6nDJJbRAmmInesId8lqA |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.\_header.observed_at | numeric | | 1559420203.347195 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.avatar_uri.href | string | | https://testdomainlink.com/media/user/1234.jpg |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.body.enrichments.language | string | | en |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.body.raw | string | | This is a test body |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.body.text/html+sanitized | string | | This is a test body text/html+sanitized |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.body.text/plain | string | | This is a test body text/plain |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.created_at.date-time | string | | 2016-12-01T00:00:00+00:00 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.created_at.raw | string | | December 2016 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.created_at.timestamp | numeric | | 1480550400 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.fpid | string | | eE9alofZWZuS0Ef5HiirIA |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.is_donor | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.is_investor | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.is_premium | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.is_private | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.is_pro | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.is_verified | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.names.handle | string | | dankemp |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.native_id | string | | dankemp |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.number_following | numeric | | 2304 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.number_of_followers | numeric | | 1703 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.number_of_messages | numeric | | 9610 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site.created_at.date-time | string | | 2018-05-03T13:35:05 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site.description.raw | string | | This is an example description. |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site.fpid | string | | \_tI5K2qyXYeqD3rUhkxMzg |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site.site_type | string | | Social Network |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site.source_uri | string | | testdomainlink.com |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site.tags.\*.name | string | | Tag Name |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site.tags.\*.parent_tag.name | string | | Parent Tag Name |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site.title | string | | Site Title |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site.updated_at.date-time | string | | 2019-03-27T15:59:59 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.\_header.collected_fpid | string | | RK6nDJJbRAmmInesId8lqA |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.\_header.observed_at | numeric | | 1559420203 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.avatar_uri.href | string | | https://testdomainlink.com/media/user/1234.jpg |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.body.enrichments.language | string | | en |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.body.raw | string | | This is a test body |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.body.text/html+sanitized | string | | This is a test body text/html+sanitized |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.body.text/plain | string | | This is a test body text/plain |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.created_at.date-time | string | | 2016-12-01T00:00:00+00:00 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.created_at.raw | string | | December 2016 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.created_at.timestamp | numeric | | 1480550400 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.fpid | string | | eE9alofZWZuS0Ef5HiirIA |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.is_donor | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.is_investor | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.is_premium | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.is_private | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.is_pro | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.is_verified | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.names.handle | string | | dankemp |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.native_id | string | | dankemp |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.number_following | numeric | | 2304 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.number_of_followers | numeric | | 1703 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.number_of_messages | numeric | | 9610 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site.created_at.date-time | string | | 2018-05-03T13:35:05 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site.description.raw | string | | This is an example description |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site.fpid | string | | \_tI5K2qyXYeqD3rUhkxMzg |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site.site_type | string | | Social Network |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site.source_uri | string | | testdomainlink.com |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site.tags.\*.name | string | | Tag Name |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site.tags.\*.parent_tag.name | string | | Parent Tag Name |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site.title | string | | Site Title |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site.updated_at.date-time | string | | 2019-03-27T15:59:59 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.\_header.collected_fpid | string | | RK6nDJJbRAmmInesId8lqA |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.\_header.observed_at | numeric | | 1559420203 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.avatar_uri.href | string | | https://testdomainlink.com/media/user/1234.jpg |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.body.enrichments.language | string | | en |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.body.raw | string | | This is a test body |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.body.text/html+sanitized | string | | This is a test body text/html+sanitized |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.body.text/plain | string | | This is a test body text/plain |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.created_at.date-time | string | | 2016-12-01T00:00:00+00:00 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.created_at.raw | string | | December 2016 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.created_at.timestamp | numeric | | 1480550400 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.fpid | string | | eE9alofZWZuS0Ef5HiirIA |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.is_donor | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.is_investor | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.is_premium | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.is_private | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.is_pro | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.is_verified | boolean | | True False |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.names.handle | string | | dankemp |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.native_id | string | | dankemp |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.number_following | numeric | | 2304 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.number_of_followers | numeric | | 1703 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.number_of_messages | numeric | | 9610 |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.site_actor.source_uri | string | | https://testdomainlink.com/dankemp |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.site_actor.source_uri | string | | https://testdomainlink.com/dankemp |
action_result.data.\*.\_source.site_actor.site_actor.site_actor.source_uri | string | | https://testdomainlink.com/dankemp |
action_result.data.\*.\_source.site_actor.site_actor.source_uri | string | | https://testdomainlink.com/dankemp |
action_result.data.\*.\_source.site_actor.source_uri | string | `url` | urn:fp:resource:qualified:conversation:chat:telegram:site_actor:1061080441 |
action_result.data.\*.\_source.site_actor.title | string | | Test Title |
action_result.data.\*.\_source.site_actor.type | string | | user |
action_result.data.\*.\_source.site_actor.url | string | `fp attribute value` `url` | https://testdomainlink.com/user/UniqueUsername642 |
action_result.data.\*.\_source.site_actor.username | string | `url` `user name` | ABOALZBER2 |
action_result.data.\*.\_source.site_actor_count.count | numeric | | 6219 |
action_result.data.\*.\_source.site_actor_count.first_resource.fpid | string | | KHXTQDjDWe6qk2t7cZGYbw |
action_result.data.\*.\_source.site_actor_count.first_resource.names.handle | string | | Emu |
action_result.data.\*.\_source.site_actor_count.first_resource.native_id | string | | 633735-emu |
action_result.data.\*.\_source.site_actor_count.last_resource.fpid | string | | 5lauqgEyXjmm-EZbwSOUvQ |
action_result.data.\*.\_source.site_actor_count.last_resource.names.handle | string | | mantq |
action_result.data.\*.\_source.site_actor_count.last_resource.native_id | string | | 1195854-mantq |
action_result.data.\*.\_source.size.number_of_bytes | numeric | | 31380 |
action_result.data.\*.\_source.size.raw | string | | 31.38 KB |
action_result.data.\*.\_source.source | string | `url` | Analyst Research |
action_result.data.\*.\_source.source_type | string | | Analyst Research |
action_result.data.\*.\_source.source_uri | string | `url` | https://testdomainlink.com/test |
action_result.data.\*.\_source.syntax | string | | text |
action_result.data.\*.\_source.thread.native_id | string | | 209360561 |
action_result.data.\*.\_source.thread.site.behavior | string | | replace |
action_result.data.\*.\_source.thread.site.href | string | | urn:fp:type:resource.qualified.site:Ra2dBSXnXjKqoLS7wJPWgw |
action_result.data.\*.\_source.thread.site.target | string | | $.site |
action_result.data.\*.\_source.thread.type | string | | thread |
action_result.data.\*.\_source.thread_count.count | numeric | | 2506 |
action_result.data.\*.\_source.times_seen | numeric | | 1 |
action_result.data.\*.\_source.timestamp | string | | 1549413013 |
action_result.data.\*.\_source.title | string | | CVE-2019-10802 |
action_result.data.\*.\_source.to_ids | boolean | | True False |
action_result.data.\*.\_source.top_domains.\*.count | numeric | | 182662 |
action_result.data.\*.\_source.top_domains.\*.value | string | | testdomainlink.com |
action_result.data.\*.\_source.top_domains.count | numeric | | 262 |
action_result.data.\*.\_source.top_domains.value | string | | testdomainlink.com |
action_result.data.\*.\_source.top_passwords.\*.count | numeric | | 1038 |
action_result.data.\*.\_source.top_passwords.\*.value | string | `sha1` `email` `md5` | e10adc3949ba59abbe56e057f20f883e |
action_result.data.\*.\_source.total_records | numeric | | 671072 |
action_result.data.\*.\_source.track1 | string | | 4147202342565650^LAST/NAME ^2102201148941100000000751000000 |
action_result.data.\*.\_source.track2 | string | | 4147202342565650=210220114894751 |
action_result.data.\*.\_source.track_information | string | | TR2 |
action_result.data.\*.\_source.type | string | | md5 |
action_result.data.\*.\_source.unique_records | numeric | | 671066 |
action_result.data.\*.\_source.unique_visits | numeric | | 0 |
action_result.data.\*.\_source.updated_at.date-time | string | | 2016-11-08T08:00:00+00:00 |
action_result.data.\*.\_source.updated_at.raw | string | | 2016-11-08T08:00:00 |
action_result.data.\*.\_source.updated_at.timestamp | numeric | | 1478592000 |
action_result.data.\*.\_source.url | string | `fp attribute value` `url` | https://www.testdomainlink.com/test |
action_result.data.\*.\_source.uuid | string | | 5c5a2a95-de34-4b51-8f23-124a0a640c05 |
action_result.data.\*.\_source.value.attachment | string | `sha256` | 72832db9b951663b8f322778440b8720ea95cde0349a1d26477edd95b3915479 |
action_result.data.\*.\_source.value.comment | string | `file name` | |
action_result.data.\*.\_source.value.domain | string | `fp attribute value` `domain` | adsfinder.xyz |
action_result.data.\*.\_source.value.email-src | string | `fp attribute value` `email` | email@testdomainlink.com |
action_result.data.\*.\_source.value.ip-dst | string | `fp attribute value` `ip` | 210.122.7.129 |
action_result.data.\*.\_source.value.ip-dst|port | string | `fp attribute value` | 5.79.68.110|80 |
action_result.data.\*.\_source.value.link | string | `url` | https://www.testdomainlink.com/test.html |
action_result.data.\*.\_source.value.md5 | string | `fp attribute value` `md5` | 120862db74f9e202c91466fe93efc50a |
action_result.data.\*.\_source.value.other | string | | id:wc4XnQq4X-GrNjTP9gFh4g |
action_result.data.\*.\_source.value.sha1 | string | `fp attribute value` `sha1` | 1489f923c4dca729178b3e3233458550d8dddf29 |
action_result.data.\*.\_source.value.sha256 | string | `fp attribute value` `sha256` | 32acb0ab5c16e624764f282f84f160984d436c777ad1a41ee8080b50db98e199 |
action_result.data.\*.\_source.value.url | string | `fp attribute value` `url` | http://ww1.testdomainlink.com/?subid1=1234 |
action_result.data.\*.\_source.value.x509-fingerprint-sha1 | string | `fp attribute value` `sha1` | 6565a33dd73b11a30a072537c9424a5b767750e1 |
action_result.data.\*.\_type | string | | \_doc |
action_result.status | string | | success failed |
action_result.message | string | | Total results: 478 |
action_result.summary.total_results | numeric | | 478 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list indicators'

Fetch a list of IoCs that occur in the context of an event from the Flashpoint Platform

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**attributes_types** | optional | Enable a search by attribute types(allows Comma-separated list) | string | `fp attribute type` |
**query** | optional | Filter the results based on the field value or free text search | string | `fp attribute value` |
**limit** | optional | Maximum number of indicators to be fetched (default: 500) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.attributes_types | string | `fp attribute type` | url domain ip-src ip-dst md5 sha1 sha256 sha512 |
action_result.parameter.limit | numeric | | 1000 |
action_result.parameter.query | string | `fp attribute value` | "test text" gandcrab+ransomware category:"Payload Delivery" +value.\\\*:"5.79.68.110|80" +value.url:"http://reborntechnology.co.uk/ups.com/WebTracking/PO-58666526964013/" "http://reborntechnology.co.uk/ups.com/WebTracking/PO-58666526964013/" |
action_result.data.\*.Attribute.Event.RelatedEvent.\*.Event.fpid | string | | g8L1tzecUgOS6FWvBJrCxA |
action_result.data.\*.Attribute.Event.RelatedEvent.\*.Event.info | string | | EventInfo |
action_result.data.\*.Attribute.Event.fpid | string | | zP1UL5zqWf6PxQv8f5OkdA |
action_result.data.\*.Attribute.Event.href | string | | https://api.flashpoint.io/technical-intelligence/v1/event/zP1UL5zqWf6PxQv8f5OkdA |
action_result.data.\*.Attribute.Event.info | string | | EventInfo_f59e91ef018b716d525bf7bcf50edbc040321748_2019-06-17T04:01:01.000Z |
action_result.data.\*.Attribute.Event.timestamp | string | | 1560895664 |
action_result.data.\*.Attribute.category | string | | Payload delivery |
action_result.data.\*.Attribute.fpid | string | | tQ3UYKNAUV-iSWQp7s3ppg |
action_result.data.\*.Attribute.href | string | | https://api.flashpoint.io/technical-intelligence/v1/attribute/tQ3UYKNAUV-iSWQp7s3ppg |
action_result.data.\*.Attribute.timestamp | string | | 1560895664 |
action_result.data.\*.Attribute.type | string | `fp attribute type` | md5 |
action_result.data.\*.Attribute.uuid | string | | c0e430ce-c96a-47ac-aa7d-d90b83bd4fe5 |
action_result.data.\*.Attribute.value.comment | string | | |
action_result.data.\*.Attribute.value.md5 | string | `fp attribute value` `md5` | 7444589a147dc4e5b351cc20eadedc22 |
action_result.data.\*.Event.Galaxy.\*.GalaxyCluster.\*.authors | string | | Davide Arcuri |
action_result.data.\*.Event.Galaxy.\*.GalaxyCluster.\*.description | string | | This is a test description |
action_result.data.\*.Event.Galaxy.\*.GalaxyCluster.\*.galaxy_id | string | | 22 |
action_result.data.\*.Event.Galaxy.\*.GalaxyCluster.\*.meta.external_id | string | | T1022 |
action_result.data.\*.Event.Galaxy.\*.GalaxyCluster.\*.meta.kill_chain | string | | test-attack:enterprise-attack:exfiltration |
action_result.data.\*.Event.Galaxy.\*.GalaxyCluster.\*.meta.mitre_data_sources | string | | Process monitoring |
action_result.data.\*.Event.Galaxy.\*.GalaxyCluster.\*.meta.mitre_platforms | string | | Windows |
action_result.data.\*.Event.Galaxy.\*.GalaxyCluster.\*.meta.refs | string | `url` | https://www.testdomainlink.com/test.html |
action_result.data.\*.Event.Galaxy.\*.GalaxyCluster.\*.meta.synonyms | string | | Pandemyia |
action_result.data.\*.Event.Galaxy.\*.GalaxyCluster.\*.source | string | `url` | https://testdomainlink.com/test |
action_result.data.\*.Event.Galaxy.\*.GalaxyCluster.\*.tag_id | string | | 163 |
action_result.data.\*.Event.Galaxy.\*.GalaxyCluster.\*.tag_name | string | | dxsp-xxgh:test-type="Test Attachment - T1193" |
action_result.data.\*.Event.Galaxy.\*.GalaxyCluster.\*.type | string | | test-type |
action_result.data.\*.Event.Galaxy.\*.GalaxyCluster.\*.uuid | string | | fb2242d8-1707-11e8-ab20-6fa7448c3640 |
action_result.data.\*.Event.Galaxy.\*.GalaxyCluster.\*.value | string | | Spearphishing Attachment - T1193 |
action_result.data.\*.Event.Galaxy.\*.GalaxyCluster.\*.version | string | | 4 |
action_result.data.\*.Event.Galaxy.\*.description | string | | Test description |
action_result.data.\*.Event.Galaxy.\*.icon | string | | map |
action_result.data.\*.Event.Galaxy.\*.name | string | | Test Name |
action_result.data.\*.Event.Galaxy.\*.namespace | string | | test-namespace |
action_result.data.\*.Event.Galaxy.\*.type | string | | test-type |
action_result.data.\*.Event.Galaxy.\*.uuid | string | | fa7016a8-1707-11e8-82d0-1b73d76eb204 |
action_result.data.\*.Event.Galaxy.\*.version | string | | 4 |
action_result.data.\*.Event.RelatedEvent.\*.Event.date | string | | 2019-02-11 |
action_result.data.\*.Event.RelatedEvent.\*.Event.fpid | string | | g8L1tzecUgOS6FWvBJrCxA |
action_result.data.\*.Event.RelatedEvent.\*.Event.info | string | | DarkHotel |
action_result.data.\*.Event.RelatedEvent.\*.Event.timestamp | string | | 1549907330 |
action_result.data.\*.Event.RelatedEvent.\*.Event.uuid | string | | 5c61b582-7d5c-4857-a944-05cc0a640c05 |
action_result.data.\*.Event.Tag.\*.name | string | `file name` | TagName |
action_result.data.\*.Event.Tag.\*.numerical_value | string | | |
action_result.data.\*.Event.Tags | string | | post_date: 2018-09-15 12:07:00 |
action_result.data.\*.Event.attack_ids | string | | T1022 |
action_result.data.\*.Event.attribute_count | string | | 1 |
action_result.data.\*.Event.date | string | | 2019-02-05 |
action_result.data.\*.Event.event_creator_email | string | `email` | email@testdomainlink.com |
action_result.data.\*.Event.fpid | string | | zP1UL5zqWf6PxQv8f5OkdA |
action_result.data.\*.Event.href | string | `url` | https://api.flashpoint.io/technical-intelligence/v1/event/zP1UL5zqWf6PxQv8f5OkdA |
action_result.data.\*.Event.info | string | | CryptingService_f59e91ef018b716d525bf7bcf50edbc040321748_2019-06-17T04:01:01.000Z |
action_result.data.\*.Event.publish_timestamp | string | | 1549412790 |
action_result.data.\*.Event.report | string | `url` | https://fp.tools/home/intelligence/reports/report/E_J_zA_tTamKK61VWvnyxg |
action_result.data.\*.Event.reports | string | `url` | https://fp.tools/home/intelligence/reports/report/hDeeeDt1TV6r6XtDGVQKcQ |
action_result.data.\*.Event.timestamp | string | | 1560895664 |
action_result.data.\*.Event.uuid | string | | 5c5a29b6-1d44-4b67-bcc5-12600a640c05 |
action_result.data.\*.basetypes | string | `fp query basetypes` | indicator_attribute |
action_result.data.\*.category | string | | Payload delivery |
action_result.data.\*.fpid | string | | tQ3UYKNAUV-iSWQp7s3ppg |
action_result.data.\*.header\_.indexed_at | numeric | | 1560989498 |
action_result.data.\*.header\_.ingested_at | numeric | | 1560988795 |
action_result.data.\*.header\_.is_visible | boolean | | True False |
action_result.data.\*.header\_.observed_at | numeric | | 1560988795 |
action_result.data.\*.header\_.source | string | | urn:fp:resource:qualified:indicator |
action_result.data.\*.href | string | `url` | https://api.flashpoint.io/technical-intelligence/v1/attribute/tQ3UYKNAUV-iSWQp7s3ppg |
action_result.data.\*.timestamp | string | | 1560895664 |
action_result.data.\*.type | string | `fp attribute type` | md5 |
action_result.data.\*.uuid | string | | c0e430ce-c96a-47ac-aa7d-d90b83bd4fe5 |
action_result.data.\*.value.AS | string | `fp attribute value` | AS16276 |
action_result.data.\*.value.attachment | string | `fp attribute value` | 72832db9b951663b8f322778440b8720ea95cde0349a1d26477edd95b3915479 |
action_result.data.\*.value.authentihash | string | `fp attribute value` | c50d6e2cf0e6018b5ed8fc3ffea51e0aa5d4bb4e1c027b65ed9a5fff84db9765 |
action_result.data.\*.value.btc | string | `fp attribute value` | 15HUUDBjLD34XfCu6YtafT7ARSt2TBrLBe |
action_result.data.\*.value.campaign-name | string | `fp attribute value` | WizardOpium |
action_result.data.\*.value.comment | string | `url` | |
action_result.data.\*.value.cookie | string | `fp attribute value` | adwords_02 |
action_result.data.\*.value.domain | string | `fp attribute value` `domain` | adsfinder.xyz |
action_result.data.\*.value.email-dst | string | `fp attribute value` `email` | trash023@ambcomission.com |
action_result.data.\*.value.email-src | string | `fp attribute value` `email` | email@testdomainlink.com |
action_result.data.\*.value.email-src-display-name | string | `fp attribute value` | Telstra |
action_result.data.\*.value.email-subject | string | `fp attribute value` | Your Telstra Business Email Bill |
action_result.data.\*.value.filename | string | `fp attribute value` | secure-ingdirect.top |
action_result.data.\*.value.first-name | string | `fp attribute value` | Javad |
action_result.data.\*.value.float | string | `fp attribute value` | 6.1704414228235 |
action_result.data.\*.value.github-username | string | `fp attribute value` | BlackRouter |
action_result.data.\*.value.hostname | string | `fp attribute value` | putrr16.com |
action_result.data.\*.value.imphash | string | `fp attribute value` | a872d0dcbb4472f66f79cb57e73e177d |
action_result.data.\*.value.ip-dst | string | `fp attribute value` `ip` | 210.122.7.129 |
action_result.data.\*.value.ip-dst|port | string | `fp attribute value` | 5.79.68.110|80 |
action_result.data.\*.value.ip-src | string | `fp attribute value` `ip` | 101.55.64.246 |
action_result.data.\*.value.link | string | `fp attribute value` | https://www.testdomainlink.com/test.html |
action_result.data.\*.value.malware-sample | string | `fp attribute value` | czicmren.exe|2f17c915610b08fb59c01981ed2594c5 |
action_result.data.\*.value.md5 | string | `fp attribute value` `md5` | 7444589a147dc4e5b351cc20eadedc22 |
action_result.data.\*.value.mutex | string | `fp attribute value` | c2hpdHmjcmF6eUBleHBsb2l0Lmlt_NONE_DL |
action_result.data.\*.value.other | string | `fp attribute value` | id:wc4XnQq4X-GrNjTP9gFh4g |
action_result.data.\*.value.pattern-in-file | string | `fp attribute value` | D:\\Project\\FoxPanel222\\FoxPanel\\obj\\Debug\\FoxPanel.pdb |
action_result.data.\*.value.pattern-in-memory | string | `fp attribute value` | %PUBLIC%\\Public\\hUpdated.ps1 |
action_result.data.\*.value.pdb | string | `fp attribute value` | u:\\SAM\\Servers\\Sam-onion-no-check-lock-file-enc-all-ext\\SAM\\obj\\Release\\MIKOPONI.pdb |
action_result.data.\*.value.port | string | `fp attribute value` | 443 |
action_result.data.\*.value.regkey | string | `fp attribute value` | HKEY_CURRENT_USER\\SOFTWARE\\FakeMessage\\FakeMessage |
action_result.data.\*.value.regkey|value | string | `fp attribute value` | HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run|%APPDATA%\\9bc79ecb-e94e-4db2-bd38-4950445a4f10\\dsl host\\dslhost.exe |
action_result.data.\*.value.sha1 | string | `fp attribute value` `sha1` | ba6045f30a940efdede47b0c6e3a73d3df7e0bfe |
action_result.data.\*.value.sha256 | string | `fp attribute value` `sha256` | 32acb0ab5c16e624764f282f84f160984d436c777ad1a41ee8080b50db98e199 |
action_result.data.\*.value.sha512 | string | `fp attribute value` | ad2f7c7470a9a48faa311d9eb85b1e30686bd553915434eed77e8103986401899a789702ae6af63e00c14195f4c2eb1c4c03c2f92c26bf90ddc293e76dfbee08 |
action_result.data.\*.value.size-in-bytes | string | `fp attribute value` | Enriched via the stiximport module |
action_result.data.\*.value.snort | string | `fp attribute value` | alert http $HOME_NET any -> $EXTERNAL_NET any (msg:"FlashPoint DMSniff UserAgent"; flow:established,to_server; content:"DSNF\_"; http_user_agent; classtype:trojan-activity; sid:9000030; rev:1; metadata:author Jason Reaves;) |
action_result.data.\*.value.ssdeep | string | `fp attribute value` | 3072:pNwZ4j/a2NlHbAoTL4592kHhEBZTWTBfg09ruXlN:pNwZ4zaibAoTL45oMEPWTBp9ruXl |
action_result.data.\*.value.target-external | string | `fp attribute value` | www.testdomainlink.com |
action_result.data.\*.value.target-machine | string | `fp attribute value` | 103.205.134.74 |
action_result.data.\*.value.target-org | string | `fp attribute value` | Norsk Hydro ASA |
action_result.data.\*.value.text | string | `fp attribute value` | %TEMP%\\8112.tmp reads from %WINDIR%\\system32\\lsass.exe. |
action_result.data.\*.value.threat-actor | string | `fp attribute value` | 104.235.89.6 |
action_result.data.\*.value.twitter-id | string | `fp attribute value` | @BlackR0uter |
action_result.data.\*.value.uri | string | `fp attribute value` | https://testdomainlink.com/test |
action_result.data.\*.value.url | string | `fp attribute value` `url` | http://ww1.testdomainlink.com/?subid1=1234 |
action_result.data.\*.value.user-agent | string | `fp attribute value` | Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0; NP02) |
action_result.data.\*.value.whois-creation-date | string | `fp attribute value` | 2019-01-09 |
action_result.data.\*.value.whois-registrant-email | string | `fp attribute value` `email` | 253125567@qq.com |
action_result.data.\*.value.whois-registrant-name | string | `fp attribute value` | User Name |
action_result.data.\*.value.whois-registrant-phone | string | `fp attribute value` | 9688007762430 |
action_result.data.\*.value.whois-registrar | string | `fp attribute value` | user.name@mail.com |
action_result.data.\*.value.x509-fingerprint-md5 | string | `fp attribute value` `md5` | 378d5543048e583a06a0819f25bd9e85 |
action_result.data.\*.value.x509-fingerprint-sha1 | string | `fp attribute value` `sha1` | 6565a33dd73b11a30a072537c9424a5b767750e1 |
action_result.data.\*.value.x509-fingerprint-sha256 | string | `fp attribute value` `sha256` | 27af4b890db1a611d0054d5d4a7d9a36c9f52dffeb67a053be9ea03a495a9302 |
action_result.data.\*.value.yara | string | `fp attribute value` | rule APT15_MirageFox
{
meta:
author = "Flashpoint"
analyst = "c.testn"
fp_report = "APT15_MirageFox"
source = "hxxps://www[.]intezer[.]com/miragefox-apt15-resurfaces-with-new-tools-based-on-old-ones/"
md5 = "afe24283fd933bac9d0c933e0c08ba02"
sha256 = "28d6a9a709b9ead84aece250889a1687c07e19f6993325ba5295410a478da30a"

```
strings:
	$MirageFox = { 4D 69 72 61 67 65 46 6F 78 5F 53 65 72 76 65 72 2E 64 61 74 00 64 6C 6C 5F 77 57 69 6E 4D 61 69 }
		/\*
		.rdata:100129B0 word_100129B0   dw 0                    ; DATA XREF: .rdata:100129A4o
		.rdata:100129B2 aMiragefoxServe db 'MirageFox_Server.dat',0
		.rdata:100129B2                                         ; DATA XREF: .rdata:1001298Co
		.rdata:100129C7 aDllWwinmain    db 'dll_wWinMain',0     ; DATA XREF: .rdata:off_100129ACo
		.rdata:100129D4                 align 800h
		.rdata:100129D4 _rdata          ends
		\*/

	$SvcSend = { 5C 63 6D 64 2E 65 78 65 00 00 00 00 57 69 6E 53 74 61 30 5C 44 65 66 61 75 6C 74 00 25 73 6F 73 33 32 5F 5F 25 64 2E 69 6E 69 00 00 25 73 75 73 72 33 32 5F 5F 25 64 2E 69 6E 69 00 25 73 75 73 72 65 72 5F 5F 25 64 2E 69 6E 69 00 25 73 20 25 73 20 2D 20 25 73 0A 00 44 3A 5C 53 76 63 53 65 6E 64 2E 6C 6F 67 }
		/\*
		.data:100134CC ; CHAR aCmdExe[]
		.data:100134CC aCmdExe         db '\\cmd.exe',0         ; DATA XREF: sub_100041A2+1B8o
		.data:100134D5                 align 4
		.data:100134D8 aWinsta0Default db 'WinSta0\\Default',0  ; DATA XREF: sub_100041A2+188o
		.data:100134E8 aSos32DIni      db '%sos32__%d.ini',0   ; DATA XREF: sub_100041A2+5Ao
		.data:100134F7                 align 4
		.data:100134F8 aSusr32DIni     db '%susr32__%d.ini',0  ; DATA XREF: sub_100041A2+3Fo
		.data:100134F8                                         ; sub_100045D3+24o
		.data:10013508 aSusrerDIni     db '%susrer__%d.ini',0  ; DATA XREF: sub_100041A2+21o
		.data:10013518 aSSS            db '%s %s - %s',0Ah,0   ; DATA XREF: sub_10004766+57o
		.data:10013524 aDSvcsendLog    db 'D:\\SvcSend.log',0   ; DATA XREF: sub_10004766+27o
		.data:10013533                 align 4
		.data:10013534 aA              db 'a+',0               ; DATA XREF: sub_10004766+22o
		.data:10013537                 align 4
		.data:10013538 unk_10013538    db  20h                 ; DATA XREF: sub_10004B19+2o
		\*/

condition:
	(uint16(0) == 0x5A4D and uint8(uint32(0x3c)+23) == 0x21 and $MirageFox and $SvcSend) or
	(uint16(0) == 0x5A4D and uint8(uint32(0x3c)+23) == 0x21 and $MirageFox) // Some variants do not drop SvcSend.log. Comment out this last condition to detect only variants that drop SvcSend.log
```

} |
action_result.status | string | | success failed |
action_result.message | string | | Total iocs: 1000 |
action_result.summary.total_iocs | numeric | | 1000 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'search indicators'

Fetch an IoC value of a specific attribute type from the list of available IoCs on the Flashpoint Platform

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**attribute_type** | required | Retrieve specific indicator's attribute type result | string | `fp attribute type` |
**attribute_value** | required | Retrieve specific indicator's attribute type result based on the provided value | string | `fp attribute value` |
**limit** | optional | Maximum number of reports to be fetched (default: 500) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.attribute_type | string | `fp attribute type` | url domain ip-src ip-dst md5 sha1 sha256 sha512 |
action_result.parameter.attribute_value | string | `fp attribute value` | 73d125f84503bd87f8142cf2ba8ab05e http://ww1.testdomainlink.com/?subid1=1234 |
action_result.parameter.limit | numeric | | 500 |
action_result.data.\*.Attribute.Event.RelatedEvent.\*.Event.fpid | string | | g8L1tzecUgOS6FWvBJrCxA |
action_result.data.\*.Attribute.Event.RelatedEvent.\*.Event.info | string | | DarkHotel |
action_result.data.\*.Attribute.Event.fpid | string | | zP1UL5zqWf6PxQv8f5OkdA |
action_result.data.\*.Attribute.Event.href | string | | https://api.flashpoint.io/technical-intelligence/v1/event/zP1UL5zqWf6PxQv8f5OkdA |
action_result.data.\*.Attribute.Event.info | string | | CryptingService_f59e91ef018b716d525bf7bcf50edbc040321748_2019-06-17T04:01:01.000Z |
action_result.data.\*.Attribute.Event.timestamp | string | | 1560895664 |
action_result.data.\*.Attribute.category | string | | Payload delivery |
action_result.data.\*.Attribute.fpid | string | | tQ3UYKNAUV-iSWQp7s3ppg |
action_result.data.\*.Attribute.href | string | | https://api.flashpoint.io/technical-intelligence/v1/attribute/tQ3UYKNAUV-iSWQp7s3ppg |
action_result.data.\*.Attribute.timestamp | string | | 1560895664 |
action_result.data.\*.Attribute.type | string | `fp attribute type` | md5 |
action_result.data.\*.Attribute.uuid | string | | c0e430ce-c96a-47ac-aa7d-d90b83bd4fe5 |
action_result.data.\*.Attribute.value.comment | string | | |
action_result.data.\*.Attribute.value.md5 | string | `fp attribute value` `md5` | 7444589a147dc4e5b351cc20eadedc22 |
action_result.data.\*.Event.RelatedEvent.\*.Event.fpid | string | | Z0x7QOWoX0yJ4iYuK2ZYLA |
action_result.data.\*.Event.RelatedEvent.\*.Event.info | string | | VBCrypter pivot on Wipro data |
action_result.data.\*.Event.Tags | string | | region:China |
action_result.data.\*.Event.fpid | string | | h-Uvmip4VPSshdEj7PgmcQ |
action_result.data.\*.Event.href | string | `url` | https://api.flashpoint.io/technical-intelligence/v1/event/A-1RokO9Wqq11S78N2TojA |
action_result.data.\*.Event.info | string | | APT 1 Historic Indicators |
action_result.data.\*.Event.timestamp | string | | 1539871610 |
action_result.data.\*.category | string | | Payload delivery |
action_result.data.\*.fpid | string | | -2kF-m_qWw6mpDcF4MuITg |
action_result.data.\*.href | string | `url` | https://api.flashpoint.io/technical-intelligence/v1/attribute/caG9zjTIW8u_md8rfGWDjg |
action_result.data.\*.timestamp | string | | 1539871466 |
action_result.data.\*.type | string | `fp attribute type` | md5 |
action_result.data.\*.uuid | string | | 5bc892ea-ed70-45e4-8edb-5b560a640c05 |
action_result.data.\*.value.AS | string | `fp attribute value` | AS16276 |
action_result.data.\*.value.attachment | string | `fp attribute value` | 72832db9b951663b8f322778440b8720ea95cde0349a1d26477edd95b3915479 |
action_result.data.\*.value.authentihash | string | `fp attribute value` | c50d6e2cf0e6018b5ed8fc3ffea51e0aa5d4bb4e1c027b65ed9a5fff84db9765 |
action_result.data.\*.value.btc | string | `fp attribute value` | 15HUUDBjLD34XfCu6YtafT7ARSt2TBrLBe |
action_result.data.\*.value.campaign-name | string | `fp attribute value` | WizardOpium |
action_result.data.\*.value.comment | string | | |
action_result.data.\*.value.cookie | string | `fp attribute value` | adwords_02 |
action_result.data.\*.value.domain | string | `fp attribute value` `domain` | adsfinder.xyz |
action_result.data.\*.value.email-dst | string | `fp attribute value` `email` | trash023@ambcomission.com |
action_result.data.\*.value.email-src | string | `fp attribute value` `email` | email@testdomainlink.com |
action_result.data.\*.value.email-src-display-name | string | `fp attribute value` | Telstra |
action_result.data.\*.value.email-subject | string | `fp attribute value` | Your Telstra Business Email Bill |
action_result.data.\*.value.filename | string | `fp attribute value` | secure-ingdirect.top |
action_result.data.\*.value.first-name | string | `fp attribute value` | Javad |
action_result.data.\*.value.float | string | `fp attribute value` | 6.1704414228235 |
action_result.data.\*.value.github-username | string | `fp attribute value` | BlackRouter |
action_result.data.\*.value.hostname | string | `fp attribute value` | testdomainlink.com |
action_result.data.\*.value.imphash | string | `fp attribute value` | a872d0dcbb4472f66f79cb57e73e177d |
action_result.data.\*.value.ip-dst | string | `fp attribute value` `ip` | 210.122.7.129 |
action_result.data.\*.value.ip-dst|port | string | `fp attribute value` | 5.79.68.110|80 |
action_result.data.\*.value.ip-src | string | `fp attribute value` `ip` | 101.55.64.246 |
action_result.data.\*.value.link | string | `fp attribute value` | https://www.testdomainlink.com/test.html |
action_result.data.\*.value.malware-sample | string | `fp attribute value` | sample.exe|2f17c915610bxxxb59c01981ed2594c5 |
action_result.data.\*.value.md5 | string | `fp attribute value` `md5` | 73d125f84503bd87f8142cf2ba8ab05e |
action_result.data.\*.value.mutex | string | `fp attribute value` | c2hpdHmjcmF6eUBleHBsb2l0Lmlt_NONE_DL |
action_result.data.\*.value.other | string | `fp attribute value` | id:wc4XnQq4X-GrNjTP9gFh4g |
action_result.data.\*.value.pattern-in-file | string | `fp attribute value` | D:\\PATH.ext |
action_result.data.\*.value.pattern-in-memory | string | `fp attribute value` | %PUBLIC%\\Public\\hUpdated.ps1 |
action_result.data.\*.value.pdb | string | `fp attribute value` | u:\\SAM\\Servers\\Sam-onion-no-check-lock-file-enc-all-ext\\SAM\\obj\\Release\\MIKOPONI.pdb |
action_result.data.\*.value.port | string | `fp attribute value` | 443 |
action_result.data.\*.value.regkey | string | `fp attribute value` | HKEY_CURRENT_USER\\SOFTWARE\\FakeMessage\\FakeMessage |
action_result.data.\*.value.regkey|value | string | `fp attribute value` | HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run|%APPDATA%\\9bc79ecb-e94e-4db2-bd38-4950445a4f10\\dsl host\\dslhost.exe |
action_result.data.\*.value.sha1 | string | `fp attribute value` `sha1` | ba6045f30a940efdede47b0c6e3a73d3df7e0bfe |
action_result.data.\*.value.sha256 | string | `fp attribute value` `sha256` | 32acb0ab5c16e624764f282f84f160984d436c777ad1a41ee8080b50db98e199 |
action_result.data.\*.value.sha512 | string | `fp attribute value` | ad2f7c7470a9a48faa311d9eb85b1e30686bd553915434eed77e8103986401899a789702ae6af63e00c14195f4c2eb1c4c03c2f92c26bf90ddc293e76dfbee08 |
action_result.data.\*.value.size-in-bytes | string | `fp attribute value` | Enriched via the stiximport module |
action_result.data.\*.value.snort | string | `fp attribute value` | alert http $HOME_NET any -> $EXTERNAL_NET any (msg:"FlashPoint DMSniff UserAgent"; flow:established,to_server; content:"DSNF\_"; http_user_agent; classtype:trojan-activity; sid:9000030; rev:1; metadata:author Jason Reaves;) |
action_result.data.\*.value.ssdeep | string | `fp attribute value` | 3072:pNwZ4j/a2NlHbAoTL4592kHhEBZTWTBfg09ruXlN:pNwZ4zaibAoTL45oMEPWTBp9ruXl |
action_result.data.\*.value.target-external | string | `fp attribute value` | www.testdomainlink.com |
action_result.data.\*.value.target-machine | string | `fp attribute value` | 103.205.134.74 |
action_result.data.\*.value.target-org | string | `fp attribute value` | Org Value |
action_result.data.\*.value.text | string | `fp attribute value` | %TEMP%\\8112.tmp reads from %WINDIR%\\system32\\lsass.exe. |
action_result.data.\*.value.threat-actor | string | `fp attribute value` | 104.235.89.6 |
action_result.data.\*.value.twitter-id | string | `fp attribute value` | @Gdbncdsxx |
action_result.data.\*.value.uri | string | `fp attribute value` | https://testdomainlink.com/test |
action_result.data.\*.value.url | string | `fp attribute value` `url` | http://ww1.testdomainlink.com/?subid1=1234 |
action_result.data.\*.value.user-agent | string | `fp attribute value` | User Agent |
action_result.data.\*.value.whois-creation-date | string | `fp attribute value` | 2019-01-09 |
action_result.data.\*.value.whois-registrant-email | string | `fp attribute value` `email` | 2531sdbaejrw7@qq.com |
action_result.data.\*.value.whois-registrant-name | string | `fp attribute value` | User Name |
action_result.data.\*.value.whois-registrant-phone | string | `fp attribute value` | 9688007762430 |
action_result.data.\*.value.whois-registrar | string | `fp attribute value` | user.name@mail.com |
action_result.data.\*.value.x509-fingerprint-md5 | string | `fp attribute value` `md5` | 378d5543048e583a06a0819f25bd9e85 |
action_result.data.\*.value.x509-fingerprint-sha1 | string | `fp attribute value` `sha1` | 6565a33dd73b11a30a072537c9424a5b767750e1 |
action_result.data.\*.value.x509-fingerprint-sha256 | string | `fp attribute value` `sha256` | 27af4b890db1a611d0054d5d4a7d9a36c9f52dffeb67a053be9ea03a495a9302 |
action_result.data.\*.value.yara | string | `fp attribute value` | rule APT15_MirageFox
{
meta:
author = "Flashpoint"
analyst = "c.testn"
fp_report = "APT15_MirageFox"
source = "hxxps://www[.]intezer[.]com/miragefox-apt15-resurfaces-with-new-tools-based-on-old-ones/"
md5 = "afe24283fd933bac9d0c933e0c08ba02"
sha256 = "28d6a9a709b9ead84aece250889a1687c07e19f6993325ba5295410a478da30a"

```
strings:
	$MirageFox = { 4D 69 72 61 67 65 46 6F 78 5F 53 65 72 76 65 72 2E 64 61 74 00 64 6C 6C 5F 77 57 69 6E 4D 61 69 }
		/\*
		.rdata:100129B0 word_100129B0   dw 0                    ; DATA XREF: .rdata:100129A4o
		.rdata:100129B2 aMiragefoxServe db 'MirageFox_Server.dat',0
		.rdata:100129B2                                         ; DATA XREF: .rdata:1001298Co
		.rdata:100129C7 aDllWwinmain    db 'dll_wWinMain',0     ; DATA XREF: .rdata:off_100129ACo
		.rdata:100129D4                 align 800h
		.rdata:100129D4 _rdata          ends
		\*/

	$SvcSend = { 5C 63 6D 64 2E 65 78 65 00 00 00 00 57 69 6E 53 74 61 30 5C 44 65 66 61 75 6C 74 00 25 73 6F 73 33 32 5F 5F 25 64 2E 69 6E 69 00 00 25 73 75 73 72 33 32 5F 5F 25 64 2E 69 6E 69 00 25 73 75 73 72 65 72 5F 5F 25 64 2E 69 6E 69 00 25 73 20 25 73 20 2D 20 25 73 0A 00 44 3A 5C 53 76 63 53 65 6E 64 2E 6C 6F 67 }
		/\*
		.data:100134CC ; CHAR aCmdExe[]
		.data:100134CC aCmdExe         db '\\cmd.exe',0         ; DATA XREF: sub_100041A2+1B8o
		.data:100134D5                 align 4
		.data:100134D8 aWinsta0Default db 'WinSta0\\Default',0  ; DATA XREF: sub_100041A2+188o
		.data:100134E8 aSos32DIni      db '%sos32__%d.ini',0   ; DATA XREF: sub_100041A2+5Ao
		.data:100134F7                 align 4
		.data:100134F8 aSusr32DIni     db '%susr32__%d.ini',0  ; DATA XREF: sub_100041A2+3Fo
		.data:100134F8                                         ; sub_100045D3+24o
		.data:10013508 aSusrerDIni     db '%susrer__%d.ini',0  ; DATA XREF: sub_100041A2+21o
		.data:10013518 aSSS            db '%s %s - %s',0Ah,0   ; DATA XREF: sub_10004766+57o
		.data:10013524 aDSvcsendLog    db 'D:\\SvcSend.log',0   ; DATA XREF: sub_10004766+27o
		.data:10013533                 align 4
		.data:10013534 aA              db 'a+',0               ; DATA XREF: sub_10004766+22o
		.data:10013537                 align 4
		.data:10013538 unk_10013538    db  20h                 ; DATA XREF: sub_10004B19+2o
		\*/

condition:
	(uint16(0) == 0x5A4D and uint8(uint32(0x3c)+23) == 0x21 and $MirageFox and $SvcSend) or
	(uint16(0) == 0x5A4D and uint8(uint32(0x3c)+23) == 0x21 and $MirageFox) // Some variants do not drop SvcSend.log. Comment out this last condition to detect only variants that drop SvcSend.log
```

} |
action_result.status | string | | success failed |
action_result.message | string | | Total iocs: 1 |
action_result.summary.total_iocs | numeric | | 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2026 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
