                  **********************************************************                    
                  *                                                        *
                  *     Thanks to, of IP RIVER KENYA LTD/POWERNET LTD      *   
	          *                      *Gal Arbel                        *
	          *                    *Collins Mitei                      *
                  *                                                        *
                  **********************************************************


				     <<Version Support>>

* This App was built and tested using Splunk Enterprise Version: 8.1.1 platform but should compatible with higher or lower versions without major issues.
* If you experience issues with other versions, feel free to contact us on email:techsupport@powernet.co.ke for support.

			            <<System Requirements>>

* Radware Alteon running v.32 and above with valid advanced traffic events license.
* Splunk Entreprise

				       <<Configuration>>

* Configure traffic events on the alteon using the default tcp port 5140 using the guidline on Radware's portal
* Configure the Splunk Server IP as your traffic events real server on alteon.
* Configure the Alteon to forward syslog events (RFC3164) to the Splunk server IP on udp:8089
* Configure your splunk server to listen on 2 ports (Data inputs) as below for traffic events and syslog events respectively as below

  <N/B: Use the same index, alteon for both sources as indicated.>

For Traffic Events:

   index= alteon
   source= tcp:5140
   sourcetype (Manual)= Alteon_events
	      Category= Web
	      App= Search

For Syslog Events:

   index= alteon
   source= udp:8089 
   sourcetype (Manual)= syslog
	      Category= Operating System
	      App= system
