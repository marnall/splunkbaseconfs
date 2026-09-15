# Custom parameters of the CIP TI Feed Slack alert action, declared so that btool
# and AppInspect resolve them. Override per alert with
# action.cip_ti_slack.param.<name>; defaults live in default/alert_actions.conf.

[cip_ti_slack]
param.channel = <string> Optional Slack channel override (modern webhooks ignore this).
param.max_rows = <integer> Max match rows listed in one Slack message (capped at 50).
param.kind = <string> live|past. Empty means a live alert. 'past' renders the past-contact header (used by the retroactive sweep).
param.mask_internal_ip = <boolean> Mask internal host IP octets in the message. 1 = mask, 0 = show full address (default 0, for an access-restricted SOC channel).
param.webhook_url = <string> Optional per-alert webhook override; prefer the encrypted Set up webhook.
