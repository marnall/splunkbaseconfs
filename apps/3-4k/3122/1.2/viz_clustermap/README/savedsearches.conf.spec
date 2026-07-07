# Custom clustermap viz settings

display.visualizations.custom.viz_clustermap.clustermap.lat = <float>
* Latitude of initial map position

display.visualizations.custom.viz_clustermap.clustermap.lng = <float>
* Longitude of initial map position

display.visualizations.custom.viz_clustermap.clustermap.zoom = <int>
* Initial zoom level of map

display.visualizations.custom.viz_clustermap.clustermap.tiles = [light|dark|custom]
* Map tiles to use

display.visualizations.custom.viz_clustermap.clustermap.tiles_url = <string>
* Custom tiles URL template to use when fetching map tile images

display.visualizations.custom.viz_clustermap.clustermap.tiles_min_zoom = <int>
display.visualizations.custom.viz_clustermap.clustermap.tiles_max_zoom = <int>
* Zoom bounds for custom tile layer

display.visualizations.custom.viz_clustermap.clustermap.size = <int>
* Size of the cluster icons in pixels

display.visualizations.custom.viz_clustermap.clustermap.maxClusters = <int>
* Maximum number of cluster to fetch from the search results at a time

# Custom colors
# The results are divided into 4 bins, each represented by a different color
# Use these settings to customize the coloring of those bins

display.visualizations.custom.viz_clustermap.clustermap.markerColor1 = <color>
* Color of the lowest range of cluster icons

display.visualizations.custom.viz_clustermap.clustermap.markerColor2 = <color>
* Color of the second-lowest range of cluster icons

display.visualizations.custom.viz_clustermap.clustermap.markerColor3 = <color>
* Color of the second-highest range of cluster icons

display.visualizations.custom.viz_clustermap.clustermap.markerColor4 = <color>
* Color of the highest range of cluster icons

display.visualizations.custom.viz_clustermap.clustermap.numberFormat_min_<min> = <numeral-format>
* Define the number format numbers greater than the given minimum value <min>
* The value is a numeral format string. For more information check out http://numeraljs.com/
* The number format rule with the greatest <min> value, while still being lower than the actual value, will take precedence.
