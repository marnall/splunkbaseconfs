[comment]: # "Auto-generated SOAR connector documentation"
# EclecticIQ app

Publisher: EclecticIQ  
Connector Version: 2.0.0  
Product Vendor: EclecticIQ  
Product Name: Intelligence Center integration  
Product Version Supported (regex): ".\*"  
Minimum Product Version: 5.5.0  

EclecticIQ Intelligence Center integration

[comment]: # "File: README.md"
[comment]: # "Copyright (c) EclecticIQ, 2019-2023"
[comment]: # ""
[comment]: # "Licensed under the Apache License, Version 2.0 (the 'License');"
[comment]: # "you may not use this file except in compliance with the License."
[comment]: # "You may obtain a copy of the License at"
[comment]: # ""
[comment]: # "    http://www.apache.org/licenses/LICENSE-2.0"
[comment]: # ""
[comment]: # "Unless required by applicable law or agreed to in writing, software distributed under"
[comment]: # "the License is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,"
[comment]: # "either express or implied. See the License for the specific language governing permissions"
[comment]: # "and limitations under the License."
[comment]: # ""

# EclecticIQ Intelligence Center app for Splunk SOAR

The EclecticIQ Intelligence Center app for Splunk SOAR allows you to
enrich intelligence and create different entities on the Intelligence
Center, search for entities and ingest threat intelligence into Splunk
SOAR as events to use in playbooks.

## Install the app in Splunk SOAR

To install the app in Splunk SOAR:

1.  Open the Apps menu

2.  Install the application:

    - Select **New Apps** and search for "EclecticIQ".

    Or, you can install using the package file:

    1.  Select **Install app**
    2.  In the window that appears, drag and drop the package file to
        open it.

Once done, you can find it in **Apps \> Unconfigured Apps**.

## Configure EclecticIQ Intelligence Center

Configure EclecticIQ Intelligence Center to connect to the app. Log into
EclecticIQ Intelligence Center and do the following:

1.  Create an API token. Select your user profile picture at the bottom
    left, then select **API tokens \> + New API token**.

    Copy the API token and store it safely.

2.  To create Entities (Indicators and Sightings) you need to create a
    Source Group that will be used as a source for that entity.

3.  If you want to fetch entities as events into SOAR, create an
    outgoing feed with following parameters:

    - **Transport Type:** HTTP download.
    - **Content Type:** EclecticIQ JSON
    - **Datasets:** Add one or more datasets. Entities from these
      datasets will be made accessible to Splunk SOAR. For more
      information, see the "On-Poll action" section below.
    - **Update strategy:**
      - (Recommended) Append, or
      - Replace
    - **Authorized groups:** Select one or more groups that your user
      account belongs to. Your account must be assigned a role in that
      group that has at least `read entities` and `read extracts`
      permissions.

4.  Note down the **ID** of the outgoing feed you just created. To find
    the outgoing feed ID:

    1.  Select the outgoing feed.

    2.  Inspect the URL that appears in your browser address bar.

        E.g.:
        `https://ic-playground.eclecticiq.com/main/configuration/outgoing-feeds?tab=detail&detail=62`

        The outgoing feed ID is the value for the `detail` query
        parameter.

        In the example here, the outgoing feed ID is `62`.

Once done, configure the EclecticIQ Intelligence Center app for Splunk
SOAR.

In Splunk SOAR:

1.  In the **New Asset** menu, select **Asset Settings**. Set the
    following fields:

    - **EclecticIQ Intelligence Center address:** Enter a fully
      qualified URL for the Intelligence Center instance to connect to.

      E.g.: <https://ic-playground.eclecticiq.com>

    - **EclecticIQ Password/Token:** Enter the API token you generated
      earlier.

    - **EclecticIQ Group Name for Entities:** Enter the **Source Group**
      you created earlier.

    - **EclecticIQ Outgoing Feed ID \# for polling:** Enter the ID of
      the outgoing feed you created earlier.

    - **EclecticIQ SSL cert check:** Enable if you provide a custom
      certificate to your EclecticIQ Intelligence Center.

      You must add these custom certificates to the Splunk SOAR
      (On-premises) certificate store. See:
      <https://docs.splunk.com/Documentation/SOARonprem/6.0.0/Admin/AddOrRemoveCertificates>

    - **Proxy settings:** Set proxy settings to allow Splunk SOAR to
      connect to your Intelligence Center instance.

