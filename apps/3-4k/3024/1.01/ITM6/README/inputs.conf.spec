#Copyright (C) 2014 Kieren Crossland
[itm6_sql_input://<collection_name>]
*This is how the itm6 data collector is configured

tems = <value>
*Name of the TEMS connection to use for this query

at = <value>
*The TEMS to run the query at

system = <value>
*MSL or Node to query

table = <value>
*Name of ITM6 table

fields = <quoted string list>
*List of fields to query from table

clause = <value>
*Add WHERE, ORDER/GROUP BY etc here.

timeout = <value>
*Timeout value for the SOAP query

[itm6_obj_input://<collection_name>]
*This is how the itm6 data collector is configured

tems = <value>
*Name of the TEMS connection to use for this query

target = <value>
*MSL or Node to query

object = <value>
*Name of ITM6 object

attributes = <quoted string list>
*List of attributes to query from object

afilter = <f;op;v:f;op;v list>
*List of values in format:
*attribute1;operator1;value1:attribute2;operator2;value2:...

history = <value>
*Collect historical data

[itm6_daily_health_check://<collection_name>]
*This is how the itm6 data collector is configured

tems = <value>
*Name of the TEMS connection to use for this query


[itm6_dash_input://<collection_name>]

tems = <value>
*The name of the TEMS connection to use for this query.

datasource = <value>
*The DDP Data Source

sourcetoken = <value>
*MSL or Node to query.

dataset = <value>
*The DDP Data Set

properties = <value>
*The short name of the properties you wish to return, defaults to all

condition = <value>
*Set a condition for the query

fieldformat = value
*Display field labels or their long name