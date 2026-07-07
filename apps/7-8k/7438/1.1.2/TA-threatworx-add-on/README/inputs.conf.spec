[threatworx_threat://<name>]
only_impacting_threats = If checked then only Threats which are impacting organizational assets will be ingested.

[threatworx_vulnerability_impact://<name>]
priority = Specify the priority of the vulnerability impacts for filtering. It is recommended to filter and ingest "Do Now" priority impacts in to Splunk.
rating = Specify the rating of the vulnerability impacts for filtering. It is recommended to filter and ingest "Urgent" and "Critical" impacts in to Splunk.
asset_tags = Specify a comma separated list of asset tags for filtering. It is recommended to specify appropriate asset tags.
asset_tags_match_criteria = Specify asset tags matching criteria

[threatworx_sast://<name>]
rating = Specify the rating of the SAST vulnerabilities for filtering. It is recommended to filter and ingest "Urgent" and "Critical" SAST vulnerabilities in to Splunk.
asset_tags = Specify a comma separated list of asset tags for filtering. It is recommended to specify appropriate asset tags.
asset_tags_match_criteria = Specify asset tags matching criteria

[threatworx_secret://<name>]
rating = Specify the rating of the code secrets for filtering. It is recommended to filter and ingest "Urgent" and "Critical" code secrets in to Splunk.
secret_detection_method = Specify the secret detection method for filtering. It is recommended to ingest secrets detected using regular expression and entropy based detection methods.
asset_tags = Specify a comma separated list of asset tags for filtering. It is recommended to specify appropriate asset tags.
asset_tags_match_criteria = Specify asset tags matching criteria

[threatworx_misconfiguration://<name>]
rating = Specify the rating of the misconfigurations for filtering. It is recommended to filter and ingest "Urgent" and "Critical" misconfigurations in to Splunk.
asset_tags = Specify a comma separated list of asset tags for filtering. It is recommended to specify appropriate asset tags.
asset_tags_match_criteria = Specify asset tags matching criteria