# MySQL

Publisher: Splunk <br>
Connector Version: 2.1.9 <br>
Product Vendor: Oracle Corporation <br>
Product Name: MySQL <br>
Minimum Product Version: 5.1.0

This app supports investigative actions against a MySQL database

### Configuration variables

This table lists the configuration variables required to operate MySQL. These variables are specified when configuring a MySQL asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**host** | required | string | Hostname or IP address |
**username** | required | string | Username |
**password** | required | password | Password |
**database** | required | string | Database Name |
**verify_ssl** | optional | boolean | Verify server certificate |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[list columns](#action-list-columns) - List the columns of a table <br>
[list tables](#action-list-tables) - List the tables in the database <br>
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

List the columns of a table

Type: **investigate** <br>
Read only: **True**

Describes the structure of a table in the database by displaying information about its columns. The only tables which it will be able to query for must have a name composed of only alphanumeric characters + '\_' and '$'.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**table_name** | required | Name of table | string | `mysql table name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.table_name | string | `mysql table name` | contact |
action_result.data.\*.Default | string | | Default Value |
action_result.data.\*.Extra | string | | auto_increment |
action_result.data.\*.Field | string | | id |
action_result.data.\*.Key | string | | PRI |
action_result.data.\*.Null | string | | NO |
action_result.data.\*.Type | string | | int(11) |
action_result.summary.total_rows | numeric | | 4 |
action_result.message | string | | Total rows: 4 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list tables'

List the tables in the database

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.table_name | string | `mysql table name` | contact |
action_result.summary.total_rows | numeric | | 1 |
action_result.message | string | | Total rows: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'run query'

Run a query against a table or tables in the database

Type: **investigate** <br>
Read only: **False**

It is recommended to use the <b>format_vars</b> parameter when applicable. For example, if you wanted to find a specific IP, you could set <b>query</b> to a formatted string, like "select * from my_hosts where ip = %s" (note the use of %s), and set <b>format_vars</b> to the IP address. This will ensure the inputs are safely sanitized and avoid SQL injection attacks. Regardless of the type of input it's expecting, the only format specifier which should be used is %s.<br>Setting <b>no_commit</b> will make it so the App does not commit any changes made to the DB (So, you can ensure its a run only query). However, many statements on MySQL will implicitly commit (as can be read about <a href="https://dev.mysql.com/doc/refman/5.6/en/implicit-commit.html">here</a>) meaning that this parameter will have no effect in cases where these statements are used.<br><br>The <b>format_vars</b> parameter accepts a comma seperated list. You can escape commas by surrounding them in double quotes, and escape double quotes with a backslash. Assuming you have a list of values for the format vars, you can employ this code in your playbooks to properly format it into a string:<br> <code>format_vars_str = ','.join(['"{}"'.format(str(x).replace('\\\\', '\\\\\\\\').replace('"', '\\\\"')) for x in format_vars_list])</code>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query** | required | Query string | string | `sql query` |
**format_vars** | optional | Comma seperated list of variables | string | |
**no_commit** | optional | Do not commit changes to database | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.format_vars | string | | 8.8.8.8 |
action_result.parameter.no_commit | boolean | | True False |
action_result.parameter.query | string | `sql query` | select * from my_hosts where ip = %s |
action_result.data.\* | string | | |
action_result.summary.total_rows | numeric | | 6 |
action_result.message | string | | Total rows: 6 |
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
