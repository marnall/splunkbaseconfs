Summary:

The FrozenFreeUp app allows you to remove the archived frozen data from Splunk indexer instance. The app deletes the db_ and rb_ folders under Frozen path with specified age according to the configurations in the inputs.conf file.

This app should be installed on the Indexer servers. Currently this app supports Indexers installed on nix servers.


Important Note: 

	Always consider organization’s data retention policies while setting up the configurations.
	
	Make sure to give the exact Frozen path configured in Splunk. Wrong path may lead to the removal of unintended data.


Advantages:

Deleting the frozen buckets in Splunk has many advantages which are no limited to the following

•	Storage optimization by freeing up disk space. 
•	Enhanced data processing efficiency by reallocating resources.
•	Performance improvement in data retrieval 
•	Reduces the complexity of data backup 
•	Maintains a high level of data integrity.  
