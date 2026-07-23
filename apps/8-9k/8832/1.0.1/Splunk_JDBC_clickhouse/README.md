# Splunk DBX Add-on for Clickhouse

## Overview
This is a custom JDBC driver Add-on that enables Splunk DB Connect to communicate with ClickHouse databases (including ClickHouse Cloud). Since Splunk does not officially provide a ClickHouse driver Add-on by default, this custom Add-on packages the necessary JDBC driver and configuration files into a format that can be easily installed on Splunk Enterprise or Splunk Cloud.

## Changes & Specifications
- **Packaged JDBC Driver**: Includes the official `clickhouse-jdbc-all-0.9.8.jar` (v0.9.8) downloaded directly from Maven Central.
- **Unified Driver Artifact**: Uses the shaded `all` artifact which encapsulates the ClickHouse driver and all required dependencies into a single JAR file. This resolves classloader isolation issues within Splunk DB Connect (such as `NoClassDefFoundError` occurring when splitting dependencies across multiple JARs).
- **Configuration Added**: Pre-configured `db_connection_types.conf` to automatically register ClickHouse as a supported database type in the Splunk DB Connect UI.

## Installation
1. Install this Add-on via the Splunk Web UI ("Manage Apps" -> "Install app from file").
2. Navigate to the **Splunk DB Connect** App.
3. Go to **Configuration > Databases > Drivers** and click **Reload**.
4. Verify that "ClickHouse" appears in the list with a green checkmark indicating successful installation.
