Sankey Visualization
Version: 1.0.0
Created by Daniel Spavin (daniel@spavin.net)



# Version Support
10.0, 9.3, 9.2, 9.1, 9.0, 8.2, 8.1, 8.0, 7.x



# Who is this app for?
Sankey diagrams show metric flows and category relationships. You can use a Sankey diagram to visualize relationship density and trends.



# How does the app work?
This app provides a visualization that you can use in your own apps and dashboards.

To use it in your dashboards, simply install the app, and create a search that provides the values you want to display.



# Usecases for the Network Diagram Visualization:
Displaying user activity flows on a website
Purchasing trends of users
Data or financial transfers
How data is moved around different queues or systems


The following fields can be used in the search:
| Field   | Description |
|---------|-------------|
| from    | The system, queue, or category that defines the source of a flow. This can be either the "from" field, or the first non-number field in the results. |
| to      | The system, queue, or category that defines the destination of a flow. This can be either the "to" field, or the second non-number field in the results. |
| value   | The quantity or size of the flow. This will determine the both the size of the link between the from and to nodes, as well as the speed of any animations. |
| tooltip | Text to display on the details panel, when configured to show. You cannot include HTML, only plain text. |

Note: Field names are not case sensitive, e.g. you can use 'From' or 'from'

If the field names do not match "to","from", and "value" then the visualisation will guess which is the value, from, and to fields. If you want to include Tooltips, the field must be called "tooltip" (case insensitive).

# Example Search
A simple way to create the data necessary for the visualisation is to use stats or tstats.

This example looks at indexes and sourcetypes. Each row/event will have 3 fields defined: index, sourcetype, and value. 

`| tstats count as value, WHERE index=_internal by sourcetype, index
| sort - value
| head 10
| table sourcetype, index, value`



# Tokens
Tokens are generated each time you click a node or link. This can be useful if you want to populate another panel on the dashboard with a custom search, or link to a new dashboard with the tokens carying across.

Node (from): This is the name of the node as it was defined in the search results. Default value: $skv_from_node_token$. Same as $row.from$.
Node (to): This is the name of the destination node as it was defined in the search results. Default value: $skv_to_node_token$. Same as $row.to$.
Tool Tip: When you click on a node this is the tooltip value that pops up. Default value:$skv_tooltip_token$. Same as $row.tooltip$.


# Drill-Down
Drill-down support is available. To access the drill-down options, click the ... button when editing a dashboard, and select Drilldown.



# Release Notes
v 1.0.0
Initial version.


# Issues and Limitations
If you have a bug report or feature request, please contact daniel@spavin.net



# Privacy and Legal
No personally identifiable information is logged or obtained in any way through this visualizaton.



# For support
Send email to daniel@spavin.net

Support is not guaranteed and will be provided on a best effort basis.



# 3rd Party Libraries
This visualization uses the D3 library.

Sankey icon created by Pericon - Flaticon



D3 Licence
https://github.com/d3/d3/blob/main/LICENSE
Copyright 2010-2023 Mike Bostock

Permission to use, copy, modify, and/or distribute this software for any purpose
with or without fee is hereby granted, provided that the above copyright notice
and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF
THIS SOFTWARE.