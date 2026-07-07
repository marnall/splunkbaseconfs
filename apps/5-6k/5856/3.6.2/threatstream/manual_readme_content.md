**Playbook Backward Compatibility**

- New action parameters have been added to the actions given below. Hence, it is requested to the
  end-user please update their existing playbooks and provide values to these new action
  parameters to ensure the correct functioning of the playbooks created on the earlier versions of
  the app.

  - **For version 3.4.X :**

    - Import domain observable - **source** parameter has been added
    - Import URL observable - **source, allow_unresolved** parameters have been added
    - Import IP observable - **source** parameter has been added
    - Import file observable - **source** parameter has been added
    - Import email observable - **source** parameter has been added
    - Detonate file - **use_premium_sandbox, use_vmray_sandbox, vmray_max_jobs, fields**
      parameters have been added
    - Detonate URL - **use_premium_sandbox, use_vmray_sandbox, vmray_max_jobs, fields**
      parameters have been added

  - **For version 3.0.X :**

    - Import domain observable - **with_approval, allow_unresolved** parameters have been
      added
    - Import URL observable - **with_approval** parameter has been added
    - Import IP observable - **with_approval** parameter has been added
    - Import file observable - **with_approval** parameter has been added
    - Import email observable - **with_approval** parameter has been added
    - Import observables - **with_approval, allow_unresolved** parameters have been added
    - List threat models - **publication_status** parameter has been added

  - **For version 2.0.9 :**

    - Create Incident - **create_on_cloud** parameter has been added
    - Import domain observable - **create_on_cloud** parameter has been added
    - Import URL observable - **create_on_cloud** parameter has been added
    - Import IP observable - **create_on_cloud** parameter has been added
    - Import file observable - **create_on_cloud** parameter has been added
    - Import email observable - **create_on_cloud** parameter has been added
    - Import observables - **create_on_cloud** parameter has been added

**Asset Configuration Parameters**

- **is_cloud_instance** - This boolean parameter is used to indicate whether the Anomali
  Threatstream instance is on the cloud. If the parameter is left unchecked, the app and its
  functionalities will internally consider it as an on-prem instance.

**Prerequisite for \[Delete Incident / Delete Actor / Delete Vulnerability / Delete Rule / Delete
Threat Bulletin\] actions**

- The authenticated user in the app should have appropriate permissions (Organization Admin) for
  deleting the incidents/actors/vulnerabilities/rules/threat-bulletins on the Anomali Threatstream
  instance for these actions to be executed successfully.

**Behavior for [Whois IP] action**

- If the action can fetch additional whois data for the provided IP then, the action will pass
  successfully with that additional data.
- If the action is unable to fetch additional whois data for the provided IP then, the action will
  pass successfully without that additional data but with an appropriate message.

**Behavior for Domain Reputation**

- The action will try to find an intelligence with the same name provided in the [domain]
  parameter in the Anomali ThreatStream instance. If it is not found, then 'None' will be
  displayed under the corresponding columns in the output view.
- If the provided domain is not found as intelligence in the Anomali ThreatStream instance, then
  the user needs to import a domain observable with the provided domain as input and then try to
  re-run the [domain reputation] action.

**On Poll Functionality**

- It fetches the incidents (belonging to the configured organization ID in the configuration
  parameters) and their intelligence data to ingest them as containers and artifacts.

- Approaches for fetching incidents based on the **Ingest only incidents marked published**
  configuration parameter

  - Parameter kept unchecked: Ingesting all the incidents irrespective of their publication
    status
  - Parameter kept checked: Ingesting the incidents which are only in the published state

- Types of polling

  - Manual Polling

    - All the incidents are fetched, controlled by the count mentioned in the container_count
      parameter in the oldest first order based on the **modified_ts** value of the incidents
      irrespective of the incidents fetched in the last run. If the user tries to run the
      manual polling again with a value less than the already ingested incidents, then, again
      the same incidents will be fetched starting from the oldest first and will be marked as
      duplicates. It is recommended to run manual polling using a relatively greater value in
      the container_count parameter to ensure all the incidents are ingested.
    - The **modified_ts** time of the last fetched incident is not considered for consequent
      runs of the manual polling.

  - Scheduled | Interval Polling

    - Same functionality as manual polling along with the additional points mentioned below:

      - **The maximum number of incidents to poll in the first run of the scheduled
        polling** configuration parameter governs the number of incidents fetched in the
        first run.
      - The **modified_ts** time of the last fetched incident is stored in the
        **last_incident_time** key of the state file.
      - For the consecutive runs, the incidents are fetched starting from the time stored in
        the **last_incident_time** key of the state file.
      - Please provide a larger value in the **Maximum number of incidents to poll in the
        first run of the scheduled polling** configuration parameter to fetch all the
        existing (older) incidents in the first run itself. From the consecutive runs, the
        newly created or the modified incidents will be automatically ingested.

**Behavior for \[Create vulnerability / Update vulnerability / Create actor / Update Actor / Create
threat bulletin / Update threat bulletin\] actions**

- Trusted circles are not available locally on On-prem (Hybrid) instance.

**Behavior for \[Create vulnerability / Update vulnerability / Create actor / Update Actor / Create
threat bulletin / Update threat bulletin / Create incident / Update incident\] actions**

- The action uses different API endpoints for creating / updating an entity and associating
  intelligence, attachments, import sessions or comments to the entity.
- If the action fails to associate the intelligence, attachments, import sessions or comments
  while creating an entity, the user can associate them by running the Update action with valid
  inputs.

**Confidence action parameter for import observable related actions**

- For [import file observable] and [import email observable] actions user has to provide the
  confidence value in [confidence] action parameter.

