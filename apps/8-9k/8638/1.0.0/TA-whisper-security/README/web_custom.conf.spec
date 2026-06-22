#
# web_custom.conf.spec — Custom REST endpoint expose stanzas for Whisper Security TA
#
# This file documents the settings in web_custom.conf that control which
# custom REST endpoints are exposed via the Splunk Web layer.
#

[expose:<name>]
pattern = <string>
* URL pattern to expose for the REST endpoint.
* Example: whisper_test_connectivity

methods = <string>
* Comma-separated list of HTTP methods allowed.
* Example: POST, GET
