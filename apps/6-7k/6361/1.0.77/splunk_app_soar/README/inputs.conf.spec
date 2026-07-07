[audit://<name>]
global_account = <string>
* Set by the app.
* SOAR server config id

start_by_shell = <boolean>
* Whether or not to run the specified command through the operating system
  shell or command prompt.
* If you set this setting to "true", the host operating system runs the
  specified command through the OS shell ("/bin/sh -c" on *NIX,
  "cmd.exe /c" on Windows.)
* If you set the setting to "false", the input runs the program directly
  without attempting to expand shell metacharacters.
* You might want to explicitly set the setting to "false" for scripts
  that you know do not need UNIX shell metacharacter expansion. This is
  a Splunk best practice.
* Default (on *nix machines): true
* Default (on Windows machines): false

python.version = {default|python|python2|python3}
* For Python scripts only, selects which Python version to use.
* Set to either "default" or "python" to use the system-wide default Python
  version.
* Optional.
* Default: Not set; uses the system-wide Python version.

sourcetype = <string>
* Sets the sourcetype key/field for events from this input.
* Explicitly declares the source type for this input instead of letting
  it be determined through automated methods. This is important for
  search and for applying the relevant configuration for this data type
  during parsing and indexing.
* Sets the sourcetype key initial value. The key is used during
  parsing or indexing to set the source type field during
  indexing. It is also the source type field used at search time.
* As a convenience, the chosen string is prepended with 'sourcetype::'.
* Default: soar

interval = <integer>
* How often, in seconds, to poll for new data.
* This setting is required, and the input does not run if the setting is
  not present.
* The recommended setting depends on the Performance Monitor object,
  counter(s), and instance(s) that you define in the input, and how much
  performance data you need.
  * Objects with numerous instantaneous or per-second counters, such
    as "Memory", "Processor", and "PhysicalDisk" should have shorter
    interval times specified (anywhere from 1-3 seconds).
  * Less volatile counters such as "Terminal Services", "Paging File",
    and "Print Queue" can have longer intervals configured.

start = <string>
* The starting date to poll audit logs from SOAR
* This value is only applicable during the first run. Afterwards,
  the checkpoint value in $SPLUNK_HOME/var/lib/splunk/modinputs/audit 
  is used to prevent duplicate events.

disabled = <boolean>
* Whether or not the file system change monitor input is active.
* Set this setting to "true" to disable the input, and "false" to enable it.
* Default: false
