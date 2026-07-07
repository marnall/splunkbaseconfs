# VMRay

Publisher: VMRay \
Connector Version: 2.6.1 \
Product Vendor: VMRay GmbH \
Product Name: VMRay Platform \
Minimum Product Version: 5.5.0

This app enables you to detonate files and URLs, and perform investigative actions, using the VMRay Platform, thereby giving you automated analysis and advanced threat detection through an agentless hypervisor-based sandbox

## Port Information

The app uses HTTP/HTTPS protocol for communicating with the VMRay Server. Below are the default
ports used by Splunk SOAR.

| Service Name | Transport Protocol | Port |
|--------------|--------------------|------|
| http | tcp | 80 |
| https | tcp | 443 |

### Configuration variables

This table lists the configuration variables required to operate VMRay. These variables are specified when configuring a VMRay Platform asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**vmray_server** | required | string | Server IP/Hostname |
**vmray_api_key** | required | password | API Key |
**disable_cert_verification** | optional | boolean | Disable Certificate Verification |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity \
[get file](#action-get-file) - Download a file from the VMRay Platform and add it to the vault \
[detonate file](#action-detonate-file) - Detonate file in the VMRay Platform \
[detonate url](#action-detonate-url) - Detonate a URL in the VMRay Platform \
[get iocs](#action-get-iocs) - Get the iocs for a sample \
[get vtis](#action-get-vtis) - Get the vtis for a sample \
[get report](#action-get-report) - Get the report(s) for a submission \
[get info](#action-get-info) - Get information of a specific sample \
[get screenshots](#action-get-screenshots) - Get screenshots from an analysis

## action: 'test connectivity'

Validate the asset configuration for connectivity

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'get file'

Download a file from the VMRay Platform and add it to the vault

Type: **investigate** \
Read only: **True**

Downloads the file with the given hash from the VMRay Platform and adds it to the vault. This action returns a vault id which can be used to detonate the file.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | The hash of the file to be downloaded | string | `hash` `sha256` `sha1` `md5` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.hash | string | `hash` `md5` `sha1` `sha256` | |
action_result.data.\*.vault_id | string | `vault id` | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary.vault_id | string | `vault id` | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'detonate file'

Detonate file in the VMRay Platform

Type: **generic** \
Read only: **False**

The <b>file_name</b> parameter overrides the filename, if none is given the app tries to get the filename from the vaults metadata. The <b>type</b> overrides the automatic detection of the VMRay Platform. The <b>config</b> parameter specifies additional configuration options passed to the VMRay Platform (See user_config in the REST API documentation). With <b>jobrules</b> you can specify custom jobrule entries (See jobrule_enries in the REST API documentation). The <b>timeout</b> parameter specifies the time to wait for the submission to be finished before aborting this action (default is 600 seconds).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault_id** | required | The vault_id of the file to be analyzed | string | `vault id` |
**ioc_only** | optional | Only import artifacts that are IOCs | boolean | |
**file_name** | optional | The file name to use | string | `file name` |
**comment** | optional | Comment for this submission | string | |
**tags** | optional | Tags for this submission | string | |
**type** | optional | The sample type | string | |
**config** | optional | Additional configuration | string | |
**jobrules** | optional | Jobrules | string | |
**timeout** | optional | Submission timeout, default is 600 seconds | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.tags | string | | |
action_result.parameter.ioc_only | boolean | | False True |
action_result.parameter.vault_id | string | `vault id` | |
action_result.parameter.type | string | | |
action_result.parameter.jobrules | string | | |
action_result.parameter.timeout | numeric | | |
action_result.parameter.comment | string | | |
action_result.parameter.config | string | | |
action_result.parameter.file_name | string | `file name` | |
action_result.data.\*.analysis.analysis_analyzer_id | numeric | | |
action_result.data.\*.analysis.analysis_analyzer_name | string | | |
action_result.data.\*.analysis.analysis_analyzer_version | string | | |
action_result.data.\*.analysis.analysis_configuration_id | numeric | | |
action_result.data.\*.analysis.analysis_configuration_name | string | | |
action_result.data.\*.analysis.analysis_created | string | | |
action_result.data.\*.analysis.analysis_job_id | numeric | | |
action_result.data.\*.analysis.analysis_job_started | string | | |
action_result.data.\*.analysis.analysis_jobrule_id | numeric | | |
action_result.data.\*.analysis.analysis_jobrule_sampletype | string | | |
action_result.data.\*.analysis.analysis_prescript_id | numeric | | |
action_result.data.\*.analysis.analysis_priority | numeric | | |
action_result.data.\*.analysis.analysis_result_code | numeric | | |
action_result.data.\*.analysis.analysis_result_str | string | | |
action_result.data.\*.analysis.analysis_sample_id | numeric | `vmray sample id` | |
action_result.data.\*.analysis.analysis_sample_md5 | string | `md5` | |
action_result.data.\*.analysis.analysis_sample_sha1 | string | `sha1` | |
action_result.data.\*.analysis.analysis_sample_sha256 | string | `sha256` | |
action_result.data.\*.analysis.analysis_verdict | string | | |
action_result.data.\*.analysis.analysis_size | numeric | | |
action_result.data.\*.analysis.analysis_snapshot_id | numeric | | |
action_result.data.\*.analysis.analysis_snapshot_name | string | | |
action_result.data.\*.analysis.analysis_submission_id | numeric | `vmray submission id` | |
action_result.data.\*.analysis.analysis_user_email | string | | |
action_result.data.\*.analysis.analysis_user_id | numeric | | |
action_result.data.\*.analysis.analysis_vm_id | numeric | | |
action_result.data.\*.analysis.analysis_vm_name | string | | |
action_result.data.\*.analysis.analysis_vmhost_id | numeric | | |
action_result.data.\*.analysis.analysis_vmhost_name | string | | |
action_result.data.\*.analysis.analysis_vti_built_in_rules_version | string | | |
action_result.data.\*.analysis.analysis_vti_custom_rules_hash | string | | |
action_result.data.\*.analysis.analysis_vti_score | numeric | | |
action_result.data.\*.analysis.analysis_webif_url | string | | |
action_result.data.\*.analysis.analysis_yara_latest_ruleset_date | string | | |
action_result.data.\*.analysis.analysis_yara_match_count | numeric | | |
action_result.data.\*.reputation_lookup.reputation_lookup_created | string | | |
action_result.data.\*.reputation_lookup.reputation_lookup_id | numeric | | |
action_result.data.\*.reputation_lookup.reputation_lookup_job_id | numeric | | |
action_result.data.\*.reputation_lookup.reputation_lookup_result_code | numeric | | |
action_result.data.\*.reputation_lookup.reputation_lookup_sample_id | numeric | `vmray sample id` | |
action_result.data.\*.reputation_lookup.reputation_lookup_sample_md5 | string | `md5` | |
action_result.data.\*.reputation_lookup.reputation_lookup_sample_sha1 | string | `sha1` | |
action_result.data.\*.reputation_lookup.reputation_lookup_sample_sha256 | string | `sha256` | |
action_result.data.\*.reputation_lookup.reputation_lookup_verdict | string | | |
action_result.data.\*.reputation_lookup.reputation_lookup_submission_id | numeric | | |
action_result.data.\*.reputation_lookup.reputation_lookup_user_email | string | | |
action_result.data.\*.reputation_lookup.reputation_lookup_user_id | numeric | | |
action_result.data.\*.analysis.summary.extracted_files.\*.md5_hash | string | `md5` | |
action_result.data.\*.analysis.summary.extracted_files.\*.sha1_hash | string | `sha1` | |
action_result.data.\*.analysis.summary.extracted_files.\*.sha256_hash | string | `sha256` | |
action_result.data.\*.analysis.summary.extracted_files.\*.norm_filename | string | `file path` | |
action_result.data.\*.analysis.summary.artifacts.ips.\*.ip_address | string | `ip` | |
action_result.data.\*.analysis.summary.artifacts.urls.\*.url | string | `url` | |
action_result.data.\*.analysis.summary.artifacts.mutexes.\*.mutex_name | string | | |
action_result.data.\*.analysis.summary.artifacts.registry.\*.reg_key_name | string | | |
action_result.data.\*.analysis.summary.artifacts.files.\*.norm_filename | string | `file path` | |
action_result.data.\*.analysis.summary.artifacts.domains.\*.domain | string | `domain` | |
action_result.data.\*.analysis.summary.artifacts.emails.\*.sender | string | `email` | |
action_result.data.\*.analysis.summary.artifacts.emails.\*.subject | string | | |
action_result.data.\*.analysis.summary.artifacts.processes.\*.cmd_line | string | | |
action_result.data.\*.analysis.summary.mitre_attack.techniques.\*.description | string | | |
action_result.data.\*.analysis.summary.mitre_attack.techniques.\*.id | string | | |
action_result.data.\*.analysis.summary.vti.vti_rule_matches.\*.category_desc | string | | |
action_result.data.\*.analysis.summary.vti.vti_rule_matches.\*.rule_score | numeric | | |
action_result.data.\*.analysis.summary.vti.vti_rule_matches.\*.operation_desc | string | | |
action_result.data.\*.analysis.summary.vti.vti_rule_matches.\*.rule_classifications | string | | |
action_result.data.\*.analysis.summary.vti.vti_rule_matches.\*.technique_desc | string | | |
action_result.data.\*.analysis.summary.vti.vti_rule_matches.\*.threat_names.\*.name | string | | |
action_result.data.\*.analysis.analysis_id | numeric | `vmray analysis id` | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary.submission_id | numeric | `vmray submission id` | |
action_result.summary.submission_finished | boolean | | False True |
action_result.summary.verdict | string | | |
action_result.summary.url | string | | |
action_result.summary.billing_type | string | | |
action_result.summary.recursive_submission_ids.child_submission_ids.\*.child_submission_id | numeric | `vmray submission id` | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'detonate url'

Detonate a URL in the VMRay Platform

Type: **generic** \
Read only: **False**

See <b>detonate file</b> for a detailed parameter description. The <b>timeout</b> parameter specifies the time to wait for the submission to be finished before aborting this action (default is 600 seconds).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL to detonate | string | `url` |
**ioc_only** | optional | Only import artifacts that are IOCs | boolean | |
**comment** | optional | Comment for this submission | string | |
**tags** | optional | Tags added for this submission | string | |
**config** | optional | Additional configuration | string | |
**jobrules** | optional | Jobrules | string | |
**timeout** | optional | Submission timeout, default is 600 seconds | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.tags | string | | |
action_result.parameter.jobrules | string | | |
action_result.parameter.timeout | numeric | | |
action_result.parameter.comment | string | | |
action_result.parameter.config | string | | |
action_result.parameter.url | string | `url` | |
action_result.parameter.ioc_only | boolean | | False True |
action_result.data.\*.analysis.analysis_analyzer_id | numeric | | |
action_result.data.\*.analysis.analysis_analyzer_name | string | | |
action_result.data.\*.analysis.analysis_analyzer_version | string | | |
action_result.data.\*.analysis.analysis_configuration_id | numeric | | |
action_result.data.\*.analysis.analysis_configuration_name | string | | |
action_result.data.\*.analysis.analysis_created | string | | |
action_result.data.\*.analysis.analysis_id | numeric | `vmray analysis id` | |
action_result.data.\*.analysis.analysis_job_id | numeric | | |
action_result.data.\*.analysis.analysis_job_started | string | | |
action_result.data.\*.analysis.analysis_jobrule_id | numeric | | |
action_result.data.\*.analysis.analysis_jobrule_sampletype | string | | |
action_result.data.\*.analysis.analysis_prescript_id | numeric | | |
action_result.data.\*.analysis.analysis_priority | numeric | | |
action_result.data.\*.analysis.analysis_result_code | numeric | | |
action_result.data.\*.analysis.analysis_result_str | string | | |
action_result.data.\*.analysis.analysis_sample_id | numeric | `vmray sample id` | |
action_result.data.\*.analysis.analysis_sample_md5 | string | `md5` | |
action_result.data.\*.analysis.analysis_sample_sha1 | string | `sha1` | |
action_result.data.\*.analysis.analysis_sample_sha256 | string | `sha256` | |
action_result.data.\*.analysis.analysis_verdict | string | | |
action_result.data.\*.analysis.analysis_size | numeric | | |
action_result.data.\*.analysis.analysis_snapshot_id | numeric | | |
action_result.data.\*.analysis.analysis_snapshot_name | string | | |
action_result.data.\*.analysis.analysis_submission_id | numeric | `vmray submission id` | |
action_result.data.\*.analysis.analysis_user_email | string | | |
action_result.data.\*.analysis.analysis_user_id | numeric | | |
action_result.data.\*.analysis.analysis_vm_id | numeric | | |
action_result.data.\*.analysis.analysis_vm_name | string | | |
action_result.data.\*.analysis.analysis_vmhost_id | numeric | | |
action_result.data.\*.analysis.analysis_vmhost_name | string | | |
action_result.data.\*.analysis.analysis_vti_built_in_rules_version | string | | |
action_result.data.\*.analysis.analysis_vti_custom_rules_hash | string | | |
action_result.data.\*.analysis.analysis_vti_score | numeric | | |
action_result.data.\*.analysis.analysis_webif_url | string | | |
action_result.data.\*.analysis.analysis_yara_latest_ruleset_date | string | | |
action_result.data.\*.analysis.analysis_yara_match_count | numeric | | |
action_result.data.\*.reputation_lookup.reputation_lookup_created | string | | |
action_result.data.\*.reputation_lookup.reputation_lookup_id | numeric | | |
action_result.data.\*.reputation_lookup.reputation_lookup_job_id | numeric | | |
action_result.data.\*.reputation_lookup.reputation_lookup_result_code | numeric | | |
action_result.data.\*.reputation_lookup.reputation_lookup_sample_id | numeric | `vmray sample id` | |
action_result.data.\*.reputation_lookup.reputation_lookup_sample_md5 | string | `md5` | |
action_result.data.\*.reputation_lookup.reputation_lookup_sample_sha1 | string | `sha1` | |
action_result.data.\*.reputation_lookup.reputation_lookup_sample_sha256 | string | `sha256` | |
action_result.data.\*.reputation_lookup.reputation_lookup_verdict | string | | |
action_result.data.\*.reputation_lookup.reputation_lookup_submission_id | numeric | | |
action_result.data.\*.reputation_lookup.reputation_lookup_user_email | string | | |
action_result.data.\*.reputation_lookup.reputation_lookup_user_id | numeric | | |
action_result.data.\*.analysis.summary.extracted_files.\*.md5_hash | string | `md5` | |
action_result.data.\*.analysis.summary.extracted_files.\*.sha1_hash | string | `hash` `sha1` | |
action_result.data.\*.analysis.summary.extracted_files.\*.sha256_hash | string | `hash` `sha256` | |
action_result.data.\*.analysis.summary.extracted_files.\*.norm_filename | string | `file path` | |
action_result.data.\*.analysis.summary.artifacts.ips.\*.ip_address | string | `ip` | |
action_result.data.\*.analysis.summary.artifacts.urls.\*.url | string | `url` | |
action_result.data.\*.analysis.summary.artifacts.mutexes.\*.mutex_name | string | | |
action_result.data.\*.analysis.summary.artifacts.registry.\*.reg_key_name | string | | |
action_result.data.\*.analysis.summary.artifacts.files.\*.norm_filename | string | `file path` | |
action_result.data.\*.analysis.summary.artifacts.domains.\*.domain | string | `domain` | |
action_result.data.\*.analysis.summary.artifacts.emails.\*.sender | string | `email` | |
action_result.data.\*.analysis.summary.artifacts.emails.\*.subject | string | | |
action_result.data.\*.analysis.summary.artifacts.processes.\*.cmd_line | string | | |
action_result.data.\*.analysis.summary.mitre_attack.techniques.\*.description | string | | |
action_result.data.\*.analysis.summary.mitre_attack.techniques.\*.id | string | | |
action_result.data.\*.analysis.summary.vti.vti_rule_matches.\*.category_desc | string | | |
action_result.data.\*.analysis.summary.vti.vti_rule_matches.\*.rule_score | numeric | | |
action_result.data.\*.analysis.summary.vti.vti_rule_matches.\*.operation_desc | string | | |
action_result.data.\*.analysis.summary.vti.vti_rule_matches.\*.rule_classifications | string | | |
action_result.data.\*.analysis.summary.vti.vti_rule_matches.\*.technique_desc | string | | |
action_result.data.\*.analysis.summary.vti.vti_rule_matches.\*.threat_names.\*.name | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary.submission_id | numeric | `vmray submission id` | |
action_result.summary.submission_finished | boolean | | False True |
action_result.summary.verdict | string | | |
action_result.summary.url | string | | |
action_result.summary.billing_type | string | | |
action_result.summary.recursive_submission_ids.child_submission_ids.\*.child_submission_id | numeric | `vmray submission id` | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get iocs'

Get the iocs for a sample

Type: **investigate** \
Read only: **True**

This action requires a <b>sample_id</b>. The <b>timeout</b> parameter specifies the time to wait for the vtis to be finished before aborting this action. The <b>timeout</b> is specified in seconds. Zero indicates no wait, hence the action will return immediately. If this option is not set it will default to a ten-minute timeout. The <b>all_artifacts</b> parameter specifies whether to consider all artifacts when retrieving a sample's iocs.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**sample_id** | required | The VMRay Platform sample ID | numeric | `vmray sample id` |
**timeout** | optional | Timeout | numeric | |
**all_artifacts** | optional | All artifacts | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.sample_id | numeric | `vmray sample id` | |
action_result.parameter.timeout | numeric | | |
action_result.parameter.all_artifacts | boolean | | |
action_result.data.iocs.domains | string | | |
action_result.data.iocs.email_addresses | string | | |
action_result.data.iocs.emails | string | | |
action_result.data.iocs.filenames | string | | |
action_result.data.iocs.files | string | | |
action_result.data.iocs.ips | string | | |
action_result.data.iocs.mutexes | string | | |
action_result.data.iocs.processes | string | | |
action_result.data.iocs.registry | string | | |
action_result.data.iocs.urls | string | | |
action_result.data.sample_verdict | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.parameter.sample_id | numeric | `vmray sample id` | |
action_result.summary.sample_verdict | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get vtis'

Get the vtis for a sample

Type: **investigate** \
Read only: **True**

This action requires a <b>sample_id</b>. The <b>timeout</b> parameter specifies the time to wait for the vtis to be finished before aborting this action. The <b>timeout</b> is specified in seconds. Zero indicates no wait, hence the action will return immediately. If this option is not set it will default to a ten-minute timeout.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**sample_id** | required | The VMRay Platform sample ID | numeric | `vmray sample id` |
**timeout** | optional | Timeout | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.sample_id | numeric | `vmray sample id` | |
action_result.parameter.timeout | numeric | | |
action_result.data.vtis.\*.analysis_ids | string | | |
action_result.data.vtis.\*.category | string | | |
action_result.data.vtis.\*.classifications | string | | |
action_result.data.vtis.\*.id | numeric | | |
action_result.data.vtis.\*.operation | string | | |
action_result.data.vtis.\*.score | numeric | | |
action_result.data.sample_verdict | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary.vtis.\*.analysis_ids | numeric | | |
action_result.summary.vtis.\*.category | string | | |
action_result.summary.vtis.\*.classifications | string | | |
action_result.summary.vtis.\*.id | numeric | | |
action_result.summary.vtis.\*.score | numeric | | |
action_result.summary.vtis.\*.operation | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get report'

Get the report(s) for a submission

Type: **investigate** \
Read only: **True**

This action requires a <b>submission_id</b>. The <b>timeout</b> parameter specifies the time to wait for the report to be finished before aborting this action. The <b>timeout</b> is specified in seconds. Zero indicates no wait, hence the action will return immediately. If this option is not set it will default to a five-minute timeout.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**submission_id** | required | The VMRay Platform submission ID | numeric | `vmray submission id` |
**ioc_only** | optional | Only import artifacts that are IOCs | boolean | |
**timeout** | optional | Timeout | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.submission_id | numeric | `vmray submission id` | |
action_result.parameter.ioc_only | boolean | | False True |
action_result.parameter.timeout | numeric | | |
action_result.data.\*.analysis.analysis_analyzer_id | numeric | | |
action_result.data.\*.analysis.analysis_analyzer_name | string | | |
action_result.data.\*.analysis.analysis_analyzer_version | string | | |
action_result.data.\*.analysis.analysis_configuration_id | numeric | | |
action_result.data.\*.analysis.analysis_configuration_name | string | | |
action_result.data.\*.analysis.analysis_created | string | | |
action_result.data.\*.analysis.analysis_id | numeric | `vmray analysis id` | |
action_result.data.\*.analysis.analysis_job_id | numeric | | |
action_result.data.\*.analysis.analysis_job_started | string | | |
action_result.data.\*.analysis.analysis_jobrule_id | numeric | | |
action_result.data.\*.analysis.analysis_jobrule_sampletype | string | | |
action_result.data.\*.analysis.analysis_prescript_id | numeric | | |
action_result.data.\*.analysis.analysis_priority | numeric | | |
action_result.data.\*.analysis.analysis_result_code | numeric | | |
action_result.data.\*.analysis.analysis_result_str | string | | |
action_result.data.\*.analysis.analysis_sample_id | numeric | `vmray sample id` | |
action_result.data.\*.analysis.analysis_sample_md5 | string | `md5` | |
action_result.data.\*.analysis.analysis_sample_sha1 | string | `sha1` | |
action_result.data.\*.analysis.analysis_sample_sha256 | string | `sha256` | |
action_result.data.\*.analysis.analysis_verdict | string | | |
action_result.data.\*.analysis.analysis_size | numeric | | |
action_result.data.\*.analysis.analysis_snapshot_id | numeric | | |
action_result.data.\*.analysis.analysis_snapshot_name | string | | |
action_result.data.\*.analysis.analysis_submission_id | numeric | `vmray submission id` | |
action_result.data.\*.analysis.analysis_user_email | string | | |
action_result.data.\*.analysis.analysis_user_id | numeric | | |
action_result.data.\*.analysis.analysis_vm_id | numeric | | |
action_result.data.\*.analysis.analysis_vm_name | string | | |
action_result.data.\*.analysis.analysis_vmhost_id | numeric | | |
action_result.data.\*.analysis.analysis_vmhost_name | string | | |
action_result.data.\*.analysis.analysis_vti_built_in_rules_version | string | | |
action_result.data.\*.analysis.analysis_vti_custom_rules_hash | string | | |
action_result.data.\*.analysis.analysis_vti_score | numeric | | |
action_result.data.\*.analysis.analysis_webif_url | string | | |
action_result.data.\*.analysis.analysis_yara_latest_ruleset_date | string | | |
action_result.data.\*.analysis.analysis_yara_match_count | numeric | | |
action_result.data.\*.reputation_lookup.reputation_lookup_created | string | | |
action_result.data.\*.reputation_lookup.reputation_lookup_id | numeric | | |
action_result.data.\*.reputation_lookup.reputation_lookup_job_id | numeric | | |
action_result.data.\*.reputation_lookup.reputation_lookup_result_code | numeric | | |
action_result.data.\*.reputation_lookup.reputation_lookup_sample_id | numeric | `vmray sample id` | |
action_result.data.\*.reputation_lookup.reputation_lookup_sample_md5 | string | `md5` | |
action_result.data.\*.reputation_lookup.reputation_lookup_sample_sha1 | string | `sha1` | |
action_result.data.\*.reputation_lookup.reputation_lookup_sample_sha256 | string | `sha256` | |
action_result.data.\*.reputation_lookup.reputation_lookup_verdict | string | | |
action_result.data.\*.reputation_lookup.reputation_lookup_submission_id | numeric | | |
action_result.data.\*.reputation_lookup.reputation_lookup_user_email | string | | |
action_result.data.\*.reputation_lookup.reputation_lookup_user_id | numeric | | |
action_result.data.\*.analysis.summary.extracted_files.\*.md5_hash | string | `md5` | |
action_result.data.\*.analysis.summary.extracted_files.\*.sha1_hash | string | `sha1` | |
action_result.data.\*.analysis.summary.extracted_files.\*.sha256_hash | string | `sha256` | |
action_result.data.\*.analysis.summary.extracted_files.\*.norm_filename | string | `file path` | |
action_result.data.\*.analysis.summary.artifacts.ips.\*.ip_address | string | `ip` | |
action_result.data.\*.analysis.summary.artifacts.urls.\*.url | string | `url` | |
action_result.data.\*.analysis.summary.artifacts.mutexes.\*.mutex_name | string | | |
action_result.data.\*.analysis.summary.artifacts.registry.\*.reg_key_name | string | | |
action_result.data.\*.analysis.summary.artifacts.files.\*.norm_filename | string | `file path` | |
action_result.data.\*.analysis.summary.artifacts.domains.\*.domain | string | `domain` | |
action_result.data.\*.analysis.summary.artifacts.emails.\*.sender | string | `email` | |
action_result.data.\*.analysis.summary.artifacts.emails.\*.subject | string | | |
action_result.data.\*.analysis.summary.artifacts.processes.\*.cmd_line | string | | |
action_result.data.\*.analysis.summary.mitre_attack.techniques.\*.description | string | | |
action_result.data.\*.analysis.summary.mitre_attack.techniques.\*.id | string | | |
action_result.data.\*.analysis.summary.vti.vti_rule_matches.\*.category_desc | string | | |
action_result.data.\*.analysis.summary.vti.vti_rule_matches.\*.rule_score | numeric | | |
action_result.data.\*.analysis.summary.vti.vti_rule_matches.\*.operation_desc | string | | |
action_result.data.\*.analysis.summary.vti.vti_rule_matches.\*.rule_classifications | string | | |
action_result.data.\*.analysis.summary.vti.vti_rule_matches.\*.technique_desc | string | | |
action_result.data.\*.analysis.summary.vti.vti_rule_matches.\*.threat_names.\*.name | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary.submission_id | numeric | `vmray submission id` | |
action_result.summary.verdict | string | | |
action_result.summary.url | numeric | | |
action_result.summary.billing_type | string | | |
action_result.summary.recursive_submission_ids.child_submission_ids.\*.child_submission_id | numeric | `vmray submission id` | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get info'

Get information of a specific sample

Type: **investigate** \
Read only: **True**

This action gets information about a sample given its <b>hash</b>. See <b>get report</b> for a description of the <b>timeout</b> parameter.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | The sample hash | string | `hash` `sha256` `sha1` `md5` |
**timeout** | optional | Timeout | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.hash | string | `hash` `md5` `sha1` `sha256` | |
action_result.parameter.timeout | numeric | | |
action_result.data.\*.sample_type | string | | |
action_result.data.\*.sample_created | string | | |
action_result.data.\*.sample_filename | string | `file name` | |
action_result.data.\*.sample_filesize | numeric | | |
action_result.data.\*.sample_highest_vti_score | numeric | | |
action_result.data.\*.sample_id | numeric | `vmray sample id` | |
action_result.data.\*.sample_is_multipart | boolean | | False True |
action_result.data.\*.sample_last_md_score | numeric | | |
action_result.data.\*.sample_last_vt_score | numeric | | |
action_result.data.\*.sample_md5hash | string | `md5` | |
action_result.data.\*.sample_priority | numeric | | |
action_result.data.\*.sample_score | numeric | | |
action_result.data.\*.sample_verdict | string | | |
action_result.data.\*.sample_sha1hash | string | `sha1` | |
action_result.data.\*.sample_sha256hash | string | `sha256` | |
action_result.data.\*.sample_url | string | `url` | |
action_result.data.\*.sample_vti_score | numeric | | |
action_result.data.\*.sample_webif_url | string | | |
action_result.data.\*.sample_classifications | string | | |
action_result.data.\*.sample_threat_names | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary.score | numeric | | |
action_result.summary.verdict | string | | |
action_result.summary.recursive_sample_ids.parent_sample_ids.\*.parent_sample_id | numeric | `vmray sample id` | |
action_result.summary.recursive_sample_ids.child_sample_ids.\*.child_sample_id | numeric | `vmray sample id` | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get screenshots'

Get screenshots from an analysis

Type: **investigate** \
Read only: **True**

This action will download screenshots taken from a specific dynamic analysis identified by <b>analysis_id</b> and store them in the vault. The screenshots are stored with file names like <b>analysis_5_screenshot_2.png</b>. In this example, '5' represents the analysis ID from which the screenshot came, and '2' indicates that it's the third screenshot taken during the analysis, in chronological order.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**analysis_id** | required | The VMRay Platform analysis ID | numeric | `vmray analysis id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.analysis_id | numeric | `vmray analysis id` | |
action_result.data.\*.file_name | string | | analysis_5_screenshot_2.png |
action_result.data.\*.vault_id | string | `vault id` | |
action_result.summary.downloaded_screenshots | numeric | | 7 |
action_result.status | string | | success failed |
action_result.message | string | | |
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
