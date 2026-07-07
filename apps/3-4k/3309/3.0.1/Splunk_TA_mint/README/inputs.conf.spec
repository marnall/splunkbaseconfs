[mi_cds://<name>]

start_by_shell = [true|false]
* Disables starting the Modular Input by the system shell and binds it directly to the splunkd process

polling_interval = <value>
* Polling interval in seconds, defaults to 5

request_limit = <value>
* Request limit in number of Data Transfer Objects (DTO), defaults to 15000

request_timeout = <value>
* Request timeout in seconds, defaults to 30

backoff_time = <value>
* Time in seconds to wait for retry after error or timeout, defaults to 10

https_proxy = <value>
* HTTPS proxy address to use for communication with the Splunk MINT Data Collector, e.g. http://10.10.1.10:3128 or https://user:pass@10.10.1.10:3128

verify_ssl = <value>
* Verify SSL flag for requests lib, set to false only if instructed by Splunk Support

cds_token = <value>
* Token for CDS

cds_url = <value>
* URL for CDS

cloud_install = <value>
* Cloud install flag, set to true only if app is installed on cloud

