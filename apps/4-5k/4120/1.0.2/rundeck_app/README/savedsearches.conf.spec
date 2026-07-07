#
# Spec file for Rundeck Alert Action for POSTing a job execution request to /api/$api_version$/job/$job_id$/run
#

action.rundeck_jobalert = [0|1]
# Enable Rundeck job running alert


action.rundeck_jobalert.param.https_api_host = <string>
# your Rundeck host , ie: foo.myrundeck.com (don't include 'https://' , this is hardcoded by default to satisfy Splunk certification requirements for secure network communications)
# (required)

action.rundeck_jobalert.param.job_id = <string>
# The job ID to run
# (required)

action.rundeck_jobalert.param.job_as_user = <string>
# specifies a username identifying the user who ran the job. Requires runAs permission.
# (optional)

action.rundeck_jobalert.param.job_run_at_time= <string>
# This is a ISO-8601 date  with optional timezone and milliseconds., e.g. 2016-11-23T12:20:55-0800 or 2016-11-23T12:20:55.123-0800
# (optional)

action.rundeck_jobalert.param.job_filter= <string>
# can be a Rundeck node filter string
# (optional)

action.rundeck_jobalert.param.job_argstring= <string>
# argument string to pass to the job, of the form: -opt value -opt2 value ....
# (optional)