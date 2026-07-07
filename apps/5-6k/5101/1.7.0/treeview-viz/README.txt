Treeview Viz
Version: 1.1.0
Created by Daniel Spavin (daniel@spavin.net)

Version Support
9.3, 9.2, 9.1, 9.0. 8.2, 8.1, 8.0, 7.x

Who is this app for?
This app is for dashboard designers who want to compactly display parent-child relationships in their data.


How does the app work?
This app provides a visualization that you can use in your own apps and dashboards.

To use it in your dashboards, simply install the app, and create a search that provides the values you want to display.


Usecases for the Tree View Visualization:
Grouping categories together, e.g. sourcetypes by host
Providing a compact interface for generating tokens for drill-downs in a dashboard
Creating a menu in a set of dashboards
Visualizing the layout of files, running process, or perfmon stats on multiple hosts

The following fields can be used in the search:
id (required): An identifier for the lable. Use this value when assigning child items. Will default to the label if not supplied.
label (required): The value shown next to the item.
parentid (optional): Sets the parent item based on id. Will create a parent folder with the same label as the ID if one doesn't already exist.
iconFolder (optional): When using "custom" style, selects icon for folders.
iconDoc (optional): When using "custom" style, selects icon for child items.

Example Search
index=_internal
| stats count by sourcetype, source
| rename source as id, sourcetype as parentId
| eval label = id
| table id, label, parentId


Tokens
Tokens are generated each time you click an item. This can be useful if you want to populate another panel on the dashboard with a custom search, or link to a new dashboard with the tokens carying across.

Label text : This is the display name of the selected item. Default value: $tv_label_token$
ID : This is the value of the selected group you clicked. Default value: $tv_id_token$
Parent ID : This is the value of the selected group you clicked. Default value: $tv_parent_id_token$
The standard Splunk drill-down tokens are also generated:

click.name : The Label text
click.value : The ID
click.name2 : The Label text
click.value2 : The ID
row.fieldname : the field "fieldname" from the search results.

Release Notes
v 1.5.0
* Updated to latest libraries for Cloud compliance

v 1.4.0
* Increased search data limit to 250,000 rows. Warnings will appear if this limit is exceeded
* Fixed bug where some drilldowns didn't work
* Added detection of very deep nesting of items. Any nesting more than 1,000 items deep will trigger an warning message
* Minor changes to example dashboards
* Updated CSS to avoid conflicts

v 1.3.0

* Fixed issue where the order of events could change the tree structure
* Fixed bug were some item names resulted in errors
* Added cycle detection - now if a cycle is detected, the node will be added to the root node instead of the parent.
* Updated to JQuery 3.5.0, other minor changes to meet Splunk Cloud validation checks

v 1.2.0
* Added ability to set color for icons via new field "color"

v 1.1.0
* New option to have all folders open when the visualization starts. Options - General - Initial State = Closed / Open
  Based on user request
* Added app manifest for Splunk Cloud 
* AppInspect now passes

v 1.0.0
Initial version

Issues and Limitations
If you have a bug report or feature request, please contact daniel@spavin.net


Privacy and Legal
No personally identifiable information is logged or obtained in any way through this visualizaton.

For support
Send email to daniel@spavin.net

Support is not guaranteed and will be provided on a best effort basis.


3rd Party Libraries
Icons made by https://fontawesome.com

FancyTree

Copyright 2008-2020 Martin Wendt,
https://wwWendt.de/

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

