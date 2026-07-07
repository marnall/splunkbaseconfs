# Splunk Export Data plugin
This is a Splunk plugin providing a custom alert script to export data to disk.
The main reason for this plugin is to have a backup solution for a single instance Splunk configuration.

* Tested on Windows with Splunk 7.2.6

## Need for a simple export tool
Without this tool the advise of Splunk is to use low level disk copy tools to:
* Rotate the hot bucket to warm buckets and back them up. 
* Or to use low level disk copy tools to back up the hot bucket.
In either case it is complicated and/or still leaves the data in the hot bucket vulnerable.

## Output format
The output is in compressed csv.gz format.

## Setup
Go to "Manage Apps -> Install app from file" and upload the file. It is directly ready for use.

## Usage
Before scheduling the action the action can be called directly from a query to test the parameters:
```
index="YOUR_INDEX" | table _time YOUR_FIRST_EXPORT_FIELD YOUR_SECOND_EXPORT_FIELD .. | sendalert export_data param.directory="C:/Backup" param.filename_prefix="YOUR_BACKUP_PREFIX"
```
The table is necessary to prevent all kind of internal fields to pollute the backup file.
When testing make sure preview is turned off, otherwise there will be partial exports next to the final one.
The resulting output will contain created timestamp: YOUR_BACKUP_20190615-114906.csv.gz

Note that there is a time limit on alert action to execute. So prevent heaving queries or export very big batches of data at once.