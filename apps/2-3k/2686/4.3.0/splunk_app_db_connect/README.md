# DB Connect - App

The directory structure of
a [Splunk app](https://dev.splunk.com/enterprise/docs/developapps/createapps/appanatomy/).

## Structure

| Directory | Description                          |
|-----------|--------------------------------------|
| appserver | App implementations                  |
| bin       | Entry points to the app, executables |
| default   | Default configuration files          |
| metadata  | Permission files                     |
| readme    | Documentation files                  |
| static    | App icon and images                  |

## Binary File Declaration

### dbxquery.exe

Splunk Modular Input launcher, what Splunk self-discover (defined in `inputs.conf`) and execute. This
executable is responsible for trigger `dbxquery.jar`. Provided by [Splunk SDK for Java](https://github.com/splunk/splunk-sdk-java/tree/master/launchers).

`dbxquery.jar` provides socket communication that handle `dbxquery` and `dbxlookup` commands.

**DBX Query:**

`| dbxquery query="SELECT version()" connection="My-SQL"`

**DBX Lookup:**

`| dbxlookup connection="My-SQL" query="SELECT id, product FROM customer_order;" "id" AS "order_id" OUTPUT "product" AS "product_name"`

### server.exe

Splunk Modular Input launcher, what Splunk self-discover (defined in `inputs.conf`) and execute. This
executable is responsible for trigger `server.jar`. Provided by [Splunk SDK for Java](https://github.com/splunk/splunk-sdk-java/tree/master/launchers).

`server.jar` provides a Java Rest API with the main DB Connect features:

* Scheduled inputs.
* Scheduled outputs.
* Manage connection.
* Manage identities.
