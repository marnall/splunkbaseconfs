"""Conservative, stateless VMware syslog normalization. Standard library only."""

import json
import re
from vmware_vision_cim import CIM_FIELDS, normalize

VERSION = "1.1.0"
EVENTS = {}


def _events(names, action, category="lifecycle", status="success", state=""):
    for name in names.split():
        EVENTS[name] = (action, category, status, state)


_events("VmCreatedEvent VmDeployedEvent", "created")
_events("VmClonedEvent", "cloned")
_events("VmRemovedEvent", "deleted", state="removed")
_events("VmRegisteredEvent", "registered")
_events("VmUnregisteredEvent", "unregistered", state="unregistered")
_events("VmPoweredOnEvent DrsVmPoweredOnEvent", "power_on", "power", state="powered_on")
_events("VmPoweredOffEvent", "power_off", "power", state="powered_off")
_events("VmSuspendedEvent", "suspended", "power", state="suspended")
_events("VmResettingEvent", "reset_requested", "power", "requested")
_events("VmStartingEvent VmPowerOnEvent", "power_on_requested", "power", "requested")
_events("VmStoppingEvent", "power_off_requested", "power", "requested")
_events("VmGuestShutdownEvent", "guest_shutdown_requested", "power", "requested")
_events("VmGuestRebootEvent", "guest_reboot_requested", "power", "requested")
_events("VmReconfiguredEvent", "reconfigured", "configuration")
_events("VmRenamedEvent", "renamed", "configuration")
_events("VmMigratedEvent DrsVmMigratedEvent", "migrated", "migration")
_events("VmRelocatedEvent", "relocated", "migration")
_events(
    "VmBeingHotMigratedEvent VmBeingMigratedEvent VmBeingRelocatedEvent",
    "migration_requested",
    "migration",
    "requested",
)
_events("VmSnapshotTakenEvent", "snapshot_created", "snapshot")
_events(
    "VmSnapshotRemovedEvent VmSnapshotRemoveAllEvent", "snapshot_deleted", "snapshot"
)
_events("VmRevertedToSnapshotEvent", "snapshot_reverted", "snapshot")
_events(
    "VmFailedToPowerOnEvent VmFailedToPowerOffEvent VmFailedToSuspendEvent VmFailedToResetEvent",
    "power_failed",
    "power",
    "failure",
)
_events(
    "VmFailedMigrateEvent VmFailedRelayoutEvent",
    "migration_failed",
    "migration",
    "failure",
)
_events("VmFailedToCreateEvent", "create_failed", "lifecycle", "failure")
_events("VmDasBeingResetEvent", "ha_restart_requested", "availability", "requested")
_events("VmDasResetFailedEvent", "ha_restart_failed", "availability", "failure")
_events("VmDasUpdateOkEvent", "ha_updated", "availability")
_events("UserLoginSessionEvent", "login", "authentication")
_events("UserLogoutSessionEvent", "logout", "authentication")
_events(
    "BadUsernameSessionEvent InvalidLogin", "login_failed", "authentication", "failure"
)
_events(
    "PermissionAddedEvent PermissionUpdatedEvent PermissionRemovedEvent",
    "permission_changed",
    "security",
)
_events("RoleAddedEvent RoleUpdatedEvent RoleRemovedEvent", "role_changed", "security")
_events(
    "AlarmStatusChangedEvent AlarmCreatedEvent AlarmRemovedEvent AlarmReconfiguredEvent",
    "alarm_changed",
    "alarm",
    "observed",
)
_events("AlarmAcknowledgedEvent", "alarm_acknowledged", "alarm")
_events(
    "HostConnectedEvent HostDisconnectedEvent HostConnectionLostEvent",
    "host_connection_changed",
    "infrastructure",
    "observed",
)
_events(
    "EnteredMaintenanceModeEvent ExitMaintenanceModeEvent",
    "maintenance_changed",
    "infrastructure",
)
_events(
    "DatastoreCreatedEvent DatastoreDestroyedEvent DatastoreRenamedEvent",
    "datastore_changed",
    "storage",
)
_events("TaskEvent", "task", "task", "observed")

