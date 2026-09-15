# Attack Path Intelligence App

## Overview

This app models the relationship between Crown Jewels, Attack Surfaces and
Attack Vectors, providing an asset-weighted view of possible attack paths.
It ships with sample lookup data and a dashboard for visualizing and
prioritizing attack paths based on business impact rather than framework
coverage alone.

## Version Support

- Splunk Enterprise 9.0 and above
- Splunk Cloud Platform

## Requirements

No external dependencies. No data ingestion required. The app works entirely
from CSV lookups included in the package.

## Installation

1. Install the app from Splunkbase or extract the package into
   $SPLUNK_HOME/etc/apps
2. Restart Splunk
3. Open the Attack Path Intelligence App from the app menu

## Configuration

The app ships with generic sample data. Replace the contents of the following
lookups with your own inventory:

- crown_jewel_lookup.csv
- attack_surface_lookup.csv
- attack_vector_lookup.csv
- crown_jewel_surface_lookup.csv
- surface_vector_lookup.csv

The relationship lookups use IDs. A crown jewel can be linked to multiple
attack surfaces, and an attack surface can affect multiple crown jewels.

## How to Run

Open the Attack Path Intelligence dashboard and use the dropdown filters to
explore attack paths by crown jewel, exposure, surface, vector and risk band.

## Troubleshooting

If panels return no results, validate the lookups individually:

    | inputlookup crown_jewel_lookup
    | inputlookup attack_surface_lookup
    | inputlookup attack_vector_lookup
    | inputlookup crown_jewel_surface_lookup
    | inputlookup surface_vector_lookup

Ensure the IDs in the relationship lookups match the IDs in the entity lookups.

## Release Notes

Version 1.0.0: Initial release.

## Support

This app is provided as-is. For questions, contact the author through the
Splunkbase app page.

## License

Apache License 2.0
