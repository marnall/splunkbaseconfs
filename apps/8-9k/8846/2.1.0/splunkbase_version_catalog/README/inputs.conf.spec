[splunkbase_catalog://<name>]
app_ids = <string> Comma-separated list of Splunkbase numeric app IDs to track (the number in the app's Splunkbase URL, e.g. 833,2890). Leave empty and set fetch_all = true to catalogue the entire Splunkbase listing.
fetch_all = <boolean> When true, paginates the entire Splunkbase listing instead of only app_ids. Heavy: roughly one request per app. Default false.
max_apps = <integer> Upper bound on how many apps to retrieve when fetch_all is true. Default 200.
run_at = <string> Fixed daily time (24-hour HH:MM, search head local time) to refresh the catalogue, e.g. "03:15". Default "03:15" if left blank.
proxy_url = <string> Optional outbound HTTP(S) proxy URL, e.g. https://proxy.example.com:8080.
verify_ssl = <boolean> Verify TLS certificates on outbound Splunkbase calls. Default true.
