[elasticsearch://<name>]
elasticsearch_account = Elasticsearch Account from Configuration to use for this input.
elasticsearch_domain_port = Elasticsearch Domain Name: eg: elasticsearch.example.com:port
elasticsearch_index = Name of the Elastic index to search
elasticsearch_date_field_name = Name of the datetime field to search
time_range = Time Range to monitor events/documents from elasticsearch. e.g: for 1 hour, use 1h, 1 day, use 1d. default is 1h
custom_sourcetype = Enter a custom sourcetype. Default is elasticsearch:$elasticsearchidex:json