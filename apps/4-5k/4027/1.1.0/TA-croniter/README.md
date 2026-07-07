# Change Log
## 1.0
+ Initial Release

## 1.0.1
+ Confirmed compatibility with Splunk 7.2

## 1.0.2
+ Updated Croniter library to 0.3.27 (Previous version: 0.3.22)
+ Updated Splunk SDK to version 1.6.6 (Previous version: 1.6.2)
+ Removed explicit inclusion of six library. Splunk SDK now seems to include this.
+ Added option to specify an end epoch field instead of iteration count

## 1.0.3
+ Updated dateutil library
+ Confirmed compatibility with 7.3

## 1.0.4
+ Confirmed compatibility with 8.0 (python3 environment enabled globally)

## 1.0.5
+ Confirmed compat with 8.1
+ Upgraded Splunk SDK 1.6.14
+ Upgraded Croniter Library to 0.3.36
+ Upgrade dateutil Library to 2.8.1
+ Added natsort 7.0.1

## 1.1.0
+ Upgraded Splunk SDK
+ Upgraded Croniter library
+ Upgraded dateutil library
+ Upgraded natsort library
+ Confirmed Splunk 8.2 compatibility

# Prerequisites
This search command is packaged with the following external libraries:
+ Splunk SDK for Python (http://dev.splunk.com/python)
+ Python Croniter Library (https://github.com/taichino/croniter)
+ Python dateutil Library (https://github.com/dateutil/dateutil)
+ Python six Library (https://pypi.org/project/six/)
+ Python natsort Library (https://github.com/SethMMorton/natsort)

Nothing further is required for this add-on to function.

# Installation
Follow standard Splunk installation procedures to install this app.

Reference: https://docs.splunk.com/Documentation/AddOns/released/Overview/Singleserverinstall
Reference: https://docs.splunk.com/Documentation/AddOns/released/Overview/Distributedinstall

# Description
The purpose of this command is to help visualize cron schedules and produce timestamps for expected runs based on the cron schedule. This was created largely to address the question, "How many searches are going to be running at timeblock X based on current search schedules?" While it may be used in other contexts, this command was built for that single purpose.

# Usage
## Command Type
* Streaming

## Command Usage
```
| croniter iterations=25 input=cron_schedule start_epoch=timestamp_field
```
Or
```
| croniter input=cron_schedule start_epoch=timestamp_field end_epoch=timestamp_field
```

Note that if both "iterations" and "end_epoch" are specified, the end_epoch will take precedence.

## Sample Search
Starting now, show the next 25 expected runs for scheduled searches using a cron schedule and combine them to show which times have the highest number of searches scheduled.
```
| rest /servicesNS/-/-/saved/searches splunk_server=local 
| where disabled=0 and is_scheduled=1 
| table cron_schedule,title,disabled,is_scheduled 
| croniter iterations=25 input=cron_schedule 
| stats values(title) as searches,dc(title) as dc_searches by croniter_return 
| convert ctime(croniter_return) timeformat="%Y-%m-%d %H:%M:%S" 
| sort 0 - dc_searches

```

Same as the previous except start the iterations at a timestamp 2 days previous:
```
| rest /servicesNS/-/-/saved/searches splunk_server=local 
| where disabled=0 and is_scheduled=1 
| table cron_schedule,title,disabled,is_scheduled 
| eval start_epoch=relative_time(now(),"-2d@d")
| croniter iterations=5 input=cron_schedule start_epoch=start_epoch
| stats values(title) as searches,dc(title) as dc_searches by croniter_return 
| convert ctime(croniter_return) timeformat="%Y-%m-%d %H:%M:%S" 
| sort 0 - dc_searches
```

Search using an end epoch instead of iteration count as the marker for stopping the generation:
```
| rest /servicesNS/-/-/saved/searches splunk_server=local 
| where disabled=0 and is_scheduled=1 
| table cron_schedule,title,disabled,is_scheduled
| eval myendepoch=relative_time(now(),"+3d@d")
| croniter end_epoch=myendepoch input=cron_schedule
```

# Support
If support is required or you would like to contribute to this project, please reference: https://gitlab.com/johnfromthefuture/TA-croniter. This app is supported by the developer as time allows.
