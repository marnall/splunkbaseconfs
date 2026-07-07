Network Diagram Visualization
Version: 1.7.0
Created by Daniel Spavin (daniel@spavin.net)

Version Support
9.4, 9.3, 9.2, 9.1, 9.0, 8.1, 8.0, 7.3, 7.2, 7.1, 7.0, 6.6


Who is this app for?
This app is for dashboard designers who want to display how different entities are related to eachother on a dashboard panel.



How does the app work?
This app provides a visualization that you can use in your own apps and dashboards.

To use it in your dashboards, simply install the app, and create a search that provides the values you want to display.



Usecases for the Network Diagram Visualization:
Displaying current server status based on CPU, Memory, I/O, and Disk usage
Visually associating users with actions, e.g. purchases, crashes, errors
Visualising the connection speeds between two hosts or services
Showing how events are related to eachother


The following fields can be used in the search:
from (required): The unique name of the source entity.
to (optional): The unique name of the destination entity.
value (optional): Text to display as a tool tip. Populates token: $row.value$ when the node is clicked.
nodeText (optional): Text to display as the text under the node. Defaults to the from field. Populates token: $click.value$ when a node is clicked.
type (optional): This is used to display the entity on the dashboard (from). Use the list of icons available, Splunk server icons, or shapes.
color (optional): Used to set the color of the text and icon (you can now color Splunk icons too).
linktext (optional): Text to display on the link between the from and to entities.
linkcolor (optional): Colour of the link - use HTML colours or "red" / "yellow" / "green" / "blue". Invalid colours may make the viz fail to display.
linkwidth (optional): the width of the link between nodes. The optimal size range is between 0 and 15.
linklength (optional): The length of the link between two nodes. Will be ignored if Physics is enabled.
x (optional): Used in the 'Create Layouts' dashboard to set the location within the viz.
y (optional): Used in the 'Create Layouts' dashboard to set the location within the viz.
Options can be overwritten, so if type or color is set multiple times in the search results, the last value will be used. This is useful if you wish to set the icon types and values via a lookup table at the end of your search.



Example Search
A simple way to create the data necessary for the visualisation is to:

Select all the relevant data
Use | appendpipe [...] multiple times to define the FROM and TO values
Clean up the results by only outputting valid Network Diagram Viz fields
This example looks at all hosts, indexes, and sourcetypes. Each row/event will have 3 fields defined: host, index, and sourcetype. By using | appendpipe and using | stats we can define the From -> To relationships and define icons for each type:

| tstats values(sourcetype) as sourcetype  WHERE index=* OR index=_* by host, index
 | mvexpand sourcetype
 | appendpipe [|stats count by host, index| rename host as from, index as to| eval type="server"]
 | appendpipe [|stats count by index, sourcetype| rename index as from, sourcetype as to| eval type="index"]
 | appendpipe [|stats count by sourcetype| rename sourcetype as from | eval type="file"]
 | search from=*
 | table from, to, type

Save Layout Designs
You can save the layout of a Network Diagram Viz to make sure a specific layout is always displayed on your dashboards.

To create a layout, go to the Create Layouts dashboard and follow these steps:

Paste in your search then click Run Search to generate a Network Diagram Viz
Drag the nodes around until you are happy with the design.
A new search is generated in the third panel. Replace your original search with the new search to save your layout.
Note: You must have physics turned off: General > Enable Physics = false

You must also turn off hierarchy settings: Hierarchy > Hierarchy View = false

To prevent users from altering your layout, you can choose to disable draggable nodes: General > Draggable Nodes = false



Tokens
Tokens are generated each time you click a node. This can be useful if you want to populate another panel on the dashboard with a custom search, or link to a new dashboard with the tokens carying across.

Node or link text: This is the name of the node as it was defined in the search results for either the node or link. Default value: $nd_value_token$. Same as $row.name$.
Node (from): This is the unique node name (e.g. the server name) of the node you clicked, or if you clicked on a link it will show the from node. Default value: $nd_node_token$. Same as $row.name$.
Node (to): When you click on a link this is populated with the to node. Default value: $nd_to_node_token$. Same as $row.to$.
Tool Tip: When you click on a node this is the tooltip value that pops up. Default value: $nd_tooltip_token$. Same as $row.value$.


Drill-Down
Drill-down support is available. To access the drill-down options, click the ... button when editing a dashboard, and select Drilldown. See Drill-Down settings for more information.



