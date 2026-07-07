# Splunk App

Splunk integration for [BloodHound Enterprise](https://bloodhoundenterprise.io/)

## Enable data input (disabled by default)
1. Go to ‘Data inputs’ under ‘Settings’
2. Scroll down and click on BloodHound Enterprise
3. Click ‘Enable’

# List BHE log entries
Splunk search: `index=_internal source="*.log" "BHE "`

# Change default data streaming interval
Change the `interval` value in `bhe-splunk-app/default/inputs.conf`. The value is in seconds. The default value is 14400 (4 hours).
