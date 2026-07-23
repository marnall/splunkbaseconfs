[rss_feed_input://<name>]
http_timeout = HTTP request timeout in seconds. (Default: 30)
index = (Default: default)
interval = Time interval of the data input, in seconds. (Default: 300)
sourcetype = Sourcetype assigned to indexed feed entries. (Default: rss:feed)
strip_html_tags = Remove HTML markup from title, summary, and content before indexing.
timestamp_field = Feed entry field used as _time when Event timestamp is Feed entry field. (Default: published)
timestamp_mode = Use poll execution time as Splunk _time, or a date field from each feed entry. (Default: indexing_time)
url = RSS or ATOM feed URL.
verify_ssl = Verify SSL certificates when fetching the feed. (Default: 1)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set
