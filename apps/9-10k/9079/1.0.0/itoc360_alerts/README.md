# ITOC360 Alert Action for Splunk

Send Splunk alerts to [ITOC360](https://itoc360.com), the on-call alert routing
and incident management platform. Triggered alerts are forwarded to the ITOC360
events API, deduplicated, routed through escalation policies, and delivered to
the right on-call engineer.

## Prerequisites

An ITOC360 account — sign up at [itoc360.com](https://itoc360.com).

## Setup

1. In ITOC360, go to **Sources → Add Source**, select **Splunk**, and copy the
   generated source token.
2. Install this app on your Splunk search head.
3. In Splunk, edit a saved search / alert → **Add Actions → ITOC360**.
4. Paste the source token, pick a severity, and save.

When the alert triggers, an event appears in ITOC360 with the search name as
its title, the triggering result's host, and the severity you selected.

## Configuration reference

| Parameter | Description | Default |
|---|---|---|
| Source token | Token of your ITOC360 Splunk source | — (required) |
| Severity | critical / high / medium / low → mapped to ITOC360 priority | medium |
| Host field | Result field used as the alert host | host |

## Support

- Documentation: https://docs.itoc360.com
- Contact: support@itoc360.com
