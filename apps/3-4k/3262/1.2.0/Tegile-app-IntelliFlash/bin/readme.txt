This folder contains:

Python scripts:


	cfg_array_lst.py:  Executed by the user (see documentation).
		Creates 3 files:
			…/local/MstrCfg.csv:  preserves configured array info, read only by the config script (cfg_array_lst.py)

			…/local/arrays.csv:  list of controller ip and encoded credentials, read by the collection script (tegilecollect.py)

			…/lookups/arraylookuplist.csv:  used by Splunk to create the ArrayName field by cross-referencing controller IP with controller 
			  name (specified by the user when running the config script)

		Execute this script as Splunk so it has access to the Splunk env. variables:
	  	$SPLUNK_HOME/bin/splunk cmd python $SPLUNK_HOME/etc/apps/ Tegile-app-IntelliFlash/bin/cfg_array_lst.py


  
	tegilecollect.py:  Executed by Splunk.  Polls the specified array addresses (via HTTPS) and 
		writes information to a Splunk index (“tegilearray”).

Supporting modules:
	The "python2" subfolder contains python modules that are required by the scripts listed above.

See app documentation for more details


