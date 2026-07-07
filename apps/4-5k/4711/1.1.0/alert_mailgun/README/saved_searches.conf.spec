[mailgun_email_action]

action.mailgun_email_action = [0|1]
* Enable Mailgun Email Action

action.mailgun_email_action.param.url = <string>
* Mailgun URL to send to. Usually https://api.mailgun.net/v3/mydomain.com
* (required)

action.mailgun_email_action.param.api_key = <string>
* API Key
* (required)

action.mailgun_email_action.param.from = <string>
* Email address the email should be from.
* (required)

action.mailgun_email_action.param.to = <string>
* Email address to send to. Can be a comma seperated list.
* (required)

action.mailgun_email_action.param.email_type = <HTML|TEXT>
* Type of email to send. HTML or Text.
* (required)

action.mailgun_email_action.param.subject = <string>
* Subject for the email
* (required)

action.mailgun_email_action.param.content = <string>
* Content of the email
* (required)
