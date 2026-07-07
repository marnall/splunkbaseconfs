[proxy]
proxy_enabled = <bool> Should the proxy enabled or not
proxy_type = <string> type of the proxy i.e. http, https, sock4 or sock5
proxy_url = <string> Proxy url
proxy_port = <integer> Proxy port
proxy_username = <string> Username for the proxy server
proxy_password = <string> Password for the proxy server user

[logging]
loglevel = <string> Log level of the data collection logs

[additional_parameters]
base_event_type = <string> This search query will be the base search for all eventtypes. Enter Search query without a pipe operator, subsearch or report reference
messages_outstanding = <integer> Maximum messages to be fetch in single pipeline
bytes_outstanding = <integer> Maximum bytes to be fetch in single pipeline
thread_count = <integer> Maximum thread to be used to fetch data simultaneously
merged_filesize_limit = <integer> Maximum file size of merged gzip file
close_file_in_seconds = <integer> Time in seconds to keep the file in local. After this value, file will be moved to spool.

[email_notification]
email_enable = <bool>
email_address = <string>
notify_after = <string>
smtp_server = <string>
additional_message = <string>
enable_throttle = <bool>
throttle_duration = <string>

[scripted_input_parameters]
account_name = Account name for the new inputs to be created.
type = Types of events to collect. Default will be all types of events if no option is selected.
start_datetime = Only Events after this DateTime will be fetched. \n UTC Format: YYYY-MM-DDTHH:MM:SSZ (E.g. 2020-02-22T05:40:58Z)
user_end_datetime = Only Events till this DateTime will be fetched. \n UTC Format: YYYY-MM-DDTHH:MM:SSZ (E.g. 2020-02-22T05:40:58Z)
data_collection_window = Time Window in minutes between Start DateTime and End DateTime for the new inputs to be created.
index = Index for the new inputs to be created.
max_active_inputs = Maximum active inputs that can be running for the data collection.

[csv_input]
custom_path_enabled = <bool> Should the custom path enabled or not for csv data.
custom_path = <string> Full path where CSV file will be stored.
