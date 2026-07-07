[proofpoint_incidents://<name>]
account = Account to use for this input.
collection_method = (Default: continuous)
custom_sourcetype = default sourcetype:proofpoint:incident. changing this may impact index time extractions (Default: proofpoint:incident)
end_date = Applicable only for One-time collection method. provide datetime in format YYYY-MM-DDTHH:MM:SS. eg: 2021-12-28T06:40:00. If not specified then Default: current time in UTC
index = (Default: default)
interval = Time interval of the data input, in seconds. (Default: 300)
start_date = provide datetime in format YYYY-MM-DDTHH:MM:SS. eg: 2021-12-28T06:40:00. If not specified then Default: last 7 days