Once done, select **Test connectivity**.

> **Tip:** If **Test connectivity** displays errors, follow the
> displayed instructions to troubleshoot those errors, or send that
> information when contacting support.

## Playbook/investigations action

The app contains actions for different purposes, they will be reviewed
below and polling action reviewed in the next chapter.

### Enrichment actions

To enrich Observable/artifact a few actions provided: domain, email,
file, ip, url reputation. All the actions have only one required field
which contains values of observable to enrich. If an observable is
available in the EclecticIQ Intelligence Center you will get back its
maliciousness, source names, when it's been created and direct URL into
this observable in the EclecticIQ Intelligence Center.

Enrichment actions support following Observable types:

- Domain reputation - domain
- Email reputation - email
- File reputation - file, hash-md5, hash-sha1, hash-sha256, hash-sha512
- IP reputation - IPv4
- URL reputation - uri

### Create Sighting action

Create Sighting action allows to create Sighting with defined arguments
in the EclecticIQ Intelligence Center, when you create sighting you can
define:

- Sighting title
- Sighting description
- Confidence
- Impact
- Tags, by default there are two tags "Phantom Sighting, Automatically
  created", you can add more or replace them. To delimit tags use ","
- Fields to create observables which will be connected to the Sighting.
  There are fields for three observables, each has their own type,
  maliciousness and value. When you run an action you need to define at
  least one observable.

As the output you will get the Entity ID of the newly created entity.

### Create Indicator action

Create Indicator action allows to create Indicator with defined
arguments in the EclecticIQ Intelligence Center, when you create
indicator you can define:

- Indicator title
- Indicator description
- Confidence
- Impact
- Tags, by default there are two tags "Phantom Indicator, Automatically
  created", you can add more or replace them. To delimit tags use ","
- Fields to create observable which will be connected to the Indicator.
  There are dedicated fields for one ovbservable: type, malicousness and
  value. If you want to create Indicator connected to more then one
  observable use field "observable dictionary" into that field you can
  put as manny Indicators as need in following format
  "observable_value1,observale_type1,malicousness1;observable_value2,observale_type2,malicousness2;observable_value3,observale_type3,malicousness3"
  for example "121.11.121.11,ipv4,low;122.12.131.11,ipv4,high".
  Observable Malicousness could have in the dictionary following values:
  unknown, safe, low, medium, high. Delimiter between observable fields
  is "," and delimiter between observables is ";".

As the output you will get the Entity ID of the newly created entity.

### Query entity action

That action allows you to search for specific entity/ies which match
searching conditions. To start action you can define following
arguments:

- observable - put into that field observable value and you will get
  back all the entities that are connected to that observable.
- entity title - put into that field entity title you are looking for
  and you will get back all the entities matched that title.
- entity type - drop down where you can choose a specific entity type to
  search.

Searching conditions work with logic AND

As the output you will get entity title, type, description, source name,
tags, list of connected observables with their type and maliciousness,
list of relationship between requested entity and other entities.

### Query entity by ID action

That action allows you to search for entity with a specific Entity ID
avaiulble in the Intelligence Center. To start action you can define
following argument:

- **entity id:** Enter an entity ID to retrieve a specific entity.
  Entity IDs are UUIDs, e.g.: `a86f8393-eff6-4b31-b203-f63152be5a43`

Thie retrieves a specific entity's:

- title
- type
- description
- source name
- tags
- list of connected observables with their type and maliciousness
- list of relationship between requested entity and other entities

### EclecticIQ request GET action

