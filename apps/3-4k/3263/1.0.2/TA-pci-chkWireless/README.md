#TA-pci-chkWireless
### Description
A simple add-on which pulls in and normalizes data at the search tier for PCI uses. Requires lspci to be installed (script in BIN directory to help if you need it) on Linux. Windows I just query your services. 

### Installation
Tested on CentOS 5,6 and 7. Windows 7. 

Install add-on on endpoints and search tier. By default uses main index. PCI requires that you store this data for 1 year. So ensure your index has that level of retention. By default this is set to main which is almost never the right place. Update it to match your needs. 

### Usage
Install, restart. By default wireless being enabled is qualified as an attack. You can adjust this in tags.conf if you're not intereted in using this app that way. You should also create some logic on the severity field in your alerts/notables/DMs or code it right into props.conf. If you don't care too much you can rename my vendor_severity field to severity and you'll have CIM compliance. 

### Contributing
I didn't invest a lot of time in the Windows script. If you have some ideas please shoot them my way. 

### History
1.0.2 - PCI DSS 3.2.1 supported. Cleaned up props.conf with CIM fields and switch readme file to GIT style
1.0.1 - Added Windows scripts by request. 
1.0.0 - Basic Linux version released to splunkbase

### Credits
Daniel Wilson

### License
Creative Commons

### TO DO/BUGS
1. Need to understand why we can't search by pci_dss_requirement field
2. Build out some GUIs
3. Build a canned report for PCI use cases
4. Add Solaris support
