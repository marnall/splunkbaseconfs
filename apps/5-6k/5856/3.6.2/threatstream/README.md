# ThreatStream

Publisher: Splunk <br>
Connector Version: 3.6.2 <br>
Product Vendor: Anomali <br>
Product Name: ThreatStream <br>
Minimum Product Version: 6.3.0

Integrates a variety of generic, reputation, and investigative actions from the Anomali ThreatStream threat intelligence platform

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

### Configuration variables

This table lists the configuration variables required to operate ThreatStream. These variables are specified when configuring a ThreatStream asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**hostname** | required | string | Host Name |
**organization_id** | optional | numeric | Organization ID for filtering incidents when polling |
**username** | required | string | User name |
**api_key** | required | password | API Key |
**first_run_containers** | optional | numeric | Maximum number of incidents to poll in the first run of the scheduled polling |
**ingest_only_published_incidents** | optional | boolean | Ingest only incidents marked as published |
**is_cloud_instance** | optional | boolean | Is the provided instance in hostname parameter cloud? |
**verify_server_cert** | optional | boolean | Verify server certificate |

### Supported Actions

[test connectivity](#action-test-connectivity) - Test connectivity to ThreatStream by querying the intelligence endpoint <br>
[file reputation](#action-file-reputation) - Get information about a file <br>
[domain reputation](#action-domain-reputation) - Get information about a given domain <br>
[ip reputation](#action-ip-reputation) - Get information about a given IP <br>
[email reputation](#action-email-reputation) - Get information about a given email <br>
[url reputation](#action-url-reputation) - Get information about a URL <br>
[whois ip](#action-whois-ip) - Execute a whois lookup on the given IP <br>
[whois domain](#action-whois-domain) - Execute a whois lookup on the given domain <br>
[get observable](#action-get-observable) - Get observable present in ThreatStream by ID number <br>
[list observables](#action-list-observables) - List observables present in ThreatStream <br>
[get vulnerability](#action-get-vulnerability) - Get vulnerability present in ThreatStream by ID number <br>
[list vulnerabilities](#action-list-vulnerabilities) - List vulnerabilities present in ThreatStream <br>
[list incidents](#action-list-incidents) - List incidents present in ThreatStream <br>
[delete incident](#action-delete-incident) - Delete incident in ThreatStream by ID number <br>
[get incident](#action-get-incident) - Get incident in ThreatStream by ID number <br>
[create incident](#action-create-incident) - Create an incident in ThreatStream <br>
[update incident](#action-update-incident) - Update an incident in ThreatStream by ID number <br>
[import domain observable](#action-import-domain-observable) - Import domain observable into ThreatStream <br>
[import url observable](#action-import-url-observable) - Import URL observable into ThreatStream <br>
[import ip observable](#action-import-ip-observable) - Import IP observable into ThreatStream <br>
[import file observable](#action-import-file-observable) - Import file observable into ThreatStream <br>
[import email observable](#action-import-email-observable) - Import email observable into ThreatStream <br>
[import observables](#action-import-observables) - Import observables into ThreatStream <br>
[tag observable](#action-tag-observable) - Add a tag to the observable <br>
[get pcap](#action-get-pcap) - Download pcap file of a sample submitted to the sandbox and add it to vault <br>
[detonate file](#action-detonate-file) - Detonate file in ThreatStream <br>
[detonate url](#action-detonate-url) - Detonate URL in ThreatStream <br>
[get status](#action-get-status) - Retrieve detonation status present in Threatstream <br>
[get report](#action-get-report) - Retrieve detonation report present in Threatstream <br>
[on poll](#action-on-poll) - Callback action for the on_poll ingest functionality <br>
[run query](#action-run-query) - Run observables query in ThreatStream <br>
[list import sessions](#action-list-import-sessions) - List all the import sessions <br>
[update import session](#action-update-import-session) - This action updates the fields of the provided item id <br>
[list threat models](#action-list-threat-models) - List all the threat models <br>
[create threat bulletin](#action-create-threat-bulletin) - Create a threat bulletin in ThreatStream <br>
[update threat bulletin](#action-update-threat-bulletin) - Update a threat bulletin in ThreatStream <br>
[list threat bulletins](#action-list-threat-bulletins) - List threat bulletins present in ThreatStream <br>
[list associations](#action-list-associations) - List associations of an entity present in ThreatStream <br>
[create rule](#action-create-rule) - Creates a new rule in Threatstream <br>
[update rule](#action-update-rule) - Update a rule in ThreatStream by ID number <br>
[list rules](#action-list-rules) - List rules present in ThreatStream <br>
[delete rule](#action-delete-rule) - Delete rule in ThreatStream by ID number <br>
[add association](#action-add-association) - Create associations between threat model entities on the ThreatStream platform <br>
[remove association](#action-remove-association) - Remove associations between threat model entities on the ThreatStream platform <br>
[list actors](#action-list-actors) - List actors present in ThreatStream <br>
[list imports](#action-list-imports) - List imports present in ThreatStream <br>
[create vulnerability](#action-create-vulnerability) - Create a vulnerability in ThreatStream <br>
[update vulnerability](#action-update-vulnerability) - Update the vulnerability in ThreatStream <br>
[create actor](#action-create-actor) - Create an actor in ThreatStream <br>
[update actor](#action-update-actor) - Update an actor in ThreatStream <br>
[delete threat bulletin](#action-delete-threat-bulletin) - Delete threat bulletin in ThreatStream by ID <br>
[delete vulnerability](#action-delete-vulnerability) - Delete vulnerability in ThreatStream by ID <br>
[delete actor](#action-delete-actor) - Delete actor in ThreatStream by ID number <br>
[update observable](#action-update-observable) - Update an observable in ThreatStream <br>
[create investigation](#action-create-investigation) - Create an investigation in ThreatStream <br>
[list investigations](#action-list-investigations) - List investigations present in ThreatStream <br>
[get investigation](#action-get-investigation) - Retrieve investigation present in Threatstream by ID <br>
[update investigation](#action-update-investigation) - Update an investigation in ThreatStream <br>
[delete investigation](#action-delete-investigation) - Delete investigation in ThreatStream by ID number

## action: 'test connectivity'

Test connectivity to ThreatStream by querying the intelligence endpoint

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'file reputation'

Get information about a file

Type: **investigate** <br>
Read only: **True**

If nothing is found, this is because ThreatStream has no information on that file. If the limit parameter is not provided, then the default value (1000) will be considered as the value of the limit parameter.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash of file | string | `sha1` `sha256` `md5` `hash` |
**limit** | optional | Total number of observables to return | numeric | |
**extend_source** | optional | Fetch extra data from Anomali server if available | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.extend_source | boolean | | True False |
action_result.parameter.hash | string | `sha1` `sha256` `md5` `hash` | 9bfc3649f7e6067764ce8ef18e8bfbb837bc68f2dd83e37daa05477c604492b2 |
action_result.parameter.limit | numeric | | 1000 |
action_result.data.\*.asn | string | | |
action_result.data.\*.confidence | numeric | | |
action_result.data.\*.country | string | | |
action_result.data.\*.created_ts | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.expiration_ts | string | | |
action_result.data.\*.extended_source | string | | |
action_result.data.\*.external_references.VirusTotal | string | | |
action_result.data.\*.external_references.remote_api | boolean | | True False |
action_result.data.\*.feed_id | numeric | | |
action_result.data.\*.id | numeric | `threatstream intelligence id` | |
action_result.data.\*.import_session_id | string | | |
action_result.data.\*.ip | string | `ip` | |
action_result.data.\*.is_anonymous | boolean | | True False |
action_result.data.\*.is_editable | boolean | | True False |
action_result.data.\*.is_public | boolean | | |
action_result.data.\*.itype | string | | |
action_result.data.\*.latitude | string | | |
action_result.data.\*.longitude | string | | |
action_result.data.\*.meta.detail2 | string | | |
action_result.data.\*.meta.severity | string | | |
action_result.data.\*.modified_ts | string | | |
action_result.data.\*.org | string | | |
action_result.data.\*.owner_organization_id | numeric | `threatstream organization id` | |
action_result.data.\*.rdns | string | | |
action_result.data.\*.resource_uri | string | | |
action_result.data.\*.retina_confidence | numeric | | |
action_result.data.\*.source | string | | |
action_result.data.\*.source_reported_confidence | numeric | | |
action_result.data.\*.status | string | | |
action_result.data.\*.tags | string | | |
action_result.data.\*.tags.\*.id | string | | |
action_result.data.\*.tags.\*.name | string | | |
action_result.data.\*.tags.\*.org_id | string | | |
action_result.data.\*.tags.\*.source_user | string | | |
action_result.data.\*.tags.\*.source_user_id | string | | |
action_result.data.\*.threat_type | string | | |
action_result.data.\*.threatscore | numeric | | |
action_result.data.\*.tlp | string | | |
action_result.data.\*.trusted_circle_ids | string | | |
action_result.data.\*.type | string | | md5 |
action_result.data.\*.update_id | numeric | | |
action_result.data.\*.uuid | string | | 4cf3228b-0de4-45f0-a66d-255b6ff32eaa |
action_result.data.\*.value | string | `md5` | |
action_result.summary | string | | |
action_result.message | string | | Successfully retrieved information on File |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'domain reputation'

Get information about a given domain

Type: **investigate** <br>
Read only: **True**

If nothing is found, this may be due to the format of the domain. Try excluding any subdomains (namely www). If there is still no information found, then it is because ThreatStream has no information on that domain. ThreatStream, however, may still have Passive DNS (PDNS) information on it, which can be found in extra data. If the limit parameter is not provided, then the default value (1000) will be considered as the value of the limit parameter.<br>Extra data includes PDNS, insights, and external resources. By default, extra data is not included in the response. You can update the flag params to include the extra data. The <b>search_exact_value</b> parameter searches for the exact domain on ThreatStream server. If this parameter is kept <b>true</b>, then the <b>extend_source</b> parameter will be ignored and no extra information will be available.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain to investigate | string | `domain` `url` |
**limit** | optional | Total number of observables to return | numeric | |
**extend_source** | optional | Fetch extra data from Anomali server if available | boolean | |
**pdns** | optional | If enabled, pdns will also be fetched | boolean | |
**insights** | optional | If enabled, insights will also be fetched | boolean | |
**external_references** | optional | If enabled, external references will also be fetched | boolean | |
**search_exact_value** | optional | Search for the exact domain | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain | string | `domain` `url` | test.com |
action_result.parameter.extend_source | boolean | | True False |
action_result.parameter.external_references | boolean | | True False |
action_result.parameter.insights | boolean | | True False |
action_result.parameter.limit | numeric | | |
action_result.parameter.pdns | boolean | | True False |
action_result.parameter.search_exact_value | boolean | | True False |
action_result.data.\*.asn | string | | |
action_result.data.\*.confidence | numeric | | |
action_result.data.\*.country | string | | |
action_result.data.\*.created_ts | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.expiration_ts | string | | |
action_result.data.\*.extended_source | string | | |
action_result.data.\*.external_references.Google Safe Browsing | string | | |
action_result.data.\*.external_references.URLVoid | string | | |
action_result.data.\*.external_references.VirusTotal | string | | |
action_result.data.\*.external_references.Web of Trust | string | | |
action_result.data.\*.external_references.urlscan.io | string | | https://test.io/domain/uponvoice.net |
action_result.data.\*.feed_id | numeric | | |
action_result.data.\*.id | numeric | `threatstream intelligence id` | |
action_result.data.\*.import_session_id | string | | |
action_result.data.\*.ip | string | `ip` | |
action_result.data.\*.is_anonymous | boolean | | True False |
action_result.data.\*.is_editable | boolean | | True False |
action_result.data.\*.is_public | boolean | | |
action_result.data.\*.itype | string | | |
action_result.data.\*.latitude | string | | |
action_result.data.\*.longitude | string | | |
action_result.data.\*.meta.detail2 | string | | |
action_result.data.\*.meta.severity | string | | |
action_result.data.\*.modified_ts | string | | |
action_result.data.\*.org | string | | |
action_result.data.\*.owner_organization_id | numeric | `threatstream organization id` | |
action_result.data.\*.rdns | string | | |
action_result.data.\*.resource_uri | string | | |
action_result.data.\*.retina_confidence | numeric | | |
action_result.data.\*.source | string | | |
action_result.data.\*.source_reported_confidence | numeric | | |
action_result.data.\*.status | string | | |
action_result.data.\*.tags.\*.id | string | | |
action_result.data.\*.tags.\*.name | string | | |
action_result.data.\*.tags.\*.org_id | string | | |
action_result.data.\*.tags.\*.source_user | string | | |
action_result.data.\*.tags.\*.source_user_id | string | | |
action_result.data.\*.threat_type | string | | |
action_result.data.\*.threatscore | numeric | | |
action_result.data.\*.tlp | string | | |
action_result.data.\*.trusted_circle_ids | string | | |
action_result.data.\*.type | string | | domain |
action_result.data.\*.update_id | numeric | | |
action_result.data.\*.uuid | string | | 4cf3228b-0de4-45f0-a66d-255b6ff32eaa |
action_result.data.\*.value | string | `domain` | |
action_result.summary | string | | |
action_result.message | string | | Successfully retrieved information on Domain |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'ip reputation'

Get information about a given IP

Type: **investigate** <br>
Read only: **True**

If nothing is found, then it is because ThreatStream has no information on that IP. ThreatStream, however, may still have Passive DNS (PDNS) information on it, which can be found in extra data. If the limit parameter is not provided, then the default value (1000) will be considered as the value of the limit parameter.<br>Extra data includes PDNS, insights, and external resources. By default, extra data is not included in the response. You can update the flag params to include the extra data.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to investigate | string | `ip` `ipv6` |
**limit** | optional | Total number of observables to return | numeric | |
**extend_source** | optional | Fetch extra data from Anomali server if available | boolean | |
**pdns** | optional | If enabled, pdns will also be fetched | boolean | |
**insights** | optional | If enabled, insights will also be fetched | boolean | |
**external_references** | optional | If enabled, external references will also be fetched | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.extend_source | boolean | | True False |
action_result.parameter.external_references | boolean | | True False |
action_result.parameter.insights | boolean | | True False |
action_result.parameter.ip | string | `ip` `ipv6` | 122.122.122.122 |
action_result.parameter.limit | numeric | | 1000 |
action_result.parameter.pdns | boolean | | True False |
action_result.data.\*.asn | string | | |
action_result.data.\*.can_add_public_tags | boolean | | True False |
action_result.data.\*.confidence | numeric | | |
action_result.data.\*.country | string | | |
action_result.data.\*.created_by | string | | |
action_result.data.\*.created_ts | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.expiration_ts | string | | |
action_result.data.\*.extended_source | string | | |
action_result.data.\*.external_references.Google Safe Browsing | string | | |
action_result.data.\*.external_references.IPVoid | string | | |
action_result.data.\*.external_references.Shodan | string | | |
action_result.data.\*.external_references.VirusTotal | string | | |
action_result.data.\*.external_references.remote_api | boolean | | True False |
action_result.data.\*.external_references.urlscan.io | string | | https://test.io/domain/uponvoice.net |
action_result.data.\*.feed_id | numeric | | |
action_result.data.\*.id | numeric | `threatstream intelligence id` | |
action_result.data.\*.import_session_id | numeric | | |
action_result.data.\*.import_source | string | | |
action_result.data.\*.ip | string | `ip` | |
action_result.data.\*.is_anonymous | boolean | | False |
action_result.data.\*.is_editable | boolean | | False |
action_result.data.\*.is_public | boolean | | |
action_result.data.\*.itype | string | | |
action_result.data.\*.latitude | string | | |
action_result.data.\*.longitude | string | | |
action_result.data.\*.meta.detail | string | | Blocklist Brute Force IPs |
action_result.data.\*.meta.detail2 | string | | |
action_result.data.\*.meta.severity | string | | |
action_result.data.\*.modified_ts | string | | |
action_result.data.\*.org | string | | |
action_result.data.\*.owner_organization_id | numeric | `threatstream organization id` | |
action_result.data.\*.rdns | string | | |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_uri | string | | |
action_result.data.\*.retina_confidence | numeric | | |
action_result.data.\*.source | string | | |
action_result.data.\*.source_created | string | | |
action_result.data.\*.source_modified | string | | |
action_result.data.\*.source_reported_confidence | numeric | | |
action_result.data.\*.status | string | | |
action_result.data.\*.subtype | string | | |
action_result.data.\*.tags | string | | |
action_result.data.\*.tags.\*.id | string | | |
action_result.data.\*.tags.\*.name | string | | |
action_result.data.\*.tags.\*.org_id | string | | |
action_result.data.\*.tags.\*.remote_api | boolean | | True False |
action_result.data.\*.tags.\*.source_user | string | | |
action_result.data.\*.tags.\*.source_user_id | string | | |
action_result.data.\*.tags.\*.tlp | string | | red |
action_result.data.\*.threat_type | string | | |
action_result.data.\*.threatscore | numeric | | |
action_result.data.\*.tlp | string | | |
action_result.data.\*.trusted_circle_ids | string | | |
action_result.data.\*.type | string | | ip |
action_result.data.\*.update_id | numeric | | |
action_result.data.\*.uuid | string | | 4cf3228b-0de4-45f0-a66d-255b6ff32eaa |
action_result.data.\*.value | string | `ip` | |
action_result.summary | string | | |
action_result.message | string | | Successfully retrieved information on IP |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'email reputation'

Get information about a given email

Type: **investigate** <br>
Read only: **True**

If the limit parameter is not provided, then the default value (1000) will be considered as the value of the limit parameter. The <b>search_exact_value</b> parameter searches for the exact email on ThreatStream server. If this parameter is kept <b>true</b>, then the <b>extend_source</b> parameter will be ignored and no extra information will be available.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**email** | required | Email to investigate | string | `email` |
**limit** | optional | Total number of observables to return | numeric | |
**extend_source** | optional | Fetch extra data from Anomali server if available | boolean | |
**search_exact_value** | optional | Search for the exact email | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.email | string | `email` | test.com |
action_result.parameter.extend_source | boolean | | True False |
action_result.parameter.limit | numeric | | 1000 |
action_result.parameter.search_exact_value | boolean | | True False |
action_result.data.\*.asn | string | | |
action_result.data.\*.confidence | numeric | | |
action_result.data.\*.country | string | | |
action_result.data.\*.created_ts | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.expiration_ts | string | | |
action_result.data.\*.extended_source | string | | |
action_result.data.\*.external_references.remote_api | boolean | | True False |
action_result.data.\*.feed_id | numeric | | |
action_result.data.\*.id | numeric | `threatstream intelligence id` | |
action_result.data.\*.import_session_id | string | | |
action_result.data.\*.ip | string | `ip` | test@test.com |
action_result.data.\*.is_anonymous | boolean | | True False |
action_result.data.\*.is_editable | boolean | | True False |
action_result.data.\*.is_public | boolean | | |
action_result.data.\*.itype | string | | |
action_result.data.\*.latitude | string | | |
action_result.data.\*.longitude | string | | |
action_result.data.\*.meta.detail | string | | |
action_result.data.\*.meta.detail2 | string | | |
action_result.data.\*.meta.severity | string | | |
action_result.data.\*.modified_ts | string | | |
action_result.data.\*.org | string | | |
action_result.data.\*.owner_organization_id | numeric | `threatstream organization id` | |
action_result.data.\*.rdns | string | | |
action_result.data.\*.resource_uri | string | | |
action_result.data.\*.retina_confidence | numeric | | |
action_result.data.\*.source | string | | |
action_result.data.\*.source_reported_confidence | numeric | | |
action_result.data.\*.status | string | | |
action_result.data.\*.tags | string | | |
action_result.data.\*.tags.\*.id | string | | |
action_result.data.\*.tags.\*.name | string | | |
action_result.data.\*.tags.\*.org_id | string | | |
action_result.data.\*.tags.\*.source_user | string | | |
action_result.data.\*.tags.\*.source_user_id | string | | |
action_result.data.\*.threat_type | string | | |
action_result.data.\*.threatscore | numeric | | |
action_result.data.\*.tlp | string | | |
action_result.data.\*.trusted_circle_ids | string | | |
action_result.data.\*.type | string | | email |
action_result.data.\*.update_id | numeric | | |
action_result.data.\*.uuid | string | | 4cf3228b-0de4-45f0-a66d-255b6ff32eaa |
action_result.data.\*.value | string | `email` | |
action_result.summary | string | | |
action_result.message | string | | Successfully retrieved information on Email |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'url reputation'

Get information about a URL

Type: **investigate** <br>
Read only: **True**

If nothing is found, this is because ThreatStream has no information on that URL. If the limit parameter is not provided, then the default value (1000) will be considered as the value of the limit parameter. The <b>search_exact_value</b> parameter searches for the exact url on ThreatStream server. If this parameter is kept <b>true</b>, then the <b>extend_source</b> parameter will be ignored and no extra information will be available.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL to investigate | string | `url` |
**limit** | optional | Total number of observables to return | numeric | |
**extend_source** | optional | Fetch extra data from Anomali server if available | boolean | |
**search_exact_value** | optional | Search for the exact url | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.extend_source | boolean | | True False |
action_result.parameter.limit | numeric | | 1000 |
action_result.parameter.url | string | `url` | http://122.122.122.122/ |
action_result.parameter.search_exact_value | boolean | | True False |
action_result.data.\*.asn | string | | |
action_result.data.\*.confidence | numeric | | |
action_result.data.\*.country | string | | |
action_result.data.\*.created_ts | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.expiration_ts | string | | |
action_result.data.\*.extended_source | string | | |
action_result.data.\*.feed_id | numeric | | |
action_result.data.\*.id | numeric | `threatstream intelligence id` | |
action_result.data.\*.import_session_id | numeric | | |
action_result.data.\*.ip | string | `ip` | |
action_result.data.\*.is_anonymous | boolean | | False |
action_result.data.\*.is_editable | boolean | | False |
action_result.data.\*.is_public | boolean | | |
action_result.data.\*.itype | string | | |
action_result.data.\*.latitude | numeric | | |
action_result.data.\*.longitude | numeric | | |
action_result.data.\*.meta.detail | string | | |
action_result.data.\*.meta.detail2 | string | | |
action_result.data.\*.meta.registrant_address | string | | |
action_result.data.\*.meta.registrant_created | string | | |
action_result.data.\*.meta.registrant_email | string | | test@test.com |
action_result.data.\*.meta.registrant_name | string | | Protection of Private Person |
action_result.data.\*.meta.registrant_org | string | | |
action_result.data.\*.meta.registrant_phone | string | | |
action_result.data.\*.meta.registrant_updated | string | | |
action_result.data.\*.meta.severity | string | | |
action_result.data.\*.modified_ts | string | | |
action_result.data.\*.org | string | | |
action_result.data.\*.owner_organization_id | numeric | `threatstream organization id` | |
action_result.data.\*.rdns | string | | |
action_result.data.\*.resource_uri | string | | |
action_result.data.\*.retina_confidence | numeric | | |
action_result.data.\*.source | string | | |
action_result.data.\*.source_reported_confidence | numeric | | |
action_result.data.\*.status | string | | |
action_result.data.\*.tags | string | | |
action_result.data.\*.tags.\*.id | string | | |
action_result.data.\*.tags.\*.name | string | | |
action_result.data.\*.tags.\*.org_id | string | | |
action_result.data.\*.tags.\*.source_user | string | | |
action_result.data.\*.tags.\*.source_user_id | string | | |
action_result.data.\*.threat_type | string | | |
action_result.data.\*.threatscore | numeric | | |
action_result.data.\*.tlp | string | | |
action_result.data.\*.trusted_circle_ids | string | | |
action_result.data.\*.type | string | | url |
action_result.data.\*.update_id | numeric | | |
action_result.data.\*.uuid | string | | 4cf3228b-0de4-45f0-a66d-255b6ff32eaa |
action_result.data.\*.value | string | `url` | |
action_result.summary | string | | |
action_result.message | string | | Successfully retrieved information on URL |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'whois ip'

Execute a whois lookup on the given IP

Type: **investigate** <br>
Read only: **True**

ThreatStream returns whois info as a raw string (present in the raw field) which the app will then attempt to parse into the output. Depending on the contents of the raw string, it may not be able to parse all or any of the required fields.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP | string | `ip` `ipv6` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` `ipv6` | 122.122.122.122 |
action_result.data.\*.addtional_info | string | | |
action_result.data.\*.addtional_info.asn | string | | 4134 |
action_result.data.\*.addtional_info.asn_cidr | string | | 122.122.122.122/13 |
action_result.data.\*.addtional_info.asn_country_code | string | | CN |
action_result.data.\*.addtional_info.asn_date | string | | 2009-10-23 |
action_result.data.\*.addtional_info.asn_description | string | | National, NL |
action_result.data.\*.addtional_info.asn_registry | string | | apnic |
action_result.data.\*.addtional_info.nets.\*.address | string | | 3 test IP Street Address |
action_result.data.\*.addtional_info.nets.\*.cidr | string | | 122.122.122.122/32 |
action_result.data.\*.addtional_info.nets.\*.city | string | | |
action_result.data.\*.addtional_info.nets.\*.country | string | | CN |
action_result.data.\*.addtional_info.nets.\*.created | string | | |
action_result.data.\*.addtional_info.nets.\*.description | string | | WX |
action_result.data.\*.addtional_info.nets.\*.emails | string | `email` | testmalicious@cta.cq.cn |
action_result.data.\*.addtional_info.nets.\*.handle | string | | ZL235-AP |
action_result.data.\*.addtional_info.nets.\*.name | string | | WX |
action_result.data.\*.addtional_info.nets.\*.postal_code | string | | |
action_result.data.\*.addtional_info.nets.\*.range | string | | 122.122.122.122 - 122.122.122.122 |
action_result.data.\*.addtional_info.nets.\*.state | string | | |
action_result.data.\*.addtional_info.nets.\*.updated | string | | |
action_result.data.\*.addtional_info.nir | string | | |
action_result.data.\*.addtional_info.query | string | `ip` | 122.122.122.122 |
action_result.data.\*.addtional_info.raw | string | | |
action_result.data.\*.addtional_info.raw_referral | string | | |
action_result.data.\*.addtional_info.referral | string | | |
action_result.data.\*.contacts.admin.handle | string | | IM646-AP |
action_result.data.\*.contacts.billing | string | | |
action_result.data.\*.contacts.registrant | string | | |
action_result.data.\*.contacts.registrant.name | string | | IP Manager |
action_result.data.\*.contacts.tech.handle | string | | IM646-AP |
action_result.data.\*.emails | string | `email` | hostmaster@nic.or.kr |
action_result.data.\*.raw | string | | inetnum: 61.32.0.0 - 61.39.255.255 netname: BORANET descr: LG DACOM Corporation admin-c: IM646-AP tech-c: IM646-AP country: KR status: ALLOCATED PORTABLE mnt-by: MNT-KRNIC-AP mnt-irt: IRT-KRNIC-KR last-modified: 2017-02-03T00:55:02Z source: APNIC irt: IRT-KRNIC-KR address: Jeollanam-do Naju-si Jinheung-gil e-mail: irt@nic.or.kr abuse-mailbox: irt@nic.or.kr admin-c: IM574-AP tech-c: IM574-AP auth: # Filtered remarks: irt@nic.or.kr was validated on 2019-10-01 mnt-by: MNT-KRNIC-AP last-modified: 2019-10-01T08:41:39Z source: APNIC person: IP Manager address: Seoul Yongsan-gu Hangang-daero 32 country: KR phone: +82-2-10-1 e-mail: ipadm@lguplus.co.kr nic-hdl: IM646-AP mnt-by: MNT-KRNIC-AP last-modified: 2017-08-07T01:06:21Z source: APNIC inetnum: 61.32.0.0 - 61.39.255.255 netname: BORANET-KR descr: LG DACOM Corporation country: KR admin-c: IA5-KR tech-c: IA5-KR status: ALLOCATED PORTABLE mnt-by: MNT-KRNIC-AP mnt-irt: IRT-KRNIC-KR remarks: This information has been partially mirrored by APNIC from remarks: KRNIC. To obtain more specific information, please use the remarks: KRNIC whois server at whois.test.or.kr. changed: hostmaster@nic.or.kr source: KRNIC person: IP Manager address: Seoul Yongsan-gu Hangang-daero 32 address: LG UPLUS country: KR phone: +82-2-10-1 e-mail: ipadm@lguplus.co.kr nic-hdl: IA5-KR mnt-by: MNT-KRNIC-AP changed: hostmaster@nic.or.kr source: KRNIC |
action_result.data.\*.status | string | | Allocated Portable |
action_result.data.\*.updated_date | string | | 2017-08-07T01:06:21 |
action_result.summary | string | | |
action_result.message | string | | Successfully retrieved whois info Successfully retrieved whois info. Unable to fetch additional info for the given IP. ERROR: HTTP lookup failed for http://whois.test.or.kr/eng/whois.jsc. |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'whois domain'

Execute a whois lookup on the given domain

Type: **investigate** <br>
Read only: **True**

ThreatStream returns whois info as a raw string (present in the raw field) which the app will then attempt to parse into the output. Depending on the contents of the raw string, it may not be able to parse all or any of the required fields.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain | string | `domain` `url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain | string | `domain` `url` | malware3.obfuscated.network test.com |
action_result.data.\*.contacts.admin | string | | |
action_result.data.\*.contacts.admin.city | string | | Redacted For Privacy |
action_result.data.\*.contacts.admin.country | string | | Redacted For Privacy |
action_result.data.\*.contacts.admin.email | string | `email` | please query the rdds service of the registrar of record identified in this output for information on how to contact the registrant, admin, or tech contact of the queried domain name. |
action_result.data.\*.contacts.admin.fax | string | | REDACTED FOR PRIVACY |
action_result.data.\*.contacts.admin.fax_ext | string | | REDACTED FOR PRIVACY |
action_result.data.\*.contacts.admin.handle | string | | REDACTED FOR PRIVACY |
action_result.data.\*.contacts.admin.name | string | | Redacted For Privacy |
action_result.data.\*.contacts.admin.organization | string | | Redacted For Privacy |
action_result.data.\*.contacts.admin.phone | string | | REDACTED FOR PRIVACY ext. REDACTED FOR PRIVACY |
action_result.data.\*.contacts.admin.postalcode | string | | REDACTED FOR PRIVACY |
action_result.data.\*.contacts.admin.state | string | | Redacted For Privacy |
action_result.data.\*.contacts.admin.street | string | | Redacted For Privacy |
action_result.data.\*.contacts.billing | string | | |
action_result.data.\*.contacts.registrant | string | | |
action_result.data.\*.contacts.registrant.city | string | | Redacted For Privacy |
action_result.data.\*.contacts.registrant.country | string | | United States |
action_result.data.\*.contacts.registrant.email | string | `email` | please query the rdds service of the registrar of record identified in this output for information on how to contact the registrant, admin, or tech contact of the queried domain name. |
action_result.data.\*.contacts.registrant.fax | string | | REDACTED FOR PRIVACY |
action_result.data.\*.contacts.registrant.fax_ext | string | | REDACTED FOR PRIVACY |
action_result.data.\*.contacts.registrant.handle | string | | REDACTED FOR PRIVACY |
action_result.data.\*.contacts.registrant.name | string | | Redacted For Privacy |
action_result.data.\*.contacts.registrant.organization | string | | Domains By Proxy, LLC |
action_result.data.\*.contacts.registrant.phone | string | | REDACTED FOR PRIVACY ext. REDACTED FOR PRIVACY |
action_result.data.\*.contacts.registrant.postalcode | string | | REDACTED FOR PRIVACY |
action_result.data.\*.contacts.registrant.state | string | | Arizona |
action_result.data.\*.contacts.registrant.street | string | | Redacted For Privacy |
action_result.data.\*.contacts.tech | string | | |
action_result.data.\*.contacts.tech.city | string | | Redacted For Privacy |
action_result.data.\*.contacts.tech.country | string | | Redacted For Privacy |
action_result.data.\*.contacts.tech.email | string | `email` | please query the rdds service of the registrar of record identified in this output for information on how to contact the registrant, admin, or tech contact of the queried domain name. |
action_result.data.\*.contacts.tech.fax | string | | REDACTED FOR PRIVACY |
action_result.data.\*.contacts.tech.fax_ext | string | | REDACTED FOR PRIVACY |
action_result.data.\*.contacts.tech.handle | string | | REDACTED FOR PRIVACY |
action_result.data.\*.contacts.tech.name | string | | Redacted For Privacy |
action_result.data.\*.contacts.tech.organization | string | | Redacted For Privacy |
action_result.data.\*.contacts.tech.phone | string | | REDACTED FOR PRIVACY ext. REDACTED FOR PRIVACY |
action_result.data.\*.contacts.tech.postalcode | string | | REDACTED FOR PRIVACY |
action_result.data.\*.contacts.tech.state | string | | Redacted For Privacy |
action_result.data.\*.contacts.tech.street | string | | Redacted For Privacy |
action_result.data.\*.creation_date | string | | 2017-04-08T04:08:19 1997-09-15T00:00:00 |
action_result.data.\*.emails | string | `email` | abuse@test.com whoisrequest@test.com |
action_result.data.\*.expiration_date | string | | 2023-04-08T04:08:19 2028-09-13T00:00:00 |
action_result.data.\*.id | string | | 65e105d7aa3a44bfb2c5cab6e6e9e4a4-DONUTS 2138514_DOMAIN_COM-VRSN |
action_result.data.\*.nameservers | string | | ns-cloud-c4.test.com ns4.test.com |
action_result.data.\*.raw | string | | Domain Name: obfuscated.network Registry Domain ID: 65e105d7aa3a44bfb2c5cab6e6e9e4a4-DONUTS Registrar WHOIS Server: whois.godaddy.com/ Registrar URL: http://www.godaddy.com/domains/search.aspx?ci=8990 Updated Date: 2019-09-23T23:57:27Z Creation Date: 2017-04-08T04:08:19Z Registry Expiry Date: 2023-04-08T04:08:19Z Registrar: GoDaddy.com, LLC Registrar IANA ID: 146 Registrar Abuse Contact Email: abuse@godaddy.com Registrar Abuse Contact Phone: +1.4806242505 Domain Status: clientDeleteProhibited https://icann.org/epp#clientDeleteProhibited Domain Status: clientRenewProhibited https://icann.org/epp#clientRenewProhibited Domain Status: clientTransferProhibited https://icann.org/epp#clientTransferProhibited Domain Status: clientUpdateProhibited https://icann.org/epp#clientUpdateProhibited Registry Registrant ID: REDACTED FOR PRIVACY Registrant Name: REDACTED FOR PRIVACY Registrant Organization: Domains By Proxy, LLC Registrant Street: REDACTED FOR PRIVACY Registrant City: REDACTED FOR PRIVACY Registrant State/Province: Arizona Registrant Postal Code: REDACTED FOR PRIVACY Registrant Country: US Registrant Phone: REDACTED FOR PRIVACY Registrant Phone Ext: REDACTED FOR PRIVACY Registrant Fax: REDACTED FOR PRIVACY Registrant Fax Ext: REDACTED FOR PRIVACY Registrant Email: Please query the RDDS service of the Registrar of Record identified in this output for information on how to contact the Registrant, Admin, or Tech contact of the queried domain name. Registry Admin ID: REDACTED FOR PRIVACY Admin Name: REDACTED FOR PRIVACY Admin Organization: REDACTED FOR PRIVACY Admin Street: REDACTED FOR PRIVACY Admin City: REDACTED FOR PRIVACY Admin State/Province: REDACTED FOR PRIVACY Admin Postal Code: REDACTED FOR PRIVACY Admin Country: REDACTED FOR PRIVACY Admin Phone: REDACTED FOR PRIVACY Admin Phone Ext: REDACTED FOR PRIVACY Admin Fax: REDACTED FOR PRIVACY Admin Fax Ext: REDACTED FOR PRIVACY Admin Email: Please query the RDDS service of the Registrar of Record identified in this output for information on how to contact the Registrant, Admin, or Tech contact of the queried domain name. Registry Tech ID: REDACTED FOR PRIVACY Tech Name: REDACTED FOR PRIVACY Tech Organization: REDACTED FOR PRIVACY Tech Street: REDACTED FOR PRIVACY Tech City: REDACTED FOR PRIVACY Tech State/Province: REDACTED FOR PRIVACY Tech Postal Code: REDACTED FOR PRIVACY Tech Country: REDACTED FOR PRIVACY Tech Phone: REDACTED FOR PRIVACY Tech Phone Ext: REDACTED FOR PRIVACY Tech Fax: REDACTED FOR PRIVACY Tech Fax Ext: REDACTED FOR PRIVACY Tech Email: Please query the RDDS service of the Registrar of Record identified in this output for information on how to contact the Registrant, Admin, or Tech contact of the queried domain name. Name Server: ns-cloud-c1.googledomains.com Name Server: ns-cloud-c2.googledomains.com Name Server: ns-cloud-c3.googledomains.com Name Server: ns-cloud-c4.googledomains.com DNSSEC: signedDelegation URL of the ICANN Whois Inaccuracy Complaint Form: https://www.icann.org/wicf/ >>> Last update of WHOIS database: 2020-01-12T06:25:08Z \<<< For more information on Whois status codes, please visit https://icann.org/epp Terms of Use: Donuts Inc. provides this Whois service for information purposes, and to assist persons in obtaining information about or related to a domain name registration record. Donuts does not guarantee its accuracy. Users accessing the Donuts Whois service agree to use the data only for lawful purposes, and under no circumstances may this data be used to: a) allow, enable, or otherwise support the transmission by e-mail, telephone, or facsimile of mass unsolicited, commercial advertising or solicitations to entities other than the registrar’s own existing customers and b) enable high volume, automated, electronic processes that send queries or data to the systems of Donuts or any ICANN-accredited registrar, except as reasonably necessary to register domain names or modify existing registrations. When using the Donuts Whois service, please consider the following: The Whois service is not a replacement for standard EPP commands to the SRS service. Whois is not considered authoritative for registered domain objects. The Whois service may be scheduled for downtime during production or OT&E maintenance periods. Queries to the Whois services are throttled. If too many queries are received from a single IP address within a specified time, the service will begin to reject further queries for a period of time to prevent disruption of Whois service access. Abuse of the Whois system through data mining is mitigated by detecting and limiting bulk query access from single sources. Where applicable, the presence of a [Non-Public Data] tag indicates that such data is not made publicly available due to applicable data privacy laws or requirements. Should you wish to contact the registrant, please refer to the Whois records available through the registrar URL listed above. Access to non-public data may be provided, upon request, where it can be reasonably confirmed that the requester holds a specific legitimate interest and a proper legal basis for accessing the withheld data. Access to this data can be requested by submitting a request via the form found at https://donuts.domains/about/policies/whois-layered-access/ Donuts Inc. reserves the right to modify these terms at any time. By submitting this query, you agree to abide by this policy. Domain Name: google.com Registry Domain ID: 2138514_DOMAIN_COM-VRSN Registrar WHOIS Server: whois.markmonitor.com Registrar URL: http://www.markmonitor.com Updated Date: 2019-09-09T08:39:04-0700 Creation Date: 1997-09-15T00:00:00-0700 Registrar Registration Expiration Date: 2028-09-13T00:00:00-0700 Registrar: MarkMonitor, Inc. Registrar IANA ID: 292 Registrar Abuse Contact Email: abusecomplaints@markmonitor.com Registrar Abuse Contact Phone: +1.2083895770 Domain Status: clientUpdateProhibited (https://www.icann.org/epp#clientUpdateProhibited) Domain Status: clientTransferProhibited (https://www.icann.org/epp#clientTransferProhibited) Domain Status: clientDeleteProhibited (https://www.icann.org/epp#clientDeleteProhibited) Domain Status: serverUpdateProhibited (https://www.icann.org/epp#serverUpdateProhibited) Domain Status: serverTransferProhibited (https://www.icann.org/epp#serverTransferProhibited) Domain Status: serverDeleteProhibited (https://www.icann.org/epp#serverDeleteProhibited) Registrant Organization: Google LLC Registrant State/Province: CA Registrant Country: US Admin Organization: Google LLC Admin State/Province: CA Admin Country: US Tech Organization: Google LLC Tech State/Province: CA Tech Country: US Name Server: ns3.google.com Name Server: ns2.google.com Name Server: ns1.google.com Name Server: ns4.google.com DNSSEC: unsigned URL of the ICANN WHOIS Data Problem Reporting System: http://wdprs.internic.net/ >>> Last update of WHOIS database: 2020-01-11T17:54:34-0800 \<<< For more information on WHOIS status codes, please visit: https://www.icann.org/resources/pages/epp-status-codes If you wish to contact this domain’s Registrant, Administrative, or Technical contact, and such email address is not visible above, you may do so via our web form, pursuant to ICANN’s Temporary Specification. To verify that you are not a robot, please enter your email address to receive a link to a page that facilitates email communication with the relevant contact(s). Web-based WHOIS: https://domains.markmonitor.com/whois If you have a legitimate interest in viewing the non-public WHOIS details, send your request and the reasons for your request to whoisrequest@markmonitor.com and specify the domain name in the subject line. We will review that request and may ask for supporting documentation and explanation. The data in MarkMonitor’s WHOIS database is provided for information purposes, and to assist persons in obtaining information about or related to a domain name’s registration record. While MarkMonitor believes the data to be accurate, the data is provided "as is" with no guarantee or warranties regarding its accuracy. By submitting a WHOIS query, you agree that you will use this data only for lawful purposes and that, under no circumstances will you use this data to: (1) allow, enable, or otherwise support the transmission by email, telephone, or facsimile of mass, unsolicited, commercial advertising, or spam; or (2) enable high volume, automated, or electronic processes that send queries, data, or email to MarkMonitor (or its systems) or the domain name contacts (or its systems). MarkMonitor.com reserves the right to modify these terms at any time. By submitting this query, you agree to abide by this policy. MarkMonitor is the Global Leader in Online Brand Protection. MarkMonitor Domain Management(TM) MarkMonitor Brand Protection(TM) MarkMonitor AntiCounterfeiting(TM) MarkMonitor AntiPiracy(TM) MarkMonitor AntiFraud(TM) Professional and Managed Services Visit MarkMonitor at https://www.markmonitor.com Contact us at +1.8007459229 In Europe, at +44.02032062220 -- |
action_result.data.\*.registrar | string | | test.com, LLC test, Inc. |
action_result.data.\*.status | string | | clientUpdateProhibited https://icann.org/epp#clientUpdateProhibited serverDeleteProhibited (https://www.icann.org/epp#serverDeleteProhibited) |
action_result.data.\*.updated_date | string | | 2019-09-23T23:57:27 2019-09-09T08:39:04 |
action_result.data.\*.whois_server | string | | whois.test.com/ whois.test.com |
action_result.summary | string | | |
action_result.message | string | | Successfully retrieved whois info |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get observable'

Get observable present in ThreatStream by ID number

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**intelligence_id** | required | ID number of intelligence to return | string | `threatstream intelligence id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.intelligence_id | string | `threatstream intelligence id` | 171143571 |
action_result.data.\*.asn | string | | |
action_result.data.\*.can_add_public_tags | boolean | | True False |
action_result.data.\*.confidence | numeric | | 50 |
action_result.data.\*.country | string | | |
action_result.data.\*.created_by | string | `email` | test@test.com |
action_result.data.\*.created_ts | string | | 2019-12-12T09:07:42.124Z |
action_result.data.\*.description | string | | |
action_result.data.\*.expiration_ts | string | | 2020-03-11T09:04:49.324Z |
action_result.data.\*.feed_id | numeric | | 0 |
action_result.data.\*.id | numeric | `threatstream intelligence id` | 171143571 |
action_result.data.\*.import_session_id | string | | 235 |
action_result.data.\*.import_source | string | | |
action_result.data.\*.ip | string | | |
action_result.data.\*.is_anonymous | boolean | | True False |
action_result.data.\*.is_editable | boolean | | True False |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.itype | string | | mal_email |
action_result.data.\*.latitude | string | | |
action_result.data.\*.longitude | string | | |
action_result.data.\*.meta.detail2 | string | | imported by user 136 |
action_result.data.\*.meta.severity | string | | low |
action_result.data.\*.modified_ts | string | | 2019-12-12T09:08:15.714Z |
action_result.data.\*.org | string | | |
action_result.data.\*.owner_organization_id | numeric | | 67 |
action_result.data.\*.rdns | string | | |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_uri | string | | /api/v2/intelligence/171143571/?remote_api=true |
action_result.data.\*.retina_confidence | numeric | | -1 |
action_result.data.\*.source | string | `email` | test@test.com |
action_result.data.\*.source_created | string | | |
action_result.data.\*.source_modified | string | | |
action_result.data.\*.source_reported_confidence | numeric | | 50 |
action_result.data.\*.status | string | | active |
action_result.data.\*.subtype | string | | |
action_result.data.\*.tags | string | | |
action_result.data.\*.tags.\*.id | string | | cg0 |
action_result.data.\*.tags.\*.name | string | | test_name |
action_result.data.\*.tags.\*.org_id | string | | 67 |
action_result.data.\*.tags.\*.remote_api | boolean | | True False |
action_result.data.\*.tags.\*.tlp | string | | red |
action_result.data.\*.threat_type | string | | malware |
action_result.data.\*.threatscore | numeric | | 10 |
action_result.data.\*.tlp | string | | amber |
action_result.data.\*.trusted_circle_ids | string | | |
action_result.data.\*.type | string | | email |
action_result.data.\*.update_id | numeric | | 343406992 |
action_result.data.\*.uuid | string | | 4a035a95-6a80-4eaf-be5e-c2bfc4bdf570 |
action_result.data.\*.value | string | `email` | test@test00.com |
action_result.summary | string | | |
action_result.message | string | | Successfully retrieved observable |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list observables'

List observables present in ThreatStream

Type: **investigate** <br>
Read only: **True**

<ul><li>The observables will be listed in the latest first order on the basis of created_ts.</li><li>If the limit parameter is not provided, then the default value (1000) will be considered as the value of the limit parameter.</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**limit** | optional | Total number of observables to return | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 5 |
action_result.data.\*.asn | string | | |
action_result.data.\*.can_add_public_tags | boolean | | True False |
action_result.data.\*.confidence | numeric | | 57 |
action_result.data.\*.country | string | | DE |
action_result.data.\*.created_by | string | | testuser2@test.testdata.com |
action_result.data.\*.created_ts | string | | 2019-09-06T08:27:20.995Z |
action_result.data.\*.description | string | | |
action_result.data.\*.expiration_ts | string | | 2019-09-07T08:27:17.860Z |
action_result.data.\*.feed_id | numeric | | 122 |
action_result.data.\*.id | numeric | `threatstream intelligence id` | 53702579051 |
action_result.data.\*.import_session_id | string | | |
action_result.data.\*.import_source | string | | |
action_result.data.\*.ip | string | `ip` | 122.122.122.122 |
action_result.data.\*.is_anonymous | boolean | | True False |
action_result.data.\*.is_editable | boolean | | True False |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.itype | string | | tor_ip |
action_result.data.\*.latitude | string | | 49.7739 |
action_result.data.\*.longitude | string | | 8.8844 |
action_result.data.\*.meta.detail | string | | |
action_result.data.\*.meta.detail2 | string | | imported by user 668 |
action_result.data.\*.meta.registrant_address | string | | |
action_result.data.\*.meta.registrant_created | string | | |
action_result.data.\*.meta.registrant_email | string | | test@test00.com |
action_result.data.\*.meta.registrant_name | string | | Protection of Private Person |
action_result.data.\*.meta.registrant_org | string | | |
action_result.data.\*.meta.registrant_phone | string | | |
action_result.data.\*.meta.registrant_updated | string | | |
action_result.data.\*.meta.registrantion_created | string | | 2001-06-28T16:04:59+00:00 |
action_result.data.\*.meta.registrantion_updated | string | | 2014-08-13T20:24:31+00:00 |
action_result.data.\*.meta.registration_created | string | | 1993-02-09T05:00:00+00:00 |
action_result.data.\*.meta.registration_updated | string | | 2019-02-05T15:21:43+00:00 |
action_result.data.\*.meta.severity | string | | low |
action_result.data.\*.modified_ts | string | | 2019-09-06T08:27:20.995Z |
action_result.data.\*.org | string | | ENTEGA Medianet GmbH |
action_result.data.\*.owner_organization_id | numeric | | 2 |
action_result.data.\*.rdns | string | | |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_uri | string | | /api/v2/intelligence/53702579051/ |
action_result.data.\*.retina_confidence | numeric | | 57 |
action_result.data.\*.source | string | | TOR Exit Nodes |
action_result.data.\*.source_created | string | | |
action_result.data.\*.source_modified | string | | |
action_result.data.\*.source_reported_confidence | numeric | | 100 |
action_result.data.\*.status | string | | active |
action_result.data.\*.subtype | string | | |
action_result.data.\*.tags | string | | |
action_result.data.\*.tags.\*.id | string | | dgo |
action_result.data.\*.tags.\*.name | string | | Suspicious-Domain-Registration |
action_result.data.\*.tags.\*.org_id | string | | 67 |
action_result.data.\*.tags.\*.remote_api | boolean | | True False |
action_result.data.\*.tags.\*.tlp | string | | red |
action_result.data.\*.threat_type | string | | tor |
action_result.data.\*.threatscore | numeric | | 15 |
action_result.data.\*.tlp | string | | |
action_result.data.\*.trusted_circle_ids | string | | |
action_result.data.\*.type | string | | ip |
action_result.data.\*.update_id | numeric | | 4887255342 |
action_result.data.\*.uuid | string | | 9f6cb8db-bb18-45e0-b46a-da9b2f783d1c |
action_result.data.\*.value | string | | 122.122.122.122 |
action_result.summary.observables_returned | numeric | | 5 |
action_result.message | string | | Observables returned: 5 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get vulnerability'

Get vulnerability present in ThreatStream by ID number

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vulnerability_id** | required | ID number of vulnerability to return | string | `threatstream vulnerability id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.vulnerability_id | string | `threatstream vulnerability id` | 5679 |
action_result.data.\*.aliases | string | | |
action_result.data.\*.assignee_user | string | | |
action_result.data.\*.body_content_type | string | | markdown |
action_result.data.\*.created_ts | string | | 2019-12-11T07:19:48.120816 |
action_result.data.\*.cvss2_score | string | | |
action_result.data.\*.cvss3_score | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.embedded_content_type | string | | |
action_result.data.\*.embedded_content_url | string | | |
action_result.data.\*.feed_id | string | | 0 |
action_result.data.\*.id | numeric | | 5679 |
action_result.data.\*.is_anonymous | boolean | | True False |
action_result.data.\*.is_cloneable | string | | yes |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.is_system | boolean | | True False |
action_result.data.\*.logo_s3_url | string | | |
action_result.data.\*.modified_ts | string | | 2019-12-11T07:19:48.129404 |
action_result.data.\*.name | string | | test_vulnerabilities_remote |
action_result.data.\*.organization.id | string | | 67 |
action_result.data.\*.organization.name | string | | qa.test.com |
action_result.data.\*.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.organization_id | numeric | `threatstream organization id` | 67 |
action_result.data.\*.owner_user.email | string | `email` | test@qa.test.com |
action_result.data.\*.owner_user.id | string | | 136 |
action_result.data.\*.owner_user.name | string | | testuser2 |
action_result.data.\*.owner_user.resource_uri | string | | /api/v1/user/136/ |
action_result.data.\*.owner_user_id | numeric | | 136 |
action_result.data.\*.parent | string | | |
action_result.data.\*.publication_status | string | | new |
action_result.data.\*.published_ts | string | | |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_uri | string | | /api/v1/vulnerability/5679/?remote_api=true |
action_result.data.\*.source | string | | |
action_result.data.\*.starred_by_me | boolean | | True False |
action_result.data.\*.starred_total_count | numeric | | 0 |
action_result.data.\*.tlp | string | | |
action_result.data.\*.update_id | string | | 14060 |
action_result.data.\*.votes.me | string | | |
action_result.data.\*.votes.total | numeric | | 0 |
action_result.data.\*.watched_by_me | boolean | | True False |
action_result.data.\*.watched_total_count | numeric | | 0 |
action_result.summary | string | | |
action_result.message | string | | Successfully retrieved vulnerability |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list vulnerabilities'

List vulnerabilities present in ThreatStream

Type: **investigate** <br>
Read only: **True**

<ul><li>The vulnerabilities will be listed in the latest first order on the basis of created_ts.</li><li>If the limit parameter is not provided, then the default value (1000) will be considered as the value of the limit parameter.</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**limit** | optional | Total number of vulnerabilities to return | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 1000 |
action_result.data.\*.assignee_user | string | | |
action_result.data.\*.can_add_public_tags | boolean | | True False |
action_result.data.\*.circles.\*.id | string | | 146 |
action_result.data.\*.circles.\*.name | string | | Anomali Curated OSINT |
action_result.data.\*.circles.\*.remote_api | boolean | | True False |
action_result.data.\*.circles.\*.resource_uri | string | | /api/v1/trustedcircle/146/ |
action_result.data.\*.created_ts | string | | 2017-11-16T00:43:49.307763 |
action_result.data.\*.embedded_content_url | string | | |
action_result.data.\*.feed_id | numeric | | 0 |
action_result.data.\*.id | numeric | `threatstream vulnerability id` | 1 |
action_result.data.\*.is_anonymous | boolean | | True False |
action_result.data.\*.is_cloneable | string | | yes_private_only |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.is_system | boolean | | True False |
action_result.data.\*.modified_ts | string | | 2010-12-16T05:00:00 |
action_result.data.\*.name | string | | CVE-1999-0001 |
action_result.data.\*.organization.id | string | `threatstream organization id` | 2342 |
action_result.data.\*.organization.name | string | | test_organization_name.us |
action_result.data.\*.organization.title | string | | analyst |
action_result.data.\*.organization_id | numeric | `threatstream organization id` | 2 |
action_result.data.\*.owner_user_id | numeric | | 136 |
action_result.data.\*.publication_status | string | | published |
action_result.data.\*.published_ts | string | | 1999-12-30T05:00:00 |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_uri | string | | /api/v1/vulnerability/1/ |
action_result.data.\*.source | string | | mitre |
action_result.data.\*.source_created | string | | |
action_result.data.\*.source_modified | string | | |
action_result.data.\*.tags | string | | NVD-CWE-Other |
action_result.data.\*.tags_v2.\*.id | string | | 2_CWE-20 |
action_result.data.\*.tags_v2.\*.name | string | | CWE-20 |
action_result.data.\*.tags_v2.\*.org_id | numeric | | 67 |
action_result.data.\*.tags_v2.\*.remote_api | boolean | | True False |
action_result.data.\*.tags_v2.\*.tlp | string | | red |
action_result.data.\*.tlp | string | | white |
action_result.data.\*.update_id | numeric | | 451620 |
action_result.data.\*.uuid | string | | |
action_result.summary.vulnerabilities_returned | numeric | | 1000 |
action_result.message | string | | Vulnerabilities returned: 1000 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list incidents'

List incidents present in ThreatStream

Type: **investigate** <br>
Read only: **True**

<ul><li>The incidents will be listed in the latest first order on the basis of created_ts.</li><li>If the limit parameter is not provided, then the default value (1000) will be considered as the value of the limit parameter.</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**intel_value** | optional | Intelligence value to filter incidents (ie. google.com) | string | |
**limit** | optional | Total number of incidents to return | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.intel_value | string | | test@test.com |
action_result.parameter.limit | numeric | | 10 |
action_result.data.\*.assignee_user | string | | |
action_result.data.\*.can_add_public_tags | boolean | | True False |
action_result.data.\*.circles.\*.id | string | | 145 |
action_result.data.\*.circles.\*.name | string | | Anomali Labs Premium |
action_result.data.\*.circles.\*.resource_uri | string | | /api/v1/test/145/ |
action_result.data.\*.created_ts | string | | 2015-08-11T19:39:13.604417 |
action_result.data.\*.end_date | string | | 2011-04-08T04:00:00 |
action_result.data.\*.feed_id | numeric | | 0 |
action_result.data.\*.id | numeric | `threatstream incident id` | 1 |
action_result.data.\*.is_anonymous | boolean | | False True |
action_result.data.\*.is_cloneable | string | | yes_private_only |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.modified_ts | string | | 2015-09-25T16:51:45.730982 |
action_result.data.\*.name | string | | Test Incident Name |
action_result.data.\*.organization_id | numeric | `threatstream organization id` | 1223 |
action_result.data.\*.owner_user_id | numeric | | 136 |
action_result.data.\*.parent.id | string | | 5794 |
action_result.data.\*.parent.name | string | | MySpace Credential Leak (2016) |
action_result.data.\*.parent.recource_uri | string | | /api/v1/incident/5794/ |
action_result.data.\*.publication_status | string | | published |
action_result.data.\*.published_ts | string | | 2015-09-25T16:51:45.730982 |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_uri | string | | /api/v1/incident/1/ |
action_result.data.\*.source_created | string | | |
action_result.data.\*.source_modified | string | | |
action_result.data.\*.starred_by_me | boolean | | True False |
action_result.data.\*.starred_total_count | numeric | | 1 |
action_result.data.\*.start_date | string | | 2015-08-11T19:18:53.160000 |
action_result.data.\*.status | string | | |
action_result.data.\*.status.display_name | string | | New |
action_result.data.\*.status.id | numeric | | 1 |
action_result.data.\*.status.resource_uri | string | | /api/v1/incidentstatustype/1/ |
action_result.data.\*.tags | string | | Breach |
action_result.data.\*.tags_v2.\*.id | string | | 1223_Axiom |
action_result.data.\*.tags_v2.\*.name | string | | Axiom |
action_result.data.\*.tags_v2.\*.org_id | numeric | | 67 |
action_result.data.\*.tags_v2.\*.remote_api | boolean | | True False |
action_result.data.\*.tags_v2.\*.tlp | string | | white |
action_result.data.\*.tlp | string | | white |
action_result.data.\*.uuid | string | | f47b82f2-3607-42bc-9ed1-5c86e15e952b |
action_result.data.\*.votes.me | string | | |
action_result.data.\*.votes.total | numeric | | 0 |
action_result.data.\*.watched_by_me | boolean | | True False |
action_result.data.\*.watched_total_count | numeric | | 0 |
action_result.summary.incidents_returned | numeric | | 142 |
action_result.message | string | | Incidents returned: 142 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete incident'

Delete incident in ThreatStream by ID number

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**incident_id** | required | ID number of incident to delete | string | `threatstream incident id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.incident_id | string | `threatstream incident id` | 15518 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully deleted incident |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get incident'

Get incident in ThreatStream by ID number

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**incident_id** | required | ID number of incident to return | string | `threatstream incident id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.incident_id | string | `threatstream incident id` | 1000000003 |
action_result.data.\*.assignee_user | string | | |
action_result.data.\*.body_content_type | string | | markdown |
action_result.data.\*.can_add_public_tags | boolean | | True False |
action_result.data.\*.created_ts | string | | 2019-12-11T07:12:16.022460 |
action_result.data.\*.description | string | | |
action_result.data.\*.embedded_content_type | string | | |
action_result.data.\*.embedded_content_url | string | | |
action_result.data.\*.end_date | string | | |
action_result.data.\*.feed_id | numeric | | 0 |
action_result.data.\*.id | numeric | | 1000000003 |
action_result.data.\*.intelligence.\*.asn | string | | |
action_result.data.\*.intelligence.\*.association_info.\*.comment | string | | |
action_result.data.\*.intelligence.\*.association_info.\*.created | string | | 2021-05-27T12:26:00.546115 |
action_result.data.\*.intelligence.\*.association_info.\*.from_id | string | | 173098 |
action_result.data.\*.intelligence.\*.association_info.\*.remote_api | boolean | | True False |
action_result.data.\*.intelligence.\*.can_add_public_tags | boolean | | True False |
action_result.data.\*.intelligence.\*.confidence | numeric | | 50 |
action_result.data.\*.intelligence.\*.country | string | | |
action_result.data.\*.intelligence.\*.created_by | string | `email` | qa+test@test00.com |
action_result.data.\*.intelligence.\*.created_ts | string | | 2019-12-12T09:05:12.270082 |
action_result.data.\*.intelligence.\*.description | string | | |
action_result.data.\*.intelligence.\*.expiration_ts | string | | 2020-03-11T09:04:49.324000 |
action_result.data.\*.intelligence.\*.feed_id | numeric | | 0 |
action_result.data.\*.intelligence.\*.id | string | `threatstream intelligence id` | 1000000009 |
action_result.data.\*.intelligence.\*.import_session_id | string | | 1000000005 |
action_result.data.\*.intelligence.\*.import_source | string | | |
action_result.data.\*.intelligence.\*.ip | string | | |
action_result.data.\*.intelligence.\*.is_anonymous | boolean | | True False |
action_result.data.\*.intelligence.\*.is_editable | boolean | | True False |
action_result.data.\*.intelligence.\*.is_public | boolean | | True False |
action_result.data.\*.intelligence.\*.itype | string | | mal_email |
action_result.data.\*.intelligence.\*.latitude | string | | |
action_result.data.\*.intelligence.\*.longitude | string | | |
action_result.data.\*.intelligence.\*.meta.detail2 | string | | imported by user 136 |
action_result.data.\*.intelligence.\*.meta.registrant_address | string | | calavi, Calavi, BENIN, 229 |
action_result.data.\*.intelligence.\*.meta.registrant_email | string | | test@outlook.com |
action_result.data.\*.intelligence.\*.meta.registrant_name | string | | test registrant |
action_result.data.\*.intelligence.\*.meta.registrant_phone | string | | 22966300066 |
action_result.data.\*.intelligence.\*.meta.registration_created | string | | 2017-05-31T12:18:59+00:00 |
action_result.data.\*.intelligence.\*.meta.registration_updated | string | | 2017-06-26T12:58:10+00:00 |
action_result.data.\*.intelligence.\*.meta.severity | string | | low |
action_result.data.\*.intelligence.\*.modified_ts | string | | 2019-12-12T09:05:42.169722 |
action_result.data.\*.intelligence.\*.org | string | | |
action_result.data.\*.intelligence.\*.owner_organization_id | numeric | | 67 |
action_result.data.\*.intelligence.\*.rdns | string | | |
action_result.data.\*.intelligence.\*.remote_api | boolean | | True False |
action_result.data.\*.intelligence.\*.resource_uri | string | | |
action_result.data.\*.intelligence.\*.retina_confidence | numeric | | -1 |
action_result.data.\*.intelligence.\*.source | string | `email` | qa+test@test00.com |
action_result.data.\*.intelligence.\*.source_reported_confidence | numeric | | 50 |
action_result.data.\*.intelligence.\*.status | string | | active |
action_result.data.\*.intelligence.\*.subtype | string | | |
action_result.data.\*.intelligence.\*.tags | string | | |
action_result.data.\*.intelligence.\*.tags.\*.category | string | | user |
action_result.data.\*.intelligence.\*.tags.\*.id | numeric | | 123 |
action_result.data.\*.intelligence.\*.tags.\*.name | string | | test_hybrid |
action_result.data.\*.intelligence.\*.tags.\*.org_id | string | | 67 |
action_result.data.\*.intelligence.\*.tags.\*.remote_api | boolean | | True False |
action_result.data.\*.intelligence.\*.tags.\*.source_user | string | | |
action_result.data.\*.intelligence.\*.tags.\*.source_user_id | string | | 1234 |
action_result.data.\*.intelligence.\*.tags.\*.tagger | string | | user |
action_result.data.\*.intelligence.\*.tags.\*.tlp | string | | white |
action_result.data.\*.intelligence.\*.threat_type | string | | malware |
action_result.data.\*.intelligence.\*.threatscore | numeric | | 10 |
action_result.data.\*.intelligence.\*.tlp | string | | amber |
action_result.data.\*.intelligence.\*.trusted_circle_ids | string | | |
action_result.data.\*.intelligence.\*.type | string | | email |
action_result.data.\*.intelligence.\*.update_id | numeric | | 100010 |
action_result.data.\*.intelligence.\*.uuid | string | | a5f417fb-0c7e-4eb7-b590-bca1af0c3dfb |
action_result.data.\*.intelligence.\*.value | string | `email` | test@tes123.com |
action_result.data.\*.is_anonymous | boolean | | True False |
action_result.data.\*.is_cloneable | string | | yes |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.logo_s3_url | string | | |
action_result.data.\*.modified_ts | string | | 2019-12-12T13:21:42.080982 |
action_result.data.\*.name | string | | test_local_incident |
action_result.data.\*.organization.id | string | | 67 |
action_result.data.\*.organization.name | string | | qa.test.com |
action_result.data.\*.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.organization_id | numeric | `threatstream organization id` | 67 |
action_result.data.\*.owner_user.email | string | `email` | qa+test@qa.test.com |
action_result.data.\*.owner_user.id | string | | 136 |
action_result.data.\*.owner_user.name | string | | testuser2 |
action_result.data.\*.owner_user.resource_uri | string | | /api/v1/user/136/ |
action_result.data.\*.owner_user_id | numeric | | 136 |
action_result.data.\*.parent | string | | |
action_result.data.\*.publication_status | string | | new |
action_result.data.\*.published_ts | string | | |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_uri | string | | /api/v1/incident/1000000003/ |
action_result.data.\*.source_created | string | | |
action_result.data.\*.source_modified | string | | |
action_result.data.\*.starred_by_me | boolean | | True False |
action_result.data.\*.starred_total_count | numeric | | 0 |
action_result.data.\*.start_date | string | | |
action_result.data.\*.status.display_name | string | | New |
action_result.data.\*.status.id | numeric | | 1 |
action_result.data.\*.status.resource_uri | string | | /api/v1/incidentstatustype/1/ |
action_result.data.\*.status_desc | string | | |
action_result.data.\*.tags_v2.\*.id | string | | 15e |
action_result.data.\*.tags_v2.\*.name | string | | test_name |
action_result.data.\*.tags_v2.\*.org_id | numeric | | 67 |
action_result.data.\*.tags_v2.\*.remote_api | boolean | | True False |
action_result.data.\*.tags_v2.\*.tlp | string | | white |
action_result.data.\*.tlp | string | | amber |
action_result.data.\*.uuid | string | | 28a86936-dfa8-44aa-9305-b3a5b9dbfbed |
action_result.data.\*.votes.me | string | | |
action_result.data.\*.votes.total | numeric | | 0 |
action_result.data.\*.watched_by_me | boolean | | True False |
action_result.data.\*.watched_total_count | numeric | | 0 |
action_result.summary | string | | |
action_result.message | string | | Successfully retrieved incident |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create incident'

Create an incident in ThreatStream

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**local_intelligence** | optional | Comma-separated list of local intelligence IDs to associate with the incident - Note that this appends | string | `threatstream intelligence id` |
**cloud_intelligence** | optional | Comma-separated list of remote intelligence IDs to associate with the incident - Note that this appends | string | `threatstream intelligence id` |
**name** | required | Name to give the incident | string | |
**fields** | optional | JSON formatted string of fields to include with the incident | string | |
**is_public** | optional | Classification designation | boolean | |
**create_on_cloud** | optional | Create on remote (cloud)? (applicable only for hybrid on-prem instances) | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.cloud_intelligence | string | `threatstream intelligence id` | 171831109 |
action_result.parameter.create_on_cloud | boolean | | True False |
action_result.parameter.fields | string | | {"status": 2} |
action_result.parameter.is_public | boolean | | True False |
action_result.parameter.local_intelligence | string | `threatstream intelligence id` | 1000000003,1000000004 |
action_result.parameter.name | string | | new_threatstream_2 |
action_result.data.\*.assignee_user | string | | |
action_result.data.\*.body_content_type | string | | markdown |
action_result.data.\*.created_ts | string | | 2019-12-15T06:39:20.395924 |
action_result.data.\*.description | string | | |
action_result.data.\*.embedded_content_type | string | | |
action_result.data.\*.embedded_content_url | string | | |
action_result.data.\*.end_date | string | | |
action_result.data.\*.feed_id | numeric | | 0 |
action_result.data.\*.fjregnvjnj | string | | frfer |
action_result.data.\*.id | numeric | `threatstream incident id` | 1000000008 |
action_result.data.\*.intelligence.\*.id | numeric | | 1000000003 |
action_result.data.\*.invalid field | string | | failed |
action_result.data.\*.is_anonymous | boolean | | True False |
action_result.data.\*.is_cloneable | string | | yes |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.logo_s3_url | string | | |
action_result.data.\*.modified_ts | string | | 2019-12-15T06:39:20.407307 |
action_result.data.\*.name | string | | new_threatstream_2 |
action_result.data.\*.organization.id | string | `threatstream organization id` | 67 |
action_result.data.\*.organization.name | string | | qa.test.com |
action_result.data.\*.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.organization_id | numeric | `threatstream organization id` | 67 |
action_result.data.\*.owner_user.email | string | `email` | qa+test@qa.test.com |
action_result.data.\*.owner_user.id | string | | 136 |
action_result.data.\*.owner_user.name | string | | testuser2 |
action_result.data.\*.owner_user.resource_uri | string | | /api/v1/user/136/ |
action_result.data.\*.owner_user_id | numeric | | 136 |
action_result.data.\*.parent | string | | |
action_result.data.\*.publication_status | string | | new |
action_result.data.\*.published_ts | string | | |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_uri | string | | /api/v1/incident/1000000008/ |
action_result.data.\*.source_created | string | | |
action_result.data.\*.source_modified | string | | |
action_result.data.\*.starred_by_me | boolean | | True False |
action_result.data.\*.starred_total_count | numeric | | 0 |
action_result.data.\*.start_date | string | | |
action_result.data.\*.status.display_name | string | | New |
action_result.data.\*.status.id | numeric | | 1 |
action_result.data.\*.status.resource_uri | string | | /api/v1/incidentstatustype/1/ |
action_result.data.\*.status_desc | string | | |
action_result.data.\*.tlp | string | | |
action_result.data.\*.uuid | string | | 68ed8fc0-8f3b-4a86-bc52-724a0057d43b |
action_result.data.\*.votes.me | string | | |
action_result.data.\*.votes.total | numeric | | 0 |
action_result.data.\*.watched_by_me | boolean | | True False |
action_result.data.\*.watched_total_count | numeric | | 0 |
action_result.summary | string | | |
action_result.summary.created_on_cloud | boolean | | True False |
action_result.message | string | | Successfully created incident |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update incident'

Update an incident in ThreatStream by ID number

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**local_intelligence** | optional | Comma-separated list of local intelligence IDs to associate with the incident - Note that this appends | string | |
**cloud_intelligence** | optional | Comma-separated list of remote intelligence IDs to associate with the incident - Note that this appends | string | |
**fields** | optional | JSON formatted string of fields to update on the incident | string | |
**incident_id** | required | ID number of incident to update | string | `threatstream incident id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.cloud_intelligence | string | | 171831109 |
action_result.parameter.fields | string | | {"status": 2} |
action_result.parameter.incident_id | string | `threatstream incident id` | 1000000008 |
action_result.parameter.local_intelligence | string | | 1000000002 |
action_result.data.\*.assignee_user | string | | |
action_result.data.\*.body_content_type | string | | markdown |
action_result.data.\*.created_ts | string | | 2019-12-15T06:39:20.395924 |
action_result.data.\*.description | string | | |
action_result.data.\*.embedded_content_type | string | | |
action_result.data.\*.embedded_content_url | string | | |
action_result.data.\*.end_date | string | | |
action_result.data.\*.feed_id | numeric | | 0 |
action_result.data.\*.id | numeric | `threatstream incident id` | 1000000008 |
action_result.data.\*.intelligence.\*.id | numeric | `threatstream incident id` | 1000000002 |
action_result.data.\*.invalid field | string | | failed |
action_result.data.\*.is_anonymous | boolean | | True False |
action_result.data.\*.is_cloneable | string | | yes |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.logo_s3_url | string | | |
action_result.data.\*.modified_ts | string | | 2019-12-15T09:23:18.988408 |
action_result.data.\*.name | string | | new_threatstream_2 |
action_result.data.\*.organization.id | string | `threatstream organization id` | 67 |
action_result.data.\*.organization.name | string | | qa.test.com |
action_result.data.\*.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.organization_id | numeric | `threatstream organization id` | 67 |
action_result.data.\*.owner_user.email | string | `email` | qa+test@qa.test.com |
action_result.data.\*.owner_user.id | string | | 136 |
action_result.data.\*.owner_user.name | string | | testuser2 |
action_result.data.\*.owner_user.resource_uri | string | | /api/v1/user/136/ |
action_result.data.\*.owner_user_id | numeric | | 136 |
action_result.data.\*.parent | string | | |
action_result.data.\*.publication_status | string | | new |
action_result.data.\*.published_ts | string | | |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_uri | string | | /api/v1/incident/1000000008/ |
action_result.data.\*.source_created | string | | |
action_result.data.\*.source_modified | string | | |
action_result.data.\*.starred_by_me | boolean | | True False |
action_result.data.\*.starred_total_count | numeric | | 0 |
action_result.data.\*.start_date | string | | |
action_result.data.\*.status.display_name | string | | Open |
action_result.data.\*.status.id | numeric | | 2 |
action_result.data.\*.status.resource_uri | string | | /api/v1/incidentstatustype/2/ |
action_result.data.\*.status_desc | string | | |
action_result.data.\*.tlp | string | | |
action_result.data.\*.uuid | string | | 28a86936-dfa8-44aa-9305-b3a5b9dbfbed |
action_result.data.\*.votes.me | string | | |
action_result.data.\*.votes.total | numeric | | 0 |
action_result.data.\*.watched_by_me | boolean | | True False |
action_result.data.\*.watched_total_count | numeric | | 0 |
action_result.summary | string | | |
action_result.message | string | | Successfully updated incident |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'import domain observable'

Import domain observable into ThreatStream

Type: **generic** <br>
Read only: **False**

<ul><li>For importing domain observables without approval, the user must provide indicator type in the field parameter (e.g - "mal_domain") whereas, for importing observables with approval, the user must provide threat type in the field parameter (e.g - "malware").</li><li>The possible values of indicator type (itype) and threat_type are listed at the starting of the documentation. If the input contains any indicator type (itype) or threat_type value except the ones listed, the action will behave according to the API behavior.</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Value of domain | string | `domain` |
**indicator_type** | required | Type of observable to import | string | |
**source** | optional | Source of observable to import (It will only be reflected on UI when observable is imported without approval) | string | |
**classification** | optional | Designate classification for observable | string | |
**severity** | optional | Severity of the observable | string | |
**tags** | optional | Comma-separated list of tags to associate with this Observable | string | `threatstream tags` |
**create_on_cloud** | optional | Create on remote (cloud)? (applicable only for hybrid on-prem instances) | boolean | |
**with_approval** | optional | Import the observable with approvals | boolean | |
**allow_unresolved** | optional | Unresolved domains will be imported if set to true | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.allow_unresolved | boolean | | True False |
action_result.parameter.classification | string | | public |
action_result.parameter.create_on_cloud | boolean | | True False |
action_result.parameter.domain | string | `domain` | test.com |
action_result.parameter.indicator_type | string | | mal_domain malware |
action_result.parameter.severity | string | | medium |
action_result.parameter.source | string | | testsource |
action_result.parameter.tags | string | `threatstream tags` | test_domain_tag |
action_result.parameter.with_approval | boolean | | True False |
action_result.data | string | | |
action_result.data.\*.import_session_id | string | | 3369 |
action_result.data.\*.job_id | string | | a75b7e4a-fc77-4d76-ad1f-4de03bbc7fa2 |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.success | boolean | | True False |
action_result.summary.created_on_cloud | boolean | | True False |
action_result.message | string | | Successfully sent the request for importing the observable |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'import url observable'

Import URL observable into ThreatStream

Type: **generic** <br>
Read only: **False**

<ul><li>For importing URL observables without approval, the user must provide indicator type in the indicator_type parameter (e.g - "phish_url") whereas, for importing observables with approval, the user must provide threat type in the indicator_type parameter (e.g - "phish").</li><li>The possible values of indicator type (itype) and threat_type are listed at the starting of the documentation. If the input contains any indicator type (itype) or threat_type value except the ones listed, the action will behave according to the API behavior.</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | Value of URL | string | `url` |
**indicator_type** | required | Type of observable to import | string | |
**source** | optional | Source of observable to import (It will only be reflected on UI when observable is imported without approval) | string | |
**classification** | optional | Designate classification for observable | string | |
**severity** | optional | Severity of the observable | string | |
**tags** | optional | Comma-separated list of tags to associate with this Observable | string | `threatstream tags` |
**create_on_cloud** | optional | Create on remote (cloud)? (applicable only for hybrid on-prem instances) | boolean | |
**with_approval** | optional | Import the observable with approvals | boolean | |
**allow_unresolved** | optional | Unresolved urls will be imported if set to true | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.allow_unresolved | boolean | | True False |
action_result.parameter.classification | string | | public |
action_result.parameter.create_on_cloud | boolean | | True False |
action_result.parameter.indicator_type | string | | phish_url phish |
action_result.parameter.severity | string | | medium |
action_result.parameter.source | string | | testsource |
action_result.parameter.tags | string | `threatstream tags` | test_url_tag |
action_result.parameter.url | string | `url` | http://122.122.122.122/ |
action_result.parameter.with_approval | boolean | | True False |
action_result.data | string | | |
action_result.summary.created_on_cloud | boolean | | True False |
action_result.message | string | | Successfully sent the request for importing the observable |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'import ip observable'

Import IP observable into ThreatStream

Type: **generic** <br>
Read only: **False**

<ul><li>For importing IP observables without approval, the user must provide indicator type in the indicator_type parameter (e.g - "apt_ip") whereas, for importing observables with approval, the user must provide threat type in the indicator_type parameter (e.g - "apt").</li><li>The possible values of indicator type (itype) and threat_type are listed at the starting of the documentation. If the input contains any indicator type (itype) or threat_type value except the ones listed, the action will behave according to the API behavior.</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_address** | required | Value of IP | string | `ip` `ipv6` |
**indicator_type** | required | Type of observable to import | string | |
**source** | optional | Source of observable to import (It will only be reflected on UI when observable is imported without approval) | string | |
**classification** | optional | Designate classification for observable | string | |
**severity** | optional | Severity of the observable | string | |
**tags** | optional | Comma-separated list of tags to associate with this Observable | string | `threatstream tags` |
**create_on_cloud** | optional | Create on remote (cloud)? (applicable only for hybrid on-prem instances) | boolean | |
**with_approval** | optional | Import the observable with approvals | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.classification | string | | public |
action_result.parameter.create_on_cloud | boolean | | True False |
action_result.parameter.indicator_type | string | | apt_ip apt |
action_result.parameter.ip_address | string | `ip` `ipv6` | 122.122.122.122 |
action_result.parameter.severity | string | | medium |
action_result.parameter.source | string | | testsource |
action_result.parameter.tags | string | `threatstream tags` | test_ip_tag |
action_result.parameter.with_approval | boolean | | True False |
action_result.data | string | | |
action_result.summary.created_on_cloud | boolean | | True False |
action_result.message | string | | Successfully sent the request for importing the observable |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'import file observable'

Import file observable into ThreatStream

Type: **generic** <br>
Read only: **False**

<ul><li>For importing file observables without approval, the user must provide indicator type in the field parameter (e.g - "crypto_hash") whereas, for importing observables with approval, the user must provide threat type in the field parameter (e.g - "crypto").</li><li>The possible values of indicator type (itype) and threat_type are listed at the starting of the documentation. If the input contains any indicator type (itype) or threat_type value except the ones listed, the action will behave according to the API behavior.</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**file_hash** | required | Hash value of file | string | `sha1` `sha256` `md5` `hash` |
**indicator_type** | required | Type of observable to import | string | |
**source** | optional | Source of observable to import (It will only be reflected on UI when observable is imported without approval) | string | |
**confidence** | required | Confidence level | numeric | |
**classification** | optional | Designate classification for observable | string | |
**severity** | optional | Severity of the observable | string | |
**tags** | optional | Comma-separated list of tags to associate with this Observable | string | `threatstream tags` |
**create_on_cloud** | optional | Create on remote (cloud)? (applicable only for hybrid on-prem instances) | boolean | |
**with_approval** | optional | Import the observable with approvals | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.classification | string | | public |
action_result.parameter.confidence | numeric | | 71 |
action_result.parameter.create_on_cloud | boolean | | True False |
action_result.parameter.file_hash | string | `sha1` `sha256` `md5` `hash` | EBDD888E3A22FE7EA3C5750DAFB5484367CA808184D480D461B5E51580AC813B |
action_result.parameter.indicator_type | string | | crypto_hash crypto |
action_result.parameter.severity | string | | medium |
action_result.parameter.source | string | | testsource |
action_result.parameter.tags | string | `threatstream tags` | test_file_tag |
action_result.parameter.with_approval | boolean | | True False |
action_result.data | string | | |
action_result.data.\*.import_session_id | string | | 1000001099 |
action_result.data.\*.job_id | string | | ba6002fd-6bb9-4e6d-912d-8d69e3db5c65 |
action_result.data.\*.success | boolean | | True False |
action_result.summary.created_on_cloud | boolean | | True False |
action_result.message | string | | Successfully sent the request for importing the observable |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'import email observable'

Import email observable into ThreatStream

Type: **generic** <br>
Read only: **False**

<ul><li>For importing email observables without approval, the user must provide indicator type in the indicator_type parameter (e.g - "spam_email") whereas, for importing observables with approval, the user must provide threat type in the indicator_type parameter (e.g - "spam").</li><li>The possible values of indicator type (itype) and threat_type are listed at the starting of the documentation. If the input contains any indicator type (itype) or threat_type value except the ones listed, the action will behave according to the API behavior.</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**email** | required | Value of email | string | `email` |
**indicator_type** | required | Type of observable to import | string | |
**source** | optional | Source of observable to import (It will only be reflected on UI when observable is imported without approval) | string | |
**confidence** | required | Confidence level | numeric | |
**classification** | optional | Designate classification for observable | string | |
**severity** | optional | Severity of the observable | string | |
**tags** | optional | Comma-separated list of tags to associate with this Observable | string | `threatstream tags` |
**create_on_cloud** | optional | Create on remote (cloud)? (applicable only for hybrid on-prem instances) | boolean | |
**with_approval** | optional | Import the observable with approvals | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.classification | string | | private |
action_result.parameter.confidence | numeric | | 79 |
action_result.parameter.create_on_cloud | boolean | | True False |
action_result.parameter.email | string | `email` | test_remote_1@tmail.com |
action_result.parameter.indicator_type | string | | spam_email spam |
action_result.parameter.severity | string | | medium |
action_result.parameter.source | string | | testsource |
action_result.parameter.tags | string | `threatstream tags` | test_email_test |
action_result.parameter.with_approval | boolean | | True False |
action_result.data | string | | |
action_result.data.\*.import_session_id | string | | 1000000020 |
action_result.data.\*.job_id | string | | 321d4116-b632-4ea5-8862-e04c6572e300 |
action_result.data.\*.success | boolean | | True False |
action_result.summary.created_on_cloud | boolean | | True False |
action_result.message | string | | Successfully sent the request for importing the observable |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'import observables'

Import observables into ThreatStream

Type: **generic** <br>
Read only: **False**

<ul><li>For importing observables without approval, the user must provide indicator type in the field parameter (e.g - {"itype": "&lt;indicator_type&gt;"}) whereas, for importing observables with approval, the user must provide threat type in the field parameter (e.g - {"threat_type": "&lt;threat_type&gt;"}).</li><li>The "allow_unresolved" parameter will be passed in the API call if the "value" parameter is set to "domain" or "url" and "with_approval" parameter is set to "False".</li><li>The possible values of indicator type (itype) and threat_type are listed at the starting of the documentation. If the input contains any indicator type (itype) or threat_type value except the ones listed, the action will behave according to the API behavior.</li><li>For importing observables of type 'URL', 'IP' and 'Domain', Threatstream itself detects the confidence value whereas, for importing observables of type 'Email', 'File', the user must provide confidence value in the field parameter (e.g - {"itype": "&lt;indicator_type&gt;", "confidence": &lt;confidence_value&gt;}).</li><li>If both the "itype" and "threat_type" values are passed in the "fields" parameter when "with_approval" is set to "True", the action will behave according to the API behavior.</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**observable_type** | required | Type of observable to import, types supported by default: [ip, domain, url, email, hash]. Custom types can also be provided if they are available on ThreatStream instance | string | |
**value** | required | Observable value | string | `ip` `domain` `url` `email` `md5` `sha1` `hash` |
**classification** | required | Designate classification for observable | string | |
**fields** | optional | JSON formatted string of fields to include with the observable | string | |
**create_on_cloud** | optional | Create on remote (cloud)? (applicable only for hybrid on-prem instances) | boolean | |
**with_approval** | optional | Import the observable with approvals | boolean | |
**allow_unresolved** | optional | Unresolved domains will be imported if set to true | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.allow_unresolved | boolean | | True False |
action_result.parameter.classification | string | | public |
action_result.parameter.create_on_cloud | boolean | | True False |
action_result.parameter.fields | string | | {"itype": "tor_ip", "confidence": 45} {"threat_type": "tor", "confidence": 45} |
action_result.parameter.observable_type | string | | ip |
action_result.parameter.value | string | `ip` `domain` `url` `email` `md5` `sha1` `hash` | 122.122.122.122 |
action_result.parameter.with_approval | boolean | | True False |
action_result.data | string | | |
action_result.data.\*.import_session_id | string | | 1045 |
action_result.data.\*.job_id | string | | 2643424c-868d-42c5-9234-8d754cfcfe4f |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.success | boolean | | True False |
action_result.summary.created_on_cloud | boolean | | True False |
action_result.message | string | | Successfully sent the request for importing the observable |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'tag observable'

Add a tag to the observable

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | Intelligence ID | string | `threatstream intelligence id` |
**source_user_id** | required | ID of user to associate with tag | string | |
**tags** | required | Comma-separated list of tags to associate with this Observable | string | `threatstream tags` |
**tlp** | optional | TLP to assign to each tag | string | `threatstream tlp` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | `threatstream intelligence id` | 51590754288 |
action_result.parameter.source_user_id | string | | 16783 |
action_result.parameter.tags | string | `threatstream tags` | test_tag |
action_result.parameter.tlp | string | `threatstream tlp` | red white |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.success | boolean | | True False |
action_result.data.\*.tags.\*.id | string | | 9x2 nyj |
action_result.data.\*.tags.\*.name | string | | tag_test |
action_result.data.\*.tags.\*.org_id | numeric | | |
action_result.data.\*.tags.\*.remote_api | boolean | | True False |
action_result.data.\*.tags.\*.source_user_id | string | | 16783 |
action_result.data.\*.tags.\*.tlp | string | | red |
action_result.summary | string | | |
action_result.message | string | | Successfully tagged Observable |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get pcap'

Download pcap file of a sample submitted to the sandbox and add it to vault

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | ID of report associated with the pcap to download | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | numeric | | 445798 |
action_result.data.\*.file_name | string | | 20190819_134705_userId-16783_dump.pcap |
action_result.data.\*.vault_id | string | `sha1` `vault id` | 285ed37b6be7b4bf1583b59150b22e9a741caede |
action_result.summary | string | | |
action_result.message | string | | PCAP file added successfully to the vault |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'detonate file'

Detonate file in ThreatStream

Type: **generic** <br>
Read only: **False**

If classification or platform parameter is added and is also mentioned in the fields parameter, the value given in the individual parameters is considered.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**platform** | optional | Which platform to run the detonation on - Ex: WINDOWS10x64. Default is 'WINDOWS7' which will run the detonation on 'WINDOWS7' platform | string | |
**vault_id** | required | Vault id of file to be detonated | string | `vault id` `sha1` |
**classification** | required | Classification of the sandbox submission - private or public | string | |
**use_premium_sandbox** | optional | Specify whether the premium sandbox should be used for detonation - true or false. If you want to use the Joe Sandbox service for detonation, set this attribute to true | boolean | |
**use_vmray_sandbox** | optional | Specify whether the vmray sandbox should be used for detonation - true or false. If you want to use the VMRay sandbox service for detonation, set this attribute to true | boolean | |
**vmray_max_jobs** | optional | Specify the number of detonations you want VMRay to perform for the submission | numeric | |
**fields** | optional | JSON formatted string of additional fields to be included in the detonate file action. e.g. {"file_has_password":"true","file_password":"abc123"}. Please check the API doc to find more information on other valid fields | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.classification | string | | public |
action_result.parameter.fields | string | | {"file_has_password":"true","file_password":"abc123","import_indicators":"true","report_radio-notes":"Credential-Exposure,compromised_email","trusted_circles":"13"} |
action_result.parameter.platform | string | | WINDOWS7 |
action_result.parameter.use_premium_sandbox | boolean | | True False |
action_result.parameter.use_vmray_sandbox | boolean | | True False |
action_result.parameter.vault_id | string | `vault id` `sha1` | dd88508cda7bcfc71ffdbc0e26afe97d3fb9a0b6 |
action_result.parameter.vmray_max_jobs | numeric | | 5 |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.reports.ANDROID4.4.detail | string | | |
action_result.data.\*.reports.ANDROID4.4.status | string | | |
action_result.data.\*.reports.ANDROID5.1.detail | string | | |
action_result.data.\*.reports.ANDROID5.1.status | string | | |
action_result.data.\*.reports.ANDROID6.0.detail | string | | |
action_result.data.\*.reports.ANDROID6.0.status | string | | |
action_result.data.\*.reports.MACOSX.detail | string | | |
action_result.data.\*.reports.MACOSX.status | string | | |
action_result.data.\*.reports.WINDOWS10.detail | string | | |
action_result.data.\*.reports.WINDOWS10.status | string | | |
action_result.data.\*.reports.WINDOWS10x64.detail | string | | |
action_result.data.\*.reports.WINDOWS10x64.status | string | | |
action_result.data.\*.reports.WINDOWS7.detail | string | | |
action_result.data.\*.reports.WINDOWS7.id | numeric | | 449205 |
action_result.data.\*.reports.WINDOWS7.status | string | | |
action_result.data.\*.reports.WINDOWS7NATIVE.detail | string | | |
action_result.data.\*.reports.WINDOWS7NATIVE.status | string | | |
action_result.data.\*.reports.WINDOWS7OFFICE2010.detail | string | | |
action_result.data.\*.reports.WINDOWS7OFFICE2010.status | string | | |
action_result.data.\*.reports.WINDOWS7OFFICE2013.detail | string | | |
action_result.data.\*.reports.WINDOWS7OFFICE2013.status | string | | |
action_result.data.\*.reports.WINDOWSXP.detail | string | | |
action_result.data.\*.reports.WINDOWSXP.id | numeric | | 449204 |
action_result.data.\*.reports.WINDOWSXP.status | string | | |
action_result.data.\*.reports.WINDOWSXPNATIVE.detail | string | | |
action_result.data.\*.reports.WINDOWSXPNATIVE.status | string | | |
action_result.data.\*.success | string | | True False |
action_result.summary | string | | |
action_result.message | string | | Successfully detonated file |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'detonate url'

Detonate URL in ThreatStream

Type: **generic** <br>
Read only: **False**

If classification or platform parameter is added and is also mentioned in the fields parameter, the value given in the individual parameters is considered.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**platform** | optional | Which platform to run the detonation on - Ex: WINDOWS10x64. Default is 'WINDOWS7' which will run the detonation on 'WINDOWS7' platform | string | |
**url** | required | URL to be detonated | string | `url` |
**classification** | required | Classification of the sandbox submission - private or public | string | |
**use_premium_sandbox** | optional | Specify whether the premium sandbox should be used for detonation - true or false. If you want to use the Joe Sandbox service for detonation, set this attribute to true | boolean | |
**use_vmray_sandbox** | optional | Specify whether the vmray sandbox should be used for detonation - true or false. If you want to use the VMRay sandbox service for detonation, set this attribute to true | boolean | |
**vmray_max_jobs** | optional | Specify the number of detonations you want VMRay to perform for the submission | numeric | |
**fields** | optional | JSON formatted string of additional fields to be included in the detonate url action. e.g. {"import_indicators":"true","report_radio-notes":"Credential-Exposure,compromised_email"}. Please check the API doc to find more infomation on other valid fields | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.classification | string | | public |
action_result.parameter.fields | string | | {"import_indicators":"true","report_radio-notes":"Credential-Exposure,compromised_email","trusted_circles":"13"} |
action_result.parameter.platform | string | | WINDOWS7 |
action_result.parameter.url | string | `url` | https://test.com |
action_result.parameter.use_premium_sandbox | boolean | | True False |
action_result.parameter.use_vmray_sandbox | boolean | | True False |
action_result.parameter.vmray_max_jobs | numeric | | 5 |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.reports.WINDOWS7.detail | string | | /api/v1/submit/451705/report/ |
action_result.data.\*.reports.WINDOWS7.id | numeric | | 451705 |
action_result.data.\*.reports.WINDOWS7.status | string | | /api/v1/submit/451705/ |
action_result.data.\*.reports.WINDOWSXP.detail | string | | /api/v1/submit/451704/report/ |
action_result.data.\*.reports.WINDOWSXP.id | numeric | | 451704 |
action_result.data.\*.reports.WINDOWSXP.status | string | | /api/v1/submit/451704/ |
action_result.data.\*.success | boolean | | True False |
action_result.summary | string | | |
action_result.message | string | | Successfully detonated URL |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get status'

Retrieve detonation status present in Threatstream

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**endpoint** | required | Endpoint given by Detonate File/URL (eg: /api/v1/submit/12345/) | string | `threatstream endpoint status` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.endpoint | string | `threatstream endpoint status` | /api/v1/submit/454240/ |
action_result.data.\*.classification | string | | private |
action_result.data.\*.confidence | numeric | | |
action_result.data.\*.date_added | string | | 2018-08-17T17:52:13.832385 |
action_result.data.\*.detail | string | | |
action_result.data.\*.file | string | | /test_file.png |
action_result.data.\*.html_report | string | | |
action_result.data.\*.id | numeric | | 291629 |
action_result.data.\*.import_indicators | boolean | | True False |
action_result.data.\*.jobID | string | | 189200 |
action_result.data.\*.maec_report | string | | |
action_result.data.\*.md5 | string | | |
action_result.data.\*.message | string | | |
action_result.data.\*.misc_info | string | | |
action_result.data.\*.notes | string | | |
action_result.data.\*.pdf_generated | numeric | | 0 |
action_result.data.\*.platform | string | | WINDOWS7 |
action_result.data.\*.platform_label | string | | Windows 7 |
action_result.data.\*.priority | numeric | | 2 |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.reportid | string | | |
action_result.data.\*.resource_uri | string | | |
action_result.data.\*.sandbox_vendor | string | | test |
action_result.data.\*.sha1 | string | | |
action_result.data.\*.sha256 | string | | |
action_result.data.\*.starred_by_me | boolean | | True False |
action_result.data.\*.starred_total_count | numeric | | 0 |
action_result.data.\*.status | string | | processing |
action_result.data.\*.url | string | `url` | |
action_result.data.\*.user.id | numeric | | 6941 |
action_result.data.\*.user.username | string | `email` `user name` | |
action_result.data.\*.user_id | numeric | | 16783 |
action_result.data.\*.verdict | string | | benign |
action_result.data.\*.virustotal | string | | |
action_result.data.\*.votes.me | string | | |
action_result.data.\*.votes.total | numeric | | 0 |
action_result.data.\*.watched_by_me | boolean | | True False |
action_result.data.\*.watched_total_count | numeric | | 0 |
action_result.data.\*.yara | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully retrieved detonation status |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get report'

Retrieve detonation report present in Threatstream

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**endpoint** | required | Endpoint given by Detonate File/URL (eg: /api/v1/submit/141/report/) | string | `threatstream endpoint report` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.endpoint | string | `threatstream endpoint report` | /api/v1/submit/141/report/ |
action_result.data.\*.pcap | string | `url` | |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.results.behavior.anomaly.\*.category | string | | unhook |
action_result.data.\*.results.behavior.anomaly.\*.funcname | string | | SetWindowsHookExW |
action_result.data.\*.results.behavior.anomaly.\*.message | string | | Function hook was modified! |
action_result.data.\*.results.behavior.anomaly.\*.name | string | | iexplore.exe |
action_result.data.\*.results.behavior.anomaly.\*.pid | numeric | | 2012 |
action_result.data.\*.results.behavior.enhanced.\*.data.classname | string | | Shell_TrayWnd |
action_result.data.\*.results.behavior.enhanced.\*.data.content | string | | 0 |
action_result.data.\*.results.behavior.enhanced.\*.data.file | string | `file name` `file path` | KERNEL32.DLL |
action_result.data.\*.results.behavior.enhanced.\*.data.moduleaddress | string | | |
action_result.data.\*.results.behavior.enhanced.\*.data.object | string | | |
action_result.data.\*.results.behavior.enhanced.\*.data.pathtofile | string | | |
action_result.data.\*.results.behavior.enhanced.\*.data.regkey | string | | DisableUNCCheck |
action_result.data.\*.results.behavior.enhanced.\*.data.windowname | string | | |
action_result.data.\*.results.behavior.enhanced.\*.eid | numeric | | 1 |
action_result.data.\*.results.behavior.enhanced.\*.event | string | | load |
action_result.data.\*.results.behavior.enhanced.\*.object | string | | library |
action_result.data.\*.results.behavior.enhanced.\*.timestamp | string | | 2018-08-18 00:52:26,968 |
action_result.data.\*.results.behavior.processes.\*.calls.\*.api | string | | NtOpenDirectoryObject |
action_result.data.\*.results.behavior.processes.\*.calls.\*.arguments.\*.name | string | | DirectoryHandle |
action_result.data.\*.results.behavior.processes.\*.calls.\*.arguments.\*.value | string | `file path` `file name` | 0x00000088 |
action_result.data.\*.results.behavior.processes.\*.calls.\*.category | string | | filesystem |
action_result.data.\*.results.behavior.processes.\*.calls.\*.id | numeric | | 0 |
action_result.data.\*.results.behavior.processes.\*.calls.\*.repeated | numeric | | 0 |
action_result.data.\*.results.behavior.processes.\*.calls.\*.return | string | | 0x00000000 |
action_result.data.\*.results.behavior.processes.\*.calls.\*.status | boolean | | True False |
action_result.data.\*.results.behavior.processes.\*.calls.\*.thread_id | string | | 2684 |
action_result.data.\*.results.behavior.processes.\*.calls.\*.timestamp | string | | 2018-08-18 00:52:26,936 |
action_result.data.\*.results.behavior.processes.\*.first_seen | string | | 2018-08-18 00:52:26,921 |
action_result.data.\*.results.behavior.processes.\*.parent_id | numeric | | 2228 |
action_result.data.\*.results.behavior.processes.\*.process_id | numeric | | 2680 |
action_result.data.\*.results.behavior.processes.\*.process_name | string | `file name` | cmd.exe |
action_result.data.\*.results.behavior.processtree.\*.children.\*.name | string | | iexplore.exe |
action_result.data.\*.results.behavior.processtree.\*.children.\*.parent_id | numeric | | 1772 |
action_result.data.\*.results.behavior.processtree.\*.children.\*.pid | numeric | | 2012 |
action_result.data.\*.results.behavior.processtree.\*.name | string | `file name` | cmd.exe |
action_result.data.\*.results.behavior.processtree.\*.parent_id | numeric | | 2228 |
action_result.data.\*.results.behavior.processtree.\*.pid | numeric | `pid` | 2680 |
action_result.data.\*.results.behavior.summary.files | string | `file path` `file name` | C:\\Windows\\system32\\rsaenh.dll |
action_result.data.\*.results.behavior.summary.keys | string | | HKEY_LOCAL_MACHINE\\Software\\Classes\\Interface\\{6C72B11B-DBE0-4C87-B1A8-7C8A36BD563D} |
action_result.data.\*.results.debug.log | string | | |
action_result.data.\*.results.dropped.\*.crc32 | string | | 7CCFDEB6 |
action_result.data.\*.results.dropped.\*.md5 | string | | e2817febfede77b8cc498c4833098742 |
action_result.data.\*.results.dropped.\*.name | string | | invalidcert[1] |
action_result.data.\*.results.dropped.\*.path | string | | /opt/ts_sandbox/cuckoo/storage/analyses/2036/files/9088658753/invalidcert[1] |
action_result.data.\*.results.dropped.\*.sha1 | string | | 6ab7cc3e5c14221cd349a932d56c6bd1acefed70 |
action_result.data.\*.results.dropped.\*.sha256 | string | | aab4f5b4bdd02b66b46643b0bbd40761c694b14857e6943f3ac03b692fd08047 |
action_result.data.\*.results.dropped.\*.sha512 | string | | 10e93a02799d727584621ab0852f864e1e9875e6a68d6dce4eee3f454cc253672a74859dd078c1779b88e26f44bd410a6c173dcd86ec49effb119d56e01bc977 |
action_result.data.\*.results.dropped.\*.size | numeric | | 4922 |
action_result.data.\*.results.dropped.\*.ssdeep | string | | 96:UUHUD0Ws5PFkiGjUpEajPCMCz27BS4bLAi:3UIWsnkdjoFDd57BS4bMi |
action_result.data.\*.results.dropped.\*.type | string | | HTML document, UTF-8 Unicode (with BOM) text, with CRLF line terminators |
action_result.data.\*.results.info.category | string | | file |
action_result.data.\*.results.info.custom | string | | |
action_result.data.\*.results.info.duration | numeric | | 1765 |
action_result.data.\*.results.info.ended | string | | 2018-08-17 18:21:40 |
action_result.data.\*.results.info.id | numeric | | 189200 |
action_result.data.\*.results.info.machine.id | numeric | | 188372 |
action_result.data.\*.results.info.machine.label | string | | WINDOWS7_4 |
action_result.data.\*.results.info.machine.manager | string | | KVM |
action_result.data.\*.results.info.machine.name | string | | WINDOWS7_4 |
action_result.data.\*.results.info.machine.shutdown_on | string | | 2018-08-17 18:21:40 |
action_result.data.\*.results.info.machine.started_on | string | | 2018-08-17 17:52:15 |
action_result.data.\*.results.info.package | string | | |
action_result.data.\*.results.info.started | string | | 2018-08-17 17:52:15 |
action_result.data.\*.results.info.version | string | | 1.3-dev |
action_result.data.\*.results.network.dns.\*.answers.\*.data | string | | 216.58.193.142 |
action_result.data.\*.results.network.dns.\*.answers.\*.type | string | | A |
action_result.data.\*.results.network.dns.\*.request | string | | test.com |
action_result.data.\*.results.network.dns.\*.type | string | | A |
action_result.data.\*.results.network.domains.\*.domain | string | | test.com |
action_result.data.\*.results.network.domains.\*.ip | string | | 172.217.2.238 |
action_result.data.\*.results.network.hosts | string | `ip` | 122.122.122.122 |
action_result.data.\*.results.network.pcap_sha256 | string | `sha256` | f6d7241fa1c3c47cec2169d11a7899d642383f15e23e325ade8677b7417a1539 |
action_result.data.\*.results.network.sorted_pcap_sha256 | string | `sha256` | 89152c1836bd3444227ad29fafd1c8cb492d2f904966c154cd3dd8497133052e |
action_result.data.\*.results.network.tcp.\*.dport | numeric | | 139 |
action_result.data.\*.results.network.tcp.\*.dst | string | `ip` | 122.122.122.122 |
action_result.data.\*.results.network.tcp.\*.offset | numeric | | 466 |
action_result.data.\*.results.network.tcp.\*.sport | numeric | | 1038 |
action_result.data.\*.results.network.tcp.\*.src | string | `ip` | 122.122.122.122 |
action_result.data.\*.results.network.tcp.\*.time | numeric | | 6.429862976074219 |
action_result.data.\*.results.network.udp.\*.dport | numeric | | 137 |
action_result.data.\*.results.network.udp.\*.dst | string | `ip` | 122.122.122.122 |
action_result.data.\*.results.network.udp.\*.offset | numeric | | 7218 |
action_result.data.\*.results.network.udp.\*.sport | numeric | | 137 |
action_result.data.\*.results.network.udp.\*.src | string | `ip` | 122.122.122.122 |
action_result.data.\*.results.network.udp.\*.time | numeric | | 6.429553985595703 |
action_result.data.\*.results.signatures.\*.alert | boolean | | True False |
action_result.data.\*.results.signatures.\*.data.\*.process.process_name | string | | test.exe |
action_result.data.\*.results.signatures.\*.data.\*.signs.\*.type | string | | api |
action_result.data.\*.results.signatures.\*.data.\*.signs.\*.value.category | string | | filesystem |
action_result.data.\*.results.signatures.\*.data.\*.signs.\*.value.return | string | | |
action_result.data.\*.results.signatures.\*.data.\*.signs.\*.value.status | boolean | | True False |
action_result.data.\*.results.signatures.\*.data.\*.signs.\*.value.thread_id | string | | 1840 |
action_result.data.\*.results.signatures.\*.data.\*.signs.\*.value.timestamp | string | | 2019-08-19 19:38:38,843 |
action_result.data.\*.results.signatures.\*.name | string | | antisandbox_sleep |
action_result.data.\*.results.signatures.\*.severity | numeric | | 3 |
action_result.data.\*.results.target.category | string | | file |
action_result.data.\*.results.target.file.crc32 | string | | 1EC6C6C8 |
action_result.data.\*.results.target.file.md5 | string | `md5` | f0216e2697dc24e71777811c6c0c5858 |
action_result.data.\*.results.target.file.name | string | | box.png |
action_result.data.\*.results.target.file.path | string | | |
action_result.data.\*.results.target.file.sha1 | string | `sha1` | 7fa1c75071fcb3efe0089cc1b78cf9a121a313cd |
action_result.data.\*.results.target.file.sha256 | string | `sha256` | |
action_result.data.\*.results.target.file.sha512 | string | | 99479dda2a5334d3f4894c063d7d0147cc8d3dad1e48f3db1130fabad13b65141cfd54831984143a39840161130884b53260c60360b529afe0a7a4f4f7904882 |
action_result.data.\*.results.target.file.size | numeric | | 7707 |
action_result.data.\*.results.target.file.ssdeep | string | | |
action_result.data.\*.results.target.file.type | string | | PNG image data, 400 x 220, 8-bit gray+alpha, non-interlaced |
action_result.data.\*.results.target.url | string | | https://test.com |
action_result.data.\*.screenshots | string | `url` | |
action_result.data.\*.success | boolean | | True False |
action_result.summary | string | | |
action_result.message | string | | Successfully retrieved detonation report |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'on poll'

Callback action for the on_poll ingest functionality

Type: **ingest** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**container_id** | optional | Parameter ignored in this app | numeric | |
**start_time** | optional | Parameter ignored in this app | numeric | |
**end_time** | optional | Parameter ignored in this app | numeric | |
**container_count** | optional | Maximum number of container records (incidents) to query for | numeric | |
**artifact_count** | optional | Parameter ignored in this app | numeric | |

#### Action Output

No Output

## action: 'run query'

Run observables query in ThreatStream

Type: **investigate** <br>
Read only: **True**

For providing the <b>query</b> parameter, please form a valid search string using the Anomali filter language (as seen on the advanced search page) and then convert it into a valid JSON string as shown in the example here. e.g. Anomali filter language-based search string = modifed_ts\_\_gt=2018-01-10&status=active has to be provided in the <b>query</b> parameter as { "modifed_ts\_\_gt": "2018-01-10", "status": "active" }<br> If offset is provided in the 'query' parameter, it will be overwritten by the offset value provided in the 'offset' parameter.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query** | required | Search string in JSON format using the Anomali filter language (as seen on the advanced search page) | string | |
**order_by** | optional | Field by which the query results will be ordered | string | |
**offset** | optional | Record offset (used with paging, when returning many results) | numeric | |
**limit** | optional | Record limit | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 1000 |
action_result.parameter.offset | numeric | | 0 |
action_result.parameter.order_by | string | | itype value |
action_result.parameter.query | string | | |
action_result.data.\*.asn | string | | 11426 |
action_result.data.\*.can_add_public_tags | boolean | | True False |
action_result.data.\*.confidence | numeric | | 11 |
action_result.data.\*.country | string | | US |
action_result.data.\*.created_by | string | | |
action_result.data.\*.created_ts | string | | 2018-03-29T23:31:34.986Z |
action_result.data.\*.description | string | | |
action_result.data.\*.expiration_ts | string | | 2018-06-27T23:31:35.004Z |
action_result.data.\*.feed_id | numeric | | 0 |
action_result.data.\*.id | numeric | `threatstream intelligence id` | 50630233146 |
action_result.data.\*.import_session_id | string | | |
action_result.data.\*.import_source | string | | |
action_result.data.\*.ip | string | `ip` | 122.122.122.122 |
action_result.data.\*.is_anonymous | boolean | | True False |
action_result.data.\*.is_editable | boolean | | True False |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.itype | string | | actor_ip |
action_result.data.\*.latitude | string | | 35.293600 |
action_result.data.\*.longitude | string | | -80.735000 |
action_result.data.\*.meta.detail | string | | smbd |
action_result.data.\*.meta.detail2 | string | | imported by user 13487 Confirmed as false positive |
action_result.data.\*.meta.limit | numeric | | 25 |
action_result.data.\*.meta.maltype | string | | |
action_result.data.\*.meta.registrant_address | string | | DomainsByProxy.com|14455 N. Hayden Road, Scottsdale, Arizona, UNITED STATES, 85260 |
action_result.data.\*.meta.registrant_email | string | | gfdf.com@domainsbyproxy.com |
action_result.data.\*.meta.registrant_name | string | | Registration Private |
action_result.data.\*.meta.registrant_org | string | | Domains By Proxy, LLC |
action_result.data.\*.meta.registrant_phone | string | | 14806242599 |
action_result.data.\*.meta.registration_created | string | | 2004-06-18T18:16:16+00:00 |
action_result.data.\*.meta.registration_updated | string | | 2020-11-13T23:57:39+00:00 |
action_result.data.\*.meta.severity | string | | low |
action_result.data.\*.modified_ts | string | | 2018-03-29T23:31:34.986Z |
action_result.data.\*.org | string | | Test org |
action_result.data.\*.owner_organization_id | numeric | | 2342 |
action_result.data.\*.rdns | string | | user-0c99mbe.test.test.com |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_uri | string | | /api/v2/intelligence/50630233146/ |
action_result.data.\*.retina_confidence | numeric | | -1 |
action_result.data.\*.source | string | | test_source.us |
action_result.data.\*.source_created | string | | |
action_result.data.\*.source_modified | string | | |
action_result.data.\*.source_reported_confidence | numeric | | 50 |
action_result.data.\*.status | string | | falsepos |
action_result.data.\*.subtype | string | | |
action_result.data.\*.tags | string | | |
action_result.data.\*.tags.\*.id | string | | tpp |
action_result.data.\*.tags.\*.name | string | | smbd |
action_result.data.\*.tags.\*.org_id | string | | 67 |
action_result.data.\*.tags.\*.remote_api | boolean | | True False |
action_result.data.\*.tags.\*.tlp | string | | red |
action_result.data.\*.threat_type | string | | p2p |
action_result.data.\*.threatscore | numeric | | 3 |
action_result.data.\*.tlp | string | | |
action_result.data.\*.trusted_circle_ids | string | | |
action_result.data.\*.type | string | | ip |
action_result.data.\*.update_id | numeric | | 1736852157 |
action_result.data.\*.uuid | string | | 094074ec-3acc-4639-8eb9-982eb002a33b |
action_result.data.\*.value | string | | 24.148.217.110 |
action_result.summary.records_returned | numeric | | 950 |
action_result.message | string | | Records returned: 950 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list import sessions'

List all the import sessions

Type: **investigate** <br>
Read only: **True**

<ul><li>For a Hybrid instance, this action will return both remote and local data based on the input parameters.</li><li>The user can use the <b>list imports</b> action to fetch only remote or local data in the response.</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**date_modified_gte** | optional | Import sessions with greater than or equal to the provided modified date will be returned | string | `threatstream date` |
**limit** | optional | Total number of import sessions to return | numeric | |
**offset** | optional | Record offset (used with paging, when returning many results) | numeric | |
**status_in** | optional | Status to filter the records | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.date_modified_gte | string | `threatstream date` | 2020-11-05T17:30:00.130822 |
action_result.parameter.limit | numeric | | 10 |
action_result.parameter.offset | numeric | | 0 |
action_result.parameter.status_in | string | | approved errors done deleted processing |
action_result.data.\*.approved_by.avatar_s3_url | string | | |
action_result.data.\*.approved_by.can_share_intelligence | boolean | | True False |
action_result.data.\*.approved_by.email | string | `email` | test@test.com |
action_result.data.\*.approved_by.id | string | | 142 |
action_result.data.\*.approved_by.is_active | boolean | | True False |
action_result.data.\*.approved_by.is_readonly | boolean | | True False |
action_result.data.\*.approved_by.must_change_password | boolean | | True False |
action_result.data.\*.approved_by.name | string | | testname |
action_result.data.\*.approved_by.nickname | string | | TestIntegrationLab |
action_result.data.\*.approved_by.organization.id | string | | 70 |
action_result.data.\*.approved_by.organization.name | string | | test |
action_result.data.\*.approved_by.organization.resource_uri | string | | /api/v1/userorganization/70/ |
action_result.data.\*.approved_by.resource_uri | string | | /api/v1/user/142/ |
action_result.data.\*.approved_by_id | string | | 142 |
action_result.data.\*.confidence | numeric | | 50 |
action_result.data.\*.date | string | | 2020-10-08T10:49:07.546945 |
action_result.data.\*.date_modified | string | | 2020-10-08T11:38:29.563295 |
action_result.data.\*.default_comment | string | | test comment |
action_result.data.\*.email | string | `email` | test@test.com |
action_result.data.\*.expiration_ts | string | | 2021-01-06T10:41:08.444000 |
action_result.data.\*.fileName | string | `url` | https://test.com/https%3A/test.com?Signature=19pJrM2OyY3wqiKi%2FDwPRThLq%2Bs%3D&Expires=1602227603&AWSAccessKeyId=AKIAQYUTUNAKSCAMMFFH |
action_result.data.\*.fileType | string | | html |
action_result.data.\*.file_name_label | string | | |
action_result.data.\*.id | numeric | `threatstream import session id` | 875 |
action_result.data.\*.intelligence_source | string | `url` | https://test.com/test |
action_result.data.\*.investigations.\*.id | string | | 34 |
action_result.data.\*.investigations.\*.name | string | | Test_y |
action_result.data.\*.investigations.\*.resource_uri | string | | /api/v1/investigation/34/ |
action_result.data.\*.is_anonymous | boolean | | True False |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.jobID | string | | |
action_result.data.\*.messages | string | | |
action_result.data.\*.name | string | | test |
action_result.data.\*.notes | string | | |
action_result.data.\*.numIndicators | numeric | | 125 |
action_result.data.\*.numRejected | numeric | | 1412 |
action_result.data.\*.num_private | numeric | | 125 |
action_result.data.\*.num_public | numeric | | 0 |
action_result.data.\*.organization.id | string | | 70 |
action_result.data.\*.organization.name | string | | test |
action_result.data.\*.organization.resource_uri | string | | /api/v1/userorganization/70/ |
action_result.data.\*.orginal_intelligence | string | | |
action_result.data.\*.processed_ts | string | | 2020-10-08T10:54:01.965978 |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_uri | string | | /api/v1/importsession/875/ |
action_result.data.\*.sandbox_submit | string | | |
action_result.data.\*.source_confidence_weight | numeric | | 0 |
action_result.data.\*.status | string | | approved |
action_result.data.\*.tags.\*.id | string | | tmh |
action_result.data.\*.tags.\*.name | string | | test |
action_result.data.\*.tags.\*.org_id | numeric | | 70 |
action_result.data.\*.tags.\*.remote_api | boolean | | True False |
action_result.data.\*.tags.\*.tlp | string | | red |
action_result.data.\*.threat_type | string | | malware |
action_result.data.\*.tlp | string | | amber |
action_result.data.\*.trusted_circles.\*.anonymous_sharing | boolean | | True False |
action_result.data.\*.trusted_circles.\*.can_override_confidence | boolean | | True False |
action_result.data.\*.trusted_circles.\*.description | string | | Test circle |
action_result.data.\*.trusted_circles.\*.id | numeric | | 10017 |
action_result.data.\*.trusted_circles.\*.is_freemium | boolean | | True False |
action_result.data.\*.trusted_circles.\*.mattermost_team_id | string | | |
action_result.data.\*.trusted_circles.\*.name | string | | Test circle |
action_result.data.\*.trusted_circles.\*.openinvite | boolean | | True False |
action_result.data.\*.trusted_circles.\*.partner | string | | |
action_result.data.\*.trusted_circles.\*.premium_channel | string | | |
action_result.data.\*.trusted_circles.\*.public | boolean | | True False |
action_result.data.\*.trusted_circles.\*.remote_api | boolean | | True False |
action_result.data.\*.trusted_circles.\*.restricted_publishing | boolean | | True False |
action_result.data.\*.trusted_circles.\*.subscription_model | string | | |
action_result.data.\*.trusted_circles.\*.use_chat | boolean | | True False |
action_result.data.\*.trusted_circles.\*.validate_subscriptions | boolean | | True False |
action_result.data.\*.user_id | numeric | | 142 |
action_result.data.\*.visibleForReview | boolean | | True False |
action_result.summary.import_sessions_returned | numeric | | 9 |
action_result.message | string | | Import sessions returned: 9 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update import session'

This action updates the fields of the provided item id

Type: **generic** <br>
Read only: **False**

If "null" is provided in the expire time parameter, then expiration time will be set to "9999-12-31T00:00:00".</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**item_id** | required | ID of the import session to update | numeric | `threatstream import session id` |
**intelligence_source** | optional | Intelligence Source to update | string | |
**tlp** | optional | Traffic Light Protocol value to update | string | `threatstream tlp` |
**tags** | optional | Comma-separated list of tags to update | string | `threatstream tags` |
**comment** | optional | Comment to update | string | |
**expire_time** | optional | Expiration time to update (Format : YYYY-MM-DD HH:MM\[:ss[.uuuuuu]\][TZ]) | string | `threatstream date` |
**threat_model_type** | optional | Comma-separated list of threat model types to associate | string | |
**threat_model_to_associate** | optional | Comma-separated list of threat model IDs to associate | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.comment | string | | |
action_result.parameter.expire_time | string | `threatstream date` | 2022-01-03T18:30:00 |
action_result.parameter.intelligence_source | string | | https://test.com |
action_result.parameter.item_id | numeric | `threatstream import session id` | 869 |
action_result.parameter.tags | string | `threatstream tags` | test_tag_4 |
action_result.parameter.threat_model_to_associate | string | | |
action_result.parameter.threat_model_type | string | | |
action_result.parameter.tlp | string | `threatstream tlp` | Green |
action_result.data.\*.approved_by.avatar_s3_url | string | | |
action_result.data.\*.approved_by.can_share_intelligence | boolean | | True False |
action_result.data.\*.approved_by.email | string | | qa+testuser2@test.data.com |
action_result.data.\*.approved_by.id | string | | 136 |
action_result.data.\*.approved_by.is_active | boolean | | True False |
action_result.data.\*.approved_by.is_readonly | boolean | | True False |
action_result.data.\*.approved_by.must_change_password | boolean | | True False |
action_result.data.\*.approved_by.name | string | | testuser2 |
action_result.data.\*.approved_by.nickname | string | | |
action_result.data.\*.approved_by.organization.id | string | | 67 |
action_result.data.\*.approved_by.organization.name | string | | org.test.com |
action_result.data.\*.approved_by.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.approved_by.resource_uri | string | | /api/v1/user/136/ |
action_result.data.\*.approved_by_id | numeric | | |
action_result.data.\*.associations.actors.\*.id | string | | 10909 |
action_result.data.\*.associations.actors.\*.name | string | | MANDRA |
action_result.data.\*.associations.actors.\*.resource_uri | string | | /api/v1/actor/10909/ |
action_result.data.\*.associations.incidents.\*.id | string | | 725 |
action_result.data.\*.associations.incidents.\*.name | string | | Incident on Cloud |
action_result.data.\*.associations.incidents.\*.resource_uri | string | | /api/v1/incident/725/ |
action_result.data.\*.associations.malware.\*.id | string | | 188 |
action_result.data.\*.associations.malware.\*.name | string | | TestMal |
action_result.data.\*.associations.malware.\*.resource_uri | string | | /api/v1/malware/188/ |
action_result.data.\*.associations.tip_reports.\*.id | string | | 9479 |
action_result.data.\*.associations.tip_reports.\*.name | string | | Test 103 |
action_result.data.\*.associations.tip_reports.\*.resource_uri | string | | /api/v1/tipreport/9479/ |
action_result.data.\*.associations.ttps.\*.id | string | | 1573 |
action_result.data.\*.associations.ttps.\*.name | string | | TestTTP |
action_result.data.\*.associations.ttps.\*.resource_uri | string | | /api/v1/ttp/1573/ |
action_result.data.\*.associations.vulnerabilities.\*.id | string | | 15657 |
action_result.data.\*.associations.vulnerabilities.\*.name | string | | TestVuln |
action_result.data.\*.associations.vulnerabilities.\*.resource_uri | string | | /api/v1/vulnerability/15657/ |
action_result.data.\*.confidence | numeric | | 50 |
action_result.data.\*.date | string | | 2020-10-06T05:53:45.585213 |
action_result.data.\*.date_modified | string | | 2020-10-25T10:08:03.990333 |
action_result.data.\*.default_comment | string | | this is a test comment |
action_result.data.\*.email | string | `email` | test@test.com |
action_result.data.\*.expiration_ts | string | | 2022-01-03T18:30:00 |
action_result.data.\*.fileName | string | | |
action_result.data.\*.fileType | string | | analyst |
action_result.data.\*.file_name_label | string | | |
action_result.data.\*.id | numeric | | 869 |
action_result.data.\*.intelligence_source | string | `url` | https://test.com |
action_result.data.\*.is_anonymous | boolean | | True False |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.jobID | string | | |
action_result.data.\*.messages | string | | |
action_result.data.\*.name | string | | test |
action_result.data.\*.notes | string | | |
action_result.data.\*.numIndicators | numeric | | 1 |
action_result.data.\*.numRejected | numeric | | 0 |
action_result.data.\*.num_private | numeric | | 1 |
action_result.data.\*.num_public | numeric | | 0 |
action_result.data.\*.organization.id | string | | 70 |
action_result.data.\*.organization.name | string | | test |
action_result.data.\*.organization.resource_uri | string | | /api/v1/userorganization/70/ |
action_result.data.\*.orginal_intelligence | string | | ['1000000138'] |
action_result.data.\*.processed_ts | string | | 2020-10-06T05:53:45.907751 |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.remote_associations.incidents.\*.assignee_user | string | | |
action_result.data.\*.remote_associations.incidents.\*.can_add_public_tags | boolean | | True False |
action_result.data.\*.remote_associations.incidents.\*.created_ts | string | | 2020-05-25T11:27:38.203866 |
action_result.data.\*.remote_associations.incidents.\*.end_date | string | | |
action_result.data.\*.remote_associations.incidents.\*.feed_id | numeric | | 0 |
action_result.data.\*.remote_associations.incidents.\*.id | numeric | | 730 |
action_result.data.\*.remote_associations.incidents.\*.is_anonymous | boolean | | True False |
action_result.data.\*.remote_associations.incidents.\*.is_cloneable | string | | yes |
action_result.data.\*.remote_associations.incidents.\*.is_public | boolean | | True False |
action_result.data.\*.remote_associations.incidents.\*.modified_ts | string | | 2020-05-25T12:10:11.244851 |
action_result.data.\*.remote_associations.incidents.\*.name | string | | Incident: public on-prem 2 |
action_result.data.\*.remote_associations.incidents.\*.organization_id | numeric | | 67 |
action_result.data.\*.remote_associations.incidents.\*.owner_user_id | numeric | | 136 |
action_result.data.\*.remote_associations.incidents.\*.publication_status | string | | published |
action_result.data.\*.remote_associations.incidents.\*.published_ts | string | | 2020-05-25T12:10:11.129180 |
action_result.data.\*.remote_associations.incidents.\*.remote_api | boolean | | True False |
action_result.data.\*.remote_associations.incidents.\*.resource_uri | string | | /api/v1/incident/730/?remote_api=true |
action_result.data.\*.remote_associations.incidents.\*.source_created | string | | |
action_result.data.\*.remote_associations.incidents.\*.source_modified | string | | |
action_result.data.\*.remote_associations.incidents.\*.start_date | string | | |
action_result.data.\*.remote_associations.incidents.\*.status.display_name | string | | New |
action_result.data.\*.remote_associations.incidents.\*.status.id | numeric | | 1 |
action_result.data.\*.remote_associations.incidents.\*.status.resource_uri | string | | /api/v1/incidentstatustype/1/ |
action_result.data.\*.remote_associations.incidents.\*.tlp | string | | |
action_result.data.\*.remote_associations.incidents.\*.uuid | string | | c46abbc8-9645-49ae-8da5-d85d805e0a57 |
action_result.data.\*.resource_uri | string | | /api/v1/importsession/869/ |
action_result.data.\*.sandbox_submit | string | | |
action_result.data.\*.source_confidence_weight | numeric | | 0 |
action_result.data.\*.status | string | | done |
action_result.data.\*.tags.\*.id | string | | nak |
action_result.data.\*.tags.\*.name | string | | test_tag |
action_result.data.\*.tags.\*.org_id | numeric | | 70 |
action_result.data.\*.tags.\*.remote_api | boolean | | True False |
action_result.data.\*.tags.\*.tlp | string | `threatstream tlp` | white |
action_result.data.\*.threat_type | string | | malware |
action_result.data.\*.tlp | string | | Green |
action_result.data.\*.user_id | numeric | | 142 |
action_result.data.\*.visibleForReview | boolean | | True False |
action_result.summary | string | | |
action_result.message | string | | Successfully updated ['expiration_ts', 'tlp', 'intelligence_source']. Successfully updated tags |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.ph | ph | | |

## action: 'list threat models'

List all the threat models

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**modified_ts\_\_gte** | optional | Threat models with greater than or equal to the provided modified time stamp will be returned | string | |
**limit** | optional | Total number of threat models to return | numeric | |
**model_type** | optional | Model type to filter the records | string | |
**tags_name** | optional | Tag name to filter the records | string | `threatstream tags` |
**publication_status** | optional | Publication status to filter the records | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 681 |
action_result.parameter.model_type | string | | tipreport |
action_result.parameter.modified_ts\_\_gte | string | | |
action_result.parameter.publication_status | string | | new |
action_result.parameter.tags_name | string | `threatstream tags` | test_tag |
action_result.data.\*.aliases | string | | test |
action_result.data.\*.assignee_user.email | string | | gita@verizon2.com |
action_result.data.\*.assignee_user.id | numeric | | 12 |
action_result.data.\*.assignee_user.name | string | | |
action_result.data.\*.circles.\*.id | numeric | | 10017 |
action_result.data.\*.circles.\*.name | string | | Test circle |
action_result.data.\*.circles.\*.remote_api | boolean | | True False |
action_result.data.\*.created_ts | string | | 2020-09-02T07:21:35.440102+00:00 |
action_result.data.\*.cvss2_score | string | | |
action_result.data.\*.cvss3_score | string | | |
action_result.data.\*.end_date | string | | |
action_result.data.\*.feed_id | numeric | | 131 |
action_result.data.\*.id | numeric | `threatstream actor id` `threatstream campaign id` `threatstream incident id` `threatstream vulnerability id` `threatstream ttp id` `threatstream threatbulletin id` `threatstream signature id` | 9479 |
action_result.data.\*.is_email | boolean | | True False |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.model_type | string | | tipreport |
action_result.data.\*.modified_ts | string | | 2020-10-06T12:06:53.021601+00:00 |
action_result.data.\*.name | string | `email` | Test 103 |
action_result.data.\*.organization.id | numeric | | 70 |
action_result.data.\*.organization.title | string | | test |
action_result.data.\*.owner_user.email | string | `email` | test@test.com |
action_result.data.\*.owner_user.id | numeric | | 142 |
action_result.data.\*.owner_user.name | string | | test |
action_result.data.\*.publication_status | string | | published |
action_result.data.\*.published_ts | string | | 2020-09-06T10:45:56.790629+00:00 |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_uri | string | | /api/v1/tipreport/9479/ |
action_result.data.\*.sort | numeric | | 1601966535004 |
action_result.data.\*.source_created | string | | |
action_result.data.\*.source_modified | string | | |
action_result.data.\*.start_date | string | | |
action_result.data.\*.status | string | | |
action_result.data.\*.tags.\*.id | string | | w4z |
action_result.data.\*.tags.\*.name | string | | tip-tag1 |
action_result.data.\*.tags.\*.org_id | numeric | | 70 |
action_result.data.\*.tags.\*.remote_api | boolean | | True False |
action_result.data.\*.tags.\*.tlp | string | | red |
action_result.data.\*.tlp | string | | white |
action_result.data.\*.type | string | | botnet |
action_result.data.\*.uuid | string | | 1f3f4c9e-9fb9-4914-b365-8bf3f17f8f76 |
action_result.summary.threat_models_returned | numeric | | 681 |
action_result.message | string | | Threat models returned: 681 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create threat bulletin'

Create a threat bulletin in ThreatStream

Type: **generic** <br>
Read only: **False**

<ul><li>Circles parameter will only be applicable when a threat bulletin will be created on the cloud.</li><li>If the body_content_type parameter is not provided, then the default value (markdown) will be considered as the value of the body_content_type parameter. Once created, body_content_type cannot be modified.</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Name to give the threat bulletin | string | |
**status** | optional | Status to give the threat bulletin | string | |
**source** | optional | Source of the threat bulletin | string | |
**tags** | optional | Comma-separated list of tags for the threat bulletin | string | |
**tlp** | optional | Tlp to give the threat bulletin | string | |
**assignee_user_id** | optional | Assignee to give the threat bulletin | numeric | |
**body** | optional | Body content to give the threat bulletin | string | |
**body_content_type** | optional | Body content type to give the threat bulletin (Once specified, body_content_type cannot be modified, Default is 'markdown') | string | |
**comments** | optional | Comments to give the threat bulletin(JSON format containing body, title, etc.) | string | |
**attachments** | optional | Vault id of an attachment to add on the threat bulletin | string | `vault id` `sha1` |
**local_intelligence** | optional | Comma-separated list of local intelligence IDs to associate with the threat bulletin - Note that this appends | string | `threatstream intelligence id` |
**cloud_intelligence** | optional | Comma-separated list of remote intelligence IDs to associate with the threat bulletin - Note that this appends | string | `threatstream intelligence id` |
**circles** | optional | Comma-separated list of circles to give the threat bulletin (Applicable only when a cloud threat bulletin will be created) | string | |
**import_sessions** | optional | Comma-separated list of sessions to give the threat bulletin | string | |
**create_on_cloud** | optional | Create on remote (cloud)? (applicable only for hybrid on-prem instances) | boolean | |
**is_public** | optional | Classification designation | boolean | |
**is_anonymous** | optional | Whether the threat bulletin user and organization information is anonymized | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.assignee_user_id | numeric | | 22 |
action_result.parameter.attachments | string | `vault id` `sha1` | b10e56af7aed0446e7c87d495700118787212378 |
action_result.parameter.body | string | | test body |
action_result.parameter.body_content_type | string | | richtext |
action_result.parameter.circles | string | | 10022,10020 |
action_result.parameter.cloud_intelligence | string | `threatstream intelligence id` | 229717444 |
action_result.parameter.comments | string | | {"body":"test comment1","title":"test comment2"} |
action_result.parameter.create_on_cloud | boolean | | True False |
action_result.parameter.import_sessions | string | | 10899,170994 |
action_result.parameter.is_anonymous | boolean | | True False |
action_result.parameter.is_public | boolean | | True False |
action_result.parameter.local_intelligence | string | `threatstream intelligence id` | 1000000298 |
action_result.parameter.name | string | | test name |
action_result.parameter.source | string | | test source |
action_result.parameter.status | string | | new |
action_result.parameter.tags | string | | test tag1, test tag2 |
action_result.parameter.tlp | string | | amber |
action_result.data.\*.all_circles_visible | boolean | | True False |
action_result.data.\*.assignee_org | string | | |
action_result.data.\*.assignee_org_id | string | | |
action_result.data.\*.assignee_org_name | string | | |
action_result.data.\*.assignee_user | string | | |
action_result.data.\*.assignee_user.avatar_s3_url | string | | |
action_result.data.\*.assignee_user.can_share_intelligence | boolean | | True False |
action_result.data.\*.assignee_user.email | string | `email` | mark@domaintools.com |
action_result.data.\*.assignee_user.id | string | | 22 |
action_result.data.\*.assignee_user.is_active | boolean | | True False |
action_result.data.\*.assignee_user.is_readonly | boolean | | True False |
action_result.data.\*.assignee_user.must_change_password | boolean | | True False |
action_result.data.\*.assignee_user.name | string | | |
action_result.data.\*.assignee_user.nickname | string | | |
action_result.data.\*.assignee_user.organization.id | string | | 11 |
action_result.data.\*.assignee_user.organization.name | string | | DomainTools |
action_result.data.\*.assignee_user.organization.resource_uri | string | | /api/v1/userorganization/11/ |
action_result.data.\*.assignee_user.resource_uri | string | | /api/v1/user/22/ |
action_result.data.\*.assignee_user_id | numeric | | 22 |
action_result.data.\*.assignee_user_name | string | | |
action_result.data.\*.attachments | string | | id |
action_result.data.\*.body | string | | test body |
action_result.data.\*.body_content_type | string | | richtext |
action_result.data.\*.campaign | string | | |
action_result.data.\*.comments.body | string | | test comment1 |
action_result.data.\*.comments.created_ts | string | | 2021-04-06T08:09:33.924401 |
action_result.data.\*.comments.id | string | | 57 |
action_result.data.\*.comments.modified_ts | string | | 2021-04-06T08:09:33.924401 |
action_result.data.\*.comments.remote_api | boolean | | True False |
action_result.data.\*.comments.tip_report | numeric | | 10890 |
action_result.data.\*.comments.title | string | | test comment2 |
action_result.data.\*.comments.tlp | string | | red |
action_result.data.\*.comments.user.avatar_s3_url | string | | |
action_result.data.\*.comments.user.can_share_intelligence | boolean | | True False |
action_result.data.\*.comments.user.email | string | `email` | test@testuser.com |
action_result.data.\*.comments.user.id | string | | 136 |
action_result.data.\*.comments.user.is_active | boolean | | True False |
action_result.data.\*.comments.user.is_readonly | boolean | | True False |
action_result.data.\*.comments.user.must_change_password | boolean | | True False |
action_result.data.\*.comments.user.name | string | | testuser2 |
action_result.data.\*.comments.user.nickname | string | | |
action_result.data.\*.comments.user.organization.id | string | | 67 |
action_result.data.\*.comments.user.organization.name | string | | test.org.com |
action_result.data.\*.comments.user.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.comments.user.resource_uri | string | | /api/v1/user/136/ |
action_result.data.\*.created_ts | string | | 2021-04-06T08:09:31.778085 |
action_result.data.\*.embedded_content_type | string | | |
action_result.data.\*.embedded_content_url | string | | |
action_result.data.\*.feed_id | numeric | | 0 |
action_result.data.\*.history.\*.action | string | | created-report |
action_result.data.\*.history.\*.detail | string | | |
action_result.data.\*.history.\*.id | string | | 33822 |
action_result.data.\*.history.\*.quantity | string | | |
action_result.data.\*.history.\*.remote_api | boolean | | True False |
action_result.data.\*.history.\*.tip_report | numeric | | 10890 |
action_result.data.\*.history.\*.ts | string | | 2021-04-06T08:09:31.778085 |
action_result.data.\*.history.\*.user.avatar_s3_url | string | | |
action_result.data.\*.history.\*.user.can_share_intelligence | boolean | | True False |
action_result.data.\*.history.\*.user.email | string | `email` | test@testuser.com |
action_result.data.\*.history.\*.user.id | string | | 136 |
action_result.data.\*.history.\*.user.is_active | boolean | | True False |
action_result.data.\*.history.\*.user.is_readonly | boolean | | True False |
action_result.data.\*.history.\*.user.must_change_password | boolean | | True False |
action_result.data.\*.history.\*.user.name | string | | testuser2 |
action_result.data.\*.history.\*.user.nickname | string | | |
action_result.data.\*.history.\*.user.organization.id | string | | 67 |
action_result.data.\*.history.\*.user.organization.name | string | | test.org.com |
action_result.data.\*.history.\*.user.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.history.\*.user.resource_uri | string | | /api/v1/user/136/ |
action_result.data.\*.id | string | `threatstream threatbulletin id` | 10890 |
action_result.data.\*.intelligence.\*.id | numeric | | 229717582 |
action_result.data.\*.is_anonymous | boolean | | True False |
action_result.data.\*.is_cloneable | string | | yes |
action_result.data.\*.is_editable | boolean | | True False |
action_result.data.\*.is_email | boolean | | True False |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.logo_s3_url | string | | |
action_result.data.\*.modified_ts | string | | 2021-04-06T08:09:31.801690 |
action_result.data.\*.name | string | | test name |
action_result.data.\*.original_source | string | | |
action_result.data.\*.original_source_id | string | | |
action_result.data.\*.owner_org.id | string | | 67 |
action_result.data.\*.owner_org.name | string | | test.org.com |
action_result.data.\*.owner_org.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.owner_org_id | numeric | | 67 |
action_result.data.\*.owner_org_name | string | | test.org.com |
action_result.data.\*.owner_user.avatar_s3_url | string | | |
action_result.data.\*.owner_user.can_share_intelligence | boolean | | True False |
action_result.data.\*.owner_user.email | string | `email` | test@testuser.com |
action_result.data.\*.owner_user.id | string | | 136 |
action_result.data.\*.owner_user.is_active | boolean | | True False |
action_result.data.\*.owner_user.is_readonly | boolean | | True False |
action_result.data.\*.owner_user.must_change_password | boolean | | True False |
action_result.data.\*.owner_user.name | string | | testuser2 |
action_result.data.\*.owner_user.nickname | string | | |
action_result.data.\*.owner_user.organization.id | string | | 67 |
action_result.data.\*.owner_user.organization.name | string | | test.org.com |
action_result.data.\*.owner_user.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.owner_user.resource_uri | string | | /api/v1/user/136/ |
action_result.data.\*.owner_user_id | numeric | | 136 |
action_result.data.\*.owner_user_name | string | | testuser2 |
action_result.data.\*.parent | string | | |
action_result.data.\*.private_status_id | string | | |
action_result.data.\*.published_ts | string | | |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_uri | string | | /api/v1/tipreport/10890/?remote_api=true |
action_result.data.\*.source | string | | test source |
action_result.data.\*.source_created | string | | |
action_result.data.\*.source_modified | string | | |
action_result.data.\*.starred_by_me | boolean | | True False |
action_result.data.\*.starred_total_count | numeric | | 0 |
action_result.data.\*.status | string | | new |
action_result.data.\*.threat_actor | string | | |
action_result.data.\*.tlp | string | | amber |
action_result.data.\*.ttp | string | | |
action_result.data.\*.uuid | string | | 3c566c79-e3c5-4c02-bb8c-acff8182b100 |
action_result.data.\*.votes.me | string | | |
action_result.data.\*.votes.total | numeric | | 0 |
action_result.data.\*.watched_by_me | boolean | | True False |
action_result.data.\*.watched_total_count | numeric | | 0 |
action_result.summary.created_on_cloud | boolean | | True False |
action_result.message | string | | Threat bulletin created successfully. Associated intelligence : 229717582, 229717444, 1000000298, 1000000001 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update threat bulletin'

Update a threat bulletin in ThreatStream

Type: **generic** <br>
Read only: **False**

Circles parameter will only be applicable when a cloud threat bulletin will be updated.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | ID of the threat bulletin | string | `threatstream threatbulletin id` |
**status** | optional | Status to give the threat bulletin | string | |
**source** | optional | Source of the threat bulletin | string | |
**tags** | optional | Comma-separated list of tags for the threat bulletin | string | |
**tlp** | optional | Tlp to give the threat bulletin | string | |
**assignee_user_id** | optional | Assignee to give the threat bulletin | numeric | |
**body** | optional | Body content to give the threat bulletin | string | |
**comments** | optional | Comments to give the threat bulletin(JSON format containing body, title, etc.) | string | |
**local_intelligence** | optional | Comma-separated list of local intelligence IDs to associate with the threat bulletin - Note that this appends | string | `threatstream intelligence id` |
**cloud_intelligence** | optional | Comma-separated list of remote intelligence IDs to associate with the threat bulletin - Note that this appends | string | `threatstream intelligence id` |
**attachments** | optional | Vault id of an attachment to add on the threat bulletin | string | `vault id` `sha1` |
**circles** | optional | Comma-separated list of circles to give the threat bulletin (Applicable only when a cloud threat bulletin will be updated) | string | |
**import_sessions** | optional | Comma-separated list of sessions to give the threat bulletin | string | |
**is_public** | optional | Classification designation | boolean | |
**is_anonymous** | optional | Whether the threat bulletin user and organization information is anonymized | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.assignee_user_id | numeric | | 10 |
action_result.parameter.attachments | string | `vault id` `sha1` | b10e56af7aed0446e7c87d495700118787212378 |
action_result.parameter.body | string | | test body |
action_result.parameter.circles | string | | 10022,10020 |
action_result.parameter.cloud_intelligence | string | `threatstream intelligence id` | 229717444 |
action_result.parameter.comments | string | | {"body":"test comment","title":"test comment"} |
action_result.parameter.id | string | `threatstream threatbulletin id` | 1000000014 |
action_result.parameter.import_sessions | string | | 10899,170994 |
action_result.parameter.is_anonymous | boolean | | True False |
action_result.parameter.is_public | boolean | | True False |
action_result.parameter.local_intelligence | string | `threatstream intelligence id` | 1000000298 |
action_result.parameter.source | string | | test source |
action_result.parameter.status | string | | published |
action_result.parameter.tags | string | | test tag |
action_result.parameter.tlp | string | | red |
action_result.data.\*.all_circles_visible | boolean | | True False |
action_result.data.\*.assignee_org | string | | |
action_result.data.\*.assignee_org_id | string | | |
action_result.data.\*.assignee_org_name | string | | |
action_result.data.\*.assignee_user | string | | |
action_result.data.\*.assignee_user.avatar_s3_url | string | | |
action_result.data.\*.assignee_user.can_share_intelligence | boolean | | True False |
action_result.data.\*.assignee_user.email | string | | admin-idefense@idefense.com |
action_result.data.\*.assignee_user.id | string | | 44 |
action_result.data.\*.assignee_user.is_active | boolean | | True False |
action_result.data.\*.assignee_user.is_readonly | boolean | | True False |
action_result.data.\*.assignee_user.must_change_password | boolean | | True False |
action_result.data.\*.assignee_user.name | string | | |
action_result.data.\*.assignee_user.nickname | string | | |
action_result.data.\*.assignee_user.organization.id | string | | 20 |
action_result.data.\*.assignee_user.organization.name | string | | iDefense |
action_result.data.\*.assignee_user.organization.resource_uri | string | | /api/v1/userorganization/20/ |
action_result.data.\*.assignee_user.resource_uri | string | | /api/v1/user/44/ |
action_result.data.\*.assignee_user_id | string | | |
action_result.data.\*.assignee_user_name | string | | |
action_result.data.\*.attachments.\*.content_type | string | | |
action_result.data.\*.attachments.\*.created_ts | string | | 2021-03-26T10:31:45.712609 |
action_result.data.\*.attachments.\*.filename | string | | abcd.txt |
action_result.data.\*.attachments.\*.id | string | | 9001 |
action_result.data.\*.attachments.\*.modified_ts | string | | 2021-03-26T10:31:45.712609 |
action_result.data.\*.attachments.\*.remote_api | boolean | | True False |
action_result.data.\*.attachments.\*.s3_thumbnail_url | string | | |
action_result.data.\*.attachments.\*.s3_url | string | | http://ui-threatstream.s3.test.com/userUploads/2021-03-26/20210326_103145_userId-136_abcd.txt |
action_result.data.\*.attachments.\*.signed_thumbnail_url | string | | |
action_result.data.\*.attachments.\*.signed_url | string | | https://test-optic.s3.ui.com/userUploads/2021-03-26/20210326_103145_userId-136_abcd.txt?Signature=p5I5tJOrB242TAOSA39eYxL7dr4%3D&Expires=1616756070&AWSAccessKeyId=AKIAQYUTUNAKSCAMMFFH |
action_result.data.\*.attachments.\*.tip_report | numeric | | 10787 |
action_result.data.\*.attachments.\*.user.avatar_s3_url | string | | |
action_result.data.\*.attachments.\*.user.can_share_intelligence | boolean | | True False |
action_result.data.\*.attachments.\*.user.email | string | | testuser2@test.user.com |
action_result.data.\*.attachments.\*.user.id | string | | 136 |
action_result.data.\*.attachments.\*.user.is_active | boolean | | True False |
action_result.data.\*.attachments.\*.user.is_readonly | boolean | | True False |
action_result.data.\*.attachments.\*.user.must_change_password | boolean | | True False |
action_result.data.\*.attachments.\*.user.name | string | | testuser2 |
action_result.data.\*.attachments.\*.user.nickname | string | | |
action_result.data.\*.attachments.\*.user.organization.id | string | | 67 |
action_result.data.\*.attachments.\*.user.organization.name | string | | test.user.com |
action_result.data.\*.attachments.\*.user.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.attachments.\*.user.resource_uri | string | | /api/v1/user/136/ |
action_result.data.\*.attachments.content_type | string | | application/octet-stream |
action_result.data.\*.attachments.created_ts | string | | 2021-04-06T08:02:48.025223 |
action_result.data.\*.attachments.filename | string | | Bien suÌ‚r.rtf |
action_result.data.\*.attachments.id | string | | 1000000009 |
action_result.data.\*.attachments.modified_ts | string | | 2021-04-06T08:02:48.025223 |
action_result.data.\*.attachments.remote_api | boolean | | True False |
action_result.data.\*.attachments.s3_thumbnail_url | string | | |
action_result.data.\*.attachments.s3_url | string | `url` | http://52.52.79.127/ts-optic-appliance/userUploads/2021-04-06/20210406_080247_userId-136_Biensur.rtf |
action_result.data.\*.attachments.signed_thumbnail_url | string | | |
action_result.data.\*.attachments.signed_url | string | `url` | https://52.52.79.127/ts-optic-appliance/userUploads/2021-04-06/20210406_080247_userId-136_Biensur.rtf?Signature=x8Yz2TkHXGvo616DTDC5ngO%2F740%3D&Expires=1617697068&AWSAccessKeyId=MKL12IRRH2NRCOHN7QB0 |
action_result.data.\*.attachments.tip_report | numeric | | 1000000014 |
action_result.data.\*.attachments.user.avatar_s3_url | string | | |
action_result.data.\*.attachments.user.can_share_intelligence | boolean | | True False |
action_result.data.\*.attachments.user.email | string | `email` | test@testuser.com |
action_result.data.\*.attachments.user.id | string | | 136 |
action_result.data.\*.attachments.user.is_active | boolean | | True False |
action_result.data.\*.attachments.user.is_readonly | boolean | | True False |
action_result.data.\*.attachments.user.must_change_password | boolean | | True False |
action_result.data.\*.attachments.user.name | string | | testuser2 |
action_result.data.\*.attachments.user.nickname | string | | |
action_result.data.\*.attachments.user.organization.id | string | | 67 |
action_result.data.\*.attachments.user.organization.name | string | | test.org.com |
action_result.data.\*.attachments.user.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.attachments.user.resource_uri | string | | /api/v1/user/136/ |
action_result.data.\*.body | string | | test body |
action_result.data.\*.body_content_type | string | | richtext |
action_result.data.\*.campaign | string | | |
action_result.data.\*.comments.\*.body | string | | test123 |
action_result.data.\*.comments.\*.created_ts | string | | 2021-03-26T10:31:46.122309 |
action_result.data.\*.comments.\*.id | string | | 33 |
action_result.data.\*.comments.\*.modified_ts | string | | 2021-03-26T10:31:46.173656 |
action_result.data.\*.comments.\*.remote_api | boolean | | True False |
action_result.data.\*.comments.\*.tip_report | numeric | | 10787 |
action_result.data.\*.comments.\*.title | string | | test123 |
action_result.data.\*.comments.\*.tlp | string | | |
action_result.data.\*.comments.\*.user.avatar_s3_url | string | | |
action_result.data.\*.comments.\*.user.can_share_intelligence | boolean | | True False |
action_result.data.\*.comments.\*.user.email | string | | testuser2@test.user.com |
action_result.data.\*.comments.\*.user.id | string | | 136 |
action_result.data.\*.comments.\*.user.is_active | boolean | | True False |
action_result.data.\*.comments.\*.user.is_readonly | boolean | | True False |
action_result.data.\*.comments.\*.user.must_change_password | boolean | | True False |
action_result.data.\*.comments.\*.user.name | string | | testuser2 |
action_result.data.\*.comments.\*.user.nickname | string | | |
action_result.data.\*.comments.\*.user.organization.id | string | | 67 |
action_result.data.\*.comments.\*.user.organization.name | string | | test.user.com |
action_result.data.\*.comments.\*.user.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.comments.\*.user.resource_uri | string | | /api/v1/user/136/ |
action_result.data.\*.comments.body | string | | test comment |
action_result.data.\*.comments.created_ts | string | | 2021-04-06T08:02:48.184466 |
action_result.data.\*.comments.id | string | | 1000000014 |
action_result.data.\*.comments.modified_ts | string | | 2021-04-06T08:02:48.184466 |
action_result.data.\*.comments.remote_api | boolean | | True False |
action_result.data.\*.comments.tip_report | numeric | | 1000000014 |
action_result.data.\*.comments.title | string | | test comment |
action_result.data.\*.comments.tlp | string | | red |
action_result.data.\*.comments.user.avatar_s3_url | string | | |
action_result.data.\*.comments.user.can_share_intelligence | boolean | | True False |
action_result.data.\*.comments.user.email | string | `email` | test@testuser.com |
action_result.data.\*.comments.user.id | string | | 136 |
action_result.data.\*.comments.user.is_active | boolean | | True False |
action_result.data.\*.comments.user.is_readonly | boolean | | True False |
action_result.data.\*.comments.user.must_change_password | boolean | | True False |
action_result.data.\*.comments.user.name | string | | testuser2 |
action_result.data.\*.comments.user.nickname | string | | |
action_result.data.\*.comments.user.organization.id | string | | 67 |
action_result.data.\*.comments.user.organization.name | string | | test.org.com |
action_result.data.\*.comments.user.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.comments.user.resource_uri | string | | /api/v1/user/136/ |
action_result.data.\*.created_ts | string | | 2021-03-30T06:02:14.276627 |
action_result.data.\*.embedded_content_type | string | | |
action_result.data.\*.embedded_content_url | string | | |
action_result.data.\*.feed_id | string | | 0 |
action_result.data.\*.history.\*.action | string | | updated-report |
action_result.data.\*.history.\*.detail | string | | |
action_result.data.\*.history.\*.id | string | | 1000000078 |
action_result.data.\*.history.\*.quantity | string | | |
action_result.data.\*.history.\*.remote_api | boolean | | True False |
action_result.data.\*.history.\*.tip_report | numeric | | 1000000014 |
action_result.data.\*.history.\*.ts | string | | 2021-04-06T08:02:47.206202 |
action_result.data.\*.history.\*.user.avatar_s3_url | string | | |
action_result.data.\*.history.\*.user.can_share_intelligence | boolean | | True False |
action_result.data.\*.history.\*.user.email | string | `email` | test@testuser.com |
action_result.data.\*.history.\*.user.id | string | | 136 |
action_result.data.\*.history.\*.user.is_active | boolean | | True False |
action_result.data.\*.history.\*.user.is_readonly | boolean | | True False |
action_result.data.\*.history.\*.user.must_change_password | boolean | | True False |
action_result.data.\*.history.\*.user.name | string | | testuser2 |
action_result.data.\*.history.\*.user.nickname | string | | |
action_result.data.\*.history.\*.user.organization.id | string | | 67 |
action_result.data.\*.history.\*.user.organization.name | string | | test.org.com |
action_result.data.\*.history.\*.user.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.history.\*.user.resource_uri | string | | /api/v1/user/136/ |
action_result.data.\*.id | string | `threatstream threatbulletin id` | 1000000014 |
action_result.data.\*.intelligence.\*.id | numeric | | 1000000001 |
action_result.data.\*.is_anonymous | boolean | | True False |
action_result.data.\*.is_cloneable | string | | yes |
action_result.data.\*.is_editable | boolean | | True False |
action_result.data.\*.is_email | boolean | | True False |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.logo_s3_url | string | | |
action_result.data.\*.modified_ts | string | | 2021-04-06T08:02:47.133081 |
action_result.data.\*.name | string | | 1 |
action_result.data.\*.original_source | string | | |
action_result.data.\*.original_source_id | string | | |
action_result.data.\*.owner_org.id | string | | 67 |
action_result.data.\*.owner_org.name | string | | test.org.com |
action_result.data.\*.owner_org.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.owner_org_id | numeric | | 67 |
action_result.data.\*.owner_org_name | string | | test.org.com |
action_result.data.\*.owner_user.avatar_s3_url | string | | |
action_result.data.\*.owner_user.can_share_intelligence | boolean | | True False |
action_result.data.\*.owner_user.email | string | `email` | test@testuser.com |
action_result.data.\*.owner_user.id | string | | 136 |
action_result.data.\*.owner_user.is_active | boolean | | True False |
action_result.data.\*.owner_user.is_readonly | boolean | | True False |
action_result.data.\*.owner_user.must_change_password | boolean | | True False |
action_result.data.\*.owner_user.name | string | | testuser2 |
action_result.data.\*.owner_user.nickname | string | | |
action_result.data.\*.owner_user.organization.id | string | | 67 |
action_result.data.\*.owner_user.organization.name | string | | test.org.com |
action_result.data.\*.owner_user.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.owner_user.resource_uri | string | | /api/v1/user/136/ |
action_result.data.\*.owner_user_id | numeric | | 136 |
action_result.data.\*.owner_user_name | string | | testuser2 |
action_result.data.\*.parent | string | | |
action_result.data.\*.private_status_id | string | | |
action_result.data.\*.published_ts | string | | 2021-04-06T08:02:47.079317 |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_uri | string | | /api/v1/tipreport/1000000014/ |
action_result.data.\*.source | string | | test source |
action_result.data.\*.source_created | string | | |
action_result.data.\*.source_modified | string | | |
action_result.data.\*.starred_by_me | boolean | | True False |
action_result.data.\*.starred_total_count | numeric | | 0 |
action_result.data.\*.status | string | | published |
action_result.data.\*.threat_actor | string | | |
action_result.data.\*.tlp | string | | red |
action_result.data.\*.ttp | string | | |
action_result.data.\*.uuid | string | | d4027da6-c694-4b22-8396-e43154331eb0 |
action_result.data.\*.votes.me | string | | |
action_result.data.\*.votes.total | numeric | | 0 |
action_result.data.\*.watched_by_me | boolean | | True False |
action_result.data.\*.watched_total_count | numeric | | 0 |
action_result.summary | string | | |
action_result.message | string | | Successfully updated threat bulletin. Associated intelligence : 1000000298, 1000000001, 229717582, 229717444 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list threat bulletins'

List threat bulletins present in ThreatStream

Type: **investigate** <br>
Read only: **True**

<ul><li>This action will list the threat bulletins in oldest first format.</li><li>is_public parameter will only be applicable as filter when its value will be set to "true" or "false". It wont be applied as a filter and will list all the threat bulletins when the value of is_public parameter is set to "all".</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**limit** | optional | Total number of threat bulletins to return | numeric | |
**name** | optional | Name to filter the threat bulletins | string | |
**status** | optional | Status to filter the threat bulletins | string | |
**source** | optional | Source to filter the threat bulletins | string | |
**assignee_user_id** | optional | Assignee to filter the threat bulletins | numeric | |
**is_public** | optional | Classification designation | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.assignee_user_id | numeric | | 22 |
action_result.parameter.is_public | string | | true false all |
action_result.parameter.limit | numeric | | 1000 |
action_result.parameter.name | string | | test name |
action_result.parameter.source | string | | test source |
action_result.parameter.status | string | | new |
action_result.data.\*.\*.all_circles_visible | boolean | | True False |
action_result.data.\*.\*.assignee_org | string | | |
action_result.data.\*.\*.assignee_org_id | string | | |
action_result.data.\*.\*.assignee_org_name | string | | |
action_result.data.\*.\*.assignee_user | string | | |
action_result.data.\*.\*.assignee_user.avatar_s3_url | string | | |
action_result.data.\*.\*.assignee_user.can_share_intelligence | boolean | | True False |
action_result.data.\*.\*.assignee_user.email | string | | tkng@anomali.com |
action_result.data.\*.\*.assignee_user.id | string | | 3 |
action_result.data.\*.\*.assignee_user.is_active | boolean | | True False |
action_result.data.\*.\*.assignee_user.is_readonly | boolean | | True False |
action_result.data.\*.\*.assignee_user.must_change_password | boolean | | True False |
action_result.data.\*.\*.assignee_user.name | string | | |
action_result.data.\*.\*.assignee_user.nickname | string | | |
action_result.data.\*.\*.assignee_user.organization.id | string | | 2 |
action_result.data.\*.\*.assignee_user.organization.name | string | | Anomali |
action_result.data.\*.\*.assignee_user.organization.resource_uri | string | | /api/v1/userorganization/2/ |
action_result.data.\*.\*.assignee_user.resource_uri | string | | /api/v1/user/3/ |
action_result.data.\*.\*.assignee_user_id | numeric | | 3 |
action_result.data.\*.\*.assignee_user_name | string | | |
action_result.data.\*.\*.body_content_type | string | | markdown |
action_result.data.\*.\*.campaign | string | | |
action_result.data.\*.\*.can_add_public_tags | string | | |
action_result.data.\*.\*.created_ts | string | | 2021-03-25T09:05:07.105073 |
action_result.data.\*.\*.feed_id | numeric | | 0 |
action_result.data.\*.\*.id | string | | 10768 |
action_result.data.\*.\*.is_anonymous | boolean | | True False |
action_result.data.\*.\*.is_cloneable | string | | yes |
action_result.data.\*.\*.is_editable | boolean | | True False |
action_result.data.\*.\*.is_email | boolean | | True False |
action_result.data.\*.\*.is_public | boolean | | True False |
action_result.data.\*.\*.modified_ts | string | | 2021-03-25T09:05:07.110410 |
action_result.data.\*.\*.name | string | | tag |
action_result.data.\*.\*.original_source | string | | |
action_result.data.\*.\*.original_source_id | string | | |
action_result.data.\*.\*.owner_org | string | | |
action_result.data.\*.\*.owner_org.id | string | | 67 |
action_result.data.\*.\*.owner_org.name | string | | test.user.com |
action_result.data.\*.\*.owner_org.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.\*.owner_org.title | string | | Analyst |
action_result.data.\*.\*.owner_org_id | string | | |
action_result.data.\*.\*.owner_org_name | string | | |
action_result.data.\*.\*.owner_user | string | | |
action_result.data.\*.\*.owner_user.avatar_s3_url | string | | |
action_result.data.\*.\*.owner_user.can_share_intelligence | boolean | | True False |
action_result.data.\*.\*.owner_user.email | string | | testuser2@qa.test.com |
action_result.data.\*.\*.owner_user.id | string | | 136 |
action_result.data.\*.\*.owner_user.is_active | boolean | | True False |
action_result.data.\*.\*.owner_user.is_readonly | boolean | | True False |
action_result.data.\*.\*.owner_user.must_change_password | boolean | | True False |
action_result.data.\*.\*.owner_user.name | string | | testuser |
action_result.data.\*.\*.owner_user.nickname | string | | |
action_result.data.\*.\*.owner_user.organization.id | string | | 67 |
action_result.data.\*.\*.owner_user.organization.name | string | | qa.test.com |
action_result.data.\*.\*.owner_user.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.\*.owner_user.resource_uri | string | | /api/v1/user/136/ |
action_result.data.\*.\*.owner_user_id | string | | |
action_result.data.\*.\*.owner_user_name | string | | |
action_result.data.\*.\*.parent | string | | |
action_result.data.\*.\*.published_ts | string | | |
action_result.data.\*.\*.remote_api | boolean | | True False |
action_result.data.\*.\*.resource_uri | string | | /api/v1/tipreport/10768/?remote_api=true |
action_result.data.\*.\*.source | string | | test |
action_result.data.\*.\*.source_created | string | | |
action_result.data.\*.\*.source_modified | string | | |
action_result.data.\*.\*.starred_by_me | boolean | | True False |
action_result.data.\*.\*.starred_total_count | numeric | | 0 |
action_result.data.\*.\*.status | string | | new |
action_result.data.\*.\*.tags_v2.\*.id | string | | rb6 |
action_result.data.\*.\*.tags_v2.\*.name | string | | file |
action_result.data.\*.\*.tags_v2.\*.org_id | numeric | | 67 |
action_result.data.\*.\*.tags_v2.\*.remote_api | boolean | | True False |
action_result.data.\*.\*.tags_v2.\*.tlp | string | | white |
action_result.data.\*.\*.threat_actor | string | | |
action_result.data.\*.\*.tlp | string | | white |
action_result.data.\*.\*.ttp | string | | |
action_result.data.\*.\*.uuid | string | | f0ae413e-9967-4b32-bd52-810fbebfb421 |
action_result.data.\*.\*.votes.me | string | | |
action_result.data.\*.\*.votes.total | numeric | | 0 |
action_result.data.\*.\*.watched_by_me | boolean | | True False |
action_result.data.\*.\*.watched_total_count | numeric | | 0 |
action_result.data.\*.all_circles_visible | boolean | | True False |
action_result.data.\*.assignee_org | string | | |
action_result.data.\*.assignee_org_id | string | | |
action_result.data.\*.assignee_org_name | string | | |
action_result.data.\*.assignee_user | string | | |
action_result.data.\*.assignee_user.avatar_s3_url | string | | |
action_result.data.\*.assignee_user.can_share_intelligence | boolean | | True False |
action_result.data.\*.assignee_user.email | string | `email` | mark@domaintools.com |
action_result.data.\*.assignee_user.id | string | | 22 |
action_result.data.\*.assignee_user.is_active | boolean | | True False |
action_result.data.\*.assignee_user.is_readonly | boolean | | True False |
action_result.data.\*.assignee_user.must_change_password | boolean | | True False |
action_result.data.\*.assignee_user.name | string | | |
action_result.data.\*.assignee_user.nickname | string | | |
action_result.data.\*.assignee_user.organization.id | string | | 11 |
action_result.data.\*.assignee_user.organization.name | string | | DomainTools |
action_result.data.\*.assignee_user.organization.resource_uri | string | | /api/v1/userorganization/11/ |
action_result.data.\*.assignee_user.resource_uri | string | | /api/v1/user/22/ |
action_result.data.\*.assignee_user_id | numeric | | 22 |
action_result.data.\*.assignee_user_name | string | | |
action_result.data.\*.body_content_type | string | | richtext |
action_result.data.\*.campaign | string | | |
action_result.data.\*.can_add_public_tags | boolean | | True False |
action_result.data.\*.circles.\*.anonymous_sharing | boolean | | True False |
action_result.data.\*.circles.\*.can_edit | boolean | | True False |
action_result.data.\*.circles.\*.can_invite | boolean | | True False |
action_result.data.\*.circles.\*.can_override_confidence | boolean | | True False |
action_result.data.\*.circles.\*.description | string | | For testing... |
action_result.data.\*.circles.\*.disable_vendor_emails | string | | |
action_result.data.\*.circles.\*.id | numeric | | 10018 |
action_result.data.\*.circles.\*.is_freemium | boolean | | True False |
action_result.data.\*.circles.\*.mattermost_team_id | string | | |
action_result.data.\*.circles.\*.member | boolean | | True False |
action_result.data.\*.circles.\*.name | string | | Test circle 2 |
action_result.data.\*.circles.\*.num_administrators | numeric | | 1 |
action_result.data.\*.circles.\*.num_members | numeric | | 1 |
action_result.data.\*.circles.\*.openinvite | boolean | | True False |
action_result.data.\*.circles.\*.pending | boolean | | True False |
action_result.data.\*.circles.\*.public | boolean | | True False |
action_result.data.\*.circles.\*.remote_api | boolean | | True False |
action_result.data.\*.circles.\*.resource_uri | string | | /api/v1/basetrustedcircle/10018/?remote_api=true |
action_result.data.\*.circles.\*.restricted_publishing | boolean | | True False |
action_result.data.\*.circles.\*.subscription_model | string | | |
action_result.data.\*.circles.\*.use_chat | boolean | | True False |
action_result.data.\*.circles.\*.validate_subscriptions | boolean | | True False |
action_result.data.\*.created_ts | string | | 2021-04-06T08:09:31.778085 |
action_result.data.\*.feed_id | numeric | | 0 |
action_result.data.\*.id | string | `threatstream threatbulletin id` | 10890 |
action_result.data.\*.is_anonymous | boolean | | True False |
action_result.data.\*.is_cloneable | string | | yes |
action_result.data.\*.is_editable | boolean | | True False |
action_result.data.\*.is_email | boolean | | True False |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.modified_ts | string | | 2021-04-06T08:09:33.982053 |
action_result.data.\*.name | string | | test name |
action_result.data.\*.original_source | string | | |
action_result.data.\*.original_source_id | string | | |
action_result.data.\*.owner_org | string | | |
action_result.data.\*.owner_org.id | string | | 67 |
action_result.data.\*.owner_org.name | string | | test.org.com |
action_result.data.\*.owner_org.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.owner_org.title | string | | Analyst |
action_result.data.\*.owner_org_id | numeric | | 67 |
action_result.data.\*.owner_org_name | string | | test.org.com |
action_result.data.\*.owner_user | string | | |
action_result.data.\*.owner_user.avatar_s3_url | string | | |
action_result.data.\*.owner_user.can_share_intelligence | boolean | | True False |
action_result.data.\*.owner_user.email | string | `email` | test@testuser.com |
action_result.data.\*.owner_user.id | string | | 136 |
action_result.data.\*.owner_user.is_active | boolean | | True False |
action_result.data.\*.owner_user.is_readonly | boolean | | True False |
action_result.data.\*.owner_user.must_change_password | boolean | | True False |
action_result.data.\*.owner_user.name | string | | testuser2 |
action_result.data.\*.owner_user.nickname | string | | |
action_result.data.\*.owner_user.organization.id | string | | 67 |
action_result.data.\*.owner_user.organization.name | string | | test.org.com |
action_result.data.\*.owner_user.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.owner_user.resource_uri | string | | /api/v1/user/136/ |
action_result.data.\*.owner_user_id | numeric | | 136 |
action_result.data.\*.owner_user_name | string | | testuser2 |
action_result.data.\*.parent | string | | |
action_result.data.\*.published_ts | string | | |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_uri | string | | /api/v1/tipreport/10890/?remote_api=true |
action_result.data.\*.source | string | | test source |
action_result.data.\*.source_created | string | | |
action_result.data.\*.source_modified | string | | |
action_result.data.\*.starred_by_me | boolean | | True False |
action_result.data.\*.starred_total_count | numeric | | 0 |
action_result.data.\*.status | string | | new |
action_result.data.\*.tags | string | | test tag2 |
action_result.data.\*.tags_v2.\*.id | string | | i45 |
action_result.data.\*.tags_v2.\*.name | string | | test tag1 |
action_result.data.\*.tags_v2.\*.org_id | numeric | | 67 |
action_result.data.\*.tags_v2.\*.remote_api | boolean | | True False |
action_result.data.\*.tags_v2.\*.tlp | string | | white |
action_result.data.\*.threat_actor | string | | |
action_result.data.\*.tlp | string | | amber |
action_result.data.\*.ttp | string | | |
action_result.data.\*.uuid | string | | 3c566c79-e3c5-4c02-bb8c-acff8182b100 |
action_result.data.\*.votes.me | string | | |
action_result.data.\*.votes.total | numeric | | 0 |
action_result.data.\*.watched_by_me | boolean | | True False |
action_result.data.\*.watched_total_count | numeric | | 0 |
action_result.summary.threat_bulletins_returned | numeric | | 1 |
action_result.message | string | | Threat bulletins returned: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list associations'

List associations of an entity present in ThreatStream

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity_id** | required | ID of the entity | string | `threatstream actor id` `threatstream campaign id` `threatstream incident id` `threatstream vulnerability id` `threatstream ttp id` `threatstream threatbulletin id` `threatstream signature id` |
**limit** | optional | Total number of associations to return | numeric | |
**entity_type** | required | Type of threat model entity to list the associations | string | |
**associated_entity_type** | required | Type of associations of the enitity to list | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.associated_entity_type | string | | vulnerability |
action_result.parameter.entity_id | string | `threatstream actor id` `threatstream campaign id` `threatstream incident id` `threatstream vulnerability id` `threatstream ttp id` `threatstream threatbulletin id` `threatstream signature id` | 1000000001 |
action_result.parameter.entity_type | string | | tipreport |
action_result.parameter.limit | numeric | | 2 |
action_result.data.\*.all_circles_visible | boolean | | True False |
action_result.data.\*.asn | string | | |
action_result.data.\*.assignee_org | string | | |
action_result.data.\*.assignee_org_id | string | | |
action_result.data.\*.assignee_org_name | string | | |
action_result.data.\*.assignee_user | string | | |
action_result.data.\*.assignee_user.avatar_s3_url | string | | |
action_result.data.\*.assignee_user.can_share_intelligence | boolean | | True False |
action_result.data.\*.assignee_user.email | string | | gita@verizon2.com |
action_result.data.\*.assignee_user.id | string | | 12 |
action_result.data.\*.assignee_user.is_active | boolean | | True False |
action_result.data.\*.assignee_user.is_readonly | boolean | | True False |
action_result.data.\*.assignee_user.must_change_password | boolean | | True False |
action_result.data.\*.assignee_user.name | string | | |
action_result.data.\*.assignee_user.nickname | string | | |
action_result.data.\*.assignee_user.organization.id | string | | 6 |
action_result.data.\*.assignee_user.organization.name | string | | Verizon2 |
action_result.data.\*.assignee_user.organization.resource_uri | string | | /api/v1/userorganization/6/ |
action_result.data.\*.assignee_user.resource_uri | string | | /api/v1/user/12/ |
action_result.data.\*.assignee_user_id | string | | |
action_result.data.\*.assignee_user_name | string | | |
action_result.data.\*.association_info.\*.comment | string | | |
action_result.data.\*.association_info.\*.created | string | | 2021-04-09T07:44:13.750043 |
action_result.data.\*.association_info.\*.from_id | string | | 10940 |
action_result.data.\*.association_info.\*.remote_api | boolean | | True False |
action_result.data.\*.body_content_type | string | | markdown |
action_result.data.\*.campaign | string | | |
action_result.data.\*.can_add_public_tags | boolean | | True False |
action_result.data.\*.circles.\*.anonymous_sharing | boolean | | True False |
action_result.data.\*.circles.\*.can_edit | boolean | | True False |
action_result.data.\*.circles.\*.can_invite | boolean | | True False |
action_result.data.\*.circles.\*.can_override_confidence | boolean | | True False |
action_result.data.\*.circles.\*.description | string | | For testing... |
action_result.data.\*.circles.\*.disable_vendor_emails | string | | |
action_result.data.\*.circles.\*.id | string | | 10019 |
action_result.data.\*.circles.\*.is_freemium | boolean | | True False |
action_result.data.\*.circles.\*.mattermost_team_id | string | | |
action_result.data.\*.circles.\*.member | boolean | | True False |
action_result.data.\*.circles.\*.name | string | | test circle local |
action_result.data.\*.circles.\*.num_administrators | numeric | | 1 |
action_result.data.\*.circles.\*.num_members | numeric | | 1 |
action_result.data.\*.circles.\*.openinvite | boolean | | True False |
action_result.data.\*.circles.\*.pending | boolean | | True False |
action_result.data.\*.circles.\*.public | boolean | | True False |
action_result.data.\*.circles.\*.remote_api | boolean | | True False |
action_result.data.\*.circles.\*.resource_uri | string | | /api/v1/trustedcircle/10019/?remote_api=true |
action_result.data.\*.circles.\*.restricted_publishing | boolean | | True False |
action_result.data.\*.circles.\*.subscription_model | string | | |
action_result.data.\*.circles.\*.use_chat | boolean | | True False |
action_result.data.\*.circles.\*.validate_subscriptions | boolean | | True False |
action_result.data.\*.confidence | numeric | | 70 |
action_result.data.\*.country | string | | |
action_result.data.\*.created_by | string | `email` | test@testuser.com |
action_result.data.\*.created_ts | string | | 2021-04-09T06:45:23.627 2021-04-13T06:44:32.259632 |
action_result.data.\*.description | string | | |
action_result.data.\*.end_date | string | | |
action_result.data.\*.expiration_ts | string | | 2021-06-21T14:30:03.799 |
action_result.data.\*.feed_id | numeric | | 0 |
action_result.data.\*.id | numeric | `threatstream actor id` `threatstream campaign id` `threatstream incident id` `threatstream vulnerability id` `threatstream ttp id` `threatstream threatbulletin id` `threatstream signature id` | 27933 |
action_result.data.\*.import_session_id | numeric | | 1000000024 |
action_result.data.\*.import_source | string | | |
action_result.data.\*.ip | string | `ip` | |
action_result.data.\*.is_anonymous | boolean | | True False |
action_result.data.\*.is_category | boolean | | True False |
action_result.data.\*.is_cloneable | string | | yes |
action_result.data.\*.is_editable | boolean | | True False |
action_result.data.\*.is_email | boolean | | True False |
action_result.data.\*.is_mitre | boolean | | True False |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.is_system | boolean | | True False |
action_result.data.\*.itype | string | | mal_email |
action_result.data.\*.latitude | string | | |
action_result.data.\*.longitude | string | | |
action_result.data.\*.meta.detail2 | string | | imported by user 136 |
action_result.data.\*.meta.severity | string | | low |
action_result.data.\*.modified_ts | string | | 2021-04-09T06:45:37.010 |
action_result.data.\*.name | string | | xyztest7 |
action_result.data.\*.objective | string | | |
action_result.data.\*.org | string | | |
action_result.data.\*.organization_id | numeric | | 67 |
action_result.data.\*.original_source | string | | |
action_result.data.\*.original_source_id | string | | |
action_result.data.\*.owner_org.id | string | | 67 |
action_result.data.\*.owner_org.name | string | | test.qa.com |
action_result.data.\*.owner_org.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.owner_org_id | numeric | | 67 |
action_result.data.\*.owner_org_name | string | | qa.test.com |
action_result.data.\*.owner_organization_id | numeric | | 67 |
action_result.data.\*.owner_user.avatar_s3_url | string | | |
action_result.data.\*.owner_user.can_share_intelligence | boolean | | True False |
action_result.data.\*.owner_user.email | string | | testuser2@qa.user.com |
action_result.data.\*.owner_user.id | string | | 136 |
action_result.data.\*.owner_user.is_active | boolean | | True False |
action_result.data.\*.owner_user.is_readonly | boolean | | True False |
action_result.data.\*.owner_user.must_change_password | boolean | | True False |
action_result.data.\*.owner_user.name | string | | testuser2 |
action_result.data.\*.owner_user.nickname | string | | |
action_result.data.\*.owner_user.organization.id | string | | 67 |
action_result.data.\*.owner_user.organization.name | string | | qa.user.com |
action_result.data.\*.owner_user.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.owner_user.resource_uri | string | | /api/v1/user/136/ |
action_result.data.\*.owner_user_id | numeric | | 136 |
action_result.data.\*.owner_user_name | string | | testuser2 |
action_result.data.\*.parent | string | | |
action_result.data.\*.publication_status | string | | review_requested |
action_result.data.\*.published_ts | string | | |
action_result.data.\*.rdns | string | | |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_uri | string | | /api/v1/vulnerability/27933/?remote_api=true |
action_result.data.\*.retina_confidence | numeric | | -1 |
action_result.data.\*.s_type | string | | Suricata |
action_result.data.\*.sort | string | | 232202446 |
action_result.data.\*.source | string | `email` | test@testuser.com |
action_result.data.\*.source_created | string | | 2019-04-10T10:10:55 |
action_result.data.\*.source_modified | string | | |
action_result.data.\*.source_reported_confidence | numeric | | -1 |
action_result.data.\*.starred_by_me | boolean | | True False |
action_result.data.\*.starred_total_count | numeric | | 0 |
action_result.data.\*.start_date | string | | |
action_result.data.\*.status | string | | active |
action_result.data.\*.status.display_name | string | | New |
action_result.data.\*.status.id | numeric | | 1 |
action_result.data.\*.status.resource_uri | string | | /api/v1/incidentstatustype/1/ |
action_result.data.\*.subtype | string | | |
action_result.data.\*.tags | string | | testing |
action_result.data.\*.tags.\*.id | string | | vjw |
action_result.data.\*.tags.\*.name | string | | test name |
action_result.data.\*.tags.\*.org_id | numeric | | 67 |
action_result.data.\*.tags.\*.remote_api | boolean | | True False |
action_result.data.\*.tags.\*.source_user_id | string | | 1234 |
action_result.data.\*.tags.\*.tlp | string | | red |
action_result.data.\*.tags_v2.\*.id | string | | 6pd |
action_result.data.\*.tags_v2.\*.name | string | | test |
action_result.data.\*.tags_v2.\*.org_id | numeric | | 67 |
action_result.data.\*.tags_v2.\*.remote_api | boolean | | True False |
action_result.data.\*.tags_v2.\*.tlp | string | | white |
action_result.data.\*.threat_actor | string | | |
action_result.data.\*.threat_type | string | | malware |
action_result.data.\*.threatscore | numeric | | 14 |
action_result.data.\*.tlp | string | | white |
action_result.data.\*.trusted_circle_ids | string | | |
action_result.data.\*.ttp | string | | |
action_result.data.\*.type | string | | email |
action_result.data.\*.update_id | string | | 335089 |
action_result.data.\*.uuid | string | | fb24da3a-429a-49f9-a409-95dcf8752447 |
action_result.data.\*.value | string | `email` `ip` `sha256` | mailabc@xyz.com |
action_result.data.\*.votes.me | string | | |
action_result.data.\*.votes.total | numeric | | 0 |
action_result.data.\*.watched_by_me | boolean | | True False |
action_result.data.\*.watched_total_count | numeric | | 0 |
action_result.summary.associations_returned | numeric | | 2 |
action_result.summary.threat_bulletin_observables_returned | numeric | | 4 |
action_result.message | string | | Associations returned: 4 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create rule'

Creates a new rule in Threatstream

Type: **generic** <br>
Read only: **False**

<li> In the field param, tags, actors, malware, campaigns, incidents, signature, tips, ttps, vulnerabilities accepts list of IDs as an example: {“incidents”: [1000000001], “actors”: [1000000001], “vulnerabilities”: [1000000001, 1000000002], “campaigns”: [1000000001], “signatures”: [1000000001], “tags”: [{“name”:“test_tag”,“tlp”:“white”}], “match_impacts”: [ “actor_ip”, “actor_ipv6” ]} </li> <li> In field param, at least one Match Within parameter (match_observables, match_reportedfiles, match_signatures, match_tips, or match_vulnerabilities) should be true. Otherwise, the action will pass and a rule will be created but it will throw an error while updating it from the UI. </li> <li>Do not specify values for both match_impacts and exclude_impacts in the same request. Indicator types specified in match_impacts are filtered out if also specified in exclude_impacts.</li>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Name of the rule | string | |
**keywords** | required | List of keywords for which you want the rule to match. i.e ["keyword1", "keyword2"] | string | |
**fields** | optional | JSON formatted string of fields to include with the rule | string | |
**create_on_cloud** | optional | Create on remote (cloud)? (applicable only for hybrid on-prem instances) | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.create_on_cloud | boolean | | False True |
action_result.parameter.fields | string | | { "actors": [ 1000000001 ], "vulnerabilities": [ 1000000001 ], "campaigns": [ 1000000001 ], "tags": [ "test", "tag1" ], "match_impacts": [ "actor_ip", "actor_ipv6" ] } |
action_result.parameter.keywords | string | | key1, testing |
action_result.parameter.name | string | | test name |
action_result.data.\*.actors.\*.id | string | `threatstream actor id` | 1000000001 |
action_result.data.\*.actors.\*.name | string | | local actor01 |
action_result.data.\*.actors.\*.remote_api | boolean | | True False |
action_result.data.\*.actors.\*.resource_uri | string | | /api/v1/actor/1000000001/ |
action_result.data.\*.campaigns.\*.id | string | `threatstream campaign id` | 1000000001 |
action_result.data.\*.campaigns.\*.name | string | | testing for common action create campaign on prem |
action_result.data.\*.campaigns.\*.remote_api | boolean | | True False |
action_result.data.\*.campaigns.\*.resource_uri | string | | /api/v1/campaign/1000000001/ |
action_result.data.\*.create_investigation | boolean | | False True |
action_result.data.\*.created_ts | string | | 2021-04-01T12:06:14.296703 |
action_result.data.\*.exclude_notify_org_whitelisted | boolean | | True False |
action_result.data.\*.exclude_notify_owner_org | boolean | | True False |
action_result.data.\*.id | numeric | `threatstream rule id` | 1000000026 |
action_result.data.\*.investigation | string | | |
action_result.data.\*.is_editable | boolean | | True False |
action_result.data.\*.is_enabled | boolean | | True False |
action_result.data.\*.keyword | string | | key1, testing |
action_result.data.\*.keywords | string | | testing |
action_result.data.\*.match_actors | boolean | | True False |
action_result.data.\*.match_campaigns | boolean | | True False |
action_result.data.\*.match_impact | string | | actor_ipv6 |
action_result.data.\*.match_incidents | boolean | | True False |
action_result.data.\*.match_malware | boolean | | True False |
action_result.data.\*.match_observables | boolean | | True False |
action_result.data.\*.match_reportedfiles | boolean | | True False |
action_result.data.\*.match_signatures | boolean | | True False |
action_result.data.\*.match_tips | boolean | | True False |
action_result.data.\*.match_ttps | boolean | | True False |
action_result.data.\*.match_vulnerabilities | boolean | | True False |
action_result.data.\*.matches | numeric | | 0 |
action_result.data.\*.modified_ts | string | | 2021-04-01T12:06:14.296721 |
action_result.data.\*.name | string | | test0 |
action_result.data.\*.notify_me | boolean | | True False |
action_result.data.\*.org_id | numeric | | 67 |
action_result.data.\*.org_shared | boolean | | False True |
action_result.data.\*.organization.id | string | | 67 |
action_result.data.\*.organization.name | string | | test.org.com |
action_result.data.\*.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_uri | string | | /api/v1/rule/1000000026/ |
action_result.data.\*.tags | string | | tag1 |
action_result.data.\*.tags.\*.name | string | | test |
action_result.data.\*.tags.\*.remote_api | boolean | | True False |
action_result.data.\*.tags.\*.tlp | string | | white |
action_result.data.\*.user.avatar_s3_url | string | | |
action_result.data.\*.user.can_share_intelligence | boolean | | True False |
action_result.data.\*.user.email | string | `email` | test@testuser.com |
action_result.data.\*.user.id | string | | 136 |
action_result.data.\*.user.is_active | boolean | | True False |
action_result.data.\*.user.is_readonly | boolean | | True False |
action_result.data.\*.user.must_change_password | boolean | | False True |
action_result.data.\*.user.name | string | | testuser2 |
action_result.data.\*.user.nickname | string | | |
action_result.data.\*.user.organization.id | string | | 67 |
action_result.data.\*.user.organization.name | string | | test.org.com |
action_result.data.\*.user.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.user.resource_uri | string | | /api/v1/user/136/ |
action_result.data.\*.user_id | numeric | | 136 |
action_result.data.\*.vulnerabilities.\*.id | string | `threatstream vulnerability id` | 1000000001 |
action_result.data.\*.vulnerabilities.\*.name | string | | test_vulnerability |
action_result.data.\*.vulnerabilities.\*.remote_api | boolean | | True False |
action_result.data.\*.vulnerabilities.\*.resource_uri | string | | /api/v1/vulnerability/1000000001/ |
action_result.summary.id | numeric | | 1000000026 |
action_result.summary.message | string | | Rule is created successfully |
action_result.message | string | | Rule is created successfully |
summary.message | numeric | | 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update rule'

Update a rule in ThreatStream by ID number

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**fields** | required | JSON formatted string of fields to update on the incident | string | |
**rule_id** | required | ID number of rule to update | string | `threatstream rule id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.fields | string | | { "actors": [ ], "vulnerabilities": [ ], "match_observables": True, "match_reportedfiles": False, "match_signatures": True, "match_tips": True, "match_vulnerabilities": True, "tags": [ "test", "tag1" ], "create_investigation": True, "match_impacts": [ "actor_ip", "actor_ipv6" ], "exclude_notify_org_whitelisted": True, "exclude_notify_owner_org": True , "incidents": [1000000184], "ttps": [119]} |
action_result.parameter.rule_id | string | `threatstream rule id` | 1000000030 |
action_result.data.\*.actors.\*.id | string | `threatstream actor id` | 1000000001 |
action_result.data.\*.actors.\*.name | string | | local actor01 |
action_result.data.\*.actors.\*.remote_api | boolean | | True |
action_result.data.\*.actors.\*.resource_uri | string | | /api/v1/actor/1000000001/ |
action_result.data.\*.campaigns.\*.id | string | `threatstream campaign id` | 1000000001 |
action_result.data.\*.campaigns.\*.name | string | | testing for common action create campaign on prem |
action_result.data.\*.campaigns.\*.remote_api | boolean | | True |
action_result.data.\*.campaigns.\*.resource_uri | string | | /api/v1/campaign/1000000001/ |
action_result.data.\*.create_investigation | boolean | | True False |
action_result.data.\*.created_ts | string | | 2021-04-01T12:24:18.067618 |
action_result.data.\*.exclude_notify_org_whitelisted | boolean | | True False |
action_result.data.\*.exclude_notify_owner_org | boolean | | True False |
action_result.data.\*.id | numeric | `threatstream rule id` | 1000000030 |
action_result.data.\*.incidents.\*.id | string | `threatstream incident id` | 1000000184 |
action_result.data.\*.incidents.\*.name | string | | Test incident name |
action_result.data.\*.incidents.\*.remote_api | boolean | | True |
action_result.data.\*.incidents.\*.resource_uri | string | | /api/v1/incident/1000000184/ |
action_result.data.\*.investigation | string | | |
action_result.data.\*.investigation.id | string | | 1000000005 |
action_result.data.\*.investigation.name | string | | Matched Rule [key, key1] by test.org.com |
action_result.data.\*.investigation.resource_uri | string | | /api/v1/investigation/1000000005/ |
action_result.data.\*.is_editable | boolean | | True |
action_result.data.\*.is_enabled | boolean | | True |
action_result.data.\*.keyword | string | | key1, testing |
action_result.data.\*.keywords | string | | testing |
action_result.data.\*.match_actors | boolean | | True False |
action_result.data.\*.match_campaigns | boolean | | True False |
action_result.data.\*.match_impact | string | | actor_ip |
action_result.data.\*.match_impacts | string | | actor_ipv6 |
action_result.data.\*.match_incidents | boolean | | True False |
action_result.data.\*.match_malware | boolean | | False |
action_result.data.\*.match_observables | boolean | | True False |
action_result.data.\*.match_reportedfiles | boolean | | False True |
action_result.data.\*.match_signatures | boolean | | True False |
action_result.data.\*.match_tips | boolean | | True False |
action_result.data.\*.match_ttps | boolean | | True False |
action_result.data.\*.match_vulnerabilities | boolean | | True False |
action_result.data.\*.matches | numeric | | 0 |
action_result.data.\*.modified_ts | string | | 2021-04-05T08:16:23.916064 |
action_result.data.\*.name | string | | test4 |
action_result.data.\*.notify_me | boolean | | True |
action_result.data.\*.org_id | numeric | | 67 |
action_result.data.\*.org_shared | boolean | | False True |
action_result.data.\*.organization.id | string | | 67 |
action_result.data.\*.organization.name | string | | test.org.com |
action_result.data.\*.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.remote_api | boolean | | True |
action_result.data.\*.resource_uri | string | | /api/v1/rule/1000000030/ |
action_result.data.\*.tags | string | | tag1 |
action_result.data.\*.tags.\*.name | string | | test |
action_result.data.\*.tags.\*.remote_api | boolean | | True False |
action_result.data.\*.tags.\*.tlp | string | | white |
action_result.data.\*.ttps.\*.id | string | `threatstream ttp id` | 119 |
action_result.data.\*.ttps.\*.name | string | | Deplete Resources [CAPEC 119] |
action_result.data.\*.ttps.\*.resource_uri | string | | /api/v1/ttp/119/ |
action_result.data.\*.user.avatar_s3_url | string | | |
action_result.data.\*.user.can_share_intelligence | boolean | | True False |
action_result.data.\*.user.email | string | `email` | test@testuser.com |
action_result.data.\*.user.id | string | | 136 |
action_result.data.\*.user.is_active | boolean | | True False |
action_result.data.\*.user.is_readonly | boolean | | False True |
action_result.data.\*.user.must_change_password | boolean | | False True |
action_result.data.\*.user.name | string | | testuser2 |
action_result.data.\*.user.nickname | string | | |
action_result.data.\*.user.organization.id | string | | 67 |
action_result.data.\*.user.organization.name | string | | test.org.com |
action_result.data.\*.user.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.user.resource_uri | string | | /api/v1/user/136/ |
action_result.data.\*.user_id | numeric | | 136 |
action_result.data.\*.vulnerabilities.\*.id | string | `threatstream vulnerability id` | 1000000001 |
action_result.data.\*.vulnerabilities.\*.name | string | | test_vulnerability |
action_result.data.\*.vulnerabilities.\*.remote_api | boolean | | True |
action_result.data.\*.vulnerabilities.\*.resource_uri | string | | /api/v1/vulnerability/1000000001/ |
action_result.summary | string | | |
action_result.summary.id | numeric | | 1000000033 |
action_result.summary.message | string | | Successfully updated rule |
action_result.message | string | | Successfully updated rule |
summary.message | numeric | | 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list rules'

List rules present in ThreatStream

Type: **investigate** <br>
Read only: **True**

<ul><li>The rules will be listed in the latest first order on the basis of created_ts.</li><li>If the limit parameter is not provided, then the default value (1000) will be considered as the value of the limit parameter.</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**limit** | optional | Total number of rules to return | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 10 1000 |
action_result.data.\*.create_investigation | boolean | | False True |
action_result.data.\*.created_ts | string | | 2021-04-09T08:27:04.162790 |
action_result.data.\*.exclude_notify_org_whitelisted | boolean | | False True |
action_result.data.\*.exclude_notify_owner_org | boolean | | False True |
action_result.data.\*.has_associations | boolean | | True False |
action_result.data.\*.id | numeric | `threatstream rule id` | 1000000036 |
action_result.data.\*.investigation | string | | |
action_result.data.\*.investigation.id | string | | 1000000005 |
action_result.data.\*.investigation.name | string | | Matched Rule [key, key1] by test.org.com |
action_result.data.\*.investigation.resource_uri | string | | /api/v1/investigation/1000000005/ |
action_result.data.\*.is_editable | boolean | | True False |
action_result.data.\*.is_enabled | boolean | | True False |
action_result.data.\*.keyword | string | | key5,key6 |
action_result.data.\*.keywords | string | | testRule |
action_result.data.\*.match_actors | boolean | | True False |
action_result.data.\*.match_campaigns | boolean | | True False |
action_result.data.\*.match_incidents | boolean | | True False |
action_result.data.\*.match_malware | boolean | | False True |
action_result.data.\*.match_observables | boolean | | True False |
action_result.data.\*.match_reportedfiles | boolean | | False True |
action_result.data.\*.match_signatures | boolean | | False True |
action_result.data.\*.match_tips | boolean | | False True |
action_result.data.\*.match_ttps | boolean | | True False |
action_result.data.\*.match_vulnerabilities | boolean | | False True |
action_result.data.\*.matches | numeric | | 0 |
action_result.data.\*.modified_ts | string | | 2021-04-09T11:19:56.898430 |
action_result.data.\*.name | string | | tetsting1 |
action_result.data.\*.notify_me | boolean | | True False |
action_result.data.\*.org_id | numeric | | 67 |
action_result.data.\*.org_shared | boolean | | False True |
action_result.data.\*.organization.id | string | | 67 |
action_result.data.\*.organization.name | string | | test.org.com |
action_result.data.\*.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_uri | string | | /api/v1/rule/1000000036/ |
action_result.data.\*.tags | string | | tag1 |
action_result.data.\*.tags.\*.name | string | | test |
action_result.data.\*.tags.\*.remote_api | boolean | | True False |
action_result.data.\*.tags.\*.tlp | string | | white |
action_result.data.\*.user.avatar_s3_url | string | | |
action_result.data.\*.user.can_share_intelligence | boolean | | True False |
action_result.data.\*.user.email | string | `email` | test@testuser.com |
action_result.data.\*.user.id | string | | 136 |
action_result.data.\*.user.is_active | boolean | | True False |
action_result.data.\*.user.is_readonly | boolean | | False True |
action_result.data.\*.user.must_change_password | boolean | | False True |
action_result.data.\*.user.name | string | | testuser2 |
action_result.data.\*.user.nickname | string | | |
action_result.data.\*.user.organization.id | string | | 67 |
action_result.data.\*.user.organization.name | string | | test.org.com |
action_result.data.\*.user.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.user.resource_uri | string | | /api/v1/user/136/ |
action_result.data.\*.user_id | numeric | | 136 |
action_result.summary.rules_returned | numeric | | 22 |
action_result.message | string | | Rules returned: 22 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete rule'

Delete rule in ThreatStream by ID number

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**rule_id** | required | ID number of rule to delete | string | `threatstream rule id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.rule_id | string | `threatstream rule id` | 15518 1000000030 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully deleted rule |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add association'

Create associations between threat model entities on the ThreatStream platform

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity_type** | required | The type of the threat model entity on which want to add the association | string | |
**entity_id** | required | The ID of the threat model entity on which want to add the association | numeric | `threatstream actor id` `threatstream campaign id` `threatstream incident id` `threatstream vulnerability id` `threatstream ttp id` `threatstream threatbulletin id` `threatstream signature id` |
**associated_entity_type** | required | The type of threat model entity which will associate the initial entity | string | |
**local_ids** | optional | Comma-separated list of local entity IDs to associate with the entity (this will appends on the existing) | string | `threatstream actor id` `threatstream campaign id` `threatstream incident id` `threatstream vulnerability id` `threatstream ttp id` `threatstream threatbulletin id` `threatstream signature id` `threatstream intelligence id` |
**remote_ids** | optional | Comma-separated list of remote enitity IDs to associate with the entity (this will appends on the existing) | string | `threatstream actor id` `threatstream campaign id` `threatstream incident id` `threatstream vulnerability id` `threatstream ttp id` `threatstream threatbulletin id` `threatstream signature id` `threatstream intelligence id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.associated_entity_type | string | | actor |
action_result.parameter.entity_id | numeric | `threatstream actor id` `threatstream campaign id` `threatstream incident id` `threatstream vulnerability id` `threatstream ttp id` `threatstream threatbulletin id` `threatstream signature id` | 10911 |
action_result.parameter.entity_type | string | | tipreport |
action_result.parameter.local_ids | string | `threatstream actor id` `threatstream campaign id` `threatstream incident id` `threatstream vulnerability id` `threatstream ttp id` `threatstream threatbulletin id` `threatstream signature id` `threatstream intelligence id` | 1000000006 |
action_result.parameter.remote_ids | string | `threatstream actor id` `threatstream campaign id` `threatstream incident id` `threatstream vulnerability id` `threatstream ttp id` `threatstream threatbulletin id` `threatstream signature id` `threatstream intelligence id` | 11783 |
action_result.data.\* | string | `threatstream actor id` `threatstream campaign id` `threatstream incident id` `threatstream vulnerability id` `threatstream ttp id` `threatstream threatbulletin id` `threatstream signature id` | 11783 |
action_result.summary | string | | |
action_result.message | string | | Successfully updated associations. Modified entities : 10909. Please check for the non-modified ids as they would be already associated or invalid |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.ph | ph | | |

## action: 'remove association'

Remove associations between threat model entities on the ThreatStream platform

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity_type** | required | Type of threat model entity from which you are removing the association | string | |
**entity_id** | required | ID of the threat model entity from which you are removing the association | numeric | `threatstream actor id` `threatstream campaign id` `threatstream incident id` `threatstream vulnerability id` `threatstream ttp id` `threatstream threatbulletin id` `threatstream signature id` |
**associated_entity_type** | required | Type of threat model entity with which you are associating the initial entity | string | |
**local_ids** | optional | Comma-separated list of local enitity IDs to associate with the entity - Note that this appends | string | `threatstream actor id` `threatstream campaign id` `threatstream incident id` `threatstream vulnerability id` `threatstream ttp id` `threatstream threatbulletin id` `threatstream signature id` `threatstream intelligence id` |
**remote_ids** | optional | Comma-separated list of remote enitity IDs to associate with the entity - Note that this appends | string | `threatstream actor id` `threatstream campaign id` `threatstream incident id` `threatstream vulnerability id` `threatstream ttp id` `threatstream threatbulletin id` `threatstream signature id` `threatstream intelligence id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.associated_entity_type | string | | actor |
action_result.parameter.entity_id | numeric | `threatstream actor id` `threatstream campaign id` `threatstream incident id` `threatstream vulnerability id` `threatstream ttp id` `threatstream threatbulletin id` `threatstream signature id` | 10911 |
action_result.parameter.entity_type | string | | tipreport |
action_result.parameter.local_ids | string | `threatstream actor id` `threatstream campaign id` `threatstream incident id` `threatstream vulnerability id` `threatstream ttp id` `threatstream threatbulletin id` `threatstream signature id` `threatstream intelligence id` | 1000000006 |
action_result.parameter.remote_ids | string | `threatstream actor id` `threatstream campaign id` `threatstream incident id` `threatstream vulnerability id` `threatstream ttp id` `threatstream threatbulletin id` `threatstream signature id` `threatstream intelligence id` | 11783 |
action_result.data.\* | string | `threatstream actor id` `threatstream campaign id` `threatstream incident id` `threatstream vulnerability id` `threatstream ttp id` `threatstream threatbulletin id` `threatstream signature id` | 11783 |
action_result.summary | string | | |
action_result.message | string | | Successfully updated associations. Modified entities : 10909. Please check for the non-modified ids as they would be already associated or invalid |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.ph | ph | | |

## action: 'list actors'

List actors present in ThreatStream

Type: **investigate** <br>
Read only: **True**

<ul><li>The actors will be listed in the latest first order on the basis of created_ts.</li><li>If the limit parameter is not provided, then the default value (1000) will be considered as the value of the limit parameter.</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**limit** | optional | Total number of actors to return | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 1000 1 |
action_result.data.\*.aliases.\*.name | string | | testin |
action_result.data.\*.assignee_user | string | | |
action_result.data.\*.can_add_public_tags | boolean | | True False |
action_result.data.\*.circles.\*.id | numeric | | 10022 |
action_result.data.\*.circles.\*.name | string | | test circle 4 |
action_result.data.\*.created_ts | string | | 2021-04-08T13:04:00.932459 2021-04-20T08:39:20.368888+00:00 |
action_result.data.\*.end_date | string | | |
action_result.data.\*.feed_id | numeric | | 0 |
action_result.data.\*.id | numeric | `threatstream actor id` | 11795 11930 |
action_result.data.\*.is_anonymous | boolean | | False True |
action_result.data.\*.is_cloneable | string | | yes |
action_result.data.\*.is_email | string | | |
action_result.data.\*.is_public | boolean | | False True |
action_result.data.\*.is_team | boolean | | False True |
action_result.data.\*.model_type | string | | actor |
action_result.data.\*.modified_ts | string | | 2021-04-23T08:42:51.176628+00:00 |
action_result.data.\*.name | string | | actor_test_2 |
action_result.data.\*.organization.id | numeric | | 70 |
action_result.data.\*.organization.title | string | | test title |
action_result.data.\*.organization_id | numeric | | 70 |
action_result.data.\*.owner_user.email | string | `email` | useremail@test.com |
action_result.data.\*.owner_user.id | numeric | | 142 |
action_result.data.\*.owner_user.name | string | | matt |
action_result.data.\*.owner_user_id | numeric | | 142 |
action_result.data.\*.primary_motivation | string | | |
action_result.data.\*.publication_status | string | | new reviewed |
action_result.data.\*.published_ts | string | | |
action_result.data.\*.resource_level | string | | |
action_result.data.\*.resource_uri | string | | /api/v1/actor/11930/ |
action_result.data.\*.sort | string | | actor-11930 |
action_result.data.\*.source_created | string | | 2019-04-10T10:10:00+00:00 |
action_result.data.\*.source_modified | string | | 2019-05-19T10:15:00+00:00 |
action_result.data.\*.start_date | string | | 2019-06-05T04:15:00+00:00 |
action_result.data.\*.status | string | | |
action_result.data.\*.tags | string | | aliases:TA505 (BAE Systems) |
action_result.data.\*.tags.\*.id | string | | bwf |
action_result.data.\*.tags.\*.name | string | | testing |
action_result.data.\*.tags.\*.org_id | numeric | | 70 |
action_result.data.\*.tags.\*.tlp | string | | white |
action_result.data.\*.tags_v2.\*.id | string | | afk |
action_result.data.\*.tags_v2.\*.name | string | | Remote Origin |
action_result.data.\*.tags_v2.\*.org_id | numeric | | 70 |
action_result.data.\*.tags_v2.\*.tlp | string | | red |
action_result.data.\*.tlp | string | | amber |
action_result.data.\*.type | string | | competitor |
action_result.data.\*.uuid | string | | 4681da86-ac0a-4d21-bd3f-156904886f66 b58939d4-21b0-427b-bb62-6dc42391bef0 |
action_result.summary.actors_returned | numeric | | 13 1 |
action_result.message | string | | Actors returned: 13 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list imports'

List imports present in ThreatStream

Type: **investigate** <br>
Read only: **True**

<ul><li>The imports will be listed in the latest first order on the basis of created_ts.</li><li>If the limit parameter is not provided, then the default value (1000) will be considered as the value of the limit parameter.</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**limit** | optional | Total number of imports to return | numeric | |
**status** | optional | Status of imports | string | |
**list_from_remote** | optional | List from remote? (applicable only for hybrid on-prem instances) | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 100 |
action_result.parameter.list_from_remote | boolean | | True False |
action_result.parameter.status | string | | |
action_result.data.\*.confidence | numeric | | 100 |
action_result.data.\*.data | string | | {u'remote_malware': [], u'signatures': [], u'remote_tipreports': [], u'intrusionsets': [], u'classification': u'public', u'comment_ip_addr': u'52.52.79.127', u'infrastructure': [], u'url_mapping': None, u'identities': [], u'datatext': u'4.63.2.45', u'remote_vulnerabilities': [], u'md5_mapping': None, u'malware': [], u'benign_is_public': False, u'tools': [], u'email_mapping': None, u'source': u'Analyst', u'remote_intrusionsets': [], u'actors': [], u'remote_infrastructure': [], u'remote_attackpatterns': [], u'tipreports': [], u'domain_mapping': None, u'circles': [], u'ipv6_mapping': None, u'attackpatterns': [], u'courseofaction': [], u'confidence': u'100', u'ip_mapping': u'mal_ip', u'campaigns': [], u'remote_ttps': [], u'customtms': [], u'reject_benign': True, u'remote_identities': [], u'remote_campaigns': [], u'remote_tools': [], u'ttps': [], u'remote_courseofaction': [], u'incidents': [], u'vulnerabilities': [], u'remote_customtms': [], u'remote_incidents': [], u'remote_signatures': [], u'remote_actors': []} |
action_result.data.\*.date | string | | 2021-04-08T10:48:12.610620 |
action_result.data.\*.date_modified | string | | 2021-04-08T10:48:12.793995 |
action_result.data.\*.expiration_ts | string | | 2021-07-07T10:48:12.609350 |
action_result.data.\*.fileName | string | `sha1` `url` | |
action_result.data.\*.fileType | string | | analyst |
action_result.data.\*.file_name_label | string | | |
action_result.data.\*.id | numeric | `threatstream import session id` | 1161 |
action_result.data.\*.intelligence_source | string | `sha1` `url` | |
action_result.data.\*.is_anonymous | boolean | | True False |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.jobID | string | | |
action_result.data.\*.messages | string | | |
action_result.data.\*.notes | string | | |
action_result.data.\*.numIndicators | numeric | | 1 |
action_result.data.\*.numRejected | numeric | | 0 |
action_result.data.\*.num_private | numeric | | 0 |
action_result.data.\*.num_public | numeric | | 0 |
action_result.data.\*.orginal_intelligence | string | | |
action_result.data.\*.processed_ts | string | | 2021-04-08T10:48:12.796620 |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_uri | string | | /api/v1/import/1161/?remote_api=true |
action_result.data.\*.source_confidence_weight | numeric | | 0 |
action_result.data.\*.status | string | | done |
action_result.data.\*.tags | string | | |
action_result.data.\*.threat_type | string | | |
action_result.data.\*.tlp | string | | |
action_result.data.\*.visibleForReview | boolean | | True False |
action_result.summary.import_returned | numeric | | 100 |
action_result.message | string | | Import returned: 100 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create vulnerability'

Create a vulnerability in ThreatStream

Type: **generic** <br>
Read only: **False**

<ul><li>The "is_public" parameter can not be set as "true" if the "create_on_cloud" parameter is "false" for hybride on-prem instances.</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Name to give the vulnerability | string | |
**fields** | optional | JSON formatted string of fields to include with the vulnerability | string | |
**local_intelligence** | optional | Comma-separated list of local intelligence IDs to associate with the vulnerability - Note that this appends | string | `threatstream intelligence id` |
**cloud_intelligence** | optional | Comma-separated list of remote intelligence IDs to associate with the vulnerability - Note that this appends | string | `threatstream intelligence id` |
**comment** | optional | Comment to give the vulnerability (JSON format containing body, title, etc.) | string | |
**attachment** | optional | Vault id of an attachment to add on the vulnerability | string | `vault id` `sha1` |
**is_public** | optional | Classification designation | boolean | |
**create_on_cloud** | optional | Create on remote (cloud)? (applicable only for hybrid on-prem instances) | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.attachment | string | `vault id` `sha1` | b10e56af7aed0446e7c87d495700118787212378 |
action_result.parameter.cloud_intelligence | string | `threatstream intelligence id` | 232202446 |
action_result.parameter.comment | string | | {"title": "comment title", "body": "This is a comment."} |
action_result.parameter.create_on_cloud | boolean | | True False |
action_result.parameter.fields | string | | {'circles': [10025, 10022], 'campaigns': [218680], 'incidents': [171066], 'vulnerability': [29891], 'signatures': [632], 'ttps': [1573], 'description': 'for analysis','comments': ['this', 'is comment'],'is_system': True, 'publication_status': 'reviewed', 'source': 'from action','source_created': '2019-04-10T10:10:55','source_modified': '2019-05-19T10:15:23','tags': ['testing', 'vulnerability'],'tlp': 'amber'} |
action_result.parameter.is_public | boolean | | True False |
action_result.parameter.local_intelligence | string | `threatstream intelligence id` | |
action_result.parameter.name | string | | abc_test_111 |
action_result.data.\*.aliases | string | | |
action_result.data.\*.assignee_user | string | | |
action_result.data.\*.attachment | string | | url |
action_result.data.\*.attachments.filename | string | | PDF_All%20valid_invalid.pdf |
action_result.data.\*.attachments.id | numeric | | 26649 |
action_result.data.\*.attachments.r_type | string | | A |
action_result.data.\*.attachments.remote_api | boolean | | True False |
action_result.data.\*.attachments.resource_uri | string | | /api/v1/vulnerabilityexternalreference/26649/?remote_api=true |
action_result.data.\*.attachments.s3_url | string | | https://test-optic.s3.user.com/userUploads/2021-05-27/20210527_133407_userId-136_69e3a3d6-b499-4ba1-b918-769a4b74463a_PDF_All20valid_invalid.pdf?Signature=uk%2FY5YOrBVwpxv0xs6sKvyXULrg%3D&Expires=1622126047&AWSAccessKeyId=AKIAQYUTUNAKSCAMMFFH |
action_result.data.\*.attachments.title | string | | PDF_All%20valid_invalid.pdf |
action_result.data.\*.attachments.url | string | | |
action_result.data.\*.body_content_type | string | | markdown |
action_result.data.\*.campaigns.\*.id | numeric | | 218680 |
action_result.data.\*.can_add_public_tags | boolean | | True False |
action_result.data.\*.circles.\*.id | string | | 10022 |
action_result.data.\*.circles.\*.name | string | | test circle 4 |
action_result.data.\*.circles.\*.resource_uri | string | | /api/v1/trustedcircle/10022/ |
action_result.data.\*.comment.!@#$%^ | string | | This is a comment. |
action_result.data.\*.comment.body | string | | This is a comment. |
action_result.data.\*.comment.created_ts | string | | 2021-04-20T09:02:34.945588 |
action_result.data.\*.comment.id | numeric | | 18 |
action_result.data.\*.comment.invalid | string | | comment title |
action_result.data.\*.comment.modified_ts | string | | 2021-04-20T09:02:34.945603 |
action_result.data.\*.comment.remote_api | boolean | | True False |
action_result.data.\*.comment.resource_uri | string | | /api/v1/vulnerability/30274/comment/18/ |
action_result.data.\*.comment.title | string | | comment title |
action_result.data.\*.comment.tlp | string | | |
action_result.data.\*.comment.user.avatar_s3_url | string | | |
action_result.data.\*.comment.user.can_share_intelligence | boolean | | True False |
action_result.data.\*.comment.user.email | string | `email` | test@test.com |
action_result.data.\*.comment.user.id | string | | 142 |
action_result.data.\*.comment.user.is_active | boolean | | True False |
action_result.data.\*.comment.user.is_readonly | boolean | | True False |
action_result.data.\*.comment.user.must_change_password | boolean | | True False |
action_result.data.\*.comment.user.name | string | | test |
action_result.data.\*.comment.user.nickname | string | | testnickname |
action_result.data.\*.comment.user.organization.id | string | | 70 |
action_result.data.\*.comment.user.organization.name | string | | test |
action_result.data.\*.comment.user.organization.resource_uri | string | | /api/v1/userorganization/70/ |
action_result.data.\*.comment.user.resource_uri | string | | /api/v1/user/142/ |
action_result.data.\*.comments | string | | is comment |
action_result.data.\*.created_ts | string | | 2021-04-20T09:02:33.703401 |
action_result.data.\*.cvss2_score | string | | |
action_result.data.\*.cvss3_score | string | | |
action_result.data.\*.description | string | | for analysis |
action_result.data.\*.embedded_content_type | string | | |
action_result.data.\*.embedded_content_url | string | | |
action_result.data.\*.feed_id | numeric | | 0 |
action_result.data.\*.id | numeric | | 30274 |
action_result.data.\*.incidents.\*.id | numeric | | 171066 |
action_result.data.\*.intelligence.\*.id | numeric | | 232202446 |
action_result.data.\*.is_anonymous | boolean | | True False |
action_result.data.\*.is_cloneable | string | | yes |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.is_system | boolean | | True False |
action_result.data.\*.logo_s3_url | string | | |
action_result.data.\*.mitre_cve_url | string | `url` | |
action_result.data.\*.modified_ts | string | | 2021-04-20T09:02:33.704376 |
action_result.data.\*.name | string | | abc_test_111 |
action_result.data.\*.organization.id | string | | 70 |
action_result.data.\*.organization.name | string | | test |
action_result.data.\*.organization.resource_uri | string | | /api/v1/userorganization/70/ |
action_result.data.\*.organization_id | numeric | | 70 |
action_result.data.\*.owner_user.email | string | `email` | test@test.com |
action_result.data.\*.owner_user.id | string | | 142 |
action_result.data.\*.owner_user.name | string | | test |
action_result.data.\*.owner_user.resource_uri | string | | /api/v1/user/142/ |
action_result.data.\*.owner_user_id | numeric | | 142 |
action_result.data.\*.parent | string | | |
action_result.data.\*.publication_status | string | | reviewed |
action_result.data.\*.published_ts | string | | |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_uri | string | | /api/v1/vulnerability/30274/ |
action_result.data.\*.signatures.\*.id | numeric | | 632 |
action_result.data.\*.source | string | | from action |
action_result.data.\*.source_created | string | | 2019-04-10T10:10:55 |
action_result.data.\*.source_modified | string | | 2019-05-19T10:15:23 |
action_result.data.\*.starred_by_me | boolean | | True False |
action_result.data.\*.starred_total_count | numeric | | 0 |
action_result.data.\*.tlp | string | | amber |
action_result.data.\*.ttps.\*.id | numeric | | 1573 |
action_result.data.\*.update_id | string | | |
action_result.data.\*.uuid | string | | fe06d084-a63b-4536-a748-3232ce650e85 |
action_result.data.\*.votes.me | string | | |
action_result.data.\*.votes.total | numeric | | 0 |
action_result.data.\*.vulnerability.\*.id | numeric | | 29891 |
action_result.data.\*.watched_by_me | boolean | | True False |
action_result.data.\*.watched_total_count | numeric | | 0 |
action_result.summary.created_on_cloud | boolean | | True False |
action_result.message | string | | Vulnerability created successfully. Associated intelligence : 232202446 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update vulnerability'

Update the vulnerability in ThreatStream

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | ID of the vulnerability | string | `threatstream vulnerability id` |
**fields** | optional | JSON formatted string of fields to include with the vulnerability | string | |
**local_intelligence** | optional | Comma-separated list of local intelligence IDs to associate with the vulnerability - Note that this appends | string | `threatstream intelligence id` |
**cloud_intelligence** | optional | Comma-separated list of remote intelligence IDs to associate with the vulnerability - Note that this appends | string | `threatstream intelligence id` |
**comment** | optional | Comment to give the vulnerability (JSON format containing body, title, etc.) | string | |
**attachment** | optional | Vault id of an attachment to add on the vulnerability | string | `vault id` `sha1` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.attachment | string | `vault id` `sha1` | b10e56af7aed0446e7c87d495700118787212378 |
action_result.parameter.cloud_intelligence | string | `threatstream intelligence id` | |
action_result.parameter.comment | string | | {"title": "comment title", "body": "This is a comment."} |
action_result.parameter.fields | string | | {'name': 'updated_test_111', 'circles': [10022], 'campaigns': [218680], 'incidents': [171066], 'vulnerability': [29891], 'signatures': [632], 'ttps': [1573], 'description': 'for analysis','is_system': True, 'publication_status': 'reviewed', 'source': 'from action','source_created': '2019-04-10T10:10:55','source_modified': '2019-05-19T10:15:23','tags': ['testing', 'vulnerability'],'tlp': 'red'} |
action_result.parameter.id | string | `threatstream vulnerability id` | 30274 |
action_result.parameter.local_intelligence | string | `threatstream intelligence id` | |
action_result.data.\*.aliases | string | | |
action_result.data.\*.assignee_user | string | | |
action_result.data.\*.attachment | string | | url |
action_result.data.\*.attachments.filename | string | | HTML%20-%20All%20valid_invalid.html |
action_result.data.\*.attachments.id | numeric | | 26653 |
action_result.data.\*.attachments.r_type | string | | A |
action_result.data.\*.attachments.remote_api | boolean | | True False |
action_result.data.\*.attachments.resource_uri | string | | /api/v1/vulnerabilityexternalreference/26653/?remote_api=true |
action_result.data.\*.attachments.s3_url | string | | https://test-optic.s3.user.com/userUploads/2021-05-27/20210527_133417_userId-136_2b5d20a5-4d12-4ff8-961c-847b5766440c_HTML20-20All20valid_invalid.html?Signature=Ymp0ntZu5HNAuoK9%2FCVPE6x3Dqw%3D&Expires=1622126057&AWSAccessKeyId=AKIAQYUTUNAKSCAMMFFH |
action_result.data.\*.attachments.title | string | | HTML%20-%20All%20valid_invalid.html |
action_result.data.\*.attachments.url | string | | |
action_result.data.\*.body_content_type | string | | markdown |
action_result.data.\*.campaigns.\*.id | numeric | | 218680 |
action_result.data.\*.can_add_public_tags | boolean | | True False |
action_result.data.\*.circles.\*.id | string | | 10022 |
action_result.data.\*.circles.\*.name | string | | test circle 4 |
action_result.data.\*.circles.\*.resource_uri | string | | /api/v1/trustedcircle/10022/ |
action_result.data.\*.comment.body | string | | This is a comment. |
action_result.data.\*.comment.created_ts | string | | 2021-04-20T09:04:26.124839 |
action_result.data.\*.comment.id | numeric | | 19 |
action_result.data.\*.comment.modified_ts | string | | 2021-04-20T09:04:26.124854 |
action_result.data.\*.comment.resource_uri | string | | /api/v1/vulnerability/30274/comment/19/ |
action_result.data.\*.comment.title | string | | comment title |
action_result.data.\*.comment.tlp | string | | |
action_result.data.\*.comment.user.avatar_s3_url | string | | |
action_result.data.\*.comment.user.can_share_intelligence | boolean | | True False |
action_result.data.\*.comment.user.email | string | `email` | test@test.com |
action_result.data.\*.comment.user.id | string | | 142 |
action_result.data.\*.comment.user.is_active | boolean | | True False |
action_result.data.\*.comment.user.is_readonly | boolean | | True False |
action_result.data.\*.comment.user.must_change_password | boolean | | True False |
action_result.data.\*.comment.user.name | string | | test |
action_result.data.\*.comment.user.nickname | string | | testnickname |
action_result.data.\*.comment.user.organization.id | string | | 70 |
action_result.data.\*.comment.user.organization.name | string | | test |
action_result.data.\*.comment.user.organization.resource_uri | string | | /api/v1/userorganization/70/ |
action_result.data.\*.comment.user.resource_uri | string | | /api/v1/user/142/ |
action_result.data.\*.created_ts | string | | 2021-04-20T09:02:33.703401 |
action_result.data.\*.cvss2_score | string | | |
action_result.data.\*.cvss3_score | string | | |
action_result.data.\*.description | string | | for analysis |
action_result.data.\*.embedded_content_type | string | | |
action_result.data.\*.embedded_content_url | string | | |
action_result.data.\*.external_references.\*.filename | string | | Bien suÌ‚r.rtf |
action_result.data.\*.external_references.\*.id | numeric | | 16545 |
action_result.data.\*.external_references.\*.r_type | string | | A |
action_result.data.\*.external_references.\*.remote_api | boolean | | True False |
action_result.data.\*.external_references.\*.resource_uri | string | | /api/v1/vulnerabilityexternalreference/16545/ |
action_result.data.\*.external_references.\*.s3_url | string | `url` | |
action_result.data.\*.external_references.\*.title | string | | Bien suÌ‚r.rtf |
action_result.data.\*.external_references.\*.url | string | | |
action_result.data.\*.feed_id | numeric | | 0 |
action_result.data.\*.id | numeric | | 30274 |
action_result.data.\*.incidents.\*.id | numeric | | 171066 |
action_result.data.\*.intelligence.\*.asn | string | | |
action_result.data.\*.intelligence.\*.can_add_public_tags | boolean | | True False |
action_result.data.\*.intelligence.\*.confidence | numeric | | -1 |
action_result.data.\*.intelligence.\*.country | string | | |
action_result.data.\*.intelligence.\*.created_by | string | | |
action_result.data.\*.intelligence.\*.created_ts | string | | 2021-05-27T12:23:59.162Z |
action_result.data.\*.intelligence.\*.description | string | | |
action_result.data.\*.intelligence.\*.expiration_ts | string | | 2021-08-25T12:23:59.083Z |
action_result.data.\*.intelligence.\*.feed_id | numeric | | 0 |
action_result.data.\*.intelligence.\*.id | numeric | | 240070494 |
action_result.data.\*.intelligence.\*.import_session_id | string | | |
action_result.data.\*.intelligence.\*.import_source | string | | |
action_result.data.\*.intelligence.\*.ip | string | | |
action_result.data.\*.intelligence.\*.is_anonymous | boolean | | True False |
action_result.data.\*.intelligence.\*.is_editable | boolean | | True False |
action_result.data.\*.intelligence.\*.is_public | boolean | | True False |
action_result.data.\*.intelligence.\*.itype | string | | mal_domain |
action_result.data.\*.intelligence.\*.latitude | string | | |
action_result.data.\*.intelligence.\*.longitude | string | | |
action_result.data.\*.intelligence.\*.meta.detail2 | string | | imported by user 136 |
action_result.data.\*.intelligence.\*.meta.severity | string | | very-high |
action_result.data.\*.intelligence.\*.modified_ts | string | | 2021-05-27T12:24:57.292Z |
action_result.data.\*.intelligence.\*.org | string | | |
action_result.data.\*.intelligence.\*.owner_organization_id | numeric | | 67 |
action_result.data.\*.intelligence.\*.rdns | string | | |
action_result.data.\*.intelligence.\*.remote_api | boolean | | True False |
action_result.data.\*.intelligence.\*.resource_uri | string | | /api/v2/intelligence/240070494/?remote_api=true |
action_result.data.\*.intelligence.\*.retina_confidence | numeric | | -1 |
action_result.data.\*.intelligence.\*.source | string | | qa.test.com |
action_result.data.\*.intelligence.\*.source_created | string | | |
action_result.data.\*.intelligence.\*.source_modified | string | | |
action_result.data.\*.intelligence.\*.source_reported_confidence | numeric | | -1 |
action_result.data.\*.intelligence.\*.status | string | | active |
action_result.data.\*.intelligence.\*.subtype | string | | |
action_result.data.\*.intelligence.\*.tags.\*.id | string | | pe3 |
action_result.data.\*.intelligence.\*.tags.\*.name | string | | test_playbook |
action_result.data.\*.intelligence.\*.tags.\*.org_id | string | | 67 |
action_result.data.\*.intelligence.\*.tags.\*.remote_api | boolean | | True False |
action_result.data.\*.intelligence.\*.tags.\*.tlp | string | | red |
action_result.data.\*.intelligence.\*.threat_type | string | | malware |
action_result.data.\*.intelligence.\*.threatscore | numeric | | 0 |
action_result.data.\*.intelligence.\*.tlp | string | | |
action_result.data.\*.intelligence.\*.trusted_circle_ids | string | | |
action_result.data.\*.intelligence.\*.type | string | | domain |
action_result.data.\*.intelligence.\*.update_id | numeric | | 482449579 |
action_result.data.\*.intelligence.\*.uuid | string | | 04179036-e714-4525-9ce2-b2b0d234073c |
action_result.data.\*.intelligence.\*.value | string | | www.testingtest8093.com |
action_result.data.\*.is_anonymous | boolean | | True False |
action_result.data.\*.is_cloneable | string | | yes |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.is_system | boolean | | True False |
action_result.data.\*.logo_s3_url | string | | |
action_result.data.\*.mitre_cve_url | string | `url` | |
action_result.data.\*.modified_ts | string | | 2021-04-20T09:04:24.429285 |
action_result.data.\*.name | string | | updated_test_111 |
action_result.data.\*.organization.id | string | | 70 |
action_result.data.\*.organization.name | string | | test |
action_result.data.\*.organization.resource_uri | string | | /api/v1/userorganization/70/ |
action_result.data.\*.organization_id | numeric | | 70 |
action_result.data.\*.owner_user.email | string | `email` | test@test.com |
action_result.data.\*.owner_user.id | string | | 142 |
action_result.data.\*.owner_user.name | string | | test |
action_result.data.\*.owner_user.resource_uri | string | | /api/v1/user/142/ |
action_result.data.\*.owner_user_id | numeric | | 142 |
action_result.data.\*.parent | string | | |
action_result.data.\*.publication_status | string | | reviewed |
action_result.data.\*.published_ts | string | | |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_uri | string | | /api/v1/vulnerability/30274/ |
action_result.data.\*.signatures.\*.id | numeric | | 632 |
action_result.data.\*.source | string | | from action |
action_result.data.\*.source_created | string | | 2019-04-10T10:10:55 |
action_result.data.\*.source_modified | string | | 2019-05-19T10:15:23 |
action_result.data.\*.starred_by_me | boolean | | True False |
action_result.data.\*.starred_total_count | numeric | | 0 |
action_result.data.\*.tlp | string | | red |
action_result.data.\*.ttps.\*.id | numeric | | 1573 |
action_result.data.\*.update_id | numeric | | 416539 |
action_result.data.\*.uuid | string | | fe06d084-a63b-4536-a748-3232ce650e85 |
action_result.data.\*.votes.me | string | | |
action_result.data.\*.votes.total | numeric | | 0 |
action_result.data.\*.vulnerability.\*.id | numeric | | 29891 |
action_result.data.\*.watched_by_me | boolean | | True False |
action_result.data.\*.watched_total_count | numeric | | 0 |
action_result.summary | string | | |
action_result.message | string | | Successfully updated vulnerability |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create actor'

Create an actor in ThreatStream

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Name to give an actor | string | |
**fields** | optional | JSON formatted string of fields to include with an actor | string | |
**local_intelligence** | optional | Comma-separated list of local intelligence IDs to associate with an actor - Note that this appends | string | `threatstream intelligence id` |
**cloud_intelligence** | optional | Comma-separated list of remote intelligence IDs to associate with an actor - Note that this appends | string | `threatstream intelligence id` |
**comment** | optional | Comment to give an actor (JSON format containing body, title, etc.) | string | |
**attachment** | optional | Vault id of an attachment to add on the actor | string | `vault id` `sha1` |
**is_public** | optional | Classification designation | boolean | |
**create_on_cloud** | optional | Create on remote (cloud)? (applicable only for hybrid on-prem instances) | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.attachment | string | `vault id` `sha1` | b10e56af7aed0446e7c87d495700118787212378 |
action_result.parameter.cloud_intelligence | string | `threatstream intelligence id` | 232202446 |
action_result.parameter.comment | string | | {"title": "comment title", "body": "This is a comment."} |
action_result.parameter.create_on_cloud | boolean | | True False |
action_result.parameter.fields | string | | {"description": "this is for test analysis", "is_team": True, "publication_status": "reviewed", "tags": ["testing", "actor"], "soph_type": 1, "soph_desc": "Testing actor soph desc", "source_created": "2019-04-10T10:10:55"} |
action_result.parameter.is_public | boolean | | True False |
action_result.parameter.local_intelligence | string | `threatstream intelligence id` | |
action_result.parameter.name | string | | actor_test_1 |
action_result.data.\*.aliases.\*.id | numeric | | 902 |
action_result.data.\*.aliases.\*.name | string | | testing |
action_result.data.\*.aliases.\*.resource_uri | string | | /api/v1/actoralias/902/ |
action_result.data.\*.assignee_user | string | | |
action_result.data.\*.attachment | string | | url |
action_result.data.\*.attachments.filename | string | | HTML%20-%20All%20valid_invalid.html |
action_result.data.\*.attachments.id | numeric | | 26632 |
action_result.data.\*.attachments.r_type | string | | A |
action_result.data.\*.attachments.remote_api | boolean | | True False |
action_result.data.\*.attachments.resource_uri | string | | /api/v1/actorexternalreference/26632/?remote_api=true |
action_result.data.\*.attachments.s3_url | string | | https://test-optic.s3.user.com/userUploads/2021-05-27/20210527_131543_userId-136_c1946412-e29e-49fa-a0ed-3316c20d76af_HTML20-20All20valid_invalid.html?Signature=Q71zTevIhJsdGfPdhKZuHy4bu14%3D&Expires=1622124943&AWSAccessKeyId=AKIAQYUTUNAKSCAMMFFH |
action_result.data.\*.attachments.title | string | | HTML%20-%20All%20valid_invalid.html |
action_result.data.\*.attachments.url | string | | |
action_result.data.\*.avatar_s3_url | string | | |
action_result.data.\*.body_content_type | string | | markdown |
action_result.data.\*.campaigns.\*.id | numeric | `threatstream campaign id` | 218680 |
action_result.data.\*.can_add_public_tags | boolean | | True False |
action_result.data.\*.circles.\*.id | string | | 10022 |
action_result.data.\*.circles.\*.name | string | | test circle 4 |
action_result.data.\*.circles.\*.resource_uri | string | | /api/v1/trustedcircle/10022/ |
action_result.data.\*.comment.!@#$%^ | string | | This is a comment. |
action_result.data.\*.comment.body | string | | This is a comment. |
action_result.data.\*.comment.created_ts | string | | 2021-04-20T08:39:21.756188 |
action_result.data.\*.comment.id | numeric | | 15 |
action_result.data.\*.comment.invalid | string | | comment title |
action_result.data.\*.comment.modified_ts | string | | 2021-04-20T08:39:21.756205 |
action_result.data.\*.comment.remote_api | boolean | | True False |
action_result.data.\*.comment.resource_uri | string | | /api/v1/actor/11930/comment/15/ |
action_result.data.\*.comment.title | string | | comment title |
action_result.data.\*.comment.tlp | string | | |
action_result.data.\*.comment.user.avatar_s3_url | string | | |
action_result.data.\*.comment.user.can_share_intelligence | boolean | | True False |
action_result.data.\*.comment.user.email | string | `email` | test@test.com |
action_result.data.\*.comment.user.id | string | | 142 |
action_result.data.\*.comment.user.is_active | boolean | | True False |
action_result.data.\*.comment.user.is_readonly | boolean | | True False |
action_result.data.\*.comment.user.must_change_password | boolean | | True False |
action_result.data.\*.comment.user.name | string | | test |
action_result.data.\*.comment.user.nickname | string | | testnickname |
action_result.data.\*.comment.user.organization.id | string | | 70 |
action_result.data.\*.comment.user.organization.name | string | | test |
action_result.data.\*.comment.user.organization.resource_uri | string | | /api/v1/userorganization/70/ |
action_result.data.\*.comment.user.resource_uri | string | | /api/v1/user/142/ |
action_result.data.\*.created_ts | string | | 2021-04-20T08:39:20.368888 |
action_result.data.\*.description | string | | for analysis |
action_result.data.\*.embedded_content_type | string | | |
action_result.data.\*.embedded_content_url | string | | |
action_result.data.\*.feed_id | numeric | | 0 |
action_result.data.\*.goals | string | | |
action_result.data.\*.id | numeric | `threatstream actor id` | 11930 |
action_result.data.\*.incidents.\*.id | numeric | `threatstream incident id` | 171066 |
action_result.data.\*.intelligence.\*.id | numeric | `threatstream intelligence id` | 232202446 |
action_result.data.\*.is_anonymous | boolean | | True False |
action_result.data.\*.is_cloneable | string | | yes |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.is_team | boolean | | True False |
action_result.data.\*.logo_s3_url | string | | |
action_result.data.\*.modified_ts | string | | 2021-04-20T08:39:20.369940 |
action_result.data.\*.name | string | | actor_test_1 |
action_result.data.\*.organization.id | string | | 70 |
action_result.data.\*.organization.name | string | | test |
action_result.data.\*.organization.resource_uri | string | | /api/v1/userorganization/70/ |
action_result.data.\*.organization_id | numeric | | 70 |
action_result.data.\*.owner_user.email | string | `email` | test@test.com |
action_result.data.\*.owner_user.id | string | | 142 |
action_result.data.\*.owner_user.name | string | | test |
action_result.data.\*.owner_user.resource_uri | string | | /api/v1/user/142/ |
action_result.data.\*.owner_user_id | numeric | | 142 |
action_result.data.\*.parent | string | | |
action_result.data.\*.personal_motivations | string | | |
action_result.data.\*.primary_motivation | string | | |
action_result.data.\*.publication_status | string | | reviewed |
action_result.data.\*.published_ts | string | | |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_level | string | | |
action_result.data.\*.resource_uri | string | | /api/v1/actor/11930/ |
action_result.data.\*.roles | string | | |
action_result.data.\*.secondary_motivations | string | | |
action_result.data.\*.signatures.\*.id | numeric | `threatstream signature id` | 632 |
action_result.data.\*.soph_desc | string | | Testing actor soph desc.. |
action_result.data.\*.soph_type | string | | |
action_result.data.\*.soph_type | string | | |
action_result.data.\*.soph_type.display_name | string | | Innovator |
action_result.data.\*.soph_type.id | numeric | | 1 |
action_result.data.\*.soph_type.resource_uri | string | | /api/v1/actorsophisticationtype/1/ |
action_result.data.\*.soph_type.value | string | | I |
action_result.data.\*.source_created | string | | 2019-04-10T10:10:55 |
action_result.data.\*.source_modified | string | | 2019-05-19T10:15:23 |
action_result.data.\*.starred_by_me | boolean | | True False |
action_result.data.\*.starred_total_count | numeric | | 0 |
action_result.data.\*.start_date | string | | 2019-06-05T04:15:03 |
action_result.data.\*.tags_v2.\*.id | string | | ywr |
action_result.data.\*.tags_v2.\*.name | string | | testing |
action_result.data.\*.tags_v2.\*.org_id | numeric | | 67 |
action_result.data.\*.tags_v2.\*.tlp | string | | white |
action_result.data.\*.threat_actor_types | string | | |
action_result.data.\*.tlp | string | | amber |
action_result.data.\*.ttps.\*.id | numeric | `threatstream ttp id` | 1573 |
action_result.data.\*.uuid | string | | b58939d4-21b0-427b-bb62-6dc42391bef0 |
action_result.data.\*.victims.\*.id | numeric | | 13 |
action_result.data.\*.victims.\*.name | string | | Health Care |
action_result.data.\*.victims.\*.resource_uri | string | | /api/v1/victimtype/13/ |
action_result.data.\*.victims.\*.value | numeric | | 12 |
action_result.data.\*.votes.me | string | | |
action_result.data.\*.votes.total | numeric | | 0 |
action_result.data.\*.vulnerability.\*.id | numeric | `threatstream vulnerability id` | 29891 |
action_result.data.\*.watched_by_me | boolean | | True False |
action_result.data.\*.watched_total_count | numeric | | 0 |
action_result.summary.created_on_cloud | boolean | | True False |
action_result.message | string | | Actor created successfully. Associated intelligence : 232202446 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update actor'

Update an actor in ThreatStream

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | ID of an actor | string | `threatstream actor id` |
**fields** | optional | JSON formatted string of fields to include with an actor | string | |
**local_intelligence** | optional | Comma-separated list of local intelligence IDs to associate with an actor - Note that this appends | string | `threatstream intelligence id` |
**cloud_intelligence** | optional | Comma-separated list of remote intelligence IDs to associate with an actor - Note that this appends | string | `threatstream intelligence id` |
**comment** | optional | Comment to give an actor (JSON format containing body, title, etc.) | string | |
**attachment** | optional | Vault id of an attachment to add on the actor | string | `vault id` `sha1` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.attachment | string | `vault id` `sha1` | b10e56af7aed0446e7c87d495700118787212378 |
action_result.parameter.cloud_intelligence | string | `threatstream intelligence id` | |
action_result.parameter.comment | string | | {"title": "comment title", "body": "This is a comment."} |
action_result.parameter.fields | string | | {"description": "this is for test analysis", "is_team": True, "publication_status": "reviewed", "tags": ["testing", "actor"], "soph_type": 1, "soph_desc": "Testing actor soph desc", "source_created": "2019-04-10T10:10:55"} |
action_result.parameter.id | string | `threatstream actor id` | 11930 |
action_result.parameter.local_intelligence | string | `threatstream intelligence id` | |
action_result.data.\*.aliases.\*.id | numeric | | 904 |
action_result.data.\*.aliases.\*.name | string | | testing |
action_result.data.\*.aliases.\*.resource_uri | string | | /api/v1/actoralias/904/ |
action_result.data.\*.assignee_user | string | | |
action_result.data.\*.attachment | string | | url |
action_result.data.\*.attachments.filename | string | | unicode.zip |
action_result.data.\*.attachments.id | numeric | | 26641 |
action_result.data.\*.attachments.r_type | string | | A |
action_result.data.\*.attachments.remote_api | boolean | | True False |
action_result.data.\*.attachments.resource_uri | string | | /api/v1/actorexternalreference/26641/?remote_api=true |
action_result.data.\*.attachments.s3_url | string | | https://test-optic.s3.user.com/userUploads/2021-05-27/20210527_131611_userId-136_62cde7fc-ce0b-4d74-a159-669769998dc0_unicode.zip?Signature=5e4NsfOOT8GwBc57JeNM9j0a7oU%3D&Expires=1622124971&AWSAccessKeyId=AKIAQYUTUNAKSCAMMFFH |
action_result.data.\*.attachments.title | string | | unicode.zip |
action_result.data.\*.attachments.url | string | | |
action_result.data.\*.avatar_s3_url | string | | |
action_result.data.\*.body_content_type | string | | markdown |
action_result.data.\*.campaigns.\*.id | numeric | `threatstream campaign id` | 218680 |
action_result.data.\*.can_add_public_tags | boolean | | True False |
action_result.data.\*.circles.\*.id | string | | 10022 |
action_result.data.\*.circles.\*.name | string | | test circle 4 |
action_result.data.\*.circles.\*.resource_uri | string | | /api/v1/trustedcircle/10022/ |
action_result.data.\*.comment.body | string | | This is a comment. |
action_result.data.\*.comment.created_ts | string | | 2021-04-20T08:52:19.742189 |
action_result.data.\*.comment.id | numeric | | 16 |
action_result.data.\*.comment.modified_ts | string | | 2021-04-20T08:52:19.742205 |
action_result.data.\*.comment.resource_uri | string | | /api/v1/actor/11930/comment/16/ |
action_result.data.\*.comment.title | string | | comment title |
action_result.data.\*.comment.tlp | string | | |
action_result.data.\*.comment.user.avatar_s3_url | string | | |
action_result.data.\*.comment.user.can_share_intelligence | boolean | | True False |
action_result.data.\*.comment.user.email | string | `email` | test@test.com |
action_result.data.\*.comment.user.id | string | | 142 |
action_result.data.\*.comment.user.is_active | boolean | | True False |
action_result.data.\*.comment.user.is_readonly | boolean | | True False |
action_result.data.\*.comment.user.must_change_password | boolean | | True False |
action_result.data.\*.comment.user.name | string | | test |
action_result.data.\*.comment.user.nickname | string | | testnickname |
action_result.data.\*.comment.user.organization.id | string | | 70 |
action_result.data.\*.comment.user.organization.name | string | | test |
action_result.data.\*.comment.user.organization.resource_uri | string | | /api/v1/userorganization/70/ |
action_result.data.\*.comment.user.resource_uri | string | | /api/v1/user/142/ |
action_result.data.\*.comments.!@#$%^&\* | string | | comment title |
action_result.data.\*.comments.body | string | | This is a comment updated by user. |
action_result.data.\*.comments.created_ts | string | | 2021-05-27T13:18:34.575822 |
action_result.data.\*.comments.id | numeric | | 1000000245 |
action_result.data.\*.comments.incorrect value | string | | This is a comment. |
action_result.data.\*.comments.modified_ts | string | | 2021-05-27T13:18:34.575846 |
action_result.data.\*.comments.remote_api | boolean | | True False |
action_result.data.\*.comments.resource_uri | string | | /api/v1/actor/1000001019/comment/1000000245/ |
action_result.data.\*.comments.title | string | | updating comment title |
action_result.data.\*.comments.tlp | string | | |
action_result.data.\*.comments.user.avatar_s3_url | string | | |
action_result.data.\*.comments.user.can_share_intelligence | boolean | | True False |
action_result.data.\*.comments.user.email | string | | qa+test@qa.user.com |
action_result.data.\*.comments.user.id | string | | 136 |
action_result.data.\*.comments.user.is_active | boolean | | True False |
action_result.data.\*.comments.user.is_readonly | boolean | | True False |
action_result.data.\*.comments.user.must_change_password | boolean | | True False |
action_result.data.\*.comments.user.name | string | | test |
action_result.data.\*.comments.user.nickname | string | | |
action_result.data.\*.comments.user.organization.id | string | | 67 |
action_result.data.\*.comments.user.organization.name | string | | qa.test.com |
action_result.data.\*.comments.user.organization.resource_uri | string | | /api/v1/userorganization/67/ |
action_result.data.\*.comments.user.resource_uri | string | | /api/v1/user/136/ |
action_result.data.\*.created_ts | string | | 2021-04-20T08:39:20.368888 |
action_result.data.\*.description | string | | for analysis |
action_result.data.\*.embedded_content_type | string | | |
action_result.data.\*.embedded_content_url | string | | |
action_result.data.\*.external_references.\*.filename | string | | Bien suÌ‚r.rtf |
action_result.data.\*.external_references.\*.id | numeric | | 16542 |
action_result.data.\*.external_references.\*.r_type | string | | A |
action_result.data.\*.external_references.\*.remote_api | boolean | | True False |
action_result.data.\*.external_references.\*.resource_uri | string | | /api/v1/actorexternalreference/16542/ |
action_result.data.\*.external_references.\*.s3_url | string | `url` | |
action_result.data.\*.external_references.\*.title | string | | Bien suÌ‚r.rtf |
action_result.data.\*.external_references.\*.url | string | | |
action_result.data.\*.feed_id | numeric | | 0 |
action_result.data.\*.goals | string | | |
action_result.data.\*.id | numeric | `threatstream actor id` | 11930 |
action_result.data.\*.incidents.\*.id | numeric | `threatstream incident id` | 171066 |
action_result.data.\*.intelligence.\*.asn | string | | |
action_result.data.\*.intelligence.\*.can_add_public_tags | boolean | | True False |
action_result.data.\*.intelligence.\*.confidence | numeric | | 50 |
action_result.data.\*.intelligence.\*.country | string | | |
action_result.data.\*.intelligence.\*.created_by | string | | qa+test@qa.user.com |
action_result.data.\*.intelligence.\*.created_ts | string | | 2019-12-17T06:50:38.403Z |
action_result.data.\*.intelligence.\*.description | string | | |
action_result.data.\*.intelligence.\*.expiration_ts | string | | 2019-12-18T08:00:00.000Z |
action_result.data.\*.intelligence.\*.feed_id | numeric | | 0 |
action_result.data.\*.intelligence.\*.id | numeric | | 171989368 |
action_result.data.\*.intelligence.\*.id | numeric | | 1000001355 |
action_result.data.\*.intelligence.\*.import_session_id | numeric | | 238 |
action_result.data.\*.intelligence.\*.import_source | string | | test |
action_result.data.\*.intelligence.\*.ip | string | | |
action_result.data.\*.intelligence.\*.is_anonymous | boolean | | True False |
action_result.data.\*.intelligence.\*.is_editable | boolean | | True False |
action_result.data.\*.intelligence.\*.is_public | boolean | | True False |
action_result.data.\*.intelligence.\*.itype | string | | mal_email |
action_result.data.\*.intelligence.\*.latitude | string | | |
action_result.data.\*.intelligence.\*.longitude | string | | |
action_result.data.\*.intelligence.\*.meta.detail2 | string | | bifocals_deactivated_on_2019-12-18_08:00:00.243473 |
action_result.data.\*.intelligence.\*.meta.severity | string | | low |
action_result.data.\*.intelligence.\*.modified_ts | string | | 2021-05-27T12:26:57.714Z |
action_result.data.\*.intelligence.\*.org | string | | |
action_result.data.\*.intelligence.\*.owner_organization_id | numeric | | 67 |
action_result.data.\*.intelligence.\*.rdns | string | | |
action_result.data.\*.intelligence.\*.remote_api | boolean | | True False |
action_result.data.\*.intelligence.\*.resource_uri | string | | /api/v2/intelligence/171989368/?remote_api=true |
action_result.data.\*.intelligence.\*.retina_confidence | numeric | | -1 |
action_result.data.\*.intelligence.\*.source | string | | qa+testuser2@qa.user.com |
action_result.data.\*.intelligence.\*.source_created | string | | |
action_result.data.\*.intelligence.\*.source_modified | string | | |
action_result.data.\*.intelligence.\*.source_reported_confidence | numeric | | 50 |
action_result.data.\*.intelligence.\*.status | string | | inactive |
action_result.data.\*.intelligence.\*.subtype | string | | |
action_result.data.\*.intelligence.\*.tags.\*.category | string | | user |
action_result.data.\*.intelligence.\*.tags.\*.id | string | | g8d |
action_result.data.\*.intelligence.\*.tags.\*.name | string | | test_name |
action_result.data.\*.intelligence.\*.tags.\*.org_id | string | | 67 |
action_result.data.\*.intelligence.\*.tags.\*.remote_api | boolean | | True False |
action_result.data.\*.intelligence.\*.tags.\*.source_user | string | | |
action_result.data.\*.intelligence.\*.tags.\*.source_user_id | string | | 1234 |
action_result.data.\*.intelligence.\*.tags.\*.tagger | string | | user |
action_result.data.\*.intelligence.\*.tags.\*.tlp | string | | white |
action_result.data.\*.intelligence.\*.threat_type | string | | malware |
action_result.data.\*.intelligence.\*.threatscore | numeric | | 10 |
action_result.data.\*.intelligence.\*.tlp | string | | green |
action_result.data.\*.intelligence.\*.trusted_circle_ids | string | | |
action_result.data.\*.intelligence.\*.type | string | | email |
action_result.data.\*.intelligence.\*.update_id | numeric | | 482449590 |
action_result.data.\*.intelligence.\*.uuid | string | | 628c8970-6297-4747-82fd-5660ac42a6c5 |
action_result.data.\*.intelligence.\*.value | string | | test_assoi_cloud@test.com |
action_result.data.\*.is_anonymous | boolean | | True False |
action_result.data.\*.is_cloneable | string | | yes |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.is_team | boolean | | True False |
action_result.data.\*.logo_s3_url | string | | |
action_result.data.\*.modified_ts | string | | 2021-04-20T08:52:18.115817 |
action_result.data.\*.name | string | | actor_test_2 |
action_result.data.\*.organization.id | string | | 70 |
action_result.data.\*.organization.name | string | | test |
action_result.data.\*.organization.resource_uri | string | | /api/v1/userorganization/70/ |
action_result.data.\*.organization_id | numeric | | 70 |
action_result.data.\*.owner_user.email | string | `email` | test@test.com |
action_result.data.\*.owner_user.id | string | | 142 |
action_result.data.\*.owner_user.name | string | | testuser |
action_result.data.\*.owner_user.resource_uri | string | | /api/v1/user/142/ |
action_result.data.\*.owner_user_id | numeric | | 142 |
action_result.data.\*.parent | string | | |
action_result.data.\*.personal_motivations | string | | |
action_result.data.\*.primary_motivation | string | | |
action_result.data.\*.publication_status | string | | reviewed |
action_result.data.\*.published_ts | string | | |
action_result.data.\*.remote_api | boolean | | True False |
action_result.data.\*.resource_level | string | | |
action_result.data.\*.resource_uri | string | | /api/v1/actor/11930/ |
action_result.data.\*.roles | string | | |
action_result.data.\*.secondary_motivations | string | | |
action_result.data.\*.signatures.\*.id | numeric | `threatstream signature id` | 632 |
action_result.data.\*.soph_desc | string | | Testing actor soph desc.. |
action_result.data.\*.soph_type | string | | |
action_result.data.\*.soph_type | string | | |
action_result.data.\*.soph_type.display_name | string | | Innovator |
action_result.data.\*.soph_type.id | numeric | | 1 |
action_result.data.\*.soph_type.resource_uri | string | | /api/v1/actorsophisticationtype/1/ |
action_result.data.\*.soph_type.value | string | | I |
action_result.data.\*.source_created | string | | 2019-04-10T10:10:55 |
action_result.data.\*.source_modified | string | | 2019-05-19T10:15:23 |
action_result.data.\*.starred_by_me | boolean | | True False |
action_result.data.\*.starred_total_count | numeric | | 0 |
action_result.data.\*.start_date | string | | 2019-06-05T04:15:03 |
action_result.data.\*.tags_v2.\*.id | string | | 7ms |
action_result.data.\*.tags_v2.\*.name | string | | testing |
action_result.data.\*.tags_v2.\*.org_id | numeric | | 67 |
action_result.data.\*.tags_v2.\*.tlp | string | | white |
action_result.data.\*.threat_actor_types | string | | |
action_result.data.\*.tlp | string | | amber |
action_result.data.\*.ttps.\*.id | numeric | `threatstream ttp id` | 1573 |
action_result.data.\*.uuid | string | | b58939d4-21b0-427b-bb62-6dc42391bef0 |
action_result.data.\*.victims.\*.id | numeric | | 13 |
action_result.data.\*.victims.\*.name | string | | Health Care |
action_result.data.\*.victims.\*.resource_uri | string | | /api/v1/victimtype/13/ |
action_result.data.\*.victims.\*.value | numeric | | 12 |
action_result.data.\*.votes.me | string | | |
action_result.data.\*.votes.total | numeric | | 0 |
action_result.data.\*.vulnerability.\*.id | numeric | `threatstream vulnerability id` | 29891 |
action_result.data.\*.watched_by_me | boolean | | True False |
action_result.data.\*.watched_total_count | numeric | | 0 |
action_result.summary | string | | |
action_result.message | string | | Successfully updated actor |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete threat bulletin'

Delete threat bulletin in ThreatStream by ID

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**threat_bulletin_id** | required | ID of the threat bulletin to delete | string | `threatstream threatbulletin id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.threat_bulletin_id | string | `threatstream threatbulletin id` | 10911 |
action_result.data.\* | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully deleted threat bulletin |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete vulnerability'

Delete vulnerability in ThreatStream by ID

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vulnerability_id** | required | ID of the vulnerability to delete | string | `threatstream vulnerability id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.vulnerability_id | string | `threatstream vulnerability id` | 1000000001 |
action_result.data.\* | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully deleted vulnerability |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete actor'

Delete actor in ThreatStream by ID number

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**actor_id** | required | ID number of actor to delete | string | `threatstream actor id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.actor_id | string | `threatstream actor id` | 15518 1000000030 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully deleted actor |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update observable'

Update an observable in ThreatStream

Type: **generic** <br>
Read only: **False**

If any of the indicator_type, confidence, tlp, severity, status, or expiration_date parameter is added and is also mentioned in the fields parameter, the value given in the individual parameters is considered.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | ID of the observable | string | `threatstream intelligence id` |
**indicator_type** | optional | Indicator type to give the observable | string | |
**confidence** | optional | Confidence to give the observable | numeric | |
**tlp** | optional | Tlp to give the observable | string | |
**severity** | optional | Severity to give the observable | string | |
**status** | optional | Status to give the observable (For example, active, inactive, falsepos) | string | |
**expiration_date** | optional | Expiration timestamp to give the observable (in UTC format) | string | |
**fields** | optional | JSON formatted string of fields to include with the observable | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.confidence | numeric | | 43 |
action_result.parameter.expiration_date | string | | 2021-11-09T14:55:06.097Z |
action_result.parameter.fields | string | | {"confidence": 60} |
action_result.parameter.id | string | `threatstream intelligence id` | 263745273 |
action_result.parameter.indicator_type | string | | mal_email |
action_result.parameter.severity | string | | low |
action_result.parameter.status | string | | false positive |
action_result.parameter.tlp | string | | red |
action_result.data.\*.asn | string | | |
action_result.data.\*.confidence | numeric | | 37 |
action_result.data.\*.country | string | | |
action_result.data.\*.created_by | string | | |
action_result.data.\*.created_ts | string | | 2021-08-10T11:48:12.678 |
action_result.data.\*.expiration_ts | string | | 2022-11-09T14:55:06.097Z |
action_result.data.\*.feed_id | numeric | | 0 |
action_result.data.\*.id | numeric | `threatstream intelligence id` | 255050731 |
action_result.data.\*.import_session_id | string | | |
action_result.data.\*.import_source | string | | |
action_result.data.\*.ip | string | | |
action_result.data.\*.is_anonymous | boolean | | False |
action_result.data.\*.is_public | boolean | | False |
action_result.data.\*.itype | string | | apt_email |
action_result.data.\*.latitude | string | | |
action_result.data.\*.longitude | string | | |
action_result.data.\*.meta.detail2 | string | | imported by user 136 |
action_result.data.\*.meta.next | string | | |
action_result.data.\*.meta.previous | string | | |
action_result.data.\*.meta.severity | string | | medium |
action_result.data.\*.modified_ts | string | | 2021-08-12T11:02:35.625 |
action_result.data.\*.org | string | | |
action_result.data.\*.owner_organization_id | numeric | | 67 |
action_result.data.\*.rdns | string | | |
action_result.data.\*.remote_api | boolean | | True |
action_result.data.\*.resource_uri | string | | |
action_result.data.\*.retina_confidence | numeric | | -1 |
action_result.data.\*.source | string | | test.source.com |
action_result.data.\*.source_created | string | | |
action_result.data.\*.source_modified | string | | |
action_result.data.\*.source_reported_confidence | numeric | | 37 |
action_result.data.\*.status | string | | active |
action_result.data.\*.subtype | string | | |
action_result.data.\*.tags.\*.id | string | | dxd |
action_result.data.\*.tags.\*.name | string | | test2 |
action_result.data.\*.tags.\*.org_id | numeric | | 67 |
action_result.data.\*.tags.\*.remote_api | numeric | | True |
action_result.data.\*.tags.\*.source_user | string | | Customer |
action_result.data.\*.tags.\*.source_user_id | string | | 1234 |
action_result.data.\*.tags.\*.tlp | string | | red |
action_result.data.\*.threat_type | string | | apt |
action_result.data.\*.threatscore | numeric | | 28 |
action_result.data.\*.tlp | string | | green |
action_result.data.\*.type | string | | email |
action_result.data.\*.update_id | numeric | | 539165917 |
action_result.data.\*.uuid | string | | 6ae8e41a-6fa1-43fb-bd08-02c1babf7fa0 |
action_result.data.\*.value | string | | 55test@test.com |
action_result.summary | string | | |
action_result.message | string | | Successfully updated observable |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create investigation'

Create an investigation in ThreatStream

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Name to give the investigation | string | |
**priority** | required | Priority assigned to the investigation | string | |
**fields** | optional | JSON formatted string of fields to include with the investigation | string | |
**create_on_cloud** | optional | Create on remote (cloud)? (applicable only for hybrid on-prem instances) | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.create_on_cloud | boolean | | True False |
action_result.parameter.fields | string | | {"tlp": "red"} |
action_result.parameter.name | string | | new_investigation |
action_result.parameter.priority | string | | low |
action_result.data.\*.assignee | string | | |
action_result.data.\*.attachments | string | | |
action_result.data.\*.candidate_session | string | | |
action_result.data.\*.circles | string | | |
action_result.data.\*.created_ts | string | | 2020-05-28T00:39:25.453003 |
action_result.data.\*.description | string | | <p>this is a low priority investigation</p> |
action_result.data.\*.elements | numeric | | 0 |
action_result.data.\*.graph_content | string | | |
action_result.data.\*.id | numeric | `threatstream investigation id` | 0 |
action_result.data.\*.import_sessions | string | | |
action_result.data.\*.investigation_attachments | string | | |
action_result.data.\*.is_public | boolean | | False |
action_result.data.\*.modified_ts | string | | 2020-05-21T18:53:11.233187 |
action_result.data.\*.name | string | | Blank Investigation Two |
action_result.data.\*.owner_org.id | string | | 2342 |
action_result.data.\*.owner_org.name | string | | test.us |
action_result.data.\*.owner_org.resource_uri | string | | /api/v1/userorganization/2342/ |
action_result.data.\*.owner_org_id | string | `id` | |
action_result.data.\*.priority | string | | low |
action_result.data.\*.reporter.avatar_s3_url | string | | |
action_result.data.\*.reporter.can_share_intelligence | boolean | | True |
action_result.data.\*.reporter.email | string | `email` | user@test.us |
action_result.data.\*.reporter.id | string | `id` | 6941 |
action_result.data.\*.reporter.is_active | boolean | | True |
action_result.data.\*.reporter.is_readonly | boolean | | True |
action_result.data.\*.reporter.must_change_password | boolean | | True |
action_result.data.\*.reporter.name | string | | |
action_result.data.\*.reporter.nickname | string | | EAlezeb |
action_result.data.\*.reporter.organization.id | string | `id` | 2324 |
action_result.data.\*.reporter.organization.name | string | | test.us |
action_result.data.\*.reporter.organization.resource_uri | string | `url` | /api/v1/userorganization/2342/ |
action_result.data.\*.reporter.resource_uri | string | `url` | /api/v1/user/6941/ |
action_result.data.\*.reporter_id | numeric | `id` | 6941 |
action_result.data.\*.resource_uri | string | `url` | /api/v1/investigation/56198/ |
action_result.data.\*.source_type | string | | user |
action_result.data.\*.status | string | | unassigned |
action_result.data.\*.tags | string | | |
action_result.data.\*.tips | string | | |
action_result.data.\*.tlp | string | | red |
action_result.data.\*.workgroups | string | | |
action_result.data.tasks | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully created investigation |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list investigations'

List investigations present in ThreatStream

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**limit** | optional | Total number of investigations to return | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 1000 |
action_result.data.\*.assignee | string | | |
action_result.data.\*.created_ts | string | | 2020-05-28T23:47:44.391824 |
action_result.data.\*.elements | numeric | | 0 |
action_result.data.\*.id | numeric | `investigation id` | 0 |
action_result.data.\*.is_public | boolean | | False |
action_result.data.\*.modified_ts | string | | 2020-05-28T23:47:44.391824 |
action_result.data.\*.name | string | | Blank Investigation Two |
action_result.data.\*.owner_org.id | string | `id` | 2342 |
action_result.data.\*.owner_org.name | string | | test.us |
action_result.data.\*.owner_org.resource_uri | string | | /api/v1/userorganization/2342/ |
action_result.data.\*.owner_org_id | string | | |
action_result.data.\*.priority | string | | low |
action_result.data.\*.reporter.avatar_s3_url | string | | |
action_result.data.\*.reporter.can_share_intelligence | boolean | | True |
action_result.data.\*.reporter.email | string | `email` | user@test.us |
action_result.data.\*.reporter.id | string | `id` | 6941 |
action_result.data.\*.reporter.is_active | boolean | | True |
action_result.data.\*.reporter.is_readonly | boolean | | True |
action_result.data.\*.reporter.must_change_password | boolean | | True |
action_result.data.\*.reporter.name | string | | |
action_result.data.\*.reporter.nickname | string | | |
action_result.data.\*.reporter.organization.id | string | `id` | 2324 |
action_result.data.\*.reporter.organization.name | string | | test.us |
action_result.data.\*.reporter.organization.resource_uri | string | | /api/v1/userorganization/2342/ |
action_result.data.\*.reporter.resource_uri | string | `url` | /api/v1/user/6941/ |
action_result.data.\*.reporter_id | numeric | `id` | 6941 |
action_result.data.\*.resource_uri | string | `url` | /api/v1/investigation/56953/ |
action_result.data.\*.source_type | string | | user |
action_result.data.\*.status | string | | unassigned |
action_result.data.\*.tags | string | | |
action_result.data.\*.tlp | string | | red |
action_result.data.\*.workgroups | string | | |
action_result.summary.investigations_returned | numeric | | 1000 |
action_result.message | string | | Investigations returned: 1000 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get investigation'

Retrieve investigation present in Threatstream by ID

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**investigation_id** | required | ID of the investigation to retrieve | numeric | `threatstream investigation id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.investigation_id | numeric | `threatstream investigation id` | 56198 |
action_result.data.\*.assignee | string | | |
action_result.data.\*.attachments | string | | |
action_result.data.\*.candidate_session | string | | |
action_result.data.\*.circles | string | | |
action_result.data.\*.created_ts | string | | 2020-05-21T18:53:11.233187 |
action_result.data.\*.description | string | | <p>this is a low priority investigation</p> |
action_result.data.\*.elements | numeric | | 0 |
action_result.data.\*.graph_content | string | | |
action_result.data.\*.id | numeric | `id` | 0 |
action_result.data.\*.import_sessions | string | | |
action_result.data.\*.investigation_attachments | string | | |
action_result.data.\*.is_public | boolean | | False |
action_result.data.\*.modified_ts | string | | 2020-05-21T18:53:11.233187 |
action_result.data.\*.name | string | | Blank Investigation Two |
action_result.data.\*.owner_org.id | string | `id` | 2342 |
action_result.data.\*.owner_org.name | string | | test.us |
action_result.data.\*.owner_org.resource_uri | string | `url` | /api/v1/userorganization/2342/ |
action_result.data.\*.owner_org_id | string | `id` | |
action_result.data.\*.priority | string | | low |
action_result.data.\*.reporter.avatar_s3_url | string | | |
action_result.data.\*.reporter.can_share_intelligence | boolean | | True |
action_result.data.\*.reporter.email | string | `email` | user@test.us |
action_result.data.\*.reporter.id | string | `id` | 6941 |
action_result.data.\*.reporter.is_active | boolean | | True |
action_result.data.\*.reporter.is_readonly | boolean | | True |
action_result.data.\*.reporter.must_change_password | boolean | | True |
action_result.data.\*.reporter.name | string | | |
action_result.data.\*.reporter.nickname | string | | EAlezeb |
action_result.data.\*.reporter.organization.id | string | `id` | 2324 |
action_result.data.\*.reporter.organization.name | string | | test.us |
action_result.data.\*.reporter.organization.resource_uri | string | | /api/v1/userorganization/2342/ |
action_result.data.\*.reporter.resource_uri | string | | /api/v1/user/6941/ |
action_result.data.\*.reporter_id | numeric | `id` | 6941 |
action_result.data.\*.resource_uri | string | `url` | /api/v1/investigation/56198/ |
action_result.data.\*.source_type | string | | user |
action_result.data.\*.status | string | | unassigned |
action_result.data.\*.tags | string | | |
action_result.data.\*.tips | string | | |
action_result.data.\*.tlp | string | | red |
action_result.data.\*.workgroups | string | | |
action_result.data.tasks | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully retrieved investigation |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update investigation'

Update an investigation in ThreatStream

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**investigation_id** | required | ID of the investigation to update | numeric | `threatstream investigation id` |
**fields** | required | JSON formatted string of fields to include with the investigation | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.fields | string | | {"tlp": "red"} |
action_result.parameter.investigation_id | numeric | `threatstream investigation id` | 56198 |
action_result.data.\*.assignee | string | | |
action_result.data.\*.attachments | string | | |
action_result.data.\*.candidate_session | string | | |
action_result.data.\*.circles | string | | |
action_result.data.\*.created_ts | string | | 2020-05-28T00:39:25.453003 |
action_result.data.\*.description | string | | <p>this is a low priority investigation</p> |
action_result.data.\*.elements | numeric | | 0 |
action_result.data.\*.graph_content | string | | |
action_result.data.\*.id | numeric | `id` | 0 |
action_result.data.\*.import_sessions | string | | |
action_result.data.\*.investigation_attachments | string | | |
action_result.data.\*.is_public | boolean | | False |
action_result.data.\*.modified_ts | string | | 2020-05-21T18:53:11.233187 |
action_result.data.\*.name | string | | Blank Investigation Two |
action_result.data.\*.owner_org.id | string | `id` | 2342 |
action_result.data.\*.owner_org.name | string | | test.us |
action_result.data.\*.owner_org.resource_uri | string | `url` | /api/v1/userorganization/2342/ |
action_result.data.\*.owner_org_id | string | `id` | |
action_result.data.\*.priority | string | | low |
action_result.data.\*.reporter.avatar_s3_url | string | | |
action_result.data.\*.reporter.can_share_intelligence | boolean | | True |
action_result.data.\*.reporter.email | string | `email` | user@test.us |
action_result.data.\*.reporter.id | string | `id` | 6941 |
action_result.data.\*.reporter.is_active | boolean | | True |
action_result.data.\*.reporter.is_readonly | boolean | | True |
action_result.data.\*.reporter.must_change_password | boolean | | True |
action_result.data.\*.reporter.name | string | | |
action_result.data.\*.reporter.nickname | string | | EAlezeb |
action_result.data.\*.reporter.organization.id | string | `id` | 2324 |
action_result.data.\*.reporter.organization.name | string | | test.us |
action_result.data.\*.reporter.organization.resource_uri | string | | /api/v1/userorganization/2342/ |
action_result.data.\*.reporter.resource_uri | string | `url` | /api/v1/user/6941/ |
action_result.data.\*.reporter_id | numeric | `id` | 6941 |
action_result.data.\*.resource_uri | string | `url` | /api/v1/investigation/56198/ |
action_result.data.\*.source_type | string | | user |
action_result.data.\*.status | string | | unassigned |
action_result.data.\*.tags | string | | |
action_result.data.\*.tips | string | | |
action_result.data.\*.tlp | string | | red |
action_result.data.\*.workgroups | string | | |
action_result.data.tasks | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully updated investigation |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete investigation'

Delete investigation in ThreatStream by ID number

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**investigation_id** | required | ID number of investigation to delete | numeric | `threatstream investigation id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.investigation_id | numeric | `threatstream investigation id` | 56911 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully deleted investigation |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2025 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
