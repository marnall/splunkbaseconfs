[targetedpacketcapture]

param.src_ip = <string>
    * Source IP from the splunk event.
    * Required.

param.session_prepend_text = <string>
    * Prefix for the session created on configured CNE
    * Required.
    * Defaults to "Suspicious:".

param.cne_host = <string>
    * CNE host name from which the event is captured.
    * Required.

param.inspect_data_dashboard = <string>
    * Inspect Data Dashboard name on CNE where user should redirect for investigation.
    * Required.
    * Defaults to "Investigate Host".

param.orig_raw = <string>
    * orig_raw data from the splunk event.
    * Required
