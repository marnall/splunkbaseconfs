[cyberark_identity_services://<name>]
tenant_url = Cyberark Tenant URL. e.g. https://aai0581.my.idaptive.app
event_types = Select here or type below.
enter_event_types = Comma separated, e.g. Cloud.Core.MfaSummary, Cloud.Core.Login
client_id = SIEM user name.
client_password = SIEM user password.
oauth_app_id = App Id of OAuth App configured for SIEM.
scope = Name of scope configured in OAuth App.
rollback = In hours. Will start fetching from Now - Rollback.
batch_size = In minutes. Time window size for querying events internally. Reduce this, in case of high load of events.