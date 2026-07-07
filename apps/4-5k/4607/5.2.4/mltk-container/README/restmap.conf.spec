[admin_external:<uniqueName>]
python.version = {default|python|python2|python3|python3.7|python3.9|latest}
* DEPRECATED. Use 'python.required' instead to specify which Python versions the
  script supports.
* For Python scripts only, selects which Python version to use.
* Either "default" or "python" select the system-wide default Python version.
* Optional.
* Default: Not set; uses the system-wide Python version.

python.required = <comma-separated list>
* For Python scripts only, the versions of Python that the script supports.
* This setting takes precedence over the 'python.version' setting if both
  have values.
* The Splunk platform selects the highest version of Python that is
  available from the list that you provide.
* The following values are supported:
  * "3.9":  The script supports Python version 3.9.
  * "3.13": The script supports Python version 3.13.
  * "latest": The script uses the latest Python interpreter available.
    * Where possible, use a specific version string rather than "latest".
    * NOTE: The "latest" value is an internal value that is related to
      a feature that is still under development.
* NOTE: Use this setting instead of the deprecated 'python.version' setting.
* This setting is optional.
* Default: Not set; uses 'python.version' if that setting has a value.

[script:<uniqueName>]
python.version = {default|python|python2|python3|python3.7|python3.9|latest}
* DEPRECATED. Use 'python.required' instead to specify which Python versions the
  script supports.
* For Python scripts only, selects which Python version to use.
* Either "default" or "python" select the system-wide default Python version.
* Optional.
* Default: Not set; uses the system-wide Python version.

python.required = <comma-separated list>
* For Python scripts only, the versions of Python that the script supports.
* This setting takes precedence over the 'python.version' setting if both
  have values.
* The Splunk platform selects the highest version of Python that is
  available from the list that you provide.
* The following values are supported:
  * "3.9":  The script supports Python version 3.9.
  * "3.13": The script supports Python version 3.13.
  * "latest": The script uses the latest Python interpreter available.
    * Where possible, use a specific version string rather than "latest".
    * NOTE: The "latest" value is an internal value that is related to
      a feature that is still under development.
* NOTE: Use this setting instead of the deprecated 'python.version' setting.
* This setting is optional.
* Default: Not set; uses 'python.version' if that setting has a value.