- For [import domain observable], [import ip observable], and [import url observable]
  actions ThreatStream automatically gives the confidence value based on some internal logical
  operations | processes as per the API documentation.

- For [import observable] action user can provide confidence value in 'fields' parameter as
  {"confidence": \<confidence_value>}.

  - For hash and email type of observable, the value of the confidence will be reflected.
  - For domain, IP, and URL type of observable, the value of the confidence will be ignored.

**Behavior of import\_\<indicator_type>\_observable and the import_observables actions**

- The action run just sends a request for importing the observable value to the Anomali server.

- The action run is a success if a response of **202 Accepted** is returned by the Anomali API.
  The action does not wait for the observable to reflect on the Anomali UI.

- The successful run of the actions does not guarantee the successful import of the observable on
  the Anomali server

  - If the provided parameters and their expected combinations are correct, then the observable
    will be successfully imported after an indefinite interval of time (based on the Anomali
    server).
  - If the provided parameters and their combinations are incorrect, then the action run would
    be a success (because the API does not return an error response for this and accepts the
    request) though the observable is not imported on the Anomali server.

- It is recommended to add a required time delay between the action blocks which are dependent on
  the successful import of an observable.

- To check if the observable was successfully imported, the user can run and check the **List
  Observables** action which fetches the observables in the latest first order (based on
  **created_ts** time).

**List of indicator types (itype) for the import\_\<indicator_type>\_observable and the
import_observables actions (To be given as input when with_approval parameter is set to False)**

| actor_ip | actor_ipv6 | adware_domain | adware_registry_key |
|-------------------------|----------------------|-------------------------|-----------------------------|
| anon_proxy | anon_proxy_ipv6 | anon_vpn | anon_vpn_ipv6 |
| apt_domain | apt_email | apt_file_name | apt_file_path |
| apt_ip | apt_ipv6 | apt_md5 | apt_mta |
| apt_mutex | apt_registry_key | apt_service_description | apt_service_displayname |
| apt_service_name | apt_ssdeep | apt_subject | apt_ua |
| apt_url | bot_ip | bot_ipv6 | brute_ip |
| brute_ipv6 | c2_domain | c2_ip | c2_ipv6 |
| c2_url | comm_proxy_domain | comm_proxy_ip | compromised_domain |
| compromised_email | compromised_ip | compromised_ipv6 | compromised_service_account |
| compromised_url | crypto_hash | crypto_ip | crypto_pool |
| crypto_url | crypto_wallet | ddos_ip | ddos_ipv6 |
| disposable_email_domain | dyn_dns | exfil_domain | exfil_ip |
| exfil_ipv6 | exfil_url | exploit_domain | exploit_ip |
| exploit_ipv6 | exploit_url | fraud_domain | fraud_ip |
| fraud_md5 | fraud_email | fraud_url | free_email_domain |
| geolocation_url | hack_tool | i2p_ip | i2p_ipv6 |
| ipcheck_url | mal_domain | mal_email | mal_file_name |
| mal_file_path | mal_ip | mal_ipv6 | mal_md5 |
| mal_mutex | mal_registry_key | mal_service_description | mal_service_displayname |
| mal_service_name | mal_ssdeep | mal_sslcert_sh1 | mal_ua |
| mal_url | p2pcnc | p2pcnc_ipv6 | parked_domain |
| parked_ip | parked_ipv6 | parked_url | pastesite_url |
| phish_domain | phish_email | phish_ip | phish_ipv6 |
| phish_md5 | phish_url | proxy_ip | proxy_ipv6 |
| scan_ip | scan_ipv6 | sinkhole_domain | sinkhole_ip |
| sinkhole_ipv6 | social_media_url | spam_domain | spam_email |
| spam_ip | spam_ipv6 | spam_mta | spam_url |
| speedtest_url | ssh_ip | ssh_ipv6 | ssl_cert_serial_number |
| suppress | suspicious_domain | suspicious_email | suspicious_ip |
| suspicious_reg_email | suspicious_url | tor_ip | tor_ipv6 |
| torrent_tracker_url | vpn_domain | vps_ip | vps_ipv6 |
| whois_bulk_reg_email | whois_privacy_domain | whois_privacy_email | |

**NOTE:** If the input contains any indicator_type value except the ones listed above, the action
will behave according to the API behavior.

**List of threat types (threat_type) for the import\_\<indicator_type>\_observable and the
import_observables actions (To be given as input when with_approval parameter is set to True)**

| adware | anomalous | anonymization | apt |
|--------|---------------|---------------|-------------|
| bot | brute | c2 | compromised |
| crypto | data_leakage | ddos | dyn_dns |
| exfil | exploit | fraud | hack_tool |
| i2p | informational | malware | p2p |
| parked | phish | scan | sinkhole |
| spam | suppress | suspicious | tor |
| vps | | | |

**NOTE:** If the input contains any threat_type value except the ones listed above, the action will
behave according to the API behavior.

## Port Information

The app uses HTTP/HTTPS protocol for communicating with the ThreatStream Server. Below are the
default ports used by Splunk SOAR.

| Service Name | Transport Protocol | Port |
|--------------|--------------------|------|
| http | tcp | 80 |
| https | tcp | 443 |

## ipwhois

This app uses the ipwhois module, which is licensed under the BSD License, Copyright (c) 2013-2019
Philip Hane.

## pythonwhois-alt

This app uses the pythonwhois-alt module, which is licensed under the MIT License, Copyright (c)
Michael Ramsey.

## dnspython

This app uses the dns module, which is licensed under the Freeware (BSD-like) License, Copyright (c)
2018 Bob Halley.
