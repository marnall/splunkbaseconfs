[splunkbase_apps://<name>]
search_query = This is the equivalent of the search bar in the Splunkbase interface. If you are looking for apps with keywords, enter them here. To get all apps, leave this blank.
fields = App information can be added or removed by including fields in the listing request.
include_archived_apps = Enable this to search for archived apps. If all apps are desired, archived or not, then a second input must be made where this checkbox is set to the opposite setting.
splunk_products = Splunkbase lists apps for Splunk Enterprise and SOAR. The specific product can be filtered for here.
results_limit = Limit the number of results. 0 = no limit
custom_source = A custom source value can be set here. Default source: "splunkbase_apps".
custom_sourcetype = A custom sourcetype can be set here. Defaults to "splunkbase:apps"