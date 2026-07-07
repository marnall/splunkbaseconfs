# D3 SUNBURST by GoAhead

## Introduction

"D3 SUNBURST" is a custom viz App to show the sunburst chart by using "D3.js".
This Sunburst chart has breadcrumbs of field name and field value and a description in central.
51 color scheme can be used and the sizes of breadcrumbs and central description color can be set by formatter.
Drilldown and dashboard token are available for additional search.

## Installation

D3 SUNBURST is a standard Splunk Visualization App and requires no special configuration.
Restarting splunk search head instance may be possibly needed for activating this app's logo.
This app is 'invisible' by default because there is no app view.

## Usage
 - **screen0(viz tab)**
 - **source=foo | table field1, field2, field3 ....**
    - The last field of result table is treated as value numbers of sunburst arc.
    - examples
        + `index=_internal | stats count by name, group, log_level`
            + **screenshot1(bubble)**

 - Functions
    - `drilldown search and dashboard search token supported by double clicking the sunburst arc area after enabled in "Click Action"`

    - `breadcrumbs of field name and field value are supported by moving the mouse cursol on the sunburst arc area`

    - `viz area size can be changed by dragging the frame`

    - `central description strings and the color can be set and changed anytime by formatter.`
 
 - Format setting examples
   - **screens**


## Included 3rd party's modules

- [d3](https://github.com/d3/d3) (6.7.0)

*This app is inspired from [Sequences sunburst by Kerry Rodden](https://bl.ocks.org/kerryrodden/766f8f6d31f645c39f488a0befa1e3c8).*



## Support

Splunk 8.x or later.


## Limit

Starting with version 1.2.0, we change the data plot limit from 1000 to 50000 or unlimited to reduce data truncation. As a result, depending on the performance of your display and browser, the second and subsequent rings may not be displayed. As a workaround, please adjust the amount of data passed using SPL commands like head.
Alternatively, please use version 1.1.0, which truncates the data plot at 1000 items.


## License

[APACHE LICENSE, VERSION 2.0](https://www.apache.org/licenses/LICENSE-2.0)

## Copyright

Copyright 2026 GoAhead Inc.

