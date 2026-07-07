# This file describes the snowtbl_endpoint.conf file that is included
# with the SNOW Table for Splunk app.
# 

# ---- Stanzas of endpoint subtypes ----
#
# incident.short_description default max length is 160 (New York version)
# incident.description default max length is 4000 (New York version)
#

[<endpoint_subtype>]

snowtbl_table = <string>
* ServiceNow table name
* If snowtbl_table is not in the stanza or empty, the snowtbl_table parameter in the request's form data is used

snowtbl_max_table = <integer>
* Maximum length of the ServiceNow table name

eptype = <create_ticket | run_query>
* Endpoint type - valid values are create_ticket or run_query

pfields = <CSV string>
* Semicolon seperated string with the ServiceNow field name, maximum length of field value, and override field value seperated by a colon
* The ct_rest and ct_general stanzas should have a field named snowtbl_fields which the user provides a JSON string with ServiceNow field names and field values
* The format is field name : maximum length of field value : override field value

alert_result_field = <string>
* ServiceNow table field to return as the alert action status
* For example, alert_result_field=number 
