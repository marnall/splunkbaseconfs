# Google GeoCode App

## Overview

Google GeoCode app is a way to translate your address fields into (latitude,longitude) and also reverse i.e. (latitude,longitude) into Address. Just use the command "printgeocode" in pipeline to your Splunk search command and convert your address to geolocation points or vice versa.

Version: 1.7.1

# Infrastructure Requiment

Any Operating system (tested on Windows 10 and Linux)
Splunk 6.5, 6.6

# Installation

  - Install the app on your Splunk Search Head(s).
  - Get a google API key from [Google API Key](https://developers.google.com/maps/documentation/javascript/get-api-key)
  - Write the API_Key in the setup page
  - Restart Splunk Search Head.

# Usage
  - Geocoding: Address to latitude,longitude
```sh
  <your splunk query>|printgeocode type=geocode address=Address
```
  OR 
```sh  
   <your splunk query>|printgeocode type=reverse latfield=<latfieldname> lonfield=<lonfieldname>
 ```
  Where type=geocoding tells the app that it is geocoding
  Address is the name of the text field in your data which contains a valid address. For example:

 ```sh
index=test sourcetype="users_addresses" | head 2| table first_name last_name address city country Address | printgeocode type=geocode address=Address
```

 ![Geocoding](https://github.com/meenalluktuke/GoogleGeoCode/blob/master/Geocoding1.PNG)

- Use map with latitude,longitude from the output of the command
 ```sh
index=test sourcetype="users_addresses" | head 2| table first_name last_name address city country Address | printgeocode type=geocode address=Address| geostats count latfield=geolocation_lat longfield=geolocation_lon 
```

  ![Geocoding Map](https://github.com/meenalluktuke/GoogleGeoCode/blob/master/Geocoding2.PNG)


- Reverse Geocoding: latitude,longitude to Address
 ```sh
index=test sourcetype="user_latlon" | head 5| table policyID line county point_latitude point_longitude | printgeocode type=reverse latfield=point_latitude lonfield=point_longitude 
```
  Where type=reverse tells the app that this is Reverse Geocoding
  and point_latitude,point_longitude are the lat,lon fields in your data
  
  
  ![Reverse Geocoding](https://github.com/meenalluktuke/GoogleGeoCode/blob/master/ReverseGeocoding.PNG)


As simple as looking for a location on Maps :)

### Troubleshooting

- If you do not get any results after printgeocode but your query is working fine otherwise, it means that probably you have exhaused the daily request limit (2500 requests per day) for free version.
--  Option1: Get a new Key and put that value in myconfig.py. Restart Splunk search head, the results should be good.
-- Option 2: Wait for midnight PST timezone for the limit to rest :)


More information and code is avaialble here:

[Gitgub Link](https://github.com/meenalluktuke/GoogleGeoCode/blob/master/README.md)

# References
The app uses the geopy Python library. Here's the link to their [documentation](https://pypi.python.org/pypi/geopy)

geopy is a Python 2 and 3 client for several popular geocoding web services.
geopy makes it easy for Python developers to locate the coordinates of addresses, cities, countries, and landmarks across the globe using third-party geocoders and other data sources.

geopy is tested against CPython 2.7, CPython 3.2, CPython 3.4, PyPy, and PyPy3.

The app uses version 1.11.0 of the geopy library.
Github link for the project - [Github Link](https://github.com/geopy/geopy)


# Contact Information
For any issues or questions, please reach out to: meenal.luktuke@gmail.com
We provide only Level-1 support for this application.