OUTPUT_FIELDS = "event_id event_type event_time event_chain_id user vcenter vm_name vm_id vm_uuid vm_key identity_quality datacenter cluster esxi_host datastore action category status observed_state severity message change_details change_fields old_value new_value src_ip task_id parser_status parser_format parser_version event_uid vendor_product".split()
OUTPUT_FIELDS += ["record_kind", "component", "vm_reference_count"]
OUTPUT_FIELDS += CIM_FIELDS
EVENT_RE = re.compile(
    r"Event\s+\[(?P<event_id>\d+)\]\s+\[[^\]]*\]\s+\[(?P<event_time>[^\]]*)\]\s+\[(?P<event_type>[^\]]*)\]\s+\[(?P<severity>[^\]]*)\]\s+\[(?P<user>[^\]]*)\]\s+\[(?P<datacenter>[^\]]*)\]\s+\[(?P<event_chain_id>[^\]]*)\]\s+\[(?P<message>.*)\]\s*$",
    re.S,
)
SYSLOG_RE = re.compile(r"^(?:<\d+>)?1\s+\S+\s+(?P<origin>\S+)\s+\S+\s+\S+\s+\S+\s+")
RELAY_RE = re.compile(
    r"^(?:<\d+>)?[A-Z][a-z]{2}\s+\d{1,2}\s+\d\d:\d\d:\d\d\s+\S+\s+(?P<inner>1\s+\d{4}-\S+\s+\S+\s+.*)$",
    re.S,
)
APP_RE = re.compile(r"^(?:<\d+>)?1\s+\S+\s+\S+\s+(?P<component>\S+)\s+")
TYPE_RE = re.compile(r"\bvim\.event\.(\w+)\b")
VM_REF_RE = re.compile(r"\[vim\.VirtualMachine:(vm-\d+),([^\]]+)\]")
KV_RE = re.compile(
    r'(?<![\w.])([\w.:-]+)\s*=\s*(?:"((?:\\.|[^"\\])*)"|\x27([^\x27]*)\x27|([^\s\],;]+))'
)


def _text(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _flatten(obj, prefix="", out=None):
    out = {} if out is None else out
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = prefix + str(key)
            out[path] = value
            if isinstance(value, dict):
                _flatten(value, path + ".", out)
    return out


def parse(raw, host="", sourcetype=""):
    out = dict.fromkeys(OUTPUT_FIELDS, "")
    out.update(
        parser_version=VERSION,
        parser_status="unmapped",
        parser_format="text",
        status="unknown",
        category="other",
        action="unknown",
        severity="unknown",
        vendor_product="VMware",
        record_kind="unclassified",
        vm_reference_count="0",
    )
    raw = _text(raw)
    message = raw
    values = {}
    # JSON envelopes are common with HEC and exported Aria events. Never eval payloads.
    try:
        payload = json.loads(raw) if raw.lstrip().startswith("{") else None
        if isinstance(payload, dict):
            values = _flatten(payload)
            embedded = payload.get("event")
            if isinstance(embedded, dict):
                values.update(_flatten(embedded))
            elif isinstance(embedded, str):
                message = embedded
            message = _text(
                values.get("text")
                or values.get("fullFormattedMessage")
                or values.get("message")
                or message
            )
            for field in (
                payload.get("fields", [])
                if isinstance(payload.get("fields"), list)
                else []
            ):
                if isinstance(field, dict) and "name" in field:
                    values[str(field["name"])] = field.get(
                        "content", field.get("value")
                    )
            out["parser_format"] = "json"
    except (ValueError, TypeError):
        pass
    for m in KV_RE.finditer(message):
        values.setdefault(m[1], next(v for v in m.groups()[1:] if v is not None))

    aliases = {
        "event_type": ("eventType", "event_type", "type", "_typeName", "eventTypeId"),
        "event_id": ("key", "event_id", "eventId"),
        "event_time": ("createdTime", "event_time", "timestamp"),
        "event_chain_id": ("chainId", "event_chain_id"),
        "user": ("userName", "user", "username", "vc_username"),
        "vcenter": ("vcenter", "vcenter_name", "vc_hostname", "vcenterHost"),
        "vm_name": ("vm.name", "vm_name", "vmName", "vmw_vm_name"),
        "vm_id": (
            "vm.vm.value",
            "vm.vm._value",
            "vm.vm.moid",
            "vm.vm",
            "vm_id",
            "vmId",
            "vm_moid",
        ),
        "vm_uuid": ("vm_uuid", "instanceUuid", "vm.instanceUuid"),
        "datacenter": ("datacenter.name", "datacenter", "datacenter_name"),
        "cluster": ("computeResource.name", "cluster", "cluster_name"),
        "esxi_host": ("host.name", "esxi_host", "esx_hostname"),
        "datastore": ("ds.name", "datastore.name", "datastore"),
        "severity": ("severity", "level", "priority"),
        "task_id": ("info.key", "task_id", "taskId"),
        "old_value": ("oldName", "old_value", "oldValue"),
        "new_value": ("newName", "new_value", "newValue"),
        "src_ip": ("ipAddress", "src_ip", "client_ip"),
        "change_details": ("configChanges", "configSpec", "change_details"),
    }
    for key, names in aliases.items():
        for name in names:
            val = values.get(name)
            if (
                key == "event_type"
                and name in ("type", "_typeName")
                and val is not None
            ):
                if (
                    not _text(val).split(".")[-1].endswith("Event")
                    and _text(val) != "InvalidLogin"
                ):
                    continue
            if (
                val is not None
                and val != ""
                and (key == "change_details" or not isinstance(val, (dict, list)))
            ):
                out[key] = _text(val)
                break
    envelope = message
    relay = RELAY_RE.match(envelope)
    if relay:
        envelope = relay["inner"]
    origin = SYSLOG_RE.match(envelope) or SYSLOG_RE.match(raw)
    app = APP_RE.match(envelope)
    if app:
        out["component"] = app["component"]
    match = EVENT_RE.search(message)
    if match:
        out.update(match.groupdict())
        out["parser_format"] = "vcenter_event"
        message = out["message"]
    else:
        out["message"] = message
    out["vcenter"] = (
        out["vcenter"] or (origin["origin"] if origin else host) or "unknown"
    )
    out["event_type"] = out["event_type"].split(".")[-1]
    if not out["event_type"]:
        typ = TYPE_RE.search(message)
        if typ:
            out["event_type"] = typ[1]
    references = dict(VM_REF_RE.findall(message))
    out["vm_reference_count"] = str(len(references))
    if len(references) == 1:
        reference_id, reference_name = next(iter(references.items()))
        # A named primary VM from structured fields takes precedence over incidental references.
        if not out["vm_id"] or out["vm_id"] == reference_id:
            out["vm_id"] = out["vm_id"] or reference_id
            out["vm_name"] = out["vm_name"] or reference_name.strip()
    if not out["vm_name"] and len(references) < 2 and out["event_type"]:
        patterns = [
            r"^Reconfigured\s+(?:virtual machine\s+)?(.+?)(?::|\s+on\s+)",
            r"^Renamed\s+(.+?)\s+to\s+",
            r"\b(?:Virtual machine|VM)\s+(.+?)\s+(?:on\s+\S+\s+)?(?:in\s+.+?\s+)?(?:was |is |has been |has |have )?(?:created|deployed|cloned|deleted|removed|destroyed|registered|unregistered|powered on|powered off|suspended|reset|reconfigured|renamed|migrated|relocated)\b",
            r"^(?:Created|Deployed|Cloned|Removed|Deleted|Registered|Unregistered|Powered on|Powered off|Suspended)\s+(?:virtual machine\s+)?(.+?)(?:\s+on\s+|\s+in\s+|$)",
        ]
        for pattern in patterns:
            m = re.search(pattern, message, re.I)
            if m:
                out["vm_name"] = m[1].strip(' "\x27')
                break
    if not out["vm_id"] and len(references) < 2:
        ids = set(re.findall(r"\bvm-\d+\b", message))
        if len(ids) == 1:
            out["vm_id"] = next(iter(ids))
    if not out["src_ip"]:
        m = re.search(r"(?:@|\bfrom\s+)((?:\d{1,3}\.){3}\d{1,3})\b", message)
        if m:
            out["src_ip"] = m[1]
    if not out["esxi_host"]:
        m = None
        if out["event_type"] in (
            "HostConnectedEvent",
            "HostDisconnectedEvent",
            "HostConnectionLostEvent",
        ):
            m = re.search(
                r"^(?:Connected to|Disconnected from|Lost connection to)\s+(\S+)",
                message,
                re.I,
            )
        if not m and out["event_type"] == "AlarmStatusChangedEvent":
            m = re.search(
                r"^Alarm 'Host connection and power state' on (\S+) changed from",
                message,
            )
        m = m or re.search(r"\bon (?:host )?([^\s,]+)(?:\s+in\s+|$)", message)
        if m:
            out["esxi_host"] = m[1]
    if not out["change_details"] and out["event_type"] == "VmReconfiguredEvent":
        m = re.search(
            r"(?:configSpec|configChanges|Changed|Changes):?\s*(.+)",
            message,
            re.I | re.S,
        )
        if m:
            out["change_details"] = m[1]
    changes = values.get("configChanges") or values.get("configSpec")
    if isinstance(changes, dict):
        out["change_fields"] = ", ".join(changes)
    if out["change_details"] and not out["change_fields"]:
        out["change_fields"] = ", ".join(
            dict.fromkeys(
                re.findall(r"\b((?:config\.)?[\w.]+)\s*(?:=|:)", out["change_details"])
            )
        )
    event = EVENTS.get(out["event_type"])
    if out["event_type"]:
        out["record_kind"] = "event"
    if event:
        out["action"], out["category"], out["status"], out["observed_state"] = event
        out["parser_status"] = "mapped"
    elif out["event_type"]:
        out["action"] = "other_event"
        out["parser_status"] = "unmapped_event_type"
    elif re.search(r"\[Originator@\d+\b", message) or out["component"] in (
        "vpxd-main",
        "vum-vmacore",
    ):
        out.update(
            record_kind="diagnostic",
            parser_status="diagnostic",
            action="diagnostic_message",
            category="diagnostic",
            status="observed",
        )
        level = re.search(
            r"\b(info|warning|warn|error|verbose|debug|panic)\s+[\w-]+\[\d+\]", message
        )
        if level:
            out["severity"] = level[1]
    if out["event_type"] == "AlarmStatusChangedEvent":
        transition = re.search(r" changed from (\w+) to (\w+)", message)
        if transition:
            out["old_value"] = out["old_value"] or transition[1]
            out["new_value"] = out["new_value"] or transition[2]
    # Explicit failures override event-class success, but text never establishes success.
    task_state = _text(
        values.get("info.state") or values.get("status") or values.get("state")
    ).lower()
    if task_state in ("error", "failed", "failure"):
        out["status"] = "failure"
        out["observed_state"] = ""
    elif out["category"] == "task" and task_state in ("success", "completed"):
        out["status"] = "success"
    elif out["category"] == "task" and task_state in ("running", "queued"):
        out["status"] = task_state
    out["severity"] = out["severity"].lower()
    identity = out["vm_uuid"] or out["vm_id"] or out["vm_name"]
    out["identity_quality"] = (
        "uuid"
        if out["vm_uuid"]
        else "moid" if out["vm_id"] else "name_only" if out["vm_name"] else "missing"
    )
    # Scope even UUIDs to a source to avoid cross-vCenter accidental merges.
    if identity:
        out["vm_key"] = out["vcenter"] + "::" + identity
    if out["event_id"]:
        out["event_uid"] = (
            out["vcenter"] + "::" + out["event_id"] + "::" + out["event_time"]
        )
    return normalize(out)
