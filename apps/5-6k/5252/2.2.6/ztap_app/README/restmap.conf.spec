# Configuration spec for restmap.conf

[script:<name>]
python.version = <string>
* Specifies the Python version to use for this REST endpoint
* Valid values: python3, python3.9, python3.13
* Default: python3

python.required = <string>
* Comma-separated list of Python versions this REST endpoint supports
* Used by Splunk Cloud Platform 10.2+ to select the highest available version
* Example: 3.9, 3.13

match = <string>
* URL pattern to match for this REST endpoint

script = <string>
* Python script to execute for this endpoint

scripttype = <string>
* Type of script execution (persist, stream, etc.)

handler = <string>
* Python handler class to process requests

output_modes = <string>
* Supported output formats (json, xml, etc.)

passPayload = <boolean>
* Whether to pass the request payload to the handler
* Default: false
