App:                InterMapper for Splunk
Current Version:    1.7
Last Modified:      2017-06-05
Splunk Version:     4.2.x, 4.3.x, 5.x, 6.0, 6.1,6.6
Authors:            Mark Jenkins, Steve Drain, Alistair Meakin, Laura Quinn


The InterMapper for Splunk App provides integration with the network monitoring application InterMapper along with a dynamic dashboard generator for your devices and a set of default dashboards out of the box including;

	* Device Notifications summary dashboard with filters for time or notification level
	* List of all devices monitored by InterMapper with drill-down action to their respective dynamic dashboard and row colouration based on current condition.
	* Splunk time line search dashboard re-skinned for InterMapper app.
	* Default Map view that also displays an initial loading screen and any critical errors.



##### What's New #####
1.6
- Removed menu "Devices"

1.2
- Removed XML errors
- Java Script updated to work with Splunk version 6
- Updated to be compatible with InterMapper 5.8 Web API
1.1
- Changed map image retrieval to reduce load on InterMapper server
- Added separate field for port in Configure App screen
- Added last update time to map dashboards
1.0.1
- Minor dashboard layout improvements
- Other minor fixes
1.0
- Added user guide page for view_alerts dashboard
0.7.7
- Updated user guide
- Added click through to alert counts on Notification dashboard
- Reduced font in Device dashboards 
0.7.6
- [Layer 2] Fixed failure to read settings file under Splunk 5.X and Windows
0.7.4
- Improved handling of a lack of Layer 2 data
- Minor fixes  
0.7.2
- Page refreshes now only take effect when no navigation menus are open
- Fixed failure to read settings file under Splunk 5.X and Windows
0.7.1
- Changed alert icons to always match InterMapper icons
- Minor fixes
0.7.0
- Added banner notification of problems connecting to InterMapper
- Map and dashboard menu links now sorted alphabetically
- Dashboards changed to use only one time picker for increased clarity
- Added force-reload on app upgrade
0.6.9
- Improved Unicode support
- Main script initiates crash recovery after 10 mins
- Fixed bugs related to map and dashboard generation
- Fixed drilldown bug
- Updated User Guide
0.6.7
- Fixed numerous bugs related to map and dashboard generation
- Performance enhancements for map and dashboard generation
- Improved configuration experience
0.6.5
- Removed unnecessary debug information from script output
0.6.4
- Dashboard and device list issue fixes.
0.5
- Beta Version


