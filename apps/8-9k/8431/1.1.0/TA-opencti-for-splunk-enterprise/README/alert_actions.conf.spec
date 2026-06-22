[opencti_create_incident_response]
param.name = <string> Name. It's a required parameter. It's default value is $name$.
param.description = <string> Description.  It's default value is $description$.
param.type = <string> Type.
param.severity = <list> Severity.  It's default value is medium.
param.priority = <list> Priority.  It's default value is p2.
param.labels = <string> Labels.
param.tlp = <list> TLP.  It's default value is tlp_amber.
param.observables_extraction = <list> Observables Extraction.  It's default value is disable.

[opencti_create_incident]
param.name = <string> Name. It's a required parameter. It's default value is $name$.
param.description = <string> Description.  It's default value is $description$.
param.type = <string> Type.
param.severity = <list> Severity.  It's default value is medium.
param.labels = <string> Labels.
param.tlp = <list> TLP.  It's default value is tlp_amber.
param.observables_extraction = <list> Observables Extraction.  It's default value is disable.

[opencti_create_sighting]
param.sighting_of_value = <string> Sighting of Value. It's a required parameter.
param.sighting_of_type = <list> Sighting of Type.  It's default value is domain_observable.
param.where_sighted_value = <string> Where Sighted (value). It's a required parameter.
param.where_sighted_type = <list> Where Sighted (type).  It's default value is system.
param.labels = <string> Labels.
param.tlp = <list> TLP.  It's default value is tlp_amber.
