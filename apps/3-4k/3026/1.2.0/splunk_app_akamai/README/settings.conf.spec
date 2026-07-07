#  Version 1.2.0
#
# This file contains possible attributes and values you can use to configure
# Splunk App for Akamai's real-time monitor.
#
# There is a settings.conf in $SPLUNK_HOME/etc/apps/splunk_app_akamai/default/.
# To set custom configurations, place a settings.conf in
# $SPLUNK_HOME/etc/apps/system/local/. For examples, see settings.conf.example.
# You must restart Splunk to enable configurations.
#
# To learn more about configuration files (including precedence) please see
# the documentation located at
# http://docs.splunk.com/Documentation/Splunk/latest/Admin/Aboutconfigurationfiles

[realtime]
* Set real-time monitor configuration options under this stanza name.
* Follow this stanza name with any number of the following attribute/value
  pairs.

REAL_TIME_DELAY = <integer>
* How much delay real time monitor has in seconds
* Some delay is necessary to collect data from edge servers, indexing and storing them in KV store
* At least 90 seconds is a minimum delay to get some accurate data in the real time monitor.
  Below this value some values can be missed.
* Defaults to 120 seconds

REAL_TIME_WINDOW = <integer>
* How big is the time window in the real-time monitor in seconds
* This limit should not exceed 1200. Setting this limit higher than 1200
  causes instability or inaccuracy in real-time monitor.
* Defaults to 300 seconds

HEAT_MAP_EVENT_TTL = <integer>
* How long an event will influence the heat map in seconds.
* Reducing this value can help to increase performance but also can impact heat map clarity because its state
  will be much more transient.
* Defaults to 5

EVENT_MAX_COUNT = <integer>
* This threshold is used as the maximum value for the number of requests from a location according to the
  HEAT_MAP_EVENT_TTL value.
* Greater or equal value will use the hottest color heat map's color (red by default).
* All others events' color will be decided according to this value.
  e.g. 25 is represented by yellow because it is the half of 50, so it's half-way on the gradient from blue to red.
* Defaults to 50

EVENT_MAX_TRAFFIC = <integer>
* This threshold (in MB) is used as the maximum value for the volume of data returned by servers for a location
  according to the HEAT_MAP_EVENT_TTL value.
* Greater or equal value will use the hottest color heat map's color (red by default).
* All others events' color will be decided according to this value.
  e.g. 500 MB is represented by yellow because it is the half of 1 GB, so it's half-way on the gradient from blue to red.
* Defaults to 10

EVENTS_FETCHING_PERIOD_IN_SECONDS = <integer>
* Fetching events data period in seconds
* Client will fetch events data from server every X seconds
* Increasing this value can reduce the pressure on the server but increase memory usage on the client
* Defaults to 15

MAX_EVENTS_FETCHED = <integer>
* Maximum number of rows retrieved for each server call to fetch events
* An event aggregates number of hits and traffic per city per second
* Note: limits.conf also contains a maxresultrows property, make sure your modifications in this file is consistent with
  limits.conf value
* Defaults to 50000

MAX_EVENTS_DISPLAYED = <integer>
* Maximum number of events displayed on the screen using an animation (Live and Recent Traffic layers)
* Increasing this value has an important impact on rendering performance
* Defaults to 300

EDGE_FETCHING_PERIOD_IN_SECONDS = <integer>
* Fetching edge servers data period in seconds
* Client will fetch edge servers data from server every X seconds
* Increasing this value can reduce the pressure on the server but increase memory usage on the client
* Defaults to 150

MAX_EDGE_SERVERS = <integer>
* Maximum number of rows retrieved for each server call to fetch edge servers data
* A row aggregates number of hits, traffic, number of edge servers per city for the last 5 minutes.
* Defaults to 10000

MAX_QUEUE_SIZE = <integer>
* Maximum number of events queued on the client
* Defaults to 30000

REQUEST_FILL_COLOR = <string>
* Color of dots representing requests event in hex rgb
* Defaults to #03A2D6 (light blue)

EDGE_FILL_COLOR = <string>
* Color of edge circles representing edge servers data in hex rgb
* Defaults to #AC99D6 (light purple)

HEATMAP_COLORS = <array of string>
* Gradient used for heat map colors
* The value is an array of string in hex rgb. Each element of the array defines a stop color in the gradient.
* Defaults to ['#00f', '#0ff', '#0f0', '#ff0', '#f00'] (from blue to red)

REQUEST_EDGE_CIRCLE_SIZE_FACTOR = <integer>
* Factor used to calculate edge server data representation according to number of requests.
* Following formula is used: Math.log10(value) * config.REQUEST_EDGE_CIRCLE_SIZE_FACTOR+ 2;
* Defaults to 4

TRAFFIC_EDGE_CIRCLE_SIZE_FACTOR = <integer>
* Factor used to calculate edge server data representation according to amount of data.
* Following formula is used: Math.log10(trafficInMB) * config.TRAFFIC_EDGE_CIRCLE_SIZE_FACTOR + 2
* Defaults to 6

MAX_EDGE_CIRCLE_SIZE = <integer>
* Biggest circle radius to represent edge server data in pixels
* Defaults to 60

ERROR_FETCHING_PERIOD_IN_SECONDS = <integer>
* Fetching error request data period in seconds
* Client will fetch error request data from server every X seconds
* Increasing this value can reduce the pressure on the server but increase memory usage on the client
* Defaults to 15

MAX_ERROR_REQUESTS = <integer>
* Maximum number of rows retrieved for each error request call to fetch error request data
* Defaults to 50000

ERROR_FILL_COLOR = <string>
* Color of error circles representing error request data in hex rgb
* Defaults to #E64B3C(red brick)

MAX_ERROR_CIRCLE_SIZE = <integer>
* Biggest circle radius to represent error request data in pixels
* Defaults to 20

# Following will unlikely be modified

CITY_MAX_RESOLUTION = <integer>
* Max resolution for which city level details will be used to display edge servers data
* Defaults to 3000

REGION_MAX_RESOLUTION = <integer>
* Max resolution for which region level details will be used to display edge servers data
* Defaults to 10000

COUNTRY_MAX_RESOLUTION = <integer>
* Max resolution for which country level details will be used to display edge servers data
* Defaults to 10000000000

DEFAULT_VIEW_CENTER = <array of floats>
* Default center view coordinates
* The array contains 2 floats to define the coordinates (longitude and latitude in this order) used to center the view
* Defaults to [0,0]
