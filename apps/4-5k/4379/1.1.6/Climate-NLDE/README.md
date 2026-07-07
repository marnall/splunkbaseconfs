# ABOUT THIS APP

* This app extracts data from dutch and german climate institues and visualises this data.

# REQUIREMENTS

* Splunk version 7.2

# RECOMMENDED SYSTEM CONFIGURATION
Will not work behind a proxy.

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

# INSTALLATION OF APP

* This app can be installed through UI using "Manage Apps" or extract zip file directly into $SPLUNK_HOME/etc/apps/ folder.
* The app will require a setup, which will automatically pop-up. Default parameters are provided, and will most probably work. 
* After setup, make sure the scripted inputs are enabled (GetNL.py and/or GetDE.py).

# TEST YOUR INSTALL
First time scripted inputs are invoked all available historical data will be extracted.
Subsequent invocations will only ask for newly added data.
* Run following search:
	search sourcetype=climate
	
# TROUBLESHOOTING

# SUPPORT

* Support Offered: Best Effort
* Support Email: debueger@freeler.nl
