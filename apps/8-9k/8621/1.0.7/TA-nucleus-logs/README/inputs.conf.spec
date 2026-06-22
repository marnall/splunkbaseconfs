[nucleus_logs://<name>]
python.version = python3
base_url = <string>  # e.g. https://test.nucleussec.com
api_key = <string>   # x-apikey value (better: store in Splunk password store later)
limit = <integer>    # page size, e.g. 500
initial_since_minutes = <integer>  # used only if no checkpoint exists, e.g. 60
verify_ssl = <boolean> # true/false
index = <string>     # e.g. nucleus
event_sourcetype = <string> # e.g. nucleus:logs
interval = <integer> # how often Splunk runs it, in seconds (set in inputs.conf UI)
