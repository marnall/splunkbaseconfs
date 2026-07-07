
## The following alert_action has been deprecated
## Please switch to cefout2 and "| cefout" as soon as possible
[cefout]
inline = [1|0]
   * Specifies whether the summary index search command will run as part 
     of the scheduled search or as a follow-on action. This is useful 
     when the results of the scheduled search are expected to be large.
    * Defaults to 1 (true).

_name = <string>
    * The name of the summary index where Splunk will write the events.
    * Defaults to "cef".
   
_ROUTING = <string>
    * The name of the routing group to forward data to for this cef output
    * Defaults to "cefroute".
    
fieldmap = <json>
    * The JSON specification for mapping from Splunk to CEF
    * See Appendix A.
    * Defaults to None
    

[cefout2]
enabled = [true|false|0|1]
    * Whether or not the search is using cefout2.
    * This exists so that we are a true noop for scheduled searches.
    * action.cefout2=0 action.cefout2.enabled=1
    * Required.
    * Defaults to false.
    
spec    = <json>
    * The JSON specification for mapping events from Splunk to CEF
    * See Appendix A.
    * Defaults to None


###### Appendix A: cefout Specification ######
# version:    The specification version 
# datasource: The datamodel and object to search
# routing:    The routing group to forward data to
# fieldmap:   See Appendix B
#
#{
#    "version":    "<cefout specification version>",
#    "datasource": { "datamodel": "<model name>",
#                    "object":    "<object name>"},
#    "routing":    "<routing group name>",
#    "fieldmap":   { <cefout field mappings> }
#}


###### Appendix B: cefout fieldmap Specification #######
# cef_value_type:   Whether to use splunk_key or cef_value for the mapping.  Defaults to "fieldmap".
# splunk_key:       The splunk field name to use for the mapping.  Defaults (cef_key->splunk_key) otherwise None:
#                   syslog_time  -> _time (time_format="%b %d %H:%M:%S")
#                   syslog_host  -> host
#                   version      -> "0"
#                   dvc_vendor   -> vendor
#                   dvc_product  -> product
#                   dvc_version  -> product_version
#                   signature_id -> signature_id
#                   name         -> signature
#                   severity     -> severity
# cef_value:        The string value to use for the mapping.  Defaults to None.
# time_format:      Convert time value in syslog header to string specified by time_format where cef_key==syslog_time
#                   See http://docs.splunk.com/Documentation/Splunk/latest/SearchReference/Commontimeformatvariables
#
# Special Handling: Subject Fields:
#                   If the fieldmap has any mappings to a splunk_key ending in CefUtils.SPLUNK_SUBJECT_KEYS
#                   This indicates that you want to go from a key whose value is mixed to a set of multiple keys of a specific type
#                   ie. smac -> All_Traffic.dest indicates to automatically set src/smac/shost based on the value of All_Traffic.dest
#                   An additional mapping from shost or src in this example would be ignored ie. shost -> myhost
#
#                   Severity Field:
#                   If the fieldmap has any mappings to cef_key "severity" we will automatically invoke `get_cef_severity(1)`
#                   If the severity is userdefined we will still test for 0-10
#                   Default is 5
#
#                   Device Vendor (dvc_vendor) and Device Product (dvc_product)
#                   If the fieldmap has mappings from dvc_vendor or dvc_product to splunk_key=*.vendor_product
#                   We will automatically revert to a dvc_vendor->vendor dvc_product->product mapping
#                   
#{        
#    "<cef_key>":  {"cef_value_type": "<fieldmap|userdefined>",
#                   "splunk_key":     "<splunk field name where cef_value_type=fieldmap>",
#                   "cef_value":      "<value where cef_value_type=userdefined>",
#                   "time_format":    "<time format>"},
#    ...
#    "<cef_key_n>": {"cef_value_type": "<fieldmap|userdefined>",
#                    "splunk_key":     "<splunk field name where cef_value_type=fieldmap>",
#                    "cef_value":      "<value where cef_value_type=userdefined>",
#                    "time_format":    "<time format>"}
#}
