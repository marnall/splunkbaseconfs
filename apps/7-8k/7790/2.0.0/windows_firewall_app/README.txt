# README

## To Do

1) Install the app in your indexers/search nodes, 

2) Setup the app from the web ui setup wizard. specify the index intended to receive the hosts firewall data.

2) Install the package or just copy and adapt the inputs.conf file content into all your nodes (forwarders...) collecting the Windows Firewall traffic log. Modify the index value according to your data sources indexing policy. Don't forget to reload conf or restart the Splunk service where the inputs.conf was imported. 

3) Activate the firewall traffic logging on the windows machines to be monitored.

 	How to do :
		  	- Press Windows + R to open the Run dialog.
			- Type wf.msc and press Enter. This opens the Windows Firewall with Advanced Security console.
			- In the console, right-click on Windows Defender Firewall with Advanced Security on Local Computer and select Properties.
			- Configure Logging for Each Profile tabs. We recommand to extend the limit size to at least 20MB
			


We provided an ip exclusion macro based on lookup file, to help remove noise detection and false positive. feel free to enrich the lookup file whitelist_ip_ranges.csv .

You can make search using this request :  

					- For traffic only events :

					   index IN `windows_firewall_index` sourcetype="windows:pfirewall" `ip_whitelist`
						
					- For firewall change only events

					   index IN `windows_firewall_index` source="*WinEventLog:Microsoft-Windows-Windows Firewall With Advanced Security/Firewall" 
						
					   


## License

Refer to https://www.splunk.com/en_us/legal/splunk-general-terms.html for licensing terms