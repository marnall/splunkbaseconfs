# OVERVIEW
 
Pixm App For Splunk provides insights to the enterprises for the Phishing Incidents detected throughout the enterprise across different devices and users. It also provides details on the Users & Devices which are being detected with Phishing Incidents.

Pixm is building an endpoint security product that uses AI computer vision to detect zero-day phishing attacks in real-time within your browser at the point of click . As soon as a zero-day phishing attack is detected, Pixm's Anti-Phishing shuts down the attack inside your browser within 1 second.

Pixm's Anti-Phishing product consists of an Agent and a browser extension. The Agent runs on Windows and Mac, and all major browsers are supported. When a user clicks on a link in an email to open in a browser, the browser extension works with the Agent running on the machine to detect zero-day phishing attacks within 1 second.

# REQUIREMENTS

* Splunk version 6.6.x, 7.x.x 
* This application should be installed on Search Head.

# Release Notes

* Version: 1.0.2

# RECOMMENDED SYSTEM CONFIGURATION

* Standard Splunk configuration of Search Head.

# SAVED SEARCHES
This application contains following saved searches, which are used in the dashboards. Out of these three are accelerated saved searches. Accelerated saved search provides better performance but consumes more memory on disk. 

* User Lookup
This saved search is used to populate "user_lookup" lookup
