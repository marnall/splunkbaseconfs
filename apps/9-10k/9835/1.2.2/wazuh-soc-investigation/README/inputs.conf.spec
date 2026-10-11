[wazuh_vuln_input://<name>]
indexer_host = <string>
* Hostname or IP of the Wazuh Indexer.

port = <integer>
* Indexer port. Default 9200.

username = <string>
* A read-only Wazuh indexer account, for example readall.

password = <string>
* Password for the indexer account. Stored encrypted by Splunk.

index_pattern = <string>
* Indexer index pattern. Default wazuh-states-vulnerabilities*.

verify_ssl = <boolean>
* Verify the indexer's SSL certificate. Default false, since Wazuh
  indexers normally use a self-signed certificate.

page_size = <integer>
* Number of documents fetched per page. Default 1000.
