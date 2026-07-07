[salesforce_commerce_cloud_logs_v2://<name>]
ocapi_credentials = Credentials for the Client ID which will be used to authenticate the add-on against SFCC
auth_headers = HTTP Auth headers
webdav_host_url = URL of the WebDAV host where the Salesforce Commerce Cloud instance serves the logs
webdav_endpoint = WebDAV endpoint to the folder where the Salesforce Commerce Cloud instance serves the logs
days_threshold = Lookup for files not older than this threshold
system_log_files_pattern = Regular expression pattern that will be used to match system log file names
custom_log_files_pattern = Regular expression pattern that will be used to match cuistom log file names
jobs_log_files_pattern = Regular expression pattern that will be used to match jobs log file names
services_log_files_pattern = Regular expression pattern that will be used to match jobs log file names
replication_log_files_pattern = Regular expression pattern that will be used to match jobs log file names
other_log_files_pattern = Regular expression pattern that will be used to match other various log file names


[salesforce_commerce_cloud_inventory://<name>]
ocapi_credentials = Credentials for the Client ID which will be used to authenticate the add-on against SFCC
ocapi_data_api_endpoint =
ocapi_hostname =
list_of_inventory_ids = List of Inventory ids separated by commas.

[salesforce_commerce_cloud_etl://<name>]
data_type = ETL data type (catalog, inventory, pricebook, navigation-catalog, site-preferences or audit_log)
events_sourcetype = Events sourcetype (if omitted 'data type' will be set)
events_host = Events host (if omitted 'remote host' will be set)
auth_type = Authentication type (Basic, OAuth or SSH key)
account = Access credentials
remote_host = Remote host
remote_directories = Remote directory list (colon separated, e.g.: /home/acme:/home/globex) where input files are stored
remote_directory_wildcard = Wildcard for filtering remote_directory content (e.g. *delta*.zip, or *full*.zip)
remote_directory_depth = The depth to look at in a remote directory
days_threshold = Lookup for files not older than this threshold
variation_attributes_to_include = Optional: Enter a comma-separated list of variation attribute IDs to include in Catalog data events (e.g., color,size)
custom_attributes_to_include = Optional: Enter a comma-separated list of custom attribute IDs to include in Catalog data events (e.g., taxCode,season)
product_additional_attributes_to_include = Optional: Enter a comma-separated list of product additional attributes to include in Catalog data events (e.g., min-order-quantity,store-non-inventory-flag)
ingest_catalog_variation_groups = Optional: Ingest variation groups to include them in Catalog data events.
audit_log_object_type_filters = Optional: Enter a comma-separated list of object types to exclude from Audit log data events (e.g., Catalog, Inventory List)
catalog_timezone = Optional: Select the timezone applied to catalog file timestamps
pricebook_timezone = Optional: Select the timezone applied to pricebook file timestamps

[salesforce_commerce_cloud_job_statuses://<name>]
ocapi_credentials = Credentials for the Client ID which will be used to authenticate the add-on against SFCC
auth_headers = HTTP Auth headers
ocapi_data_api_endpoint =
ocapi_hostname =
job_types =
from_datetime = Start date and time in format "YYYY-MM-DD HH:MM:SS". NOTE: adjust to GMT
time_buffer = Start time buffer in seconds
host_override = Set a static host which all ingested events to the index will be set to it

[salesforce_commerce_cloud_kpis://<name>]
ocapi_credentials = Credentials for the Client ID which will be used to authenticate the add-on against SFCC
endpoint =
hostname =

[salesforce_commerce_cloud_orders://<name>]
ocapi_credentials = Credentials for the Client ID which will be used to authenticate the add-on against SFCC
auth_headers = HTTP Auth headers
ocapi_shop_ordersearch_url =
ocapi_hostname =
connection_type = Connection type (OCAPI or Gateway)
from_datetime = Start date and time in format "YYYY-MM-DD'T'HH:MM:SS.SSSZ". NOTE: adjust to GMT
to_datetime = End date and time in format "YYYY-MM-DD'T'HH:MM:SS.SSSZ". NOTE: adjust to GMT
delta_period = Split the time period in the given number of seconds
site_id = Specify site identificator
time_buffer = Start time buffer in seconds
select_statement = Select statement
host_override = Set a static host which all ingested events to the index will be set to it

[salesforce_commerce_cloud_ecdn_metrics://<name>]
ocapi_credentials = Credentials for the Client ID which will be used to authenticate the add-on against SFCC
ocapi_hostname =
ocapi_endpoint =
zone =
from_datetime = Start date and time in format "YYYY-MM-DD'T'HH:MM:SS.SSSZ". NOTE: adjust to GMT
to_datetime = End date and time in format "YYYY-MM-DD'T'HH:MM:SS.SSSZ". NOTE: adjust to GMT
filter_pattern = Apply regex pattern to filter the data
time_buffer = End time buffer in seconds
delta_period = Split the time period in the given number of seconds
