#this file does absoutely nothing , but Splunk Appinspect will fail the check_alert_actions_exe_exist rule if it is not present.
#this is a logic error in Splunk Appinspect as of v2.26.0 and has been reported
#Appinspect fails to consider the use case where your alert_actions.conf file executes a custom search command rather than specifying an alert_action script.