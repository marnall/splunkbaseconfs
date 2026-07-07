# mvdiff Add-on For Splunk

This app adds the "mvdiff" command, which gives users the ability to compare two multivalue fields and find differences/similarities between their values.

### Installation

1. Install app on search heads(s).

### Usage

    ... | mvdiff left=<field name> right=<field name>

### Description

    Outputs three fields: mv_left, mv_right, mv_intersection
        * mv_left: Values ONLY present in left MV field
        * mv_right: Values ONLY present in right MV field
        * mv_intersection: Values present in both MV fields

