[opencti_stream://<name>]
import_from = The number of days to go back for the initial data collection. The start date is calculated on the basis of the current UTC time. (Default: 30)
index = (Default: default)
input_type = Choose where to store the data. 	•	KV Store keeps structured data for lookups. 	•	Index saves events for searching and alerting. (Default: kvstore)
interval = Time interval of the data input, in seconds. (Default: 0)
stream_id = OpenCTI Stream Id to consume
