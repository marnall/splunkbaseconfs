# Waterfall Custom Visualization App

 Waterfall chart is used to show the cumulative effect of sequentially introduced positive or negative values. https://en.wikipedia.org/wiki/Waterfall_chart
 It is D3 Visualization based on Chuck Lams's block http://bl.ocks.org/chucklam/f3c7b3e3709a0afd5d57
- The relevant directory structure for a visuzliation app
- Waterfall Custom visualization package directory is located under $SPLUNK_HOME\etc\apps\waterfall_custom_viz\appserver\static\visualizations\waterfall
- Relevant .conf files are placed under required directory structure

# savedsearches.conf 
$SPLUNK_HOME\etc\apps\waterfall_custom_viz\default\savedsearches.conf has configurable properties defined for SimpleXML and SplunkJS


Release Notes:
1.0.4
Releasing for AppInspection re-run. No Code Change.

1.0.3
Following features are added
	- Compiled on latest dependencies as of now
		"webpack": "^4.43.0",
		"webpack-cli": "^3.3.12"
		"d3": "^5.16.0",
		"jquery": "^3.5.1",
		"underscore": "^1.10.2"
	- Built on Mac/Nix
	- Tooltip text on mouseover
	- Drilldown on mouse click
	- Support for Dark Theme
	- Chart overflow for x & y axis to allow scrolling as per content

## Future Enhancements

The visualization current does not have following features:
	- Trellis Layout
	- x-axis label rotation
	- Dynamic Visualization size