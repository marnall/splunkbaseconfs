[mural_audit_logs://<name>]
*Retrieves Mural Audit Logs.

python.version = {python3|python3.7|python3.9}
* DEPRECATED. Use 'python.required' instead.
* For Python scripts only, selects which Python version to use.
* Default: python3

python.required = <comma-separated list>
* For Python scripts only, the versions of Python that the script supports.
* The Splunk platform selects the highest version of Python that is
  available from the list that you provide.
* Supported values: "3.9", "3.13".
* Takes precedence over 'python.version' when both are set.
* Default: 3.13

description = <value>