# Introduction
This is a custom add-on that aims to give the Splunk Enterprise administrators control over the files on the local storage of Splunk Enterprise instances. The app can search for files/directories based on RegEx patterns and can remove them based on aging criteria.

# Deployment
The app is available in SPL and TAR bundles and these can be deployed quite easily through the GUI of single instance Splunk Enterprise installations. For distributed instances read below.

## Non-clustered distributed environment
For non-clustered environments it is a matter of adding the un-archived bundle directory to the "deployment-apps" in the Deployment Server (DS) of the environment, followed by adding a server class mapping, either through the GUI of the DS or through editing the "serverclass.conf" file.

## Clustered distributed environment
For environments with Indexer clustering the add-on should be first sent to the Cluster Master (CM) and then distributed via bundle replication to the Indexers/Peers. Every consequent configuration of the app should be performed via the CM. This will ensure that configuration changes are pushed to the peers gracefully and they are restarted one by one, without losing service availability.

# Configuration scenarios

## Example1 - Configure frozen bucket housekeeping

Housekeeping is performed on an index-level using the file/directory removal tool "TA-throw-away". You need to configure new stanza for every new index that is configured to keep data in frozen state for a certain time period. In case of distributed environment with indexer cluster you should perform this directly on the Cluster Master in order to deploy the configurations to all the cluster members.

1. Login to your Cluster Master (for indexer cluster) or your Indexer (for non-clustered indexers) with your SSH client.
2. Create/Edit the "inputs.conf" file in your "TA-throw-away" add-on:

`sudo vi /opt/splunk/etc/master-apps/TA-throw-away/local/inputs.conf`

3. Use the template below to add a new housekeeping stanza in the "inputs.conf" file of the "TA-throw-away" for your index, e.g. for index "splunk_index":

_[remove_files_directories://splunk_index]  
index = _audit  
interval = 86400  
pattern = (d|r)b_\d{10,11}_\d{10,11}_.*  
retention_policy = 1  
retention_period = 32832000  
timestamp_location = name  
working_directory = /data1/frozen/splunk_index/frozendb/  
disabled = 0_  

4. Save the file.
5. For clustered indexers go back to the GUI of the Cluster Master, in the "Indexer Clustering" menu. 
   * Choose "Edit" → "Configuration Bundle Actions". 
   * Press the "Validate and Check Restart" button and wait for the process to finish. You should expect to see a result like the one shown below:  
   ![2020-10-05_10-15-37.png](.attachments/2020-10-05_10-15-37-5b84bd7a-c0aa-46ed-87b8-b1d5b42b0338.png)
    * Next, you need to press the "Push" button and wait the package to be deployed to each peer (might also perform automatic rolling restart).
    * After completing the restart, you can perform a search in the "_audit" index for events that point to directories being removed (if objects from the index frozen directory qualify). E.g.:  
   ![2020-10-05_10-17-14.png](.attachments/2020-10-05_10-17-14-d0fabb7d-f7b2-4446-8433-a075023c3efb.png)  
   * There's a known bug in Splunk, which prevents custom Python libraries to be loaded unless they are placed under `"$SPLUNK_HOME$/etc/apps/"`. This will cause issues for "TA-throw-away" in clustered indexers. To alleviate the problem, you must access every indexer in the cluster through SSH client and create a symbolic link like below:  
   `sudo ln -s /opt/splunk/etc/slave-apps/TA-throw-away/ /opt/splunk/etc/apps/TA-throw-away`

## Example2 - Adding new cluster members

In order for the "TA-throw-away" add-on to work properly, you need to deploy it from the cluster master (which will happen automatically  when you add a cluster member to the cluster). Then you also need to address a known limitation in Splunk, which is Splunk does not look for custom python code if the application that contains it is installed under anything different than `"$SPLUNK_HOME$/etc/apps/"`. This is exactly what happens when the custom add-on is deployed from the Cluster Master - it ends up installed under `"$SPLUNK_HOME$/etc/slave-apps"`. To work around this issue you should create a symbolic link under `"$SPLUNK_HOME$/etc/apps"` that points to the app in `"$SPLUNK_HOME$/etc/slave-apps"`, e.g.:  
`sudo ln -s /opt/splunk/etc/slave-apps/TA-throw-away/ /opt/splunk/etc/apps/TA-throw-away`

# Configuration details
The snippet below shows complete documentation **(please, read it carefully!)** on the parameters used in the "inputs.conf" file:  

```
#Replace all {vars} with your own and read the description carefully! Data will be deleted from disk!!!
#
#First is the stanza definition
#[remove_files_directories://{name_of_input}]
#
#Then configure the index, where events will be sent for storage. These events are holding the names of files/directories that were deleted.
#index = {name_of_index}
#
#The following parameter sets the frequency with which the input will be executed. Measured in seconds.
#interval = 86400
#
#Use ordinary RegEx pattern in the following parameter in order to select only matching files/directories for removal.
#E.g. (d|r)b_\d{10,11}_\d{10,11}_.* for Splunk index buckets.
#pattern = {RegEx}
#
#The next parameter will be used in order to remove files/directories based on their age. "1" means "enabled".
#retention_policy = 1
#
#The retention period is measured in seconds. It will be used in order to tell what is the maximum age of files/directories.
#Files/directories that are older than the maximum will be removed. E.g. if set to "86400" (these are seconds) this means that
#if the file/directory is older than 24 hours it will be qualified for removal.
#retention_period = 3600
#
#Timestamp location can be found in the name (in case of Splunk index buckets) or in the file/directory "last modified" attribute.
#Set to "name" if you would like to work with bucket names, or "last_modified" if you'd like to use the attribute of the file.
#timestamp_location = name
#
#Finally, provide the absolute path where you wish the input to look for files/directories. If you are using Splunk index buckets,
#make sure you provide the location to the frozendb directory for the particular index. Otherwise you might remove stuff which is currently being used…
#E.g. /opt/splunk/var/lib/splunk/defaultdb/frozendb/ for deleting frozen buckets from the "main" index. Path should always end with "/"!
#working_directory = {absolute_path}
#
#Use "1" if you wish to disable the input
#disabled = 0
```
