# Splunk Add-on for Electricity Carbon Intensity
Modular Input developed with Add-On Builder to query API endpoints from both the [National Grid's Carbon Intensity API](https://carbonintensity.org.uk/) and the [Electricity Maps API](https://app.electricitymaps.com/map).


Associated Jira request: https://splunk.atlassian.net/browse/FDSE-1556

## Features 
One of the easiest starting points for calculating your carbon footprint, is to look at energy consumption.

Calculating the carbon footprint associated with electricity consumption requires the following two datasets:

Electricity consumption in kilowatt hours (kWh). This will be available either from dedicated electricity meters retrieved via APIs, or one of many types of dedicated sensors such as a CT clamp (measures the current through a wire) connected to the Splunk Edge Hub. Systems Management software such as HPE iLO or Dell iDRAC can provide this information.
Carbon intensity of the electricity at time and location of consumption, in kilogram carbon dioxide equivalent per kilowatt hour (kgCO₂e/kWh). Many organisations or government bodies rely on static values for annual reporting purposes, however depending on the country, this figure may be be available on a more granular basis via an API call to the electricity supplier, generator, national Grid,government body or third party organisation.
Multiplying the Electricity consumption and Carbon intensity will provide the carbon footprint of electricity consumption in the associated time period.
The Splunk Add-on for Electricity Carbon Intensity implements calls to 2 providers, for carbon intensity of electricity. In their words:

https://carbonintensity.org.uk/: National Grid ESO's Carbon Intensity API provides an indicative trend of regional carbon intensity of the electricity system in Great Britain (GB) 96+ hours ahead of real-time. It provides programmatic and timely access to both forecast and estimated carbon intensity data.
https://api-portal.electricitymaps.com/: Electricity Maps provides companies with actionable data quantifying the carbon intensity and origin of electricity. This data is available on an hourly basis across 50+ countries and more than 160 regions.
The Sustainability Toolkit for Splunk provides the SPL to summarise data from both of these sources, and then combine it with electricity consumption calculate and analyse patterns in CO₂e emissions.

## Getting Started

### Installation
Clone this repository directly to `$SPLUNK_HOME/etc/apps`, or clone it, zipp it, and install it via Splunk's Web Interface via the "Install app from file"-button in the "Manage Apps"-section.

### Setting up accounts for authentication - National Grid Carbon Intensity API
If you want to solely use the National Grid Carbon Intensity API, you do not need to set up an account since user authentication is not required here.

### Setting up accounts for authentication - Electricity Maps
Accounts are used in the Splunk Add-on for Electricity Carbon Intensity to store the credential provided by Electricity Maps. After entering these once, they can be reused multiple times for the configuration of different Inputs.

To add an accout: 
- Open the Configuration screen and Add an account.
- Enter details: An account name of your choice Base product URL, provided by Electricity Maps, API Key, provided by Electricity Maps
- Click Add
After adding these details, you can progress to adding some Inputs.

### Configure Modular Inputs
In the "Inputs" page you can create new inputs. Regarding the Electricity Maps inputs, you can configure them with the account created in the last step.