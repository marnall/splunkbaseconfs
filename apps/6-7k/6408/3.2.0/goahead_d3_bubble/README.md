# D3 BUBBLE by GoAhead

## Introduction

RENEWAL!
"D3 BUBBLE" is a custom viz App to show the circular packing chart by using "D3.js".
The size of bubble and neighborhood of bubbles means the statistics and relationship strength.
This kind of chart is called as Bubble Cloud, Bubble Plot and Circular Packing Chart too.
We have two styles.
1. (this) D3 BUBBLE: Using legacy D3 v3.5 
2. (another: not ready) D3 DYNAMIC BUBBLE: implemented more color variety and force simulation Using D3 v6.7
We separated the former D3 BUBBLE because their circle-packing layout algorizm is much different between D3 v3 and v4 later. [ref](https://github.com/d3/d3/blob/main/CHANGES.md#hierarchies-d3-hierarchy)


## Installation

D3 BUBBLE is a standard Splunk Visualization App and requires no special configuration.
Restarting splunk search head instance may be possibly needed for activating this app's logo.
This app is 'invisible' by default because there is no app view.

## Usage
 - **screen0(viz tab)**
 - **source=foo | stats value_field by name_field, category_field**
    - *name_field: used as the label on each bubble*
    - *value_field: used as the value of each bubble (also dictates size) e.g. count*
    - *category_field: (optionally) used for grouping similar data (color effect)*
    - examples
        + `index=_internal | stats count by name group | sort - count`


 - Functions on Visualization Formatter
    - `drilldown search and dashboard search token supported by double clicking the bubble name after enabled in "Click Action under Formatter"`

    - `tooltip supported by moving the mouse cursol on the bubble`

    - `viz area size can be changed by dragging the frame`

    - `text font can be changed in range of only generic font family name`

    - `text color can be changed in range of html color palette.`

    - `selection about the font size between classic or dynamic`

    - Default property
      - width 500px
      - height 250px
      - colorPalette: category20c (d3.scale.category20c()) 
        - ref) https://github.com/d3/d3-3.x-api-reference/blob/master/Ordinal-Scales.md
        - colorPalette can be controlled by Viz Formatter




## Included 3rd party's modules

- [d3](https://github.com/d3/d3) (3.5.17)

*This app is inspired from a custom view app of [splunk_wftoolkit](https://splunkbase.splunk.com/app/1613/).*


## Support

Splunk 8.x or later.


## License

[APACHE LICENSE, VERSION 2.0](https://www.apache.org/licenses/LICENSE-2.0)

## Copyright

Copyright 2022 GoAhead Inc.

