[posthog_activity_logs://<name>]
account = The PostHog account to collect from.
include_values = Adds the previous and new value of every changed field. These can hold the content of the changed object, which makes events larger. Off by default.
index = The index to write events to. Pick one that exists on this Splunk instance. You need it to search the events. (Default: default)
interval = How often to check PostHog for new entries, in seconds. (Default: 300)
organization_id = Collects activity across every project in this organization. Find it in PostHog under Settings, Organization.
start_date = Optional. Collect from this point on the first run only, for example 2026-01-01T00:00:00Z. Later runs resume where the last one stopped.
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set
