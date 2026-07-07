Prerquisite:-
	The Zyxel firewall monitor app is based on logs thats has being forwarded to splunk by recieving at port 514 which is default.
	Also the apps default setting for index, sourcetype is being saved in Eventtype, you can change this setiing as per your configuration 
	from the link provided in apps home dashboard.



Dashboards:-

1) ZyXEL Home
	This is the home page of the app, shows all important details of the firewall like firmware version, model name, 
	device id, Current CPU and Memory levels in single value panel.
	Also includes introduction page along with the links to Edit eventtypes used in app for modularity.

2) Traffic
	This gives all the data usage statistics of firewall with chart showing data usage over the week.
	You can also view the data usage by the users and devices connected to firewall. This detailes get automatically capured by the Alerts and Reports running in the app.
	You may need to set the configurations for the alerts and reports as per your need.
	
3) Security
	This gives all the security related information of the firewall like Outsiders attacks on the internal network and ports, 
	Log in attempts from users on firewall and locked ip address from firewall also showing the maps of the same incoming host as well.

4) VPN
	This Dashboard gives informaiton about the VPN connections made. With the detials of user who access the Zyxel firewall portal .
	VPN ip assinged to user and Login details aprt from office hours.

5) Network Viz Firewall
	This gives you the network visualization for fire by user. Giving you the ip of where ever the usre has connected from the network in a visualization format.

6) Threat
	This dashboard gives the details on Crucial activities . Indifcating the Threat Level of the activities performed. 
	KPIs for total activities performed in a specific time range, The severity of the threat and the count of activities in givrn time range. 

Reports:-

Daily report to collect new devices
	This report runs daily on 00:00 AM and collects the data into lookup if any new devices connected to the network.
	The same lookup is used accross the App to get information like IP, MAC, Account and Device type.
	The account will be the owner of the device and device type will be type of device of that owner.
	(for eg- Account-"Admin" Device Type-"Laptop").
	
Alerts:-

Firewall CPU/Memory threshold breach
	Triggers when firewall CPU/Memory usage goes beyond 70, runs at every one hour.
	you can change the trigger condition as per requirement in query.
		
Firewall download/upload data traffic limit breached
	Sends alert when total downloaded data from organization goes beyond 15 GB.
	and upload data from organization goes beyond 1.5 GB.
	you can change the trigger condition as per requirement in query.
	
Mobile/Laptop download usage limit breached
	Sends alert when total downloaded data from employee's mobile device goes beyond 500 MB
	and Sends alert when total downloaded data from employee's laptop device goes beyond 1 GB.
	you can change the trigger condition as per requirement in query.
	
New device connected to network
	This alerts triggeres and send mail to administrator to fill the newly connected devices info into lookup as well as in Zyxel firewall DHCP setting,
	as the ip address assigned to the devices should be fixed for the app to work.# Binary File Declaration
# Binary File Declaration

Configuration change	
	This alert triggers and sends mail to the administrator informing him about the chnages that we made to the firewall.
	And tell administrator the source and destination with user name.

Anomalous Network activity alert	
	This alert trigger and sends mail to the administrator nforming the abnormal traffic in firewall.
	And the informaiton related to it.

Max session per host exceeded
	This alert trigger and sens mail to administrator informing about the max session exceeded per host.
	And the information related to it.

Possible arp spoofing
	This alert trigger and sens mail to administrator informing about the possible arp attack on firewall.
	And the information related to it.

Facebook Wi-Fi daemon alert	
	This alert trigger and sens mail to administrator informing about the Facebook Wi-fi daemon attack.
	And the information related to it.

Diagnostic info collection alert
	This alert trigger and sens mail to administrator informing about the diagnostic info collection.
	And the information related to it.

Authentication failure
	This alert trigger and sens mail to administrator informing about the Authentication failure on firewall.
	And the information related to it.

Scan Detection
	This alert trigger and sens mail to administrator informing about the scan Detection on firewall.
	And the information related to it.

Potential Denial-of-service or remote code execution alert	
	This alert trigger and sens mail to administrator informing about the Potential DoS/RCE attack on firewall.
	And the information related to it.# Binary File Declaration
# Binary File Declaration
# Binary File Declaration
# Binary File Declaration
# Binary File Declaration
# Binary File Declaration
# Binary File Declaration
# Binary File Declaration
