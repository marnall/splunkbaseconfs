## Rapid7 Nexpose for Splunk Enterprise

###http://www.rapid7.com

## Using this App:
   
### Setup:

Please see [Splunk's official documentation](http://docs.splunk.com/Documentation/AddOns/released/Overview/Singleserverinstall) for the initial installation of the app.

To use the dashboards, data must have been imported using the [Rapid7 Nexpose Technology Add-On for Splunk](https://splunkbase.splunk.com/app/3457/).

## Configuration

### Main Dashboard
On the dashboard, results can by filtered by index, site and time period. Selecting a new option in this panel will automatically reload the graphs.

The available site filters are the sites are those returned in the results, filtered from the selected index and time period.

The timestamp will return results from scans that finished during that time period, rather than when the events were indexed.


### Asset and Vulnerability Search
On the search pages, you may search for specific vulnerabilities and assets. The filter options, such as tags, are scraped from the events returned, after existing selections such as the time period are applied.

The "Additional Filters" box appends the entered text to the Splunk search string used to power the visualizations. 

   
## Debugging:
A log file is available to help debug issues contained within <splunk_home>/var/log/splunk/:

* splunkd.log - Splunk general log

Please contact support@rapid7.com for help, including the relevant portion of this log file.

## Changelog:
1.0 // Initial release.
1.1 // Renaming
1.2 // Filter updates