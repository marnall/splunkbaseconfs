# Hurricane Labs Open Port Detection

## OVERVIEW
Hurricane Labs Open Port Detection is the second half of the TA-opd app. This app goes on your search head. TA-opd goes
on your Heavy Forwarder which will then index the OPD data into sourcetype=opd.

If you already have TA-opd installed and configured then you're good to go with this app. If you don't, you'll want to
get that set up first. See the TA-opd app README for details.


## SPLUNK VERSION SUPPORT
7.0, 6.6


## INSTALLATION
1. Make sure TA-opd is installed on a Heavy Forwarder and is sending data to sourcetype=opd.
2. Optionally configure this app to connect to SA-Shodan


## FEATURES

### Alerts
    - 'OPD - Newly Opened Ports' alert can be set up to alert you whenever a newly opened port is seen.
       - This alert is disabled by default.
    - Any item tagged as 'baseline' will not be included in this alert.

### Suppressions
	- You can suppress specific ports and / or specific hosts utilizing eventtypes.
	- You can suppress by creating an eventtype that starts with "opd_baseline" like so:
		Create a new eventtype called opd_baseline_custom_suppression and add "index=opd dest_ip=1.2.3.4 dest_port=80"
		as the contents.

### Saved Searches
    - 'OPD Shodan Lookup Populator' (optional) - If configured to connect to the SA-Shodan app this search
    will be enabled. It will then populate the opd_shodan KV Store with all your devices that have open ports.
        - By default this runs once a day, but can be configured to run more frequently.
    This lookup will be used in the 'OPD Shodan' saved search.
    - 'OPD - Newly opened ports' (optional) - Alerts whenever a new port is discovered within the last 7 days.
    - 'OPD Shodan' (optional) - Uses the opd_shodan KV Store populated from above to find out if any of your open
    port devices are also discovered on Shodan.

### Dashboards
    - OPD
        - Allows you to search for a specific IP and hostname.
        - 'OPD New Ports Detected' search is based off the alert of the same name.
    - OPD Shodan (Optional)
        - Shows any of your devices found through Shodan's API (Requires SA-Shodan app to work:
        https://splunkbase.splunk.com/app/1766/)
        - NOTE: This dashboard relies on the opd_shodan lookup being populated. If you enable Shodan with no OPD inputs / data
        coming in for OPD, then this will be empty. If this dashboard is not showing results, make sure that data is coming
        in for OPD, then re-run the saved search 'OPD Shodan Lookup Populator' which will populate the opd_shodan lookup.
### Setup
    - If you have the SA-Shodan app installed then you can optionally set this app up to check your open
    ports against Shodan


## RELEASE NOTES

### v2.1.0
- Minor dashboard cosmetic changes.

### v2.0
- Added dashboards, configuration page and additional saved searches for Shodan connection


## DEV SUPPORT
Contact: splunk@hurricanelabs.com