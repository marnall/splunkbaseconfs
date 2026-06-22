cribl-decrypt Splunk Add-On
=============

Splunk Add-On that provides:
* A custom command to decrypt data encrypted by Cribl Stream
* Allows Splunk Admins to upload Cribl Stream key bundles and Splunk Users (with the correct permissions) to decrypt data using them.

**NOTE**: This Add-on only works on Linux hosts! It will not work on Windows because Splunk does not ship the required Python libraries OOB. 

Configuration
---------
Cribl Stream:
1. Export key bundle from cribl stream by going to Group Settings > Security > Encryption Keys and clicking "Get Key Bundle"
2. Repeat for each Worker Group that is sending encrypted data to Splunk

Cribl Decrypt Add-on for Splunk:
1. Go to the Key Management page in the Cribl Decrypt app and upload the key bundle. User will need `admin_all_objects` capability to upload the key bundle (default for `admin` role).
2. Refreshing the page will show the uploaded keys in the list. Keys are stored in Splunk Password storage.
3. To delete a key, enter key id in Delete a key field and click Delete.

Usage
---------
In any search page, use the `cribldecrypt` command to decrypt data encrypted with Cribl Stream. Users will need to have the `list_storage_passwords` capability to access the keys (default for `admin` role).
```
index=<index_name> | cribldecryptv2
```

Note: Since this command requires access to the Search Head's REST interface, it is technically a [dataset processing command](https://docs.splunk.com/Splexicon:Datasetprocessingcommand), which means that it should appear as late as possible in the search string.

Roles
---------
Only Admins by default can add or delete keys. They can also decrypt using the `cribldecryptv2` search command.

Users need the `role_cribldecrypt_key_access` role which provides the permission to list backend stored keys. This role allows them to decrypt data using the `cribldecrypt` search command but they *cannot* add or delete keys.

Important Nortice About "Legacy" cribldecrypt Command
---------
The cribldecrypt command included in version 1.x of the Cribl Decrypt App is considered "legacy" as of version 2.0 because it relies on JavaScript and Splunk's built-in node.js support. As of Splunk Enterprise 10.2 (and Splunk Cloud 10.1), node.js support has been removed, which means that the legacy command no longer works in those versions.

Migration from Version 1.x to 2.0
---------
Version 2.x of the Cribl Decrypt App introduces a new command, cribldecryptv2, which is written in Python so it will work with Splunk Enterprise 10.2 and above. The old command, cribldecrypt, is still available for backward compatibility, but it is recommended thay you switch to the new command - especially if you plan on upgrading to Splunk Enterprise 10.2 (or Splunk Cloud 10.1)

To migrate existing searches, replace instances of cribldecrypt with cribldecryptv2 in your saved searches, dashboards, reports, etc.

It is recommended that you test the new command in your environment first to ensure it works as expected before fully switching over. It is possible that the output might differ slightly between the two versions.

