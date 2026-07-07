# Change Log
## 1.0
+ Initial internal release

## 1.1
+ Cleanup for public release, documentation, bug fixing

## 1.1.1
+ Disabled inputs by default

## 1.1.2
+ Tested compat with 7.2
+ Added readme note that the command must be run with "local=true"

## 1.1.3
+ Tested compatibility with 7.3
+ Minor code change for future py3 compatibility
+ Updated included external library text files

## 1.1.4
+ Bug fix: Inconsistent space/tab usage in the lookup caused it to fail to work as expected
+ Tested compatibility with 8.0 and py3

# Prerequisites
This search command is packaged with the following external libraries:
+ GeoNames city database: http://download.geonames.org/export/dump/cities1000.zip
+ GeoNames Admin Code database: http://download.geonames.org/export/dump/admin1CodesASCII.txt
+ GeoNames Country database: http://download.geonames.org/export/dump/countryInfo.txt

The city list is maintained via a scripted input that uses the following OS utilities:
+ rm
+ wget
+ unzip
+ cat
+ cut
+ echo
+ date
+ grep

# Known Issues
+ The lookup is inefficient so results are produced slowly. This is because of the looping used to try and find a matching city to produce a lat/long. It may change in the future but it's not a show stopping issue.

# Installation
Follow standard Splunk installation procedures to install this app.

Reference: https://docs.splunk.com/Documentation/AddOns/released/Overview/Singleserverinstall
Reference: https://docs.splunk.com/Documentation/AddOns/released/Overview/Distributedinstall

## Scripted Inputs for Updating Libraries
There are two scripted inputs:
* updatecountry.sh
* updatecities.sh

These are written for Linux systems and are disabled by default. The expected libraries are included with this app and this is only important if you want to maintain updated versions of the external databases.

# Description
The purpose of this app is to provide an external lookup method for converting city information into the nearest known lat/long combination primarily for the generation of identity and asset information for Splunk Enterprise Security.

## How it works
1. Determine if a lat/lon are provided OR if a city/country/region was provided
+ If the user provides a lat/lon, we try to return a city/region/country
+ If a city/country/region is provided, we try to return the lat/lon

2. If a city/country was provided, 
+ Normalize the country provided to an ISO code, if possible (i.e. United States should be US)
+ Check to see if a region value was provided and try to normalize it as well (i.e. Colorado should be CO.)
+ Note: if a region is not provided, a partial match using just the City and Country is attempted.

3. Do the lookup
+ When doing a conversion from lat/lon to City/Region/Country - the lookup parses all cities in the list in an attempt to find the closest match based on distance between the provided lat/lon and the database lat/lon
+ When performing a city/region/country lookup, a simple text match is performed.

## Region Normalization
This app leverages the admin codes database (http://download.geonames.org/export/dump/admin1CodesASCII.txt) for region normalization. When the lookup is initialized a dictionary is created converting entries in this database from:
* CA.08	Ontario	Ontario	6093943
To:
* [CA.08] = Ontario

When a region is provided during the lookup, the app attempts to find the first matching value and return the key. If a key is found, then we use the region portion (i.e. 08) as the region for our lookup:
`region = matched_key[len(result[args.country])+1::]`

The result is the ability to match database entries formated like this:
* Amherstburg     42.11679        -83.04985       CA      08      America/Toronto

(City / Lat / Lon / Country Code / Region Code / Timezone) 

# Usage
## Command Type
* External Lookup

## Command Usage
The external lookup cannot be distributed at this time. Ensure the lookup command is set to "local=true".

```
| lookup local=true geolocate city,region,country OUTPUT lat,lon
```

Additionally, the lookup can output the matched time zone:
```
| lookup local=true geolocate city,region,country OUTPUT lat,lon,timezone
```

# Support
If support is required or you would like to contribute to this project, please reference: https://gitlab.com/johnfromthefuture/TA-geolocate. This app is supported by the developer as time allows.