This action makes a GET request to EclecticIQ Intelligence Center
[public api](https://developers.eclecticiq.com). To use this action, set
these parameters:

- **uri:** Enter the fully qualified URL to an EclecticIQ Intelligence
  Center public API endpoint, including query parameters. Do not
  URL-encode this. E.g.:
  `https://eclecticiq-threat-intel-platform.local/api/v1/observables?limit=20&data=true`

Output:

- HTTP status code of the response, and
- Parsed JSON body of the response

### EclecticIQ request POST action

This action makes a POST request to EclecticIQ Intelligence Center
[public api](https://developers.eclecticiq.com). To use this action, set
these parameters:

- **uri:** Enter the fully qualified URL to an EclecticIQ Intelligence
  Center public API endpoint, including query parameters. Do not
  URL-encode this. E.g.:
  `https://eclecticiq-threat-intel-platform.local/api/v1/entities`
- **body:** JSON payload. For payload schema documentation, see
  <https://developers.eclecticiq.com>.

Output:

- HTTP status code of the response, and
- Parsed JSON body of the response

### EclecticIQ request DELETE action

This action makes a DELETE request to EclecticIQ Intelligence Center
[public api](https://developers.eclecticiq.com). To use this action, set
these parameters:

- **uri:** Enter the fully qualified URL to an EclecticIQ Intelligence
  Center public API endpoint, including query parameters. Do not
  URL-encode this. E.g.:
  `https://eclecticiq-threat-intel-platform.local/api/v1/incoming-feeds/10?delete_entities=false`

Output:

- HTTP status code of the response, and
- Parsed JSON body of the response

### On-Poll action

That action can be turned on and scheduled via the app settings and it
will collect entities with observables from Outgoing feed and create new
events in Splunk SOAR using following logic:

- Entity will be converted to event, where Event title based on entity
  value and type, severity is based on Impact and Sensitivity based on
  TLP.
- Each observable will be created as Artifact and attached to Event.
  Artifact contains observable value and maliciousness


### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a Intelligence Center integration asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**tip_uri** |  required  | string | EclecticIQ Intelligence Center address
**tip_password** |  required  | password | EclecticIQ Password/Token
**tip_api** |  optional  | string | EclecticIQ public API version
**tip_ssl_check** |  optional  | boolean | EclecticIQ SSL Cert check
**tip_group** |  optional  | string | EclecticIQ Group Name for Entities
**tip_of_id** |  optional  | numeric | EclecticIQ Outgoing Feed ID # for polling
**tip_proxy_uri** |  optional  | string | Proxy Server Address
**tip_proxy_user** |  optional  | string | Proxy Server Username
**tip_proxy_password** |  optional  | password | Proxy Server Password

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[domain reputation](#action-domain-reputation) - Queries domain info  
[email reputation](#action-email-reputation) - Queries email info  
[file reputation](#action-file-reputation) - Queries for file reputation info  
[ip reputation](#action-ip-reputation) - Queries IP info  
[url reputation](#action-url-reputation) - Queries URL info  
[create sighting](#action-create-sighting) - Create sighting in EclecticIQ TIP  
[create indicator](#action-create-indicator) - Create indicator in EclecticIQ TIP  
[query entities](#action-query-entities) - Query EclecticIQ Intelligence Center for entities  
[query entity by id](#action-query-entity-by-id) - Query EclecticIQ Intelligence Center for entity by its ID  
[request get](#action-request-get) - Make HTTP GET request to EclecticIQ Intelligence Center  
[request post](#action-request-post) - Make HTTP POST request to EclecticIQ Intelligence Center  
[request delete](#action-request-delete) - Make HTTP DELETE request to EclecticIQ Intelligence Center  
[on poll](#action-on-poll) - Callback action for the on_poll ingest functionality  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'domain reputation'
Queries domain info

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** |  required  | Domain to query | string |  `domain`  `url` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.domain | string |  `domain`  `url`  |  
action_result.data.0 | string |  |  
action_result.data.0.created | string |  |  
action_result.data.0.last_updated | string |  |  
action_result.data.0.maliciousness | string |  |  
action_result.data.0.platform_link | string |  |  
action_result.data.0.source_name | string |  |  
action_result.summary.important_data | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'email reputation'
Queries email info

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**email** |  required  | Email to query | string |  `email` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.email | string |  `email`  |  
action_result.data.0 | string |  |  
action_result.data.0.created | string |  |  
action_result.data.0.last_updated | string |  |  
action_result.data.0.maliciousness | string |  |  
action_result.data.0.platform_link | string |  |  
action_result.data.0.source_name | string |  |  
action_result.summary.important_data | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'file reputation'
Queries for file reputation info

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** |  required  | File hash to query | string |  `hash`  `sha256`  `sha1`  `md5` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.hash | string |  `hash`  `sha256`  `sha1`  `md5`  |  
action_result.data.0 | string |  |  
action_result.data.0.created | string |  |  
action_result.data.0.last_updated | string |  |  
action_result.data.0.maliciousness | string |  |  
action_result.data.0.platform_link | string |  |  
action_result.data.0.source_name | string |  |  
action_result.summary.important_data | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'ip reputation'
Queries IP info

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** |  required  | IP to query | string |  `ip` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.ip | string |  `ip`  |  
action_result.data.0 | string |  |  
action_result.data.0.created | string |  |  
action_result.data.0.last_updated | string |  |  
action_result.data.0.maliciousness | string |  |  
action_result.data.0.platform_link | string |  |  
action_result.data.0.source_name | string |  |  
action_result.summary.important_data | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'url reputation'
Queries URL info

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** |  required  | URL to query | string |  `url` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.url | string |  `url`  |  
action_result.data.0 | string |  |  
action_result.data.0.created | string |  |  
action_result.data.0.last_updated | string |  |  
action_result.data.0.maliciousness | string |  |  
action_result.data.0.platform_link | string |  |  
action_result.data.0.source_name | string |  |  
action_result.summary.important_data | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'create sighting'
Create sighting in EclecticIQ TIP

Type: **contain**  
Read only: **False**

The EclecticIQ group name must be provided for this action to run successfully. Either in the source parameter, or the asset configuration.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**sighting_title** |  optional  | Sighting title | string | 
**sighting_description** |  optional  | Sighting description | string | 
**confidence_value** |  optional  | Confidence value | string | 
**impact_value** |  optional  | Impact value | string | 
**tags** |  optional  | Sighting tags delimited by ',' | string | 
**observable_1_value** |  required  | Observable value | string | 
**observable_1_type** |  required  | Observable type | string | 
**observable_1_maliciousness** |  optional  | Observalble maliciousness | string | 
**observable_2_value** |  optional  | Observable 2 value | string | 
**observable_2_type** |  optional  | Observable 2 type | string | 
**observable_2_maliciousness** |  optional  | Observable 2 maliciousness | string | 
**observable_3_value** |  optional  | Observable 3 value | string | 
**observable_3_type** |  optional  | Observable 3 type | string | 
**observable_3_maliciousness** |  optional  | Observable 3 maliciousness | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.confidence_value | string |  |  
action_result.parameter.impact_value | string |  |  
action_result.parameter.observable_1_maliciousness | string |  |  
action_result.parameter.observable_1_type | string |  |  
action_result.parameter.observable_1_value | string |  |  
action_result.parameter.observable_2_maliciousness | string |  |  
action_result.parameter.observable_2_type | string |  |  
action_result.parameter.observable_2_value | string |  |  
action_result.parameter.observable_3_maliciousness | string |  |  
action_result.parameter.observable_3_type | string |  |  
action_result.parameter.observable_3_value | string |  |  
action_result.parameter.sighting_description | string |  |  
action_result.parameter.sighting_title | string |  |  
action_result.parameter.tags | string |  |  
action_result.data | string |  |  
action_result.summary | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'create indicator'
Create indicator in EclecticIQ TIP

Type: **contain**  
Read only: **False**

Action creates Indicator entity in The EclecticIQ Intelligence Center. Group name used as source must be provided for this action to run successfully. Either in the source parameter, or the asset configuration.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**indicator_title** |  optional  | Indicator title | string | 
**indicator_description** |  optional  | Indicator description | string | 
**confidence_value** |  optional  | Confidence value | string | 
**impact_value** |  optional  | Impact value | string | 
**tags** |  optional  | Indicator tags delimited by ',' | string | 
**observable_1_value** |  required  | Observable value | string | 
**observable_1_type** |  required  | Observable type | string | 
**observable_1_maliciousness** |  optional  | Observalble maliciousness | string | 
**observable_dictionary** |  optional  | Observable dictionary | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.confidence_value | string |  |  
action_result.parameter.impact_value | string |  |  
action_result.parameter.indicator_description | string |  |  
action_result.parameter.indicator_title | string |  |  
action_result.parameter.observable_1_maliciousness | string |  |  
action_result.parameter.observable_1_type | string |  |  
action_result.parameter.observable_1_value | string |  |  
action_result.parameter.observable_dictionary | string |  |  
action_result.parameter.tags | string |  |  
action_result.data | string |  |  
action_result.summary | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'query entities'
Query EclecticIQ Intelligence Center for entities

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**observable** |  optional  | Observable value to query related entities | string |  `ip`  `hash`  `domain`  `url`  `sha1`  `sha256`  `md5`  `sha512` 
**entity_title** |  optional  | Text to search inside entity title | string | 
**entity_type** |  optional  | Type of entity to limit query | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.entity_title | string |  |  
action_result.parameter.entity_type | string |  |  
action_result.parameter.observable | string |  `ip`  `hash`  `domain`  `url`  `sha1`  `sha256`  `md5`  `sha512`  |  
action_result.data.0.\*.created_at | string |  |  
action_result.data.0.\*.description | string |  |  
action_result.data.0.\*.entity_title | string |  |  
action_result.data.0.\*.entity_type | string |  |  
action_result.data.0.\*.observables_output | string |  |  
action_result.data.0.\*.relationships_output | string |  |  
action_result.data.0.\*.source_name | string |  |  
action_result.data.0.\*.tags_list | string |  |  
action_result.summary | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'query entity by id'
Query EclecticIQ Intelligence Center for entity by its ID

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity_id** |  required  | Entity ID in EclecticIQ format, for example: a86f8393-eff6-4b31-b203-f63152be5a43 | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.entity_id | string |  |  
action_result.data.0.created_at | string |  |  
action_result.data.0.description | string |  |  
action_result.data.0.entity_title | string |  |  
action_result.data.0.entity_type | string |  |  
action_result.data.0.observables_output | string |  |  
action_result.data.0.relationships_output | string |  |  
action_result.data.0.source_name | string |  |  
action_result.data.0.tags_list | string |  |  
action_result.summary | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'request get'
Make HTTP GET request to EclecticIQ Intelligence Center

Type: **generic**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**uri** |  required  | EclecticIQ URI excluding Intelligence Cetner address but including API version and params if needed. e.g. /private/status | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.uri | string |  |  
action_result.data.0.reply_body | string |  |  
action_result.data.0.reply_status | string |  |  
action_result.summary | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'request post'
Make HTTP POST request to EclecticIQ Intelligence Center

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**uri** |  required  | EclecticIQ URI excluding Intelligence Cetner address but including API version and params if needed | string | 
**body** |  required  | JSON payload | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.body | string |  |  
action_result.parameter.uri | string |  |  
action_result.data.0.reply_body | string |  |  
action_result.data.0.reply_status | string |  |  
action_result.summary | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'request delete'
Make HTTP DELETE request to EclecticIQ Intelligence Center

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**uri** |  required  | EclecticIQ URI excluding Intelligence Cetner address but including API version and params if needed | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.uri | string |  |  
action_result.data.0.reply_status | string |  |  
action_result.summary | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'on poll'
Callback action for the on_poll ingest functionality

Type: **ingest**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**container_id** |  optional  | Container IDs to limit the ingestion to | string | 
**start_time** |  optional  | Start of time range, in epoch time (milliseconds) | numeric | 
**end_time** |  optional  | End of time range, in epoch time (milliseconds) | numeric | 
**container_count** |  optional  | Maximum number of container records to query for | numeric | 
**artifact_count** |  optional  | Maximum number of artifact records to query for | numeric | 
**feed_ids** |  optional  | TIP feed IDs delimited by "," | string | 

#### Action Output
No Output