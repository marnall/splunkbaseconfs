[interval_query://<name>]
mongodb_url = MognoDB Connection String
use_credentials = 
username = 
password = 
collection = 
time_field = Specify the time field which will be used to query data.
additional_query = Additional query criteira to be added (Query as if its db.collection.find())
cores = Number of cores to split the workload between.
checkpointing = Set to enabled if this job requires checkpoint capabilities (Check documentation for details)
project_fields_radio = If checked, MongoDB will return only the specified fields in the Field Projection field. If the field is unchecked the query will just exclude the specified fields.
projected_fields = A comma delimited list of the fields to be projected/supressed.
keyword_filtering_enabled = If checked the script will offer keyword filtering. You can use this field if you have a big payload field and you wish to extract only the useful data.
payload_field = Active when Keyword Filtering is checked. Specify the path to the payload filter you wish to filter through.
keywords = A comma delimited list of keywords which will be filtered. Active when Keyword Filtering is checked.
source_field_path = Provide the name of the field to use in the _source field in splunk.
host_field_path = Provide the name of the field to use in the _host field in splunk.
