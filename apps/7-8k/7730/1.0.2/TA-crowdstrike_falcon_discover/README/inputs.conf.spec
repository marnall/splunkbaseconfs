[input_cs_applications://<name>]
cron_schedule = Cron schedule expression how often data should be collected (Default: 0 0 * * *)
cs_account = Select the account created on the Configuration tab.
excluded_fields = (optional) Comma-separated list of fields to exclude from indexing. Example: name_vendor_version,host.kernel_version
fql_filter_applications = (optional) Filter applications to collect for each device.
fql_filter_applications_help = 
fql_filter_devices = (optional) Filter devices for which to collect application data.
fql_filter_devices_help = 
index = (Default: default)
index_host_info = e.g. hostname/platform/external_ip. If disabled, application events will "only" have an aid (agent/sensor ID) field for host correlation.
interval = The input is designed to run continuously (interval=0). Do not change this setting! (Default: 0)
num_worker_threads = Number of concurrent worker threads collecting data (1-10) (Default: 5)
verify = (Default: true)
