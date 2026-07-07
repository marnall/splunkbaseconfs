# Installation

Perform the Setup using the setup page.

The download of indicators is performed based on the misp_list.csv file and downloaded on the following command: '| getmisp'

By default a download is launch every day at 0:00am. In order to force a download, launch the report GetMispData


# Configuration

All the configuration is perform through the misp_lists.csv lookup:

## Columns:

* Lookup_file: Name of the standard output lookup (used in Splunk Enterprise lookups)
* URL: MISP url to be able to download the proper list (Check MISP automation documentation for further details).
* ThreatIntelTransforms: Transformation which will be applied to the CSV header in order to format it with supported column names
* SplitPatterns: Split the 'value' column into multiple columns based on the provided pattern. Note this transformation is applied before the ThreatIntelTransforms

## ThreatIntelTransforms Format:

    <src_column1>|<dest_column1>&<src_column2>|<dest_column2>

In order to add a new column, use the same format with a src_column empty.

## Split Patterns format

    <value1>|<value2>

Note that currently only the "value" is supported with the '|' separator.
