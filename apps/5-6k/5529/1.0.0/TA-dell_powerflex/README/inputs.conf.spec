[powerflex_os_instance://<name>]
system = <string> PowerFlex System
instances_rest_endpoint = <string> Rest endpoint from which the list of instances should be collected.Ex./api/types/Volume/instances?systemId={system id}&sessionTag={session tag}&lastVersion={last version}
sourcetype = <string> Sourcetype of the events collected
method = <string> API method to be used for data collection

[powerflex_os_statistics://<name>]
system = <string> PowerFlex System
instances_rest_endpoint = <string> The rest endpoint which provides the list of instances for which the statistics should be collected.Ex. /api/types/Volume/instances
statistics_rest_endpoint = <string> Rest endpoint of the statistics which should be collected for instances.Ex. /api/instances/Volume::{id}/relationships/Statistics
sourcetype = <string> Sourcetype of the events collected
method = <string> API method to be used for data collection