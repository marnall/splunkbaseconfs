# Splunk Add-on for IBM Activity Tracker

[IBM Cloud Activity Tracker](https://www.ibm.com/products/activity-tracker) can be configured to store your IBM Cloud account's control plane logs as objects in an [IBM Cloud Object Storage](https://www.ibm.com/products/cloud-object-storage) bucket. This app can be used to ingest those logs into Splunk.

## Requirements

In order to use this app, you must have:

1. an IBM Cloud account
2. an IBM Cloud Object Storage bucket in that account
3. a Service Credential with read access to objects in that bucket, including [HMAC credentials](https://cloud.ibm.com/docs/cloud-object-storage?topic=cloud-object-storage-uhc-hmac-credentials-main)
4. Activity Tracker configured to route logs to the above bucket, see [Archiving events to IBM Cloud Object Storage](https://cloud.ibm.com/docs/activity-tracker?topic=activity-tracker-archiving-ov).

## How to use

1. Install the app.
2. Launch the app and configure at least one account in the app's **Configuration** tab. This requires HMAC credentials to read from the IBM Cloud Object Storage bucket. These credentials are encrypted and stored.
3. In the app's **Inputs** tab, create at least one input. This input must reference an account created in the previous step to hold the credentials. The input also specifies which bucket to search and which was the last object to be ingested, so logs don't get ingested more than once. Provide an empty string if the app should attempt to ingest _every_ log since the dawn of time.

## Example queries

```
index=ibm severity=critical
index=ibm | timechart count by message
index=ibm | top requestData.request_body.user_name
index=ibm | stats count by initiator.host.address
index=ibm | iplocation initiator.host.address | top City, Country
index=ibm | iplocation initiator.host.address | geostats count by message
```


## Remote debugging

Add the next 4 lines to ibm_cloud_object_storage.py for remote debugging via Visual Studio Code as described in
https://github.com/splunk/vscode-extension-splunk/wiki/Debugging

'import sys, os
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
dbg.enable_debugging(timeout=25)'


Add following lines at 'ref' to enable telnet based debugging with remote_pdb:
import remote_pdb;
remote_pdb.RemotePdb(host="0.0.0.0", port=4444).set_trace()

# Binary File Declaration
* lib/charset_normalizer/md.cpython-39-x86_64-linux-gnu.so - added by uuc framework