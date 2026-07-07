[jobs_input://<name>]
account = Connection to use for this input.
api_key_id = Filter jobs by API Key ID. Exact match only.
forensic_components = Select the forensics that should be ingested into Splunk. If this input is empty, no forensics are ingested.
index = An index is a type of data repository. Select the index in which you want to collect the events. (Default: main)
ingest_forensics = Ingest normalized forensics corresponding to the ingested jobs
interval = Time interval of the data input, in seconds. (Default: 300)
since = Overrides Backfill value to backfill from a particular point in time. If included, it should be the number of seconds since the Unix epoch and MUST be in the past.
since_options = Time from which to backfill jobs during initial run. By default, no backfill is performed.
source = Filter jobs by submission source. Omit to include all
username = Filter jobs by username. Exact match only.
