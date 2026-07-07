# D3 HORIZON by GoAhead

## Introduction

Custom visualization App to show  horizon chart by using "D3.js".
This horizon chart is more colorful and has overlap function of area.

X axis is Datetime by default, however Numerical and Categorical fields are available.

Also, Drilldown and dashboard token are available for additional search. 
Furthermore, custom tooltip is supported by moving the mouse cursol on the area.

Let's compare the beautiful waves per category, this chart may possibly replace stacked area chart!

## Installation

D3 HORIZON is a standard Splunk Visualization App and requires no special configuration.
Restarting splunk search head instance may be possibly needed for activating this app's logo.
This app is 'invisible' by default because there is no app view.

## Usage
 - screenshot1.png
 - ** | table y_field x_field y_innerfield**
 - ** | stats yinner_field by y_field, x_field**

Optional: Color Grouping function
 - ** | table y_field x_field colorgroup y_innerfield**
 - ** | stats yinner_field by y_field, x_field, colorgroup**

### Input Data Format
- screenshot6.png

## Functions on Visualization Formatter. (☆: default)

  - `Click action`
  - - Click mode in (☆None, Drilldown, Set tokens) 

  - `X Axis`
  - - xAxis Type in (☆Datetime, Numerical, Categorical)
  - - Datetime Format (☆%Y-%m-%d)

  - `Area`
  - - Line Curve: ☆Natural
  - - Overlap Rate in range 0.1 ~ 0.9, ☆0.5 
  - - Max Value in (☆Hide, Show)
  - - Rendering Limit in (☆up to 50,000 , Unlimited)

  - `Color`
  - - Color Grouing function is available if your query output has "colorgroup" field which value is between 1 and 20. (not by default, you can use it after set on Color Grouping formatter.)
  - - Color Palette: ☆d3.schemeCategory10,  we have 51 color palettes!


  - `Text`
  - - Text font: ☆system-ui
  - - Text color: ☆black
  - - Text size in (☆"Big(20px)","Small(10px)")

The viz area size can be changed by dragging the frame.

## Compare to built-in Area chart
 - screenshot5.png

## Included 3rd party's modules

- [d3](https://github.com/d3/d3) (6.7.0)


## Support

Splunk 8.x or later.


## License

[APACHE LICENSE, VERSION 2.0](https://www.apache.org/licenses/LICENSE-2.0)

## Copyright

Copyright 2026 GoAhead Inc.