# Release Notes #
v 2.0.0
- All 'to' nodes are now generated by default, simplifying the generating search.
- The "box" type now has legible text. See it used on the Business Process example dashboard.
- Added business process usecase with the updated "box" type
- Drill-downs are disabled on all search results pages. This allows you to move the nodes around on the search/visualisation tab without performing a drill-down.
- There is now a faint box around the node text to help legibility
- Created new option for Physics: Partial. This option (along with dynamic lines and line length) will let you see multiple links between the same nodes without them overlapping.
- Updated libraries to the latest versions
- Bug fix: NodeText won't be overwritten with blank values
- Bug fix: Fixed error where some default icon options were ignored
- Other minor bug fixes

v 1.9.0
- Upgraded visjs code to latest version
- Added layout option for directed hierarchies: shake towards. This will change the layout to favor roots or leaves when using the directed sort mode.

v 1.8.0
- Improved dark-mode compatibility for link text
- Fixed bug were a panel resize would make the diagram appear off-centre
- Added new field: nodeText so you can have a different label for a node to the from field. Defaults to the 'from' field value.
- Added option to make drill-downs activate on double-click only, so you can move nodes around without it trying to drill-down.

v 1.7.0
- Drill-downs now work on a single click, rather than a double click
- You can now set the line length from search by specifying a linkLength field
- Default link length can be set in options
- Under Hierarchy settings you can now specify the distance between layers, and if phyiscs is disabled, spacing between nodes
- The options menu has been re-organised to better group related options
- Created a dark-mode version of the Create Layouts dashboard

v 1.6.0
- Huge performance increase - show up to 10,000 nodes within a few seconds. New performance dashboard to test out massive network diagrams.
- Added new edge types to change the way nodes are linked: Dynamic, Cubic Bezier, Discrete, Continuous, Diagonal Cross, and Straight Cross.
- Added arrows to edges to help show the flow. Show arrows at the start, middle, or end of edges.
- Edges now have a tooltip when you hover over them if you set a linktext value.
- There is a new token for tooltips: $nd_tooltip_token$.
- Fixed bug when default icon was set to a logo icon.
- Minor bug fixes related to grouping.

v 1.5.0
- Drill-Down is now supported via the Drill-down menu. This change will enable drill-downs to other dashboards, searches and URLs while also supporting custom tokens.
- There is now a date picker on the Layout Design dashboard to allow you to time limit your searches.
- Both the node label and link text size can be increased - see the new options under General: Node Text Size and Link Text Size
- Fixed bug where Splunk License server icon didn't change color

v 1.4.0
- Splunk icons can now be colored: red, yellow, green, blue. Just set your color field in your search to one of these colors.
- You can also use terms like 'error','bad','severe','high' for Red, 'amber','warning','medium','orange' for yellow, 'ok','good','low' for green, and 'debug','unknown' for blue.

v 1.3.0
- Hundreds more icons available - see the Available Icons dashboard for the complete set.
- Fixed options menu 'undefined' text that appears on Splunk 7.3.

v 1.2.0
- User requested features:
- Control the width of links using the new linkwidth field in your search (optional).
- Set the color of links using the new linkcolor field in your search (optional).
- Use the link text as a token when you click on it - defaults to: $nd_value_token$.
- Ability to disable zoom - new setting in the Options menu.
- Other updates:
- New icons - a range of new icons for Windows, Linux, Git, Skype, Java, Google Drive and others. See the Available Icons dashboard for the complete set.
- When you click on a link between two nodes, you now get tokens for the From and To nodes, as well as the link text.
- Fixed typos in dashboards and configuration settings.

v 1.1.0
- Save your layout designs. You can now use an in-built dashboard to create specific layouts based on your searches. A new search will be generated for use in your dashboards. See new dashboard: Create Layouts.

v 1.0.0
- Initial version.


Issues and Limitations
If you have a bug report or feature request, please contact daniel@spavin.net



Privacy and Legal
No personally identifiable information is logged or obtained in any way through this visualizaton.



For support
Send email to daniel@spavin.net

Support is not guaranteed and will be provided on a best effort basis.



3rd Party Libraries
This visualization uses the network module from visjs.org

Icons made by Smashicons from www.flaticon.com is licensed by CC 3.0 BY

Icons made by https://fontawesome.com