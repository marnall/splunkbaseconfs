# sendresults alert settings

action.sendresults_alert = [0|1]
* Enable sendresults_alert notification

action.sendresults_alert.param.sender = <string>
* Overrides all emails to have this sender
* Defaults to the sender from the Splunk SMTP settings
* (optional)

action.sendresults_alert.param.subject = <string>
* Overrides all emails to have this subject
* Defaults to "Splunk Alert!"
* (optional)

action.sendresults_alert.param.body = <number>
* Overrides all emails to have this body text
* Defaults to "You are receiving this e-mail because a set of sensitive events detected by a splunk search contained your e-mail as the responsible party. Auto-generated results compilation follows:"
* (optional)

action.sendresults_alert.param.maxrcpts = <number>
* Override the deault limit of recipient emails
* Defaults to 200
* (optional)

action.sendresults_alert.param.msgstyle = <string>
* Inline CSS used to style the email
* Defaults to "table {font-family:Arial;font-size:12px;border: 1px solid black;padding:3px}th {background-color:#4F81BD;color:#fff;border-left: solid 1px #e9e9e9} td {border:solid 1px #e9e9e9}"
* (optional)

action.sendresults_alert.param.showemail = [0|1]
* Show the "email_to" column in the results if present
* Defaults to 1
* (optional)

action.sendresults_alert.param.showsubj = [0|1]
* Show the "email_subj" column in the email results if present
* Defaults to 1
* (optional)

action.sendresults_alert.param.showbody = [0|1]
* Show the "email_body" column in the email results if present
* Defaults to 1
* (optional)
