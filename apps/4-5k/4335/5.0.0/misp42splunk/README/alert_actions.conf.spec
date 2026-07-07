[misp_alert_create_event]
param._cam = <json> Adaptive Response parameters.
param.misp_instance = <list> Select MISP instance. It's a required parameter.
param.title = <string> Title. It's a required parameter. It's default value is Create MISP event.
param.description = <string> Description. It's a required parameter. It's default value is Alert action to create MISP event.
param.eventid = <string> Event (UU)ID.
param.unique = <string> Unique identifier.
param.info = <string> MISP Info.
param.distribution = <list> Distribution. It's a required parameter. It's default value is 0.
param.threatlevel = <list> Threat level. It's a required parameter. It's default value is 4.
param.analysis = <list> Analysis. It's a required parameter. It's default value is 0.
param.tlp = <list> TLP. It's a required parameter. It's default value is TLP_AMBER.
param.pap = <list> PAP. It's a required parameter. It's default value is PAP_RED.
param.publish_on_creation = <list> Publish event on creation? . It's a required parameter. It's default value is 0.
param.tags = <string> MISP Tags.

[misp_alert_sighting]
param._cam = <json> Adaptive Response parameters.
param.misp_instance = <list> Select MISP instance. It's a required parameter.
param.title = <string> Title. It's a required parameter. It's default value is Sighting MISP attributes.
param.description = <string> Description.  It's default value is Alert action for MISP sighting.
param.timestamp = <string> Timestamp (EPOCH).
param.source = <string> Source.
param.mode = <list> Mode:.  It's default value is byuuid.
param.type = <list> Type:.  It's default value is 0.
