# Description
This is an add-on to import data from your Rhombus Systems cameras into Splunk via the Rhombus API access.
Currently has built in support for reading count reports, camera lists, and diagnostic feeds.

# Requirements
To use this add-on, you must have Rhombus API access.
In the add-on configurations page, you must enter your api key and paths to the certificate and private key generated when setting up your Rhombus API access.

# Usage
Before setting up any inputs, you must configure the add-on in the Configuration tab.
To set up data inputs into Splunk, use the add-on Inputs tab.  There you may create new inputs and follow the input setup prompts.
Once the inputs are set up, this add-on polls the Rhombus API and indexes events in JSON format.
A sample dashboard is available under the tab Sample Dashboard to provide a basic overview of search capabilities.
