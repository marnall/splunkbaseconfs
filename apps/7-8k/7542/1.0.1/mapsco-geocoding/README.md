[comment]: # "Auto-generated SOAR connector documentation"
# Geocoding Maps Co

Publisher: Unapproved Pty Ltd  
Connector Version: 1.0.1  
Product Vendor: My Maps Inc  
Product Name: Geocoding by Map Maker  
Product Version Supported (regex): ".\*"  
Minimum Product Version: 6.2.1  

Forward and Reverse Geocoding

[comment]: # "File: README.md"
[comment]: # ""
[comment]: # "Copyright (c) Unapped, 2024"
[comment]: # ""
[comment]: # "Licensed under the Apache License, Version 2.0 (the 'License');"
[comment]: # "you may not use this file except in compliance with the License."
[comment]: # "You may obtain a copy of the License at"
[comment]: # ""
[comment]: # "    http://www.apache.org/licenses/LICENSE-2.0"
[comment]: # ""
[comment]: # "Unless required by applicable law or agreed to in writing, software distributed under"
[comment]: # "the License is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,"
[comment]: # "either express or implied. See the License for the specific language governing permissions"
[comment]: # "and limitations under the License."
[comment]: # ""
## Getting a license key

Navigate to [maps.co site](https://geocode.maps.co/join/) \> and signup, you can get an api key there, free version limited to one req per second...

NOTE: You need to be logged in to see the lisence key

## Inputting Google API Key (OPTIONAL)

Navigate to Administration \> Administration Settings \> Google Maps. From there, insert the API key.

This will be used to display a map widget.

## Open prots

This needs an outbound port to be permitted to the base_url

## Geocoding API

### Convert Between Addresses & Geographic Coordinates

Geocoding is the process of converting a human-readable address into a pair of latitude and longitude coordinates, which are necessary to "plot" the address on a map. Reverse Geocoding is the opposite, i.e. converting a pair of lat/long coordinates into a human-readable address.

This free geocoding API service is provided by Map Maker (My Maps Inc), a web-based Map Making program. In listening to our customers, we recognized that high-volume geocoding is cost prohibitive. For example, Google Maps charges $5 per 1000 geocode requests. If you need to geocode lots of locations, that becomes expensive very quickly.

To solve this problem we created this free geocoding service, which offers generous limits that will suit most users. For those in need of very high-volume geocoding, we offer very affordable geocoding plans(https://geocode.maps.co/plans/).

You can change the base_url to use the vendors comerical offering.

This app has been developed by the team from unapped

GITHUB: https://github.com/unapped

This app is supported. Please use github to get in touch.


### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a Geocoding by Map Maker asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** |  required  | string | Base URL for service (use default)
**api_key** |  required  | password | API Key (eg: 1234asdf2345)

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[forward geocode](#action-forward-geocode) - Convert human-readable address to coordinates  
[reverse geocode](#action-reverse-geocode) - Convert coordinates to human-readable address  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

Ensures that a firewall is not blocking conections to the base URL.
Base URL should not be changed unless your are using paid API access in which case an alternative base url will be provided.

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'forward geocode'
Convert human-readable address to coordinates

Type: **investigate**  
Read only: **True**

Forward Geocoding process permits two forms of an address.
1) Convert street address to coordinates.
EG: 1 Apple Park Way. Cupertino, CA 95014. United States

2) Convert a location name to coordinates.
EG: Statue of Liberty.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**address** |  required  | Address | string |  `street address` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.address | string |  `street address`  |  
action_result.status | string |  |   success  failed 
action_result.data.\*.\*.lat | numeric |  `latitude`  |  
action_result.data.\*.\*.lon | numeric |  `longitude`  |  
action_result.data.\*.\*.display_name | numeric |  |  
action_result.message | string |  |  
action_result.summary | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'reverse geocode'
Convert coordinates to human-readable address

Type: **investigate**  
Read only: **True**

To reverse geocode, provide both the latitude and longitude parameters to the /reverse endpoint, e.g:

Convert coordinates to human-readable address.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**latitude** |  required  | Latitude coordinate | string |  `latitude` 
**longitude** |  required  | Longitude coordinate | string |  `longitude` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.latitude | string |  `latitude`  |  
action_result.parameter.longitude | string |  `longitude`  |  
action_result.data | string |  |  
action_result.summary | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |  