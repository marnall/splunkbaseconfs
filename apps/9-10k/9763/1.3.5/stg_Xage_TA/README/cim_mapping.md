# Xage → Splunk CIM mapping

Search-time order: `REPORT` (syslog header + JSON) → `EVAL` (vendor + CIM fields) → `LOOKUP` (`xage_message_cim`) → `eventtypes` → `tags`.

Existing data (`source=xage` or `source=tcp:5514`, `sourcetype=syslog`) is covered by matching `[source::…]` stanzas in `props.conf`. New data is reclassed to `sourcetype=xage:audit`.

## Event class → data model

| Xage `message` | CIM data model | `action` | Tags |
|---|---|---|---|
| `user_access_device_success` | Authentication | success | authentication, success |
| `user_access_device_fail` | Authentication + Alerts | failure | authentication, failure, alert |
| `device_write_access_enabled` | Change (endpoint) | modified | change, endpoint, audit |
| `device_write_access_disabled` | Change (endpoint) | modified | change, endpoint, audit |
| `user_on_AD_password_rotation_success` | Change (account) | modified | change, account, audit |
| `user_on_AD_password_rotation_fail` | Change (account) + Alerts | modified | change, account, audit, alert |
| `credentials_unveiled` | Change (audit) | read | change, audit, privileged |

`credentials_unveiled` is **not** tagged `authentication`. CIM Authentication.action cannot also be Change.action=`read`. Search `tag=privileged` for PAM checkout.

## Vendor field → CIM field

| Vendor | CIM | Notes |
|---|---|---|
| `details.userId` / `details.userName` / `details.unveiledByUser` | `user` | coalesce |
| `details.unveiledByUser` | `src_user` | privileged / account change |
| `details.deviceName` | `dest`, `dest_nt_host` | target workstation |
| `details.XNName` / `details.sourceId` | `dvc`, `src` | Edge Node |
| `details.accessMethodName` | `authentication_method` | e.g. Device Domain Account |
| `message` | `signature`, `command` | |
| `id` | `signature_id`, Alerts `id` | |
| `details.errorMessage` | `reason`, `result`, `description` | |
| `details.errorCode` | `reason_id`, `result_id` | e.g. 776 |
| `details.sessionID` | `session_id` | session correlation |
| `details.name` | `object` | credential (unveils) |
| `details.type` | `object_attrs` | e.g. ldap admin |
| `details.id` (nested) | `object_id` | credential UUID |
| `msgLevel` | `severity`, `severity_id` | Error→high / 3 |
| (literal) | `vendor_product` | `Xage Fabric` |
| (literal) | `app` | `xage` |

## Required CIM fields populated

**Authentication:** `action`, `app`, `user` (plus recommended `dest`, `src`, `authentication_method`).

**Change:** `action`, `dest`, `object`, `status`, `vendor_product` (plus `change_type`, `dvc`, `object_category`).

**Alerts:** `app`, `description`, `dest`, `id`, `severity`, `type`.

## Macros

- `` `xage` `` — all Xage events (`index=xage` or `source=tcp:5514`, plus `xage_sources`)
- `` `xage_cim_authentication` `` — `tag=authentication`
- `` `xage_cim_change` `` — `tag=change`
- `` `xage_cim_alerts` `` — `tag=alert`
- `` `xage_privileged` `` — unveils, write-access, password rotation

Override `` `xage_index` `` in `local/macros.conf` if the index is not `xage`.
