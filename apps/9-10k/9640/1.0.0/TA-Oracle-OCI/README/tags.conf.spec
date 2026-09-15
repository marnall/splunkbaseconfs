#   Version 1.0.0
#
# This file documents the tags.conf stanzas TA-Oracle-OCI ships
# in default/tags.conf, pairing each eventtype above with its Splunk
# Common Information Model (CIM) tag(s), plus one custom grouping tag.
# Standard tags.conf syntax only ([eventtype=<name>] with <tag> =
# enabled|disabled) -- see Splunk's own tags.conf.spec for the full
# attribute reference.

[eventtype=oci_audit]
change = enabled
* Marks oci_audit events as members of the CIM Change data model.
oracle_cloud_infrastructure = enabled
* Not a CIM tag -- this app's own custom tag so
  tag=oracle_cloud_infrastructure finds all OCI-sourced events
  regardless of which CIM model they map to.

[eventtype=oci_flowlogs]
network = enabled
communicate = enabled
* Marks oci_flowlogs events as members of the CIM Network Traffic model.
  Both tags are required together -- verified against Splunk's current
  CIM 8.5 docs; "network_traffic" is not a real CIM tag name despite
  matching the data model's display name.
oracle_cloud_infrastructure = enabled

[eventtype=oci_cloudguard_problem]
alert = enabled
* Marks oci_cloudguard_problem events as members of the CIM Alerts model.
oracle_cloud_infrastructure = enabled

[eventtype=oci_loadbalancer]
network = enabled
communicate = enabled
oracle_cloud_infrastructure = enabled

[eventtype=oci_objectstorage]
change = enabled
oracle_cloud_infrastructure = enabled

# Full CIM field-alias compliance (required field names/eval expressions
# via transforms.conf + FIELDALIAS/EVAL in props.conf) is not included --
# add it once you know which CIM models your Enterprise Security content
# actually depends on; see the "Extending CIM coverage" section in
# README.md.
