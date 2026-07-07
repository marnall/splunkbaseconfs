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
