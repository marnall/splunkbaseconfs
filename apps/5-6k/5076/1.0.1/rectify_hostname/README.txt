This app is intended to be deployed to all of your UFs.
If the host is later ever cloned or renamed,
the app will rewrite the correct hostname in the UF config,
The app will also make the hostname lowercase and shorten it.

Background:
Splunk hardcodes a server's hostname in etc/system/local on first time run.
There is serverName in server.conf, which is used by the Deployment Server.
There is host in inputs.conf, which gets passed to the Indexer.
Sometimes these hardcoded values are not desirable;
Windows hostnames often have mixed case, Nix hosts often contain the FQDN


Description:
-Scripted inputs execute PowerShell and bash scripts on startup
-The script fetches the hostname from OS 
-Converts hostname to lowercase and truncates the suffix
-Replaces text in server.conf and inputs.conf with new hostname if different
-Deletes etc/instance.cfg if needed, to reset the instance id
-Restarts splunk, if needed

Other considerations
-Tested with UFs on Win2008+, RHEL7, Solaris11
-App can be deployed to UFs and permanently left in place
-On Solaris, the script may need editing to point to the GNU tools location
-Do not deploy to a Splunk indexer, especially in a cluster
-Do not deploy to a Domain Controller.  demote, rename, promote instead. 

It is also possible to delete the values from etc/system/local.
Then the UF will fallback to values set in etc/system/default.
The default values are serverName=$HOSTNAME and host=$decideOnStartup.
It is possible to change the app to use these dynamic values.
However, my preference is to normalize the hostnames to make Splunk queries 
less prone to case sensitivity, confusion, and ambiguity to users.

