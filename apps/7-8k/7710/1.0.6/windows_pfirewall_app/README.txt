# README

## To Do

1) Install the app in your indexers/search heads, 

2) Setup the app from the web ui setup wizard. specify the index intended to receive the pfirewall data, the country where you host the monitored machines with their geolocation latitude & longitude

2) Modify and Copie the inputs.conf file from the package default to all your forwarders/indexers collecting the windows firewall traffic log. Modify the index value according to your environment. don't forget to restart the splunk service where the inputs.conf was modified.

3) Activate the firewall logging on the windows machines to be monitored.

 	How to do :
		  	- Press Windows + R to open the Run dialog.
			- Type wf.msc and press Enter. This opens the Windows Firewall with Advanced Security console.
			- In the console, right-click on Windows Defender Firewall with Advanced Security on Local Computer and select Properties.
			- Configure Logging for Each Profile tabs. We recommand to extend the limit size to at least 20MB


4) Enjoy your meal !!!


We provided an ip exclusion macro based on lookup file, to help remove noise detection and false positive. feel free to enrich the lookup file whitelist_ip_ranges.csv .

You can make search using this request :   

					   index=* sourcetype="windows:pfirewall"
						
						OR use the request below to optimize search and ignore legitimate IP

					   index IN `windows_pfirewall_index` sourcetype="windows:pfirewall" `ip_whitelist`
						
					   


## License

Refer to https://www.splunk.com/en_us/legal/splunk-general-terms.html for licensing terms