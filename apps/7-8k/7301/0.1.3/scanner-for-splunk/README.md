# Scanner for Splunk

## What is Scanner for Splunk?
Scanner provides a Splunk app that allows teams to rapidly search their object
storage logs directly from Splunk. 

It introduces two custom search commands system-wide in Splunk: `scanner` and
`scannertable`.

## Use `scanner` to return events
The `scanner` command executes a search query via the Scanner API and returns
the results as events. In Splunk parlance, this is an *events generating*
command.

Example: 

Search for ECS FireLens log events that contain the string token `ERROR` in any
field.

```
| scanner q="%ingest.source_type: 'aws:ecs_firelens' ERROR"
```

## Use `scannertable` to return a table

The `scannertable` command also executes a search query via the Scanner API, but
instead of returning the results as events, it returns the results as a table.
In Splunk parlance, this is a *report generating* command.

This command is helpful in contexts where you want to generate a report, set up
a dashboard widget, or manipulate statistical tables.

Example: 

Compute aggregated counts of CloudTrail log events by eventSource.

```
| scannertable q="%ingest.source_type: 'aws:cloudtrail' | stats by eventSource"
```

## Why use Scanner for Splunk?

Scanner is useful for teams that have a large volume of logs in object storage
and want to search them directly from Splunk.

Scanner is flexible: it provides fast search on many kinds of data formats - no
parsing work required. Formats include JSON, CSV, plaintext, and Parquet.

## How do I get started?

### 1. Start storing your high-volume logs in S3

Using tools like Vector.dev, Cribl, or other log pipeline tools, you can store
your logs in S3 instead of sending them directly to Splunk.

Many tools, like Crowdstrike Falcon Data Replicator and the Github Audit system
can write logs directly to your S3 buckets.

Once you have logs in your S3 buckets, you can start to index them with
Scanner. We support JSON, CSV, Parquet, and plaintext log files. No need to
transform them first. Just point Scanner at your raw log files.

### 2. Configure Scanner to index these high-volume logs in S3

Following Scanner's [S3 integration guide](https://docs.scanner.dev/scanner/indexing-your-logs-in-s3/getting-started),
configure Scanner to index these logs in S3. This allows search queries to
execute at high speed even as data volumes reach hundreds of terabytes or
petabytes.

### 3. Install the "Scanner for Splunk" app into your Splunk instance.

For Splunk Cloud, install "Scanner for Splunk" from Splunkbase.

For Splunk Enterprise, visit *Manage apps* > *Install app from file* and upload
the Scanner for Splunk package. Your Scanner account manager will provide you
instructions to download and install the packaged app.

### 4. Configure API keys

Navigate to the Scanner for Splunk app, and you will see a configuration page.
Enter your Scanner API keys and the URL of your Scanner instance. Each API key
must be associated with a Splunk role. 

When a user executes a Scanner command, all of the Scanner API keys associated
with their Splunk roles are used to authenticate the request. Their permissions
are the union of the permissions of all the API keys.

Scanner API keys are stored in the *storage passwords* feature of Splunk.
Hence, roles that need to use the Scanner commands must have the
`list_storage_passwords` capability.

### 4. Execute `scanner` and `scannertable` queries from within Splunk

Start executing search queries against your high-volume logs in S3 by using the
`scanner` and `scannertable` custom search commands. These commands are available
system-wide.

The commands take a parameter `q`, which must be a query written in Scanner's
query language. 

The query is executed against Scanner's ad hoc queries API. By default, the API
returns the most recent 1000 results in descending timestamp order.
