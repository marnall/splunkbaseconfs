# Splunk CIM mapping

## Scope

Version 1.4.0 and later map PT NAD JSON syslog events into Splunk Common Information
Model fields, event types, and tags. Install a compatible version of the Splunk
Common Information Model Add-on to use the data models in Splunk Enterprise or
Splunk Enterprise Security.

## Data model mappings

| PT NAD event | Event type | CIM tags | CIM dataset |
| --- | --- | --- | --- |
| Single or combined attack | `ptnad_attack` | `ids`, `attack` | Intrusion Detection / IDS_Attacks |
| Combined multi-rule incident | `ptnad_incident` | `alert` | Alerts |
| Activity detection | `ptnad_activity` | `alert` | Alerts |
| Indicator of compromise | `ptnad_ioc` | `alert` | Alerts |
| Login audit event | `ptnad_login` | `authentication`, `default` | Authentication |
| Administrative change | `ptnad_change` | `change` | Change / All_Changes |
| User account change | `ptnad_account_change` | `change`, `account` | Change / Account_Management |

## Important field mappings

| CIM field | PT NAD source or calculation |
| --- | --- |
| `action` | Authentication result, change action, or `allowed` for passive attack detection |
| `app` | `app_proto`, or `PT NAD` for audit and higher-level events |
| `category` | Rule class, rule category, IOC category, or activity type |
| `dest`, `dest_ip`, `dest_port` | `dst.ip`, `dst.dns`, `dst.port`; PT NAD host for audit events |
| `description` | Activity/rule description, message, title, or audit event |
| `dvc` | PT NAD `hostname`, sensor tag, or Splunk host metadata |
| `ids_type` | `network` for attack and incident events |
| `severity` | Activity criticality or the highest PT NAD rule priority |
| `signature`, `signature_id` | Rule/activity/IOC/audit name and identifier |
| `src`, `src_ip`, `src_port` | `src.ip`, `src.dns`, `src.port`, or audit `details.ip` |
| `transport` | Lowercase `proto` value |
| `user`, `src_user` | Audit username and account-change actor/target normalization |
| `vendor_product` | `Positive Technologies PT NAD` |

PT NAD is passive and does not block observed traffic, so attack events use
`action=allowed`. This value describes the observed connection outcome, not a
security policy decision by PT NAD.

## Combined-event contract

The native documented PT NAD attack schema contains one `alert` object. Version
Version 1.4.0 and later also accept an upstream combined JSON envelope when it contains an
`incident_id` or `type=incident` and one of these arrays:

- `alert[]` with `s_id`, `s_msg`, `s_pr`, `s_cls`
- `alerts[]` with PT NAD names (`s_id`, `s_msg`) or normalized names
  (`signature_id`, `signature`)
- `rules[]` with `id`/`rule_id`, `name`/`rule_name`, `priority`, and `category`

The TA keeps all rule identifiers and names as multivalue fields. It does not
aggregate separate syslog messages into an incident. Combined events must be
created by PT NAD or an authorized upstream integration component.

## Asset and identity framework

PT NAD asset discovery synchronization is outside this TA's scope. The TA does
not populate fields that Splunk ES owns through asset and identity correlation,
including `src_priority`, `dest_priority`, `src_bunit`, and `dest_bunit`.

## Correlation and automation

Correlation searches are customer content and must be designed by the
customer's Detection Engineer. This TA provides normalized fields and CIM data
model membership but does not ship correlation searches, notable-event rules,
or automated response playbooks. No confidential Vectra integration mechanism
is included.

## Validation searches

Confirm event types and tags:

```spl
index=ptnad
| stats count values(tag) as tags by nad_event_type eventtype
```

Validate Intrusion Detection mapping:

```spl
index=ptnad tag=ids tag=attack
| table _time action category dest dest_port dvc ids_type severity signature signature_id src src_port transport vendor_product
```

Validate combined incidents:

```spl
index=ptnad combined_event=1
| table _time nad_correlation_id rule_count related_rule_id related_rule_name severity src dest
```

Validate Authentication mapping:

```spl
index=ptnad tag=authentication
| table _time action app dest src user signature vendor_product
```

Validate Change mapping:

```spl
index=ptnad tag=change
| table _time action change_type dest dvc object object_category result src status user src_user vendor_product
```

When Splunk Enterprise Security and data model acceleration are enabled, verify
the Intrusion Detection dataset:

```spl
| tstats count from datamodel=Intrusion_Detection.IDS_Attacks by IDS_Attacks.severity IDS_Attacks.signature IDS_Attacks.src IDS_Attacks.dest
```
