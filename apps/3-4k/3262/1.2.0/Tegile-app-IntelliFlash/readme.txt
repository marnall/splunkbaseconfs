The Tegile IntelliFlash App for Splunk collects information from Tegile arrays
 and displays it in dashboard to assist in management of these arrays.
 
 Version 1.2.0

Requirements:  
	Splunk version 6.4.1
	Hardware:  12 core @ 2+GHz, 12 GB RAM
	OS: 64-bit Linux or Windows Server 2012

Installation and configuration (see documentation for additional information):

1.  Install on a single-instance Splunk server with Splunk Web App Manager
	 or by extracting the app package in …/splunk/etc/apps.
	 (see documentation for distributed env.)
2.  Use the Setup UI to specify credentials for an array and associated
         information.
3.  Login to Splunk Web, click the Tegile IntelliFlash app for Splunk icon
4.  The app defaults to the Array Information dashboard
	 (which will populate in a few minutes)
5.  You can also view the Snapshot Information dashboard by choosing it from
	 the list of dashboards in the menu

Information displayed includes:
        Pools
        Projects, Volumes, and Shares
        iSCSI and FC init and target groups
        Snapshots

The app consists of the following components:
	Python scripts:
			tegilecollect.py:  Executed by Splunk.  Polls the specified array
			 addresses and writes data to a Splunk index (“tegilearray”).
			 
	Splunk configuration files
			props.conf,  that specifies
				How to break the stream of array data into time-stamped events.
				Search-time field extractions used to populate the dashboards.
			transforms.conf, that specifies
				Path of the ArrayName lookup (…/lookups/arraylookuplist.csv)
			indexes.conf, that specifies
					Name and path of the apps's index.
			inputs.conf, that specifies
					The path of the collection script (tegilecollect.py).
					The interval at which the collection script runs.
					The Splunk sourcetype for the array data (“tegilearray”).
			eventtypes.conf
					Specifies the index and max age of event data to search.
	Splunk views (dashboards)
			Array_information:
				Lists pools, projects, volumes, Shares, iSCSI & FC groups.
			Snapshot_information:
				Lists snapshots by volume.
			
See full documentation for additional details
Contact Splunk@tegile.com for support

