[ntp_check://<name>]
check_server = 
check_version = 

[dns_check://<name>]
check_host = 
check_rr = 
check_ns = 

[tcp_check://<name>]
check_host = 
check_port = 
check_timeout = 

[icmp_check://<name>]
check_host = 
check_count = 

[http_check://<name>]
check_url = Either input a url to probe, or input a splunk search SPL that outputs a url field
is_splunk_search = 
check_timeout = 
check_sslverify = 
check_follow =