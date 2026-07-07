# Splunk App
The *Splunk App* for VulDB integrates vulnerability intelligence from VulDB into Splunk. The app communicates with VulDB by using its [API](https://vuldb.com/?doc.api) and requires a *valid API key* as well as *sufficient API credits*.

## Setup
### Changelog
5.3.1 Compatibility improvement   
5.3.0 Updated ATT&CK Enterprise Matrix, updated Splunk SDK   
5.2.2 Updated ATT&CK Enterprise Matrix, stability improvements   
5.2.1 Updated ATT&CK Enterprise Matrix Dashboard   
5.2.0 Updated ATT&CK Enterprise Matrix, updated Splunk SDK   
5.1.0 Updated ATT&CK Enterprise Matrix, stability improvements  
5.0.0 Added CVSSv4 to dashboards, updated ATT&CK Enterprise Matrix  
4.1.2 Improved handling of proxy settings  
4.1.1 Stability improvements   
4.1.0 Updated MITRE ATT&CK matrix to version 13.1; included hints for migrating the VulDB app to a new Splunk instance   
4.0.0 Added a MITRE ATT&CK matrix visualization and a related vulnerability dashboard   
3.8.0 Polling interval is now configurable   
3.7.2 Improved secret storage application   
3.7.1 Stability improvements   
3.7.0 New VulDB logo; added support for Chinese (zh), Japanese (ja) and Arabic (ar); stability improvements   
3.6.0 Added MITRE ATT&CK techniques visualization; stability improvements   
3.5.2 Improved data retrieval strategy   
3.5.1 Improved handling of arbitrarily named indices   
3.5.0 Enhanced algorithm for update fetching   
3.4.1 Stability improvements   
3.4.0 Fetch updates more frequently; show important warnings as Bulletin Messages   
3.3.0 New feature to allow fetching individual vulnerabilities   
3.2.0 Stability improvements   
3.1.0 Use the storage passwords facility to store the API key   
3.0.0 New feature to retrieve updates for vulnerabilities   
2.0.1 Stability improvements   
2.0.0 New and improved dashboards; 0day exploit prices; user interface improvements  
1.0.1 Possibility to define the time-range to fetch earlier entries at the initial startup  
1.0.0 Public Release  
0.0.1 Internal Release  

### Installation
*Installation from file:*
- Log in to Splunk with an administrative account
- Click on the gear icon (Manage Apps)
- On the next screen, click on the button labeled *Install app from file*
- Click on the button *Browse...* and browse to the location of the the VulDB Splunk App file (VulDB-Splunk-App.tar.gz), then select that file and click *Open* in the file browser dialogue. Now the name of the file appears next to the button *Browse...*.
- Check the checkbox *Upgrade app* to upgrade any older versions of the app should they exist
- Click the button labeled *Upload*

*Online installation:*
- Log in to Splunk with an administrative account
- Click on the gear icon (Manage Apps)
- Click on the button *Browse More Apps*
- in the search box, enter *VulDB* and press enter
- Click on the button *Install* to install the VulDB App

### Initial Configuration
Before configuring the VulDB Splunk App for the first time, make sure that you have a valid API key and a sufficient amount of API credits. If in doubt, [log in](https://vuldb.com/?login) to your VulDB account and [check your profile](https://vuldb.com/?my.profile.).

The VulDB Splunk App defines a new modular input type that is used for retrieving data from VulDB. Navigate to the menu *Settings / Data inputs*, under *Local inputs* find *VulDB* and click on *+ Add new*.

*Note:* if the app has been configured previously, this step is typically not required as the necessary configuration should already be present.

Give the new modular input a name, for example VulDB-datasrc and insert your API key into the field "VulDB API key". Optionally, you can specify a proxy server for outgoing connections, i.e. connections to https://vuldb.com from your Splunk server. You can also choose the language for the data fetched from VulDB, the choices are:
- English
- German
- Spanish
- French
- Italian
- Polish
- Swedish
- Chinese
- Japanese
- Arabic

The default polling interval for fetching data from VulDB is one hour (3600 seconds). This can be changed by entering the desired interval in seconds into the field "Polling Interval". The minimum possible value is 10 minutes (600) and the maximum possible value is 24 hours (86400).

It is possible to define how far from the past the App should start fetching VulDB data (default is one month if left empty). This setting can only be defined on initial creation of the modular input and cannot be changed later.

If you like to retrieve updates for vulnerabilities from VulDB, activate the check box next to *Update Settings* to show these settings. To use updates, activate the check box *Fetch updates?*.
It is possible to define how far from the past the App should start fetching updates (default is one month if left empty). Again, this setting can only be defined on initial creation of the modular input and cannot be changed later.

Clicking on *Next* will save your configuration and download an initial chunk of data from the VulDB (see below).

### Proxy Configuration
The VulDB Splunk App can be configured to use a proxy to access the VulDB API. The proxy settings can be specified on initial setup when defining the new modular input or by changing the settings of an already defined modular input. If your proxy performs SSL/TLS interception or requires to be accessed via SSL/TLS, the certificate of your proxy must be trusted. This may require adding the corresponding CA certificate to the trust list.

#### Additional Information
The VulDB Splunk App downloads data from https://vuldb.com in several chunks and it checks for new data once per hour. Upon initial data download (i.e. no data has been downloaded previously or only a long time ago), the App attempts to download all data from VulDB that is younger than the configured maximum data age.

*Note:* this will consume roughly 1000 API credits per month of data coverage (or more), depending on your choice of fetching details and on the amount of vulnerabilities in VulDB for that period.

## Usage
When you access the Splunk App, you are presented with an *overview dashboard*. This dashboard shows some *statistics and visualizations* of the VulDB data present in your Splunk instance. All visualizations in the overview have *drilldowns* defined, i.e. clicking on the numbers or graph elements will open a new window containing relevant data and details.

### Dashboards
Some *predefined dashboards* are included with the app. They can be accessed through the menu *Dashboards* in the menu bar.

You can always add your own dashboards or alter the existing ones. If you choose to change any of the predefined dashboards be aware that this may lead to non-functioning drilldowns in other dashboards.

A custom reusable visualization for the MITRE ATT&CK matrix is included with this app. It is used in the MITRE ATT&CK Overview dashboard. 

### Reports and Saved Queries
Currently, only one saved search is included with the VulDB app - it will show the VulDB log entries. Feel free to add your own searches as you see fit.

### Custom Searches
The VulDB app creates Splunk entries with a sourcetype of `VulDB`. Therefore you can use `sourcetype=VulDB` to restrict splunk searches to VulDB data.

### Logging
The VulDB App logs events to the splunk logs. A saved search is included in the VulDB app that allows you to retrieve the VulDB App logs, please click on the *Reports* menu access the saved search.

### Changing the Splunk App Configuration
The configuration of the VulDB data source (modular input) can be changed. Click on *Settings / Data inputs / VulDB*, which will show the previously defined input (or an empty list if you haven't defined the input yet). Clicking on the name of the input allows you to change its parameters.

### Updating the App
For instructions on how to update Splunk apps, please refer to the [official documentation](http://docs.splunk.com/Documentation/Splunk/latest/Admin/Managingappobjects).

### Deleting the App
For instructions on how to disable or delete Splunk apps please refer to the [official documentation](http://docs.splunk.com/Documentation/Splunk/latest/Admin/Managingappobjects). Bear in mind that deleting the app will remove the defined modular input but will not remove the VulDB data already present in your Splunk instance.

### Fetching Individual Vulnerabilities
It is possible to download one or more vulnerabilities separately from the usual data retrieval mechanisms. Navigate to the menu *Settings / Data inputs* and click on the field *Input Name* of the previously defined VulDB data input. Click on *Advanced Settings* and enter the desired VulDB IDs in the field *VulDB IDs*. Separate multiple IDs with commas if you wish to download more than one vulnerability. Then click the Save button on the bottom of the page and the specified IDs will be downloaded once from VulDB.

## Migration to a new Splunk installation
It is possible to migrate the indexed data and the state of the VulDB app to another Splunk instance. To achieve this, the indexed data in Splunk must be copied to the new installation (see the Splunk docs for details) and the state of the VulDB app must be copied to the new Splunk installation. This state is stored in the following locations:
* Cursor file for new entries: `$SPLUNK_HOME/var/lib/splunk/modinputs/VulDB-datasrc/cursor`
* Cursor file for updates of existing entries: `$SPLUNK_HOME/var/lib/splunk/modinputs/VulDB-datasrc/last_updated`

*Note*: In the above paths, the segment `VulDB-datasrc` corresponds to the name that is given to the VulDB modular input during the initial VulDB app setup (field "Input Name"). On Windows, adapt the paths correspondingly.

The following procedure is suggested:

0. Ensure that the VulDB data indexed on the existing Splunk installation is migrated to the new Splunk instance.
1. Install the VulDB app on the new Splunk instance
2. Before configuring the new VulDB app for the first time, disable Internet communication for the new Splunk instance. This is to ensure data and cursor file consistency.
3. Set up the new VulDB app by following the steps described in section [Initial Configuration](#initial-configuration) above. You can leave the field "Fetch data since" empty. If you have updates enabled in your existing installation, check the "Update settings" checkbox and the "VulDB Updates" checkbox. You can leave the field "Date" empty. Those fields are only used if no cursor files exist and we are going to use the cursor files from the existing Splunk installation.
4. In the web GUI of the new Splunk installation, navigate to Settings > Data inputs. In the section "Local inputs" click on the VulDB input. Its name will be the one you chose during setup. If you followed the suggestion in section [Initial Configuration](#initial-configuration) it will be "VulDB-datasrc". Now click on "Disable".
5. Place the configuration files ("cursor" and "last_updated") from the old Splunk installation in the corresponding directory of the new Splunk installation.
6. Enable Internet communication for the new Splunk instance
7. In the web GUI of the new Splunk installation, navigate to Settings > Data inputs. In the section "Local inputs" click on the VulDB input. Now click on "Enable". This starts data retrieval from the API and indexing.
8. Observe the VulDB app logs to check if everything works as expected.

*Note*: When migrating an entire Splunk installation, it is usually sufficient to copy the contents of `$SPLUNK_HOME` to the new instance. Consult the [official documentation](https://docs.splunk.com/Documentation/Splunk/latest/Installation/MigrateaSplunkinstance) for details.

## Help and Support
Please check the [documentation](https://vuldb.com/?doc) or [contact us](https://vuldb.com/?contact) if you have any questions. For Splunk support, please use your existing Splunk support channels. VulDB cannot provide Support for Splunk related issues.