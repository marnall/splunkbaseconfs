"""CIM mappings for explicit authentication results and VM change events."""

AUTHENTICATION_TYPES = {
    "UserLoginSessionEvent",
    "BadUsernameSessionEvent",
    "InvalidLogin",
}
CHANGE_TYPES = {}


def _changes(names, action, change_type):
    for name in names.split():
        CHANGE_TYPES[name] = (action, change_type)


_changes(
    "VmCreatedEvent VmDeployedEvent VmClonedEvent VmFailedToCreateEvent",
    "created",
    "virtualization",
)
_changes("VmRemovedEvent", "deleted", "virtualization")
_changes("VmRegisteredEvent VmUnregisteredEvent", "modified", "registration")
_changes(
    "VmPoweredOnEvent DrsVmPoweredOnEvent VmFailedToPowerOnEvent", "started", "power"
)
_changes("VmPoweredOffEvent VmFailedToPowerOffEvent", "stopped", "power")
_changes("VmSuspendedEvent VmFailedToSuspendEvent", "modified", "power")
_changes("VmFailedToResetEvent VmDasResetFailedEvent", "restarted", "power")
_changes("VmReconfiguredEvent VmRenamedEvent", "modified", "configuration")
_changes(
    "VmMigratedEvent DrsVmMigratedEvent VmRelocatedEvent VmFailedMigrateEvent VmFailedRelayoutEvent",
    "modified",
    "migration",
)
_changes(
    "VmSnapshotTakenEvent VmSnapshotRemovedEvent VmSnapshotRemoveAllEvent VmRevertedToSnapshotEvent",
    "modified",
    "snapshot",
)

CIM_FIELDS = "vmware_action cim_dataset app src dest dvc signature signature_id reason result change_type object object_id object_category object_attrs command".split()


def normalize(out):
    # Preserve the complete native vocabulary before assigning CIM action values.
    out["vmware_action"] = out["action"]
    if out["record_kind"] != "event" or out["parser_status"] != "mapped":
        return out
    kind = out["event_type"]
    if out["status"] not in ("success", "failure"):
        return out
    if kind in AUTHENTICATION_TYPES:
        out.update(
            cim_dataset="Authentication", action=out["status"], reason=out["message"]
        )
    elif kind in CHANGE_TYPES:
        action, change_type = CHANGE_TYPES[kind]
        out.update(
            cim_dataset="Change",
            action=action,
            change_type=change_type,
            object=out["vm_name"],
            object_id=out["vm_uuid"] or out["vm_id"],
            object_category="virtual_machine",
            object_attrs=out["change_details"],
        )
    else:
        return out
    out.update(
        app="vmware_vcenter",
        src=out["src_ip"],
        dest=out["vcenter"],
        dvc=out["vcenter"],
        signature=kind,
        signature_id=kind,
        result=out["message"],
    )
    # Missing source IP, command, authentication method and object ID stay absent.
    return out
