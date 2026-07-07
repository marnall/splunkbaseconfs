# Author #
Bo Chen
449072269@qq.com

# Version Support #
`7.3, 7.2, 7.1, 7.0`

# Who is this app for? #
This app is for anyone who wants to visualise time duration in a transposed waterfall format.

# How does the app work? #
This app provides a visualization that you can use in your own apps and dashboards.

To use it in your dashboards, simply install the app, and create a search that provides the values you want to display in given order.

The expected data table should like this:

`...| table _time, total, {p1}-offset, {p1}, {p2}-offset, {p2}, ...`

where `p1`,`p2` are the data pionts you want to show on it. `-offset` is mandatory for each data point even they are all 0.

For example: 

`...| table _time, total, data-1-offset, data-1, data-2-offset, data-2`

* `_time` column will be y Axis label
* `total` column will be the the first bar in the chart and no offset needed
* `data-1-offset` will be the second bar's offset in the chart and will not show
* `data-1` is the real second bar on chart and it continues for `data-2-offset`,`data-2`,...

# Release Notes #
v 0.1.0
## Issues and Limitations ##
No issues identified.

## Privacy and Legal ##
No personally identifiable information is logged or obtained in any way through this visualizaton.

## For support ##
Send email to 449072269@qq.com

Support is not guaranteed and will be provided on a best effort basis.

# Credits #
This visualization uses the echarts.js visualization library.