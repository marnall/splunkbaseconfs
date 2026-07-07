[puppet_generate_detailed_report]
python.version = python3
param.puppet_enterprise_console = <string>
* Alternate PE Console URL
param.puppet_db_url = <string>
* Alternate PuppetDB URL
param.puppet_user = <string>
* Alternate RBAC user to run the task.
param.timeout = <string>
* Alternate timeout.
param.splunk_hec_url = <string>
* Alternate Splunk HEC URL.
param.puppet_action_hec_token = <string>
* Alternate Action HEC Token.

[puppet_run_task]
python.version = python3
param.action_target = <string>
* Hostname of the target to run the task on.
* Default value is "$result.host$"
* (required)
param.task_name = <string>
* Task Name
* (required)
param.task_parameters = <string>
* Task Parameters
param.puppet_environment = <string>
* Puppet environment where the task is located.
* Default value is production.
* (required)
param.puppet_user = <string>
* Alternate RBAC user to run the task.
param.puppet_orch_server = <string>
* Alternate URL for the Orchestrator Server.
param.timeout = <string>
* Alternate timeout.
param.splunk_hec_url = <string>
* Alternate Splunk HEC URL.
param.puppet_action_hec_token = <string>
* Alternate Action HEC Token.

[puppet_run_plan]
python.version = python3
param.plan_name = <string>
* Plan Name
* (required)
param.plan_parameters = <string>
* Plan Parameters
param.puppet_environment = <string>
* Puppet environment where the plan is located.
* Default value is production.
* (required)
param.puppet_user = <string>
* Alternate RBAC user to run the plan.
param.puppet_orch_server = <string> Orch. Services URL.
* Alternate URL for the Orchestrator Server.
param.timeout = <string>
* Alternate timeout.
param.splunk_hec_url = <string>
* Alternate Splunk HEC URL.
param.puppet_action_hec_token = <string>
* Alternate Action HEC Token
