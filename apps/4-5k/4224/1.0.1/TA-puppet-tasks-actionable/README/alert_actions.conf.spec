
[puppet_enterprise_tasks]
param.description = <string> Description. It's a required parameter.
param.module = <string> Task. It's a required parameter.
param.parameters = <string> Parameters.
param.severity = <list> Severity. It's a required parameter. It's default value is INFO.
param.noop = <bool> Noop.
param.host = <string> Node. It's a required parameter.
param.environment = <string> Environment. It's a required parameter. It's default value is production.

[puppet_task_exec]
param.command = <string> Command. It's a required parameter.
param.severity = <list> Severity. It's a required parameter. It's default value is INFO.
param.environment = <string> Environment. It's a required parameter. It's default value is production.
param.description = <string> Description. It's a required parameter.
param.node = <string> Node.

