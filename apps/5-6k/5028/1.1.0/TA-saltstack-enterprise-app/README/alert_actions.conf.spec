
[saltstack_alert_action]
python.version = python3
param.saltstack_username = <string> SaltStack Username. It's a required parameter.
param.cmd = <list> Command (cmd). It's a required parameter. It's default value is local.
param.fun = <string> Function (fun). It's a required parameter. It's default value is test.ping.
param.master = <string> Master (master). It's a required parameter. It's default value is *.
param.tgt = <string> Target (tgt).
param.tgt_type = <list> Target Type (tgt_type).  It's default value is select.
param.args = <string> Args (args).
param.kwargs = <string> Kwargs (kwargs).
param.saltstack_enterprise_url = <string> SaltStack Enterprise URL.
param.request_timeout = <string> Request Timeout.
param.certificate_path = <string> Certificate Path.
param.verify_ssl = <list> Verify SSL.  It's default value is 1.

