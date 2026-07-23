# MITRE ATLAS&trade; Heatmap

Custom Visualizations give you new interactive ways to visualize your data during search and investigation, and to better communicate results in dashboards and reports. After installing this app you'll find a MITRE ATLAS Heatmap diagram as an additional item in the visualization picker in Search and Dashboard.

This app uses ATLAS v5.6.0. For more information visit https://atlas.mitre.org/

This app is a port of the [MITRE ATT&CK Heatmap for Splunk](https://github.com/alatif113/mitre_attack_heatmap) by Mohammed Latif, adapted to render the MITRE ATLAS matrix (tactics and techniques used to attack AI/ML systems) instead of the ATT&CK matrix.

## Usage

### Search Query

`| table <atlas_technique_id> <numerical_value> [description]`

OR

`| stats <aggregation> by <atlas_technique_id>`

The visualization requires at least 2 fields to be present within the search output, with an optional third:
1. **atlas_technique_id**: The ID of a MITRE ATLAS Technique (e.g. AML.T0000)
2. **numerical_value / aggregation**: A numerical value or aggregation to associate with the technique (e.g. count, sum, average)
3. **(Optional) description**: An optional description to associate with the technique, to display within a tooltip on mouse hover.

### Example search query

```
| stats count AS "Detection Count" first(description) as description by id
| table id "Detection Count" description
```

### Drilldowns

1. **Sub-Technique ID**: the ID of a selected sub-technique is drilldownable via `$row.mtr_sub-technique_id$`
2. **Technique ID**: the ID of a selected technique (either by clicking an underlying sub-technique or the technique itself) is drilldownable via `$row.mtr_technique_id$`
3. **Tactic ID**: the ID of a selected tactic (either by clicking an underlying technique or the tactic itself) is drilldownable via `$row.mtr_tactic_id$`
4. **Sub-Technique Name**: the name of a selected sub-technique is drilldownable via `$row.mtr_sub-technique_name$`
5. **Technique Name**: the name of a selected technique is drilldownable via `$row.mtr_technique_name$`
6. **Tactic Name**: the name of a selected tactic is drilldownable (either by clicking an underlying technique or the tactic itself) via `$row.mtr_tactic_name$`
7. **Sub-Technique Value**: the value of a selected sub-technique is drilldownable via `$row.mtr_sub-technique_value$`
8. **Technique Value**: the value of a selected technique is drilldownable (either by clicking an underlying sub-technique or the technique itself) via `$row.mtr_technique_value$`
9. **Tactic Value**: the value of a selected tactic is drilldownable (either by clicking an underlying technique or the tactic itself) via `$row.mtr_tactic_value$`

If any of the above values are not defined, the associated token is unset.

## Updating the ATLAS data

The matrix data lives in `appserver/static/visualizations/mitre_atlas_heatmap/build/atlasMatrix.js`. To refresh it from the latest ATLAS release:

```
cd bin
pip install pyyaml requests
python atlas2json.py
cd ../appserver/static/visualizations/mitre_atlas_heatmap
npm install webpack webpack-cli jquery underscore
webpack --config webpack.config.js
```

## Support

Please report issues via your internal channels. Based on https://github.com/alatif113/mitre_attack_heatmap.

## Change Log

### v1.0.0
- Initial release, ported from MITRE ATT&CK Heatmap for Splunk v1.9.1, data sourced from MITRE ATLAS v5.6.0.

## LICENSE / Attribution

MITRE ATLAS&trade; and ATLAS&trade; are trademarks of The MITRE Corporation. Data sourced from https://github.com/mitre-atlas/atlas-data, made available by MITRE.

This app's code is derived from the MITRE ATT&CK Heatmap for Splunk app, (c) Mohammed Latif, used under its GNU General Public License (see LICENSE).
