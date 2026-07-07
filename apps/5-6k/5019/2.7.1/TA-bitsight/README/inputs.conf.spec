[bitsight://<name>]
company_tree_multiselect = Select the companies for which you want to collect data. It will take a few seconds to populate.
edit_flag = 
index = (Default: default)
interval = Time interval of input in seconds. (Default: 86400)
skip_checkpoint = Selecting this checkbox allows TA to skip checkpointing and ingest all data at each interval. Use this option carefully, as it may lead to data duplication and increased indexing costs.
start_date = The date (UTC in "YYYY-MM-DD" format) from when to start collecting the data. The default value taken will be 90 days ago. Earliest allowed date is 400 days before today.

[bitsight_benchmarking://<name>]
company_tree_multiselect = Select the benchmarked companies for which you want to collect data. It will take a few seconds to populate.
edit_flag = 
index = (Default: default)
interval = Time interval of input in seconds. (Default: 86400)
skip_checkpoint = Skip the checkpoint mechanism by selecting this option.
start_date = The date (UTC in "YYYY-MM-DD" format) from when to start collecting the data. The default value taken will be 90 days ago. Earliest allowed date is 400 days before today.
