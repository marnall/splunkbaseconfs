
Order of operations.

1.	If you have not already set your *****SPLUNK_HOME environment***** variable on the server where Splunk resides you will need to do so prior to utilizing the custom 
    alert action within this application.  
	
2.	Mark all applicable knowledge objects with their intended status.  Review the video on the User KO Disablement dashboard for examples if necessary.

3.	After all applicable knowledge objects have been properly identified, go to the Lookup Generator dashboard located under the Admin Dashboards dropdown.  
    Only users with the admin role assigned to them will be able to view this dashboard.

4.	Go to Settings > Searches, reports, and alerts and enable the saved search KO Disablement, which is the only saved search associated with this application.
		a.  Schedule the saved search to run a time applicable to your Splunk environment.
	
5.	Once the saved search has ran, for some of the objects to reflect as disabled/enabled or deleted an admin will need to run debug/refresh in order to see the results properly 
    configured within the GUI.  
		a.	You can do this by running:  https://<IP Address of Splunk instance>:<PortNumber>/en-US/debug/refresh 
		b.	For example:  http://127.0.0.1:8000/en-US/debug/refresh
		c.	Additionally, you could download the "Add-on Debug Refresh" application from Splunkbase (https://splunkbase.splunk.com/app/1871).  This app can be used to reload 
			changed configs on the fly so you can **test and validate** them. It provides a custom search command `refresh` which reloads Splunk Configurations.

6.  The script will also create a backup of the applications modifed and place them in the ko_disablement/tmp directory and seperate them based on the owner of the KO being modifed.

7.  NOTE:  If you select/intend to modifed ALL of the KOs listed and there are multiple pages, only the KOs currently displayed within the table will get added to the lookup.  

