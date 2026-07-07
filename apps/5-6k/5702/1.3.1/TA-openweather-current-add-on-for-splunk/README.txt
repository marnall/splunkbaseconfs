This is an add-on powered by the Splunk Add-on Builder.

OpenWeather Current Add-On for Splunk consists in a modular input that allows collecting current weather events from a specific location using the following methods: CityID, ZipCode, or Geolocalization (latitude, longitude).

Uses the Weather API for current weather data, and requires a valid OpenWeather API key. The free license allows up to 60 calls per minute.



## Sourcetype:

This add-on uses the included sourcetypes:
	
	openweather:current:json for the collected current events. The event timestamp is set after the dt field in the event data.
	
	openweather:fivedayforecast:json for the collected forecast events. The event timestamp is set after the dt field in the event data.

	openweather:airpollution:json for the collected air pollution current events. The event timestamp is set after the dt field in the event data.



## Installation:

Download and install directly from Splunk, or download from Splunkbase and untar the package in $SPLUNK_HOME/etc/apps/ directory. 



## Configuration:

Go to the OpenWeather Current Add-On for Splunk in the Splunk Enterprise menu and access the configuration section where you have to add the OpenWeather account with the associated API key as password. 

Next we need to configure an modular input in the Inputs section, here we need to define the index where Splunk is going to collect the events and the Interval for collection. It is recommended that you create a dedicate index for this data. 

### For current weather events and forecast weather events:

It is required to specify a localization method and fill the value field from this method. The available localization methods are: CityID, ZipCode, or Geolocalization (latitude, longitude), with the following values:

	CityID: value: <city_id>. Example: 12345

	ZipCode: value: <zip_code>,<country_code>. Example: 1234,cn

	Geolocalization: value: <lat>,<lon>. Example: -12.34,56.78

WARNING: The CityID and ZipCode localization methods are currently deprecated and not mantained anymore. Geolocalization is the recomended method.

The units of measurement setting allows to select one of the following options:

	standard: temperature in Kelvin.

	metric: temperature in Celsius.

	imperial: temperature in Fahrenheit.

### For air pollution events:

	Geolocalization: value: <lat>,<lon>. Example: -34.615796,-58.5156989



## Observations

The OpenWeather API is deprecating the build-in CityID and ZipCode localization methods. They are still usable but unmaintained.
https://openweathermap.org/current#geocoding



## Changelog:
    1.3.1 : AirPollution input now uses HTTPS.
    1.3.0 : Added modular input for air pollution events.
    1.2.0 : Changed source value for the input stanza name. Thanks 'david.w.holland@gmail.com' for the feedback on this issue.
	    Fixed dt parsing in current and forecast inputs
	    Fixed event parsing in forecast inputs
    1.1.2 : Current weather uses HTTPS request.
    1.1.1 : AOB upgrade for jquery 3.5 and python requirements.
    1.1.0 : Added 5 day forecast input. 
    1.0.0 : Release version.
    
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-openweather-current-add-on-for-splunk/bin/ta_openweather_current_add_on_for_splunk/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-openweather-current-add-on-for-splunk/bin/ta_openweather_current_add_on_for_splunk/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-openweather-current-add-on-for-splunk/bin/ta_openweather_current_add_on_for_splunk/aob_py3/setuptools/gui-arm64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-openweather-current-add-on-for-splunk/bin/ta_openweather_current_add_on_for_splunk/aob_py3/setuptools/gui-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-openweather-current-add-on-for-splunk/bin/ta_openweather_current_add_on_for_splunk/aob_py3/setuptools/cli.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-openweather-current-add-on-for-splunk/bin/ta_openweather_current_add_on_for_splunk/aob_py3/setuptools/gui.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-openweather-current-add-on-for-splunk/bin/ta_openweather_current_add_on_for_splunk/aob_py3/setuptools/gui-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-openweather-current-add-on-for-splunk/bin/ta_openweather_current_add_on_for_splunk/aob_py3/setuptools/cli-arm64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-openweather-current-add-on-for-splunk/bin/ta_openweather_current_add_on_for_splunk/aob_py3/setuptools/cli-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-openweather-current-add-on-for-splunk/bin/ta_openweather_current_add_on_for_splunk/aob_py3/setuptools/cli-32.exe: this file does not require any source code
