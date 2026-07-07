# Italian Geospatial Lookups for Splunk

This Splunk app provides geospatial lookups and SVG maps for Italian regions and
provinces.
It also provides two supporting lookups to convert names between Italian and
English and to retrieve ISO 3166-2 codes.


### Assets

#### Maps

The maps are available in both KMZ (geospatial lookups) and SVG formats.
They use Italian subdivision names, which are different from those used by
`iplocation`.
The conversion between languages is facilitated by the supporting lookups.

The URLs for loading the SVG images in a Choropleth SVG visualization are
`/static/app/SA-geo_it_lookups/maps/geo_it_regions.svg` and
`/static/app/SA-geo_it_lookups/maps/geo_it_regions.svg`.

#### Supporting lookups

The `geo_attr_it_regions` and `geo_attr_it_provinces` lookups are useful for
data normalization and display.
Both contain the following fields:

- `name`: Italian name of the subdivision. The maps provided use these names.
- `name_en`: English name of the subdivision. `iplocation` uses these region
  names in Splunk 9.x.
- `iso_3166`: ISO 3166-2 code of the subdivision.

The province lookup also includes the additional `region` field, which
references the `name` of the region.


### Example searches

The following are non-exhaustive examples of how to use the provided lookups
in choropleth maps.

#### Geospatial lookups

```
...
| iplocation ip
| search Country="Italy" City!=""
| lookup geo_it_provinces latitude as lat, longitude as lon
| stats count by featureId
| geom geo_it_provinces allFeatures=true
```

```
...
| iplocation ip
| search Country="Italy" Region!=""
| stats count by Region
| lookup geo_attr_it_regions name_en as Region OUTPUT name as Region
| geom geo_it_regions allFeatures=true featureIdField="Region"
```

#### SVG images

```
...
| iplocation ip
| search Country="Italy" City!=""
| lookup geo_it_provinces latitude as lat, longitude as lon
| stats count by featureId
```

```
...
| iplocation ip
| search Country="Italy" Region!=""
| stats count by Region
| lookup geo_attr_it_regions name_en as Region OUTPUT name as Region
```

### Credits

The maps are based on the generalized version of [Confini delle unità amministrative a fini statistici](https://www.istat.it/notizia/confini-delle-unita-amministrative-a-fini-statistici-al-1-gennaio-2018-2/)
(2026) by [Istituto nazionale di statistica](https://www.istat.it/) and are licensed under [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0)
<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg" alt="">
<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg" alt="">

### Issues

Please submit any issue to [https://github.com/aserpi/SA-geo_it_lookups/issues](https://github.com/aserpi/SA-geo_it_lookups/issues).