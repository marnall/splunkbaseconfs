# Microsoft SQL Server

Publisher: Splunk <br>
Connector Version: 2.3.8 <br>
Product Vendor: Microsoft <br>
Product Name: Microsoft SQL Server <br>
Minimum Product Version: 6.3.0

This app supports investigative actions against a Microsoft SQL Server

This app will ignore the HTTP_PROXY and HTTPS_PROXY environment variables, as it does not use HTTP
to connect to the database.\
Below are the default ports used by Microsoft-SQL-Server.

|         Service Name | Port | Transport Protocol |
|----------------------------------------------|------|--------------------|
|          **Microsoft-SQL-Server (ms-sql-s)** | 1433 | tcp |
|          **Microsoft-SQL-Server (ms-sql-s)** | 1433 | udp |

## LGPL

This app uses the pymssql module, which is licensed under the Free Software Foundation (FSF).

## Notice for usage on RHEL FIPS system

You might have to follow the instructions [here](https://access.redhat.com/solutions/7035895)
and remove pymssql dependency found in \<path_to_phantom>/apps/microsoftsqlserver\_\*/dependencies
on your instance or downgrade to an earlier version to use this connector on RHEL system with FIPS enabled

### Configuration variables

This table lists the configuration variables required to operate Microsoft SQL Server. These variables are specified when configuring a Microsoft SQL Server asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**host** | required | string | Database hostname or IP Address |
**database** | required | string | Database name |
**username** | required | string | Username |
**password** | required | password | Password |
**port** | optional | numeric | Database Service Port |
**encryption** | optional | string | TLS encryption mode for the database connection |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[list columns](#action-list-columns) - List all the columns in a table <br>
[list tables](#action-list-tables) - List all the tables in the database <br>
[run query](#action-run-query) - Run a query against a table or tables in the database

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list columns'

List all the columns in a table

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**table_name** | required | Table Name | string | `mssql table name` |
**table_schema** | optional | Table Schema | string | `mssql table schema` |
**host** | optional | Optional database hostname or ip address | string | `hostname` `host` |
**database** | optional | Optional database name | string | `mssql database name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.database | string | `mssql database name` | testdb |
action_result.parameter.host | string | `hostname` `host` | 8.8.8.8 |
action_result.parameter.table_name | string | `mssql table name` | TestTable |
action_result.parameter.table_schema | string | `mssql table schema` | testbo |
action_result.data.\*.CHARACTER_MAXIMUM_LENGTH | numeric | | 10 |
action_result.data.\*.CHARACTER_OCTET_LENGTH | numeric | | 10 |
action_result.data.\*.CHARACTER_SET_CATALOG | string | | |
action_result.data.\*.CHARACTER_SET_NAME | string | | iso_1 |
action_result.data.\*.CHARACTER_SET_SCHEMA | string | | |
action_result.data.\*.COLLATION_CATALOG | string | | |
action_result.data.\*.COLLATION_NAME | string | | SQL_Latin1_General_AS |
action_result.data.\*.COLLATION_SCHEMA | string | | |
action_result.data.\*.COLUMN_DEFAULT | string | | |
action_result.data.\*.COLUMN_NAME | string | | col1 |
action_result.data.\*.DATA_TYPE | string | | char |
action_result.data.\*.DATETIME_PRECISION | numeric | | |
action_result.data.\*.DOMAIN_CATALOG | string | `domain` | |
action_result.data.\*.DOMAIN_NAME | string | `domain` | |
action_result.data.\*.DOMAIN_SCHEMA | string | `domain` | |
action_result.data.\*.IS_NULLABLE | string | | NO YES |
action_result.data.\*.NUMERIC_PRECISION | numeric | | |
action_result.data.\*.NUMERIC_PRECISION_RADIX | numeric | | |
action_result.data.\*.NUMERIC_SCALE | numeric | | |
action_result.data.\*.ORDINAL_POSITION | numeric | | 1 |
action_result.data.\*.TABLE_CATALOG | string | | testdb |
action_result.data.\*.TABLE_NAME | string | `mssql table schema` | TestTable |
action_result.data.\*.TABLE_SCHEMA | string | `mssql table schema` | testbo |
action_result.summary.dataset:0:columns | numeric | | 23 |
action_result.summary.dataset:0:rows | numeric | | 1 |
action_result.summary.num_columns | numeric | | 4 |
action_result.summary.num_datasets | numeric | | 1 |
action_result.message | string | | Successfully listed columns |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list tables'

List all the tables in the database

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**table_schema** | optional | Table Schema | string | `mssql table schema` |
**host** | optional | Optional database hostname or ip address | string | `hostname` `host` |
**database** | optional | Optional database name | string | `mssql database name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.database | string | `mssql database name` | testdb |
action_result.parameter.host | string | `hostname` `host` | |
action_result.parameter.table_schema | string | `mssql table schema` | testbo |
action_result.data.\*.TABLE_CATALOG | string | | testdb |
action_result.data.\*.TABLE_NAME | string | `mssql table name` | TestTable |
action_result.data.\*.TABLE_SCHEMA | string | `mssql table schema` | testbo |
action_result.data.\*.TABLE_TYPE | string | | TEST TABLE |
action_result.summary.dataset:0:columns | numeric | | 4 |
action_result.summary.dataset:0:rows | numeric | | 1 |
action_result.summary.num_datasets | numeric | | 1 |
action_result.summary.num_tables | numeric | | 4 |
action_result.message | string | | Successfully listed tables |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'run query'

Run a query against a table or tables in the database

Type: **investigate** <br>
Read only: **False**

It is recommended to use the <b>format_vars</b> parameter when applicable. For example, if you wanted to find a specific IP, you could set <b>query</b> to a formatted string, like "select * from my_hosts where ip = %s" (note the use of %s), and set <b>format_vars</b> to the IP address. This will ensure the inputs are safely sanitized and avoid SQL injection attacks. Regardless of the type of input it's expecting, the only format specifier which should be used is %s.<br>Setting <b>no_commit</b> will make it so the App does not commit any changes made to the database (so you can ensure it's a read only query).<br><br>The <b>format_vars</b> parameter accepts a comma seperated list. You can escape commas by surrounding them in double quotes, and escape double quotes with a backslash. Assuming you have a list of values for the format vars, you can employ this code in your playbooks to properly format it into a string:<br> <code>format_vars_str = ','.join(['"{}"'.format(str(x).replace('\\\\', '\\\\\\\\').replace('"', '\\\\"')) for x in format_vars_list])</code>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query** | required | Query string | string | `sql query` |
**format_vars** | optional | Comma separated list of variables | string | |
**no_commit** | optional | Do not commit changes to the Database | boolean | |
**non_query** | optional | Do not run this command in a transaction | boolean | |
**datetime_to_iso8601** | optional | Convert column types of datetime to iso8601 | boolean | |
**default_to_string** | optional | Convert any non-standard column types to string; ie. datetime | boolean | |
**add_datasets_as_rows** | optional | Run query will return each dataset as a separate row in the action result | boolean | |
**host** | optional | Optional database hostname or ip address | string | `hostname` `host` |
**database** | optional | Optional database name | string | `mssql database name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.add_datasets_as_rows | boolean | | False |
action_result.parameter.database | string | `mssql database name` | testdb |
action_result.parameter.datetime_to_iso8601 | boolean | | False |
action_result.parameter.default_to_string | boolean | | False |
action_result.parameter.format_vars | string | | |
action_result.parameter.host | string | `hostname` `host` | 8.8.8.8 |
action_result.parameter.no_commit | boolean | | False True |
action_result.parameter.non_query | boolean | | False |
action_result.parameter.query | string | `sql query` | select * from dbo.TestTable |
action_result.data.\*.\_\_name_not_provided\_\_0 | string | | |
action_result.data.\*.age | numeric | | 10 |
action_result.data.\*.baz | string | | comma, comma, quote \\" end quote \\" test, |
action_result.data.\*.bod | numeric | | 20 |
action_result.data.\*.created_at | string | | 2020-12-23 15:23:44 |
action_result.data.\*.dataset | string | | |
action_result.data.\*.dataset.\*.age | numeric | | 10 |
action_result.data.\*.dataset.\*.bod | numeric | | 20 |
action_result.data.\*.dataset.\*.created_at | string | | 2020-12-23 15:23:44 |
action_result.data.\*.dataset.\*.float_column | string | | 3.4000 |
action_result.data.\*.dataset.\*.name | string | | runbook |
action_result.data.\*.dataset.\*.petname | string | | "runbook" |
action_result.data.\*.description | string | | |
action_result.data.\*.description.age.type_code | numeric | | 3 |
action_result.data.\*.description.bod.type_code | numeric | | 3 |
action_result.data.\*.description.created_at.type_code | numeric | | 4 |
action_result.data.\*.description.float_column.type_code | numeric | | 5 |
action_result.data.\*.description.mydate.type_code | numeric | | 4 |
action_result.data.\*.description.name.type_code | numeric | | 1 |
action_result.data.\*.description.petname.type_code | numeric | | 1 |
action_result.data.\*.float_column | string | | 3.4000 |
action_result.data.\*.name | string | | runbook |
action_result.data.\*.petname | string | | "runbook" |
action_result.summary.dataset:0:columns | numeric | | 1 |
action_result.summary.dataset:0:rows | numeric | | 1 |
action_result.summary.num_datasets | numeric | | 1 |
action_result.summary.num_rows | numeric | | 6 |
action_result.message | string | | Successfully ran query |
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
