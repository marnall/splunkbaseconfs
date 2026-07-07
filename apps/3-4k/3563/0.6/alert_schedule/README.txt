@author Eric Plett

Overview

This app gives you the ability to setup alert schedules which include normal working hours, holidays, and maintenance windows
This is done by

Configuring your alert schedules in the provided lookup files
Using the included macro, `check_alerting_schedule(my_schedule_id)` at the end of your alert searches
Configuring your alert to use a Custom Trigger Condition with the check for alerts_active="true"
Alert Configuration

Example Alert can be found here Example Alert
SPL to test the current state of an alert schedule (Note:'US' is the schedule_id field in the lookups)
| makeresults 
| `check_alerting_schedule(US)`
Support

This app is community supported. 

Any bugs, enhancement requests, or general comments please send to Eric Plett