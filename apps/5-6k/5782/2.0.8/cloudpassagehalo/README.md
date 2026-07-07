# CloudPassage Halo

Publisher: Splunk \
Connector Version: 2.0.8 \
Product Vendor: CloudPassage \
Product Name: CloudPassage Halo \
Minimum Product Version: 5.1.0

This app supports a variety of investigative actions on CloudPassage Halo

### Configuration variables

This table lists the configuration variables required to operate CloudPassage Halo. These variables are specified when configuring a CloudPassage Halo asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**url** | required | string | URL (eg: https://api.cloudpassage.com) |
**client_id** | required | string | Client ID |
**client_secret** | required | password | Client secret |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate credentials provided for connectivity \
[get system info](#action-get-system-info) - Get information about a server \
[list packages](#action-list-packages) - List all packages on a given server \
[get package](#action-get-package) - Get information about a package \
[list processes](#action-list-processes) - List all processes on a given server \
[get process](#action-get-process) - Get information about a process \
[list vulnerabilities](#action-list-vulnerabilities) - List all vulnerabilities on a given server \
[get vulnerability](#action-get-vulnerability) - Get information about a vulnerability \
[list users](#action-list-users) - List all users on a given server \
[get user](#action-get-user) - Get information about a user \
[list servers](#action-list-servers) - List all servers for a given user, process, package and vulnerability

## action: 'test connectivity'

Validate credentials provided for connectivity

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'get system info'

Get information about a server

Type: **investigate** \
Read only: **True**

At least one parameter out of <b>aws_instance_id</b>, <b>ip</b> and <b>hostname</b> is mandatory. When we get multiple servers with same hostname, we will consider first matching server if in case user only provides the hostname in input parameters(aws_instance_id/ip/hostname).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**aws_instance_id** | optional | AWS instance ID | string | `cloudpassagehalo aws instance id` |
**ip** | optional | IP | string | `ip` |
**hostname** | optional | Hostname | string | `host name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.created_at | string | | 2021-08-02T09:36:33.082Z |
action_result.data.\*.group_path | string | | Splunk Phantom |
action_result.data.\*.interfaces.\*.mac_address | string | | |
action_result.data.\*.docker_labels | string | | |
action_result.data.\*.docker_running | boolean | | True False |
action_result.data.\*.docker_version | string | | |
action_result.data.\*.docker_installed | boolean | | True False |
action_result.data.\*.docker_inspection | string | | Disabled |
action_result.data.\*.docker_parameters | string | | |
action_result.data.\*.containerd_running | boolean | | True False |
action_result.data.\*.containerd_version | string | | |
action_result.data.\*.container_inspection | string | | Disabled |
action_result.data.\*.containerd_installed | boolean | | True False |
action_result.data.\*.containerd_parameters | string | | |
action_result.data.\*.agent_distribution_type | string | | software |
action_result.data.\*.read_only | boolean | | |
action_result.data.\*.self_verification_failed | boolean | | |
action_result.data.\*.kernel_machine | string | | |
action_result.data.\*.state | string | | |
action_result.data.\*.url | string | `url` | |
action_result.data.\*.interfaces.\*.netmask | string | | |
action_result.data.\*.interfaces.\*.ip_address | string | `ip` | |
action_result.data.\*.interfaces.\*.name | string | | |
action_result.data.\*.interfaces.\*.display_name | string | | |
action_result.data.\*.hostname | string | `host name` | |
action_result.data.\*.last_state_change | string | | |
action_result.data.\*.primary_ip_address | string | `ip` | |
action_result.data.\*.connecting_ip_fqdn | string | | |
action_result.data.\*.daemon_version | string | | |
action_result.data.\*.platform_version | string | | |
action_result.data.\*.reported_fqdn | string | | |
action_result.data.\*.server_label | string | | |
action_result.data.\*.os_version | string | | |
action_result.data.\*.platform | string | | |
action_result.data.\*.connecting_ip_address | string | `ip` | |
action_result.data.\*.kernel_name | string | | |
action_result.data.\*.group_id | string | | |
action_result.data.\*.group_name | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.firewall_policy | string | | |
action_result.data.\*.firewall_policy.status | string | | |
action_result.data.\*.firewall_policy.name | string | | |
action_result.data.\*.firewall_policy.url | string | `url` | |
action_result.data.\*.firewall_policy.installed | string | | |
action_result.data.\*.firewall_policy.last_checked | string | | |
action_result.data.\*.firewall_policy.id | string | | |
action_result.data.\*.aws_ec2.ec2_account_id | string | | |
action_result.data.\*.aws_ec2.ec2_security_groups | string | | |
action_result.data.\*.aws_ec2.ec2_availability_zone | string | | |
action_result.data.\*.aws_ec2.ec2_instance_type | string | | |
action_result.data.\*.aws_ec2.ec2_instance_id | string | `cloudpassagehalo aws instance id` | |
action_result.data.\*.aws_ec2.ec2_private_ip | string | `ip` | |
action_result.data.\*.aws_ec2.ec2_kernel_id | string | | |
action_result.data.\*.aws_ec2.ec2_image_id | string | | |
action_result.data.\*.aws_ec2.ec2_region | string | | |
action_result.data.\*.proxy | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.parameter.aws_instance_id | string | `cloudpassagehalo aws instance id` | |
action_result.parameter.ip | string | `ip` | 127.0.0.1 |
action_result.parameter.hostname | string | `host name` | localhost |
action_result.summary.reported_fqdn | string | | |
action_result.summary.primary_ip_address | string | | |
action_result.summary.hostname | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list packages'

List all packages on a given server

Type: **investigate** \
Read only: **True**

At least one parameter out of <b>aws_instance_id</b>, <b>ip</b> and <b>hostname</b> is mandatory. When we get multiple servers with same hostname, we will consider first matching server if in case user only provides the hostname in input parameters(aws_instance_id/ip/hostname).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**aws_instance_id** | optional | AWS instance ID | string | `cloudpassagehalo aws instance id` |
**ip** | optional | IP | string | `ip` |
**hostname** | optional | Hostname | string | `host name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.max_cvss | numeric | | 9.8 |
action_result.data.\*.cve_entries.\*.cvss_version | numeric | | 3.1 |
action_result.data.\*.cve_entries.\*.remotely_exploitable | boolean | | True False |
action_result.data.\*.remotely_exploitable | boolean | | True False |
action_result.data.\*.status | string | | |
action_result.data.\*.vendor | string | | |
action_result.data.\*.package_name | string | `cloudpassagehalo package name` | |
action_result.data.\*.url | string | `url` | |
action_result.data.\*.package_version | string | | |
action_result.data.\*.cpe | string | | |
action_result.data.\*.critical | boolean | | |
action_result.data.\*.cve_entries.\*.cve_entry | string | `cloudpassagehalo cve number` | |
action_result.data.\*.cve_entries.\*.cvss_score | numeric | | |
action_result.data.\*.cve_entries.\*.suppressed | boolean | | |
action_result.data.\*.id | string | | |
action_result.data.\*.install_date | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.parameter.aws_instance_id | string | `cloudpassagehalo aws instance id` | |
action_result.parameter.ip | string | `ip` | 127.0.0.1 |
action_result.parameter.hostname | string | `host name` | localhost |
action_result.summary.total_packages | numeric | | |
action_result.summary.reported_fqdn | string | | |
action_result.summary.primary_ip_address | string | | |
action_result.summary.hostname | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get package'

Get information about a package

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**package_name** | required | Package name | string | `cloudpassagehalo package name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.max_cvss | numeric | | 9.8 |
action_result.data.\*.cve_entries.\*.cvss_version | numeric | | 3.1 |
action_result.data.\*.cve_entries.\*.remotely_exploitable | boolean | | True False |
action_result.data.\*.remotely_exploitable | boolean | | True False |
action_result.data.\*.server_info_primary_ip_address | string | `ip` | |
action_result.data.\*.server_info_hostname | string | `host name` | |
action_result.data.\*.server_info_id | string | | |
action_result.data.\*.server_info_ec2_instance_id | string | `cloudpassagehalo aws instance id` | |
action_result.data.\*.id | string | | |
action_result.data.\*.cpe | string | | |
action_result.data.\*.url | string | `url` | |
action_result.data.\*.status | string | | |
action_result.data.\*.vendor | string | | |
action_result.data.\*.critical | boolean | | |
action_result.data.\*.install_date | string | | |
action_result.data.\*.package_name | string | `cloudpassagehalo package name` | |
action_result.data.\*.package_version | string | | |
action_result.data.\*.cve_entries.\*.cve_entry | string | `cloudpassagehalo cve number` | |
action_result.data.\*.cve_entries.\*.cvss_score | numeric | | |
action_result.data.\*.cve_entries.\*.suppressed | boolean | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.parameter.package_name | string | `cloudpassagehalo package name` | curl.x86_64 |
action_result.summary.total_packages | numeric | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list processes'

List all processes on a given server

Type: **investigate** \
Read only: **True**

At least one parameter out of <b>aws_instance_id</b>, <b>ip</b> and <b>hostname</b> is mandatory. When we get multiple servers with same hostname, we will consider first matching server if in case user only provides the hostname in input parameters(aws_instance_id/ip/hostname).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**aws_instance_id** | optional | AWS instance ID | string | `cloudpassagehalo aws instance id` |
**ip** | optional | IP | string | `ip` |
**hostname** | optional | Hostname | string | `host name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.pid | string | `pid` | |
action_result.data.\*.ppid | string | `pid` | |
action_result.data.\*.user | string | | |
action_result.data.\*.state | string | | |
action_result.data.\*.command | string | | |
action_result.data.\*.cpu_percent | string | | |
action_result.data.\*.cpu_usage | string | | |
action_result.data.\*.memory_usage | string | | |
action_result.data.\*.process_name | string | `process name` | |
action_result.data.\*.memory_percent | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.parameter.aws_instance_id | string | `cloudpassagehalo aws instance id` | |
action_result.parameter.ip | string | `ip` | 127.0.0.1 |
action_result.parameter.hostname | string | `host name` | localhost |
action_result.summary.total_processes | numeric | | |
action_result.summary.reported_fqdn | string | | |
action_result.summary.primary_ip_address | string | | |
action_result.summary.hostname | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get process'

Get information about a process

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**process_name** | required | Process name | string | `process name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.server_info_primary_ip_address | string | `ip` | |
action_result.data.\*.server_info_hostname | string | `host name` | |
action_result.data.\*.server_info_id | string | | |
action_result.data.\*.server_info_ec2_instance_id | string | `cloudpassagehalo aws instance id` | |
action_result.data.\*.pid | string | `pid` | |
action_result.data.\*.ppid | string | `pid` | |
action_result.data.\*.user | string | | |
action_result.data.\*.state | string | | |
action_result.data.\*.command | string | | |
action_result.data.\*.cpu_percent | string | | |
action_result.data.\*.cpu_usage | string | | |
action_result.data.\*.memory_usage | string | | |
action_result.data.\*.process_name | string | `process name` | |
action_result.data.\*.memory_percent | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.parameter.process_name | string | `process name` | ata_sff |
action_result.summary.total_processes | numeric | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list vulnerabilities'

List all vulnerabilities on a given server

Type: **investigate** \
Read only: **True**

At least one parameter out of <b>aws_instance_id</b>, <b>ip</b> and <b>hostname</b> is mandatory. When we get multiple servers with same hostname, we will consider first matching server if in case user only provides the hostname in input parameters(aws_instance_id/ip/hostname).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**aws_instance_id** | optional | AWS instance ID | string | `cloudpassagehalo aws instance id` |
**ip** | optional | IP | string | `ip` |
**hostname** | optional | Hostname | string | `host name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.scan.findings.\*.max_cvss | numeric | | 9.8 |
action_result.data.\*.scan.findings.\*.cve_entries.\*.cvss_version | numeric | | 3.1 |
action_result.data.\*.scan.findings.\*.cve_entries.\*.remotely_exploitable | boolean | | True False |
action_result.data.\*.scan.findings.\*.remotely_exploitable | boolean | | True False |
action_result.data.\*.id | string | | |
action_result.data.\*.hostname | string | `host name` | |
action_result.data.\*.connecting_ip_address | string | `ip` | |
action_result.data.\*.state | string | | |
action_result.data.\*.scan.id | string | | |
action_result.data.\*.scan.url | string | `url` | |
action_result.data.\*.scan.module | string | | |
action_result.data.\*.scan.status | string | | |
action_result.data.\*.scan.created_at | string | | |
action_result.data.\*.scan.completed_at | string | | |
action_result.data.\*.scan.analysis_started_at | string | | |
action_result.data.\*.scan.analysis_completed_at | string | | |
action_result.data.\*.scan.agent_started_at | string | | |
action_result.data.\*.scan.agent_completed_at | string | | |
action_result.data.\*.scan.server_id | string | | |
action_result.data.\*.scan.server_hostname | string | `host name` | |
action_result.data.\*.scan.server_url | string | `url` | |
action_result.data.\*.scan.critical_findings_count | numeric | | |
action_result.data.\*.scan.non_critical_findings_count | numeric | | |
action_result.data.\*.scan.ok_findings_count | numeric | | |
action_result.data.\*.scan.findings.\*.id | string | | |
action_result.data.\*.scan.findings.\*.url | string | `url` | |
action_result.data.\*.scan.findings.\*.package_name | string | `cloudpassagehalo package name` | |
action_result.data.\*.scan.findings.\*.package_version | string | | |
action_result.data.\*.scan.findings.\*.critical | boolean | | |
action_result.data.\*.scan.findings.\*.status | string | | |
action_result.data.\*.scan.findings.\*.cve_entries.\*.cve_entry | string | `cloudpassagehalo cve number` | |
action_result.data.\*.scan.findings.\*.cve_entries.\*.cvss_score | numeric | | |
action_result.data.\*.scan.findings.\*.cve_entries.\*.suppressed | boolean | | |
action_result.data.\*.scan.findings.\*.cpe | string | | |
action_result.data.\*.scan.findings.\*.vendor | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.parameter.aws_instance_id | string | `cloudpassagehalo aws instance id` | |
action_result.parameter.ip | string | `ip` | 127.0.0.1 |
action_result.parameter.hostname | string | `host name` | localhost |
action_result.summary.critical_packages_count | numeric | | |
action_result.summary.non_critical_packages_count | numeric | | |
action_result.summary.ok_packages_count | numeric | | |
action_result.summary.reported_fqdn | string | | |
action_result.summary.primary_ip_address | string | | |
action_result.summary.hostname | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get vulnerability'

Get information about a vulnerability

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**cve_number** | required | Common Vulnerability and Exposure number | string | `cloudpassagehalo cve number` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.scan.findings.\*.max_cvss | numeric | | 8.8 |
action_result.data.\*.scan.findings.\*.cve_entries.\*.cvss_version | numeric | | 3.1 |
action_result.data.\*.scan.findings.\*.cve_entries.\*.remotely_exploitable | boolean | | True False |
action_result.data.\*.scan.findings.\*.remotely_exploitable | boolean | | True False |
action_result.data.\*.server_info_primary_ip_address | string | `ip` | |
action_result.data.\*.server_info_hostname | string | `host name` | |
action_result.data.\*.server_info_id | string | | |
action_result.data.\*.server_info_ec2_instance_id | string | `cloudpassagehalo aws instance id` | |
action_result.data.\*.id | string | | |
action_result.data.\*.hostname | string | `host name` | |
action_result.data.\*.connecting_ip_address | string | `ip` | |
action_result.data.\*.state | string | | |
action_result.data.\*.scan.id | string | | |
action_result.data.\*.scan.url | string | `url` | |
action_result.data.\*.scan.module | string | | |
action_result.data.\*.scan.status | string | | |
action_result.data.\*.scan.findings.\*.id | string | | |
action_result.data.\*.scan.findings.\*.cpe | string | | |
action_result.data.\*.scan.findings.\*.url | string | `url` | |
action_result.data.\*.scan.findings.\*.status | string | | |
action_result.data.\*.scan.findings.\*.vendor | string | | |
action_result.data.\*.scan.findings.\*.critical | boolean | | |
action_result.data.\*.scan.findings.\*.cve_entries.\*.cve_entry | string | `cloudpassagehalo cve number` | |
action_result.data.\*.scan.findings.\*.cve_entries.\*.cvss_score | numeric | | |
action_result.data.\*.scan.findings.\*.cve_entries.\*.suppressed | boolean | | |
action_result.data.\*.scan.findings.\*.package_name | string | `cloudpassagehalo package name` | |
action_result.data.\*.scan.findings.\*.package_version | string | | |
action_result.data.\*.scan.findings.\*.install_date | string | | |
action_result.data.\*.scan.server_id | string | | |
action_result.data.\*.scan.created_at | string | | |
action_result.data.\*.scan.server_url | string | `url` | |
action_result.data.\*.scan.completed_at | string | | |
action_result.data.\*.scan.server_hostname | string | `host name` | |
action_result.data.\*.scan.agent_started_at | string | | |
action_result.data.\*.scan.ok_findings_count | numeric | | |
action_result.data.\*.scan.agent_completed_at | string | | |
action_result.data.\*.scan.analysis_started_at | string | | |
action_result.data.\*.scan.analysis_completed_at | string | | |
action_result.data.\*.scan.critical_findings_count | numeric | | |
action_result.data.\*.scan.non_critical_findings_count | numeric | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.parameter.cve_number | string | `cloudpassagehalo cve number` | CVE-2020-25695 |
action_result.summary.total_servers | numeric | | |
action_result.summary.total_critical_findings_count | numeric | | |
action_result.summary.total_non_critical_findings_count | numeric | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list users'

List all users on a given server

Type: **investigate** \
Read only: **True**

At least one parameter out of <b>aws_instance_id</b>, <b>ip</b> and <b>hostname</b> is mandatory. When we get multiple servers with same hostname, we will consider first matching server if in case user only provides the hostname in input parameters(aws_instance_id/ip/hostname).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**aws_instance_id** | optional | AWS instance ID | string | `cloudpassagehalo aws instance id` |
**ip** | optional | IP | string | `ip` |
**hostname** | optional | Hostname | string | `host name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.groups | string | | adm |
action_result.data.\*.expires | string | | |
action_result.data.\*.home_exists | boolean | | True False |
action_result.data.\*.sudo_access | string | | |
action_result.data.\*.last_login_from | string | | |
action_result.data.\*.password_locked | boolean | | True False |
action_result.data.\*.password_expired | boolean | | True False |
action_result.data.\*.password_expires | string | | |
action_result.data.\*.last_password_change | string | | 2016-11-05T00:00:00.000Z |
action_result.data.\*.password_locked_with | string | | |
action_result.data.\*.disabled_after_days_inactive | numeric | | 0 |
action_result.data.\*.days_warn_before_password_expiration | numeric | | 7 |
action_result.data.\*.maximum_days_between_password_changes | numeric | | 99999 |
action_result.data.\*.minimum_days_between_password_changes | numeric | | 0 |
action_result.data.\*.gid | string | | |
action_result.data.\*.uid | string | | |
action_result.data.\*.sid | string | | |
action_result.data.\*.url | string | `url` | |
action_result.data.\*.home | string | | |
action_result.data.\*.admin | boolean | | |
action_result.data.\*.shell | string | | |
action_result.data.\*.active | boolean | | |
action_result.data.\*.comment | string | | |
action_result.data.\*.locked | boolean | | |
action_result.data.\*.os_type | string | | |
action_result.data.\*.group_id | string | | |
action_result.data.\*.username | string | `user name` | |
action_result.data.\*.server_id | string | | |
action_result.data.\*.server_name | string | `host name` | |
action_result.data.\*.server_label | string | | |
action_result.data.\*.last_login_at | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.parameter.aws_instance_id | string | `cloudpassagehalo aws instance id` | |
action_result.parameter.ip | string | `ip` | 127.0.0.1 |
action_result.parameter.hostname | string | `host name` | localhost |
action_result.summary.total_users | numeric | | |
action_result.summary.reported_fqdn | string | | |
action_result.summary.primary_ip_address | string | | |
action_result.summary.hostname | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get user'

Get information about a user

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | required | Username | string | `user name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.account.password_locked | boolean | | True False |
action_result.data.\*.account.password_locked_with | string | | |
action_result.data.\*.full_name | string | | |
action_result.data.\*.server_info_primary_ip_address | string | `ip` | |
action_result.data.\*.server_info_hostname | string | `host name` | |
action_result.data.\*.server_info_id | string | | |
action_result.data.\*.server_info_ec2_instance_id | string | `cloudpassagehalo aws instance id` | |
action_result.data.\*.account.gid | string | | |
action_result.data.\*.account.uid | string | | |
action_result.data.\*.account.sid | string | | |
action_result.data.\*.account.url | string | `url` | |
action_result.data.\*.account.home | string | | |
action_result.data.\*.account.admin | boolean | | |
action_result.data.\*.account.shell | string | | |
action_result.data.\*.account.active | boolean | | |
action_result.data.\*.account.groups | string | | |
action_result.data.\*.account.comment | string | | |
action_result.data.\*.account.locked | boolean | | |
action_result.data.\*.account.ssh_acl | string | | |
action_result.data.\*.account.username | string | `user name` | |
action_result.data.\*.account.full_name | string | | |
action_result.data.\*.account.home_exists | boolean | | |
action_result.data.\*.account.password_required | boolean | | |
action_result.data.\*.account.password_changeable | boolean | | |
action_result.data.\*.account.sudo_access | string | | |
action_result.data.\*.account.sudo_access.\*.as_user.\* | string | | |
action_result.data.\*.account.last_login_at | string | | |
action_result.data.\*.account.last_login_from | string | | |
action_result.data.\*.account.days_since_disabled | numeric | | |
action_result.data.\*.account.last_password_change | string | | |
action_result.data.\*.account.expires | string | | |
action_result.data.\*.account.disabled_after_days_inactive | numeric | | |
action_result.data.\*.account.days_warn_before_password_expiration | numeric | | |
action_result.data.\*.account.maximum_days_between_password_changes | numeric | | |
action_result.data.\*.account.minimum_days_between_password_changes | numeric | | |
action_result.data.\*.account.password_expires | string | | |
action_result.data.\*.account.password_expired | boolean | | |
action_result.data.\*.account.ssh_authorized_keys | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.parameter.username | string | `user name` | phantom |
action_result.summary.total_users | numeric | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list servers'

List all servers for a given user, process, package and vulnerability

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | optional | Username | string | `user name` |
**process_name** | optional | Process name | string | `process name` |
**package_name** | optional | Package name | string | `cloudpassagehalo package name` |
**cve_number** | optional | Common Vulnerability and Exposure number | string | `cloudpassagehalo cve number` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.created_at | string | | 2021-08-02T09:36:33.082Z |
action_result.data.\*.group_path | string | | Splunk Phantom |
action_result.data.\*.interfaces.\*.mac_address | string | | |
action_result.data.\*.docker_labels | string | | |
action_result.data.\*.docker_running | boolean | | True False |
action_result.data.\*.docker_version | string | | |
action_result.data.\*.docker_installed | boolean | | True False |
action_result.data.\*.docker_inspection | string | | Disabled |
action_result.data.\*.docker_parameters | string | | |
action_result.data.\*.containerd_running | boolean | | True False |
action_result.data.\*.containerd_version | string | | |
action_result.data.\*.container_inspection | string | | Disabled |
action_result.data.\*.containerd_installed | boolean | | True False |
action_result.data.\*.containerd_parameters | string | | |
action_result.data.\*.agent_distribution_type | string | | software |
action_result.data.\*.read_only | boolean | | |
action_result.data.\*.self_verification_failed | boolean | | |
action_result.data.\*.kernel_machine | string | | |
action_result.data.\*.state | string | | |
action_result.data.\*.url | string | `url` | |
action_result.data.\*.interfaces.\*.netmask | string | | |
action_result.data.\*.interfaces.\*.ip_address | string | `ip` | |
action_result.data.\*.interfaces.\*.name | string | | |
action_result.data.\*.interfaces.\*.display_name | string | | |
action_result.data.\*.hostname | string | `host name` | |
action_result.data.\*.last_state_change | string | | |
action_result.data.\*.primary_ip_address | string | `ip` | |
action_result.data.\*.connecting_ip_fqdn | string | | |
action_result.data.\*.daemon_version | string | | |
action_result.data.\*.platform_version | string | | |
action_result.data.\*.reported_fqdn | string | | |
action_result.data.\*.server_label | string | | |
action_result.data.\*.os_version | string | | |
action_result.data.\*.platform | string | | |
action_result.data.\*.connecting_ip_address | string | `ip` | |
action_result.data.\*.kernel_name | string | | |
action_result.data.\*.group_id | string | | |
action_result.data.\*.group_name | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.firewall_policy | string | | |
action_result.data.\*.firewall_policy.status | string | | |
action_result.data.\*.firewall_policy.name | string | | |
action_result.data.\*.firewall_policy.url | string | `url` | |
action_result.data.\*.firewall_policy.installed | string | | |
action_result.data.\*.firewall_policy.last_checked | string | | |
action_result.data.\*.firewall_policy.id | string | | |
action_result.data.\*.aws_ec2.ec2_account_id | string | | |
action_result.data.\*.aws_ec2.ec2_security_groups | string | | |
action_result.data.\*.aws_ec2.ec2_availability_zone | string | | |
action_result.data.\*.aws_ec2.ec2_instance_type | string | | |
action_result.data.\*.aws_ec2.ec2_instance_id | string | `cloudpassagehalo aws instance id` | |
action_result.data.\*.aws_ec2.ec2_private_ip | string | `ip` | |
action_result.data.\*.aws_ec2.ec2_kernel_id | string | | |
action_result.data.\*.aws_ec2.ec2_image_id | string | | |
action_result.data.\*.aws_ec2.ec2_region | string | | |
action_result.data.\*.proxy | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.parameter.username | string | `user name` | phantom |
action_result.parameter.process_name | string | `process name` | ata_sff |
action_result.parameter.package_name | string | `cloudpassagehalo package name` | curl.x86_64 |
action_result.parameter.cve_number | string | `cloudpassagehalo cve number` | CVE-2020-25695 |
action_result.summary.total_servers | numeric | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

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
