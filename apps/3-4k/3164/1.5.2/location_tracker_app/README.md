# Location Tracker

Documentation:
http://docs.splunk.com/Documentation/LocationTracker/1.2.0/LocationTrackerViz/RealTimeTrackerIntro

## Sample Queries

```
| inputlookup locations.csv | table _time lat lon user
```
