[smime_send_email]
python.version = <string>
* Python version for the alert action.

param.to = <string>
* Comma-separated list of recipient email addresses.

param.to.required = <bool>
* Whether the To field is required.

param.to.label = <string>
* Display label for the To field.

param.cc = <string>
* Comma-separated list of CC email addresses.

param.cc.required = <bool>
* Whether the CC field is required.

param.cc.label = <string>
* Display label for the CC field.

param.bcc = <string>
* Comma-separated list of BCC email addresses.

param.bcc.required = <bool>
* Whether the BCC field is required.

param.bcc.label = <string>
* Display label for the BCC field.

param.priority = <integer>
* Email priority (1=Highest, 2=High, 3=Normal, 4=Low, 5=Lowest).

param.priority.required = <bool>
* Whether the Priority field is required.

param.priority.label = <string>
* Display label for the Priority field.

param.subject = <string>
* Email subject line. Supports token substitution.

param.subject.required = <bool>
* Whether the Subject field is required.

param.subject.label = <string>
* Display label for the Subject field.

param.body = <string>
* Email body content. Supports token substitution.

param.body.required = <bool>
* Whether the Body field is required.

param.body.label = <string>
* Display label for the Body field.

param.content_type = <string>
* Content type of the email body: html or plain.

param.content_type.required = <bool>
* Whether the Content Type field is required.

param.content_type.label = <string>
* Display label for the Content Type field.

param.format = <string>
* Format for inline results: table, raw, or csv.

param.format.required = <bool>
* Whether the Format field is required.

param.format.label = <string>
* Display label for the Format field.

param.include_link_to_alert = <bool>
* Include a link to the triggered alert in the email body.

param.include_link_to_alert.required = <bool>
* Whether the Include Link to Alert field is required.

param.include_link_to_alert.label = <string>
* Display label for the Include Link to Alert field.

param.include_link_to_results = <bool>
* Include a link to search results in the email body.

param.include_link_to_results.required = <bool>
* Whether the Include Link to Results field is required.

param.include_link_to_results.label = <string>
* Display label for the Include Link to Results field.

param.include_search_string = <bool>
* Include the search string in the email body.

param.include_search_string.required = <bool>
* Whether the Include Search String field is required.

param.include_search_string.label = <string>
* Display label for the Include Search String field.

param.include_inline = <bool>
* Include inline search results in the email body.

param.include_inline.required = <bool>
* Whether the Include Inline Results field is required.

param.include_inline.label = <string>
* Display label for the Include Inline Results field.

param.include_trigger_condition = <bool>
* Include the trigger condition in the email body.

param.include_trigger_condition.required = <bool>
* Whether the Include Trigger Condition field is required.

param.include_trigger_condition.label = <string>
* Display label for the Include Trigger Condition field.

param.include_trigger_time = <bool>
* Include the trigger time in the email body.

param.include_trigger_time.required = <bool>
* Whether the Include Trigger Time field is required.

param.include_trigger_time.label = <string>
* Display label for the Include Trigger Time field.

param.attach_csv = <bool>
* Attach search results as a CSV file.

param.attach_csv.required = <bool>
* Whether the Attach CSV field is required.

param.attach_csv.label = <string>
* Display label for the Attach CSV field.

param.attach_pdf = <bool>
* Attach a PDF of the dashboard or search results.

param.attach_pdf.required = <bool>
* Whether the Attach PDF field is required.

param.attach_pdf.label = <string>
* Display label for the Attach PDF field.
