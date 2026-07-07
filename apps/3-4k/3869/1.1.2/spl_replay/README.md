# Splunk SPL Replay

- Splunk SPL Replay version 1.1.2
- Copyright (C) 2005-2018 Splunk Inc. All Rights Reserved.

In conjunction with Splunk's SplunkZero Team (www.splunk.com), and Aplura, LLC (www.aplura.com), we are pleased to show you the `replay` custom command.

`replay` is designed to execute adhoc or scheduled searches based on results in SPL. The SA was designed to execute searches only to perform load testing/repeatable searches on a Search Head. This command WILL NOT return events back into the main search.

## Usage

The `replay` command takes several optional parameters. Defaults are listed in the table below. Three fields are required for the command to work correctly. `earliest`, `latest`, and `search`. These can be named anything (as long as the option is set), but these are the defaults. Earliest and latest are "Splunk Time Modifier" compatibile fields. You can use "-2d@d" or unix seconds in those fields. `search` contains the search to execute and must contain a generating command. 

This command will not return events back to the main search, so if you need those results, you must use data summerization techniques (think summary indexing) or the like. This command schedules and dispatches separate threads for each search using the Splunk REST endpoints. This allows the main search to finish while allowing the main Splunk scheduler the ability to execute the search based on resources. 

### SHC Compatibility
The `replay` command offers both non-SHC and SHC support. If you wish to use the SHC feature, set the corresponding flag (`shc_lb`) according to the table below. `IMPORTANT`: In order to use SHC Load balancing, you must have a common user stored in the Password Store. Use `set_credential.sh` to create the user credential in the store. The user must also exist on all SH in the cluster (the user must be created as a user AND be present in the store).

### Modes
This command offers the ability to perform in two different modes. They are `ad-hoc` and `scheduled`.

#### Ad Hoc
`Ad-hoc` mode allows a splunk user to ingest a CSV or result set of searches and dispatch them immediately. This is useful when immediate load testing is desired, with no regard for the timing of the searches. This mode is easiest to use, and requires the least amount of fields. See Example 1 below.

#### Scheduled 
`Scheduled` mode takes a specific set of fields, and *schedules* the searches. While in this mode, the main search (the one that is executed to run `replay`) will set itself into a "PAUSED" state. While in this state, it will continue to monitor and dispatch searches according to the schedules set. If you desire to end the main search, simply unpause it, and it will finalize automatically. This mechanism is required to maintain the schedules of to-be-executed searches, as well as to allow it to not become an orphan in the event of a restart, or other action, that kills the parent search. See example 2 below.

The field `schedule_time` is required for scheduled searches. This field contains a timestamp to use for scheduled exection. The DATE of the timestamp does not matter, but the TIME does. IF the timestamp is in the future, that's ok, the TIME will be used (%H:%M:%S). The scheduler supports seconds-level granularity. The default is to poll and execute searches every 10 seconds.
 
### Search Command Defaults

| Option        | Default | Type  | Description | 
| ------------- |---------|--------------|------|
| earliest      | earliest | field name | The field that contains the earliest time modifier. Can use Splunk Notation ("-1d@d") or Unix Epoch time. | 
| latest      | latest  |   field name | The field that contains the latest time modifier. Can use Splunk Notation ("-1d@d") or Unix Epoch time. |
| search | search |    field name | The field that contains the search string to execute. Must begin with a generating command. |
| schedule | false | boolean | A true value needs schedule_time to be in the results. This tells the command to schedule search execution according to time.|
| schedule_time | schedule_time | field name | This is the field that contains the time was executed. Date is not important, but the TIME is important. This is in Unix Epoch time only.|
| time_diff | 86400 | integer | This is the offset at which to schedule the search. This is in seconds. Defaults to 1 day.|
| timer | 10 | integer | This controls the polling of the scheduler in seconds. Allows for batch scheduling (every 10 seconds for example)|
| show_data | false| boolean | This shows detailed output from the REST commands used to execute the searches.|
| shc_lb | false | boolean | This allows you to use all UP members of a SHC to execute searches. |
| shc_lb_user | None | string | This specifies the user to use when dispatching to SHC members. MUST EXIST ON ALL MEMBERS AND HAVE THE PASSWORD STORED IN THE CREDENTIAL STORE ON EACH MEMBER |

## Examples

1. `| makeresults | eval search="search index=_internal | stats count by host", earliest="-1h@h", latest="now" | replay`
    - This creates the three required fields, and then executes the search.   
1. `| makeresults | eval search="search index=_internal | stats count by host", earliest="-1h@h", latest="now", schedule_time = now() + 30 | replay schedule=true`
    - This creates a scheduled search. It is scheduled for "now + 30s". 
    
## Support Offered
Support for this is community based, not commercial. Use the email address listed for further information.
You can start by generating a DIAG, using the command `$SPLUNK_HOME/bin/splunk diag --collect=app:spl_replay`. This can then be sent to whomever is supporting the app. Most likely the community. 
You can also search `index=_internal sourcetype=replay` and find detailed information. Turn on `DEBUG` logging to see even more diagnostic information.

## Event Generator

None.

## Summary Indexing, Data Model Acceleration, Report Acceleration

None. 

## Third-party software

This Add-On makes use of the "schedule" python package. "schedule" is made available under the MIT license. The original package can be found at https://pypi.python.org/pypi/schedule .