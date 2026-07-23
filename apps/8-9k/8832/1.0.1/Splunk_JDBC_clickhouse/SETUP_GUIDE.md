# ClickHouse Connection Setup Guide (Splunk DB Connect)

This document provides step-by-step instructions for connecting Splunk DB Connect to ClickHouse Cloud using the custom Splunk DBX Add-on for Clickhouse.

## 1. Prerequisites
1. Ensure the **Splunk DB Connect** App is installed and its Task Server is running properly.
2. Ensure this custom Add-on (`splunk-dbx-addon-for-clickhouse_100.tgz`) is installed in your Splunk environment.
3. Have your ClickHouse Cloud connection details ready (Host URL, Username, Password).
   - e.g., Host: `xxxxxx.clickhouse.cloud`, Port: `443`, Username: `default`

## 2. Create an Identity
Register the credentials that DB Connect will use to log into ClickHouse.

1. Open the **Splunk DB Connect** App in Splunk.
2. Navigate to **Configuration > Databases > Identities**.
3. Click **[New Identity]** in the top right.
4. Fill in the following fields and click **[Save]**:
   - **Identity Name**: Any chosen name (e.g., `clickhouse_cloud_id`)
   - **Username**: ClickHouse username (e.g., `default`)
   - **Password**: ClickHouse password

## 3. Create a Connection
Set up the connection to your ClickHouse Cloud endpoint.

1. Navigate to **Configuration > Databases > Connections**.
2. Click **[New Connection]** in the top right.
3. Fill in the following fields:
   - **Connection Name**: Any chosen name (e.g., `clickhouse_cloud`)
   - **Identity**: Select the Identity you just created (e.g., `clickhouse_cloud_id`)
   - **Connection Type**: Select **`ClickHouse`**
   - **Timezone**: Database timezone (usually `UTC`)
   - **Host**: ClickHouse Cloud endpoint (e.g., `xxxxxx.gcp.clickhouse.cloud`)
   - **Port**: **`443`** (The default secure port for ClickHouse Cloud)
   - **Default Database**: `default` (or your specific database name)

   > **Note on Ports**: ClickHouse Cloud accepts HTTPS connections on both port `443` and `8443`. This Add-on defaults to `443` because **Splunk Cloud blocks outbound traffic on non-standard ports** (including `8443`) by default. Port `443` is universally allowed on both Splunk Enterprise and Splunk Cloud environments. If you are using Splunk Enterprise on-premise, you may also use port `8443`.
4. **[CRITICAL] Enable SSL**: Ensure you **check this box**.
   - This automatically appends `?ssl=true` to the JDBC URL, which is required by ClickHouse Cloud.
5. Click **[Save]**. If the configuration is correct, a green "Success" notification will appear.

## 4. Test the Connection (SQL Explorer)
Verify the connection by executing a query.

1. Go to **Data Lab > SQL Explorer** from the top menu.
2. Select your newly created connection (`clickhouse_cloud`) from the **Connection** dropdown.
3. Enter the following test query:
   ```sql
   SELECT * FROM system.tables LIMIT 10
   ```
4. Click **[Execute SQL]**.
5. If the query results appear at the bottom of the screen, the connection is successfully established!
