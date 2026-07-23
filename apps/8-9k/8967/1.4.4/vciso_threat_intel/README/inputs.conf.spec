[vciso_feed://<name>]
feed_url = <string>
* Base URL of your vCISO instance, e.g. https://vciso.au (no trailing slash).
* Defaults to https://vciso.au.

feed_key = <string>
* OPTIONAL. Leave blank to pull the PUBLIC aggregated IOC feed (/api/iocs).
* Set your personal feed key (starts with vciso_) to pull ONLY your personal feed
* (/api/feed/<key>) instead. Generate/rotate it in your vCISO profile under
* "Personal SIEM Feed".

verify_tls = <bool>
* Verify the server certificate. Defaults to true. Set false only for an internal
* instance with a self-signed cert.

[vciso_public://<name>]
base_url = <string>
* Base URL of the vCISO instance, e.g. https://vciso.au. Defaults to https://vciso.au.
window_hours = <integer>
* How far back to pull news/advisory items each run. Defaults to 72.
verify_tls = <bool>
* Verify the server certificate. Defaults to true.
feed_key = <string>
* OPTIONAL personal feed key (vciso_...). Blank = public data only. When set, the
* input ALSO pulls your personal IOC feed (dataset=ioc). Generate the key in your
* vCISO profile under Personal SIEM Feed.
