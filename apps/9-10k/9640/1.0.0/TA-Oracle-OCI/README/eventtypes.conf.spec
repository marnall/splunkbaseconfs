#   Version 1.0.0
#
# This file documents the eventtype stanzas TA-Oracle-OCI ships
# in default/eventtypes.conf. Standard eventtypes.conf attributes only
# (search) -- see Splunk's own eventtypes.conf.spec for the full
# attribute reference. Note: eventtypes.conf's own "tags" attribute is
# deprecated by Splunk (its own spec says "see tags.conf.spec" instead),
# so it is not used here -- CIM tag assignment for these eventtypes
# lives in default/tags.conf/README/tags.conf.spec instead.

[oci_audit]
search = <string>
* sourcetype=oci:audit

[oci_flowlogs]
search = <string>
* sourcetype=oci:flowlogs

[oci_cloudguard_problem]
search = <string>
* sourcetype=oci:cloudguard:problem

[oci_loadbalancer]
search = <string>
* sourcetype=oci:loadbalancer

[oci_objectstorage]
search = <string>
* sourcetype=oci:objectstorage
