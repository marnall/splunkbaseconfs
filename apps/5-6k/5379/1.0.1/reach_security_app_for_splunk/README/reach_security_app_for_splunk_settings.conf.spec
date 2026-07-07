[proxy]
proxy_enabled = 
proxy_type = 
proxy_url = 
proxy_port = 
proxy_username = 
proxy_password = 
proxy_rdns = 

[logging]
loglevel = 

[additional_parameters]
auto_search = Boolean to start the execution immediately
url = Reach service endpoint
password = API token of Reach endpoint
interval = Time gap for executing and exporting the results in seconds
starts_from = Last day from when data collection will start
products = List of Splunk Apps/Add-ons from where data will be collected
anonymize_fields = Boolean to anonymize fields
fields_to_anonymize = List of fields to anonymize by default
result_fields = List of fields to store in result CSV files

[reach_single_execution]
status = Status of execution process
result_file_name = File name having result data
execution_start_time = Start time of the current execution
last_success_time = Time of last successful execution

[reach_periodic_execution]
status = Status of execution process
result_file_name = File name having result data
execution_start_time = Start time of the current execution
last_success_time = Time of last successful execution
checkpoint_time = Checkpoint time of last execution
