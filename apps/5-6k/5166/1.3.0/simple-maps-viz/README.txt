Simple Maps Viz ver 1.0.1

Daniel Spavin
daniel@spavin.net

#Version Support#
8.0, 7.3, 7.2, 7.1, 7.0, 6.6

#Who is this app for?#
This app is for anyone who wants an easy way to display a choropleth map without needing to know anything about KML files.

A choropleth map is a type of thematic map in which areas are shaded or patterned in proportion to a statistical variable that represents an aggregate summary of a geographic characteristic within each area. E.g. showing average temperature by state, or income per-capita.

Simple Maps Viz requires using a lookup that comes with the app. You can use the lookup with the | iplocation command to plot countries on the world map.

#How does the app work?#
This app provides a visualization that you can use in your own apps and dashboards.

To use it in your dashboards, simply install the app, and create a search that provides the values you want to display.

A lookup comes with the app that lists all the codes coresponding to map areas. You can either use the lookup directly, or create a new lookup based on a specific map's codes.

#Usecases for the Simple Maps Viz:#
* Showing the source country for IP based lookups
* Showing the relative difference in sales by geographical region
* Comparing different states' response times for monitored applications


#Use#
The following fields can be used in the search:
code (required): The code for the map element being defined - e.g. "AU-VIC" for Victoria, Australia. These codes are listed in the following lookup: simple-maps-viz-lookup
value (required): The numeric value for the map element

#Example Search#
index=web sourcetype=access_combined
| iplocation clientip
| stats count as value by Country
| lookup simple-maps-viz-lookup name as Country output code
| table code, value

Once you have selected the map you would like to use, you need to be able to associate the specific codes for each geographical region.

You can either use the global lookup: simple-maps-viz-lookup or create your own version with the required codes.

Use the Examples dashboard to see what codes are required for each map, and optionally export the list for use in your own lookup by clicking the  icon at the bottom of the panel.

#Tokens#
Tokens are generated each time you click a cell. This can be useful if you want to populate another panel on the dashboard with a custom search, or link to a new dashboard with the tokens carrying across.

| Token | Value | Example |
| $row.code$ | The map element code | AU-VIC |
| $row.value$ | The value for that map element | 12345 |
| $row.name$ | The Country/Department/Territory name | Victoria |
| $row.fieldname$ | The value for the field on the same row as the code | 12345 |



#Release Notes#
v 1.0.1
- Initial version


#Issues and Limitations#
If you have a bug report or feature request, please contact daniel@spavin.net

#Privacy#
No personally identifiable information is logged or obtained in any way through this visualization.

#For support#
Send email to daniel@spavin.net

Support is not guaranteed and will be provided on a best effort basis.

#Third-Party Libraries#
* This visualization uses ui.toast.com
* Maps provided by amcharts.com
* Icons made by Freepik from www.flaticon.com