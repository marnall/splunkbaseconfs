[update_cyberint_status]
param.account = <string> Account name configured in the add-on whose API key will be used.
param.instance_domain = <string> Cyberint API URL (e.g. https://yourcompany.cyberint.io).
param.client_name = <string> Company (client) name associated with the Cyberint instance.
param.status = <string> New alert status. Valid values: open, acknowledged, closed.
param.closure_reason = <string> Required when status is closed. Valid values: resolved, irrelevant, false_positive, irrelevant_alert_subtype, no_longer_a_threat, asset_should_not_be_monitored, asset_belongs_to_my_organization, other.
param.closure_reason_description = <string> Optional free-text description for the closure reason.
