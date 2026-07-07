SECUI MFI App for Splunk
=================================
* **Current Version:** 1.1
* **Author:** SECUI
* **Last Modified:** Nov 2016


### Overview ###
The SECUI MFI App for Splunk provides real-time and threat dashboard, traffic dashboard and 
analytical dashboards on attack, attacker, victim for the product across the SECUI MFI appliances.
 
SECUI MFI appliances is an intrusion prevention system performing the role of detecting and
blocking intrusion and attack of the network traffic flowing in from the outside real-time
after being installed as a form of Transparent Bridge not affecting the network configuration.

SECUI MFI performs detect/defense on all packets and safety protects the information assets and
resources of the internal network from DDoS attack, Flooding attack and Smurf attack, etc.


### System Requirement ###
- Splunk Version : Splunk Enterprise 6.5
- SECUI MFI Version : SECUI MFI 4.0.6 or higher


### Dependencies ###
This App depends on Sankey Diagram and Heatmap.  
Please make sure Sankey Diagram and Heatmap are installed before install this App.


### Installation ###
1. Go to splunk > Apps > Manage Apps menu.
2. Select Install app from file.
3. Click on the Browse button to select the SECUI MFI App for Splunk installation file.
4. Click on the Upload button to install.
5. Once installation is complete, go to the Settings > Server Contols menu and click on Restart Splunk to restart Splunk.


### Configuration ###
1. Select Settings > Data inputs menu.
2. Click Add new in UDP.
3. Enter UDP port number to be opened. (Ex.: 514) Enter corresponding port number when setting syslog in SECUI MFI.
4. For Source type, select Network & Security > secui:log, and select SECUI MFI App for Splunk for App context and click on the Review button.
5. Check Review contents and click on the Submit button.


### Scripts and Binaries ###
None. There are no scripts or binaries included in this application.


### Release Notes ###

- **v1.0: Nov 2016**  
  - Initial release.

- **v1.1: Nov 2016**
  - changed icons.
  - Improved the information of Attack flows in Detail Analytics.
