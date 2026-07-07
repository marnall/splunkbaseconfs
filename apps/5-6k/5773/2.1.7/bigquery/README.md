# Big Query

Publisher: Splunk <br>
Connector Version: 2.1.7 <br>
Product Vendor: Google <br>
Product Name: Big Query <br>
Minimum Product Version: 5.3.0

This app allows running investigative actions against Google BigQuery

### Service Account

This app requires a pre-configured service account to operate. Please follow the procedure outlines
at [this link](https://support.google.com/a/answer/7378726?hl=en) to create a service account.\
The following API will need to be enabled:

- Bigquery API

At the end of the creation process, the admin console should ask you to save the config as a JSON
file. Copy the contents of the JSON file in the clipboard and paste it as the value of the "Contents
of Service Account JSON file" asset configuration parameter. Double check to make sure that the
"project_id" is the same project being used with BigQuery.

### Roles

Once the service account has been created, you will then need to give the account the correct role.
To do this, find "IAM & admin" on the menu to the left on the Google Cloud Console homepage. From
there, find your service account, and give it the role "Bigquery Admin".

Package 'pyasn' has license 'MIT' with status 'needs revision'

### Configuration variables

This table lists the configuration variables required to operate Big Query. These variables are specified when configuring a Big Query asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**key_json** | required | password | Contents of Service Account JSON file |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[list tables](#action-list-tables) - List Tables <br>
[get results](#action-get-results) - Get results from a job started with 'run query' <br>
[run query](#action-run-query) - Run a Query

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list tables'

List Tables

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**dataset** | optional | Only list tables in this dataset | string | `bigquery dataset` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.dataset | string | `bigquery dataset` | |
action_result.data.\*.dataset_id | string | `bigquery dataset` | company_dataset |
action_result.data.\*.full_table_id | string | | my-company-project-513002:company_dataset.test_table_1 |
action_result.data.\*.project_id | string | | my-company-project-513002 |
action_result.data.\*.table_id | string | | test_table_1 |
action_result.summary.total_tables | numeric | | |
action_result.message | string | | Successfully listed tables |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get results'

Get results from a job started with 'run query'

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**job_id** | required | Job ID | string | `bigquery job id` |
**timeout** | optional | How long to wait for results | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.job_id | string | `bigquery job id` | 5a9e1de5-342d-4be8-a1e4-93aff49174ff |
action_result.parameter.timeout | numeric | | 30 |
action_result.data.\* | string | | |
action_result.summary.job_id | string | `bigquery job id` | 5a9e1de5-342d-4be8-a1e4-93aff49174ff |
action_result.summary.num_rows | numeric | | 1000 |
action_result.message | string | | Successfully retrieved results from Query |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'run query'

Run a Query

Type: **investigate** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query** | required | Query to run | string | `bigquery query` |
**timeout** | optional | How long to wait for results | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.query | string | `bigquery query` | SELECT weight_pounds, state, year, gestation_weeks FROM `bigquery-public-data.samples.natality` LIMIT 1000; |
action_result.parameter.timeout | numeric | | 1 |
action_result.data.\* | string | | |
action_result.summary.job_id | string | `bigquery job id` | 5a9e1de5-342d-4be8-a1e4-93aff49174ff |
action_result.summary.num_rows | numeric | | 1000 |
action_result.message | string | | Successfully retrieved results from Query |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2025 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
