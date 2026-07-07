 Introduction
--------------

This add-on dedicated to PostgreSQL monitoring. It is intended to provide deep dive into PostgreSQL database internals and metrics. Most of information is a base for App for Postgres appliaction with fancy dashboards and useful macros on board

 Prerequisites
---------------

You need to have psycopg2 python module installed on your system as well as python itself (version 2.6 or later).


 Installation
---------------

The Add-on for PostgreSQL provides data inputs for PostgreSQL server which facilitate retrieving data from PostgreSQL standard statistic views (as pg_stat and pg_statio table) and from standard PostgreSQL server logs. The Add-on for PostgreSQL requires Python (at least version 2.6) and psycopg2 python library installed on the system.

To start the PostgresSQL server monitoring you should follow theese steps:

  * Create database user dedicated to read data from PostgreSQL statistic views.

  * Enable extensive query logging in PostgreSQL. To do so you have to change the following entries in your postgresql.conf
    * log_file_mode = 640 – change in order to access PostgreSQL logs if Splunk is running on non-root user account, apart of this Splunk user must be in an appropriate supplementary group (default: 600)
    * log_min_duration_statement = 0 – change in order to log all SQL statements executed by the server; the value represents minimal query duration to be recorded by logger; by default logging of SQL statements is disabled at all (default: -1)
    * log_line_prefix = '%m pid=%p database=%d user=%u rhost=%h tid=%v sessionid=%c ' – change in order to provide some useful fields automatically extracted by Splunk (remember of trailing space in the defined string)

     After changes the are applied, restart PostgreSQL server and verify the results in log files.

  * Install the Add-on for Postgres onto the universal forwarder from which you want to collect PostgreSQL data

  * Set database connection parameters. Copy $SPLUNK_HOME/etc/apps/ta-postgres/default/postgrestats.conf to $SPLUNK_HOME/etc/apps/ta-postgres/local/postgrestats.conf and customize the connection options.

  * Turn on your PostgreSQL log files monitoring by adding "monitor" stanza in $SPLUNK_HOME/etc/apps/ta-postgres/local/inputs.conf. Let's say your log files are in: /var/lib/pgsql/9.3/data/pg_log directory and the name of each file log is similar to: postgres-Mon.log. In such case your monitor stanza can look like this:

    [monitor:///var/lib/pgsql/9.3/data/pg_log/postgresql-*.log]
    disabled = false
    sourcetype = postgresql

  After changes are applied, restart Splunk Universal Forwarder


