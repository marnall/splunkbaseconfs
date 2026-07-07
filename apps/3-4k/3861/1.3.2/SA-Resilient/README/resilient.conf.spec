# Resilient connection configuration
[config]
host = <string>
* Name of the resilient host to connect to
* (required)

user = <string>
* Resilient username (email address)
* (required)

password = <string>
* Resilient password
* (required)

cafile = <string>
* Certificate file for Resilient Server
* (optional)

org = <string>
* Resilient organization to use
* Only required if user is in multiple organizations
* (optional)

num_artifacts = <integer>
* Number of artifacts allowed to map per alert
* (required)

artifact_types = <csv list>
* Artifact types that can be mapped
* (required)

verify = <bool>
* Verify certificates on HTTPS request?
* (required)

