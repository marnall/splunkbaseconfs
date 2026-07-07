##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
## Copied from db-connect repository

[<name>]
description = <string>
# optional
# short description about the input template

interval = <integer|string>
# required
# interval to fetch data from DB and index them in Splunk
# It could be a number of seconds or a cron expression

sourcetype = <string>
# required
# source type associated to events indexed

mode = [batch|rising]
# required
# Operational mode.

query = <string>
# required
# SQL statement to retrieve data from the database

rising_column_index = <integer>
# required in rising mode
# The column number of the rising column you specified (1-based).

input_timestamp_column_index = <integer>
# required when the index_time_mode is dbColumn
# The column number of the timestamp column you specified (1-based).

input_timestamp_format = <value>
# optional
# specify the format of input timestamp column, in JavaSimpleDateString format.
# with index_time_mode as dbColumn, if this property is provided then DBX will use ResultSet#getString to get the value
# and try to parse the timestamp with given format, else if this property is not persent DBX will try to use ResultSet#getTimestamp
# to get the timestamp.

index_time_mode = [current|dbColumn]
# required
# Specifies how to set the index time.
# current: use current time as index time
# dbColumn: use a DB column as index time.

input_type = [event|metric]
# optional
# Defines which type of metric template tracks. If not given default value is event.

connection_type = <string>
# optional
# Defines for which connection type the template will be shown. If empty - will be shown for all connections.
