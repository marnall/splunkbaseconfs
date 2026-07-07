# What is it?

**Sendresults** is an immensely powerful, life-changing Splunk command and alert action developed by Discovered Intelligence that allows you to send tabulated search results to individuals dynamically, based upon the data within the results. This means that you no longer need to hardcode an email into the search, but can evaluate the email instead.

# Example Use Cases

The Use Cases are wide and far reaching. Here are some examples of where **Sendresults** might be useful:

Security

- **Sendresults** to individuals who are locked out of their accounts with instructions on how to reset their password or get their account unlocked.
- **Sendresults** to individuals or incident responders about identified security incidents relevant to them specifically

Operations

- **Sendresults** to internal business customers with a report on their Splunk license usage for a given period of time
- **Sendresults** of high severity to one person and send results of a lower severity to the whole team. Alternatively, sendresults to one person but include the whole team, when the severity is high.

# How is this different to the email action or sendemail command?

Quite different and a lot more dynamic. The email action and `sendemail` command allows a user to send the results of a search to an email address hardcoded into the alert or search string. The problem here is that you have to state the email address(es) upfront within the search and all of the results go to the specified email address(es). However, using **Sendresults**, you can dynamically evaluate the email from the individual results and send some results to one individual and other results to other individuals.

# Key Features

We have worked hard to ensure that **Sendresults** is not only simple to use, but also contains awesome functionality. Here are the key features of the command:

- Dynamically evaluate who to send results to, the email subject, email body, and the email footer, based upon the results of the search itself
- Send only relevant search results to an individual
- BCC additional email addresses if necessary
- A simple command and alert action – no scripting or coding required
- Uses the built in email configuration of Splunk
- Parse inline CSS to customise the look of the tabulated results
- Specify a limit on the amount of results sent
- Email group, comma separated or individual email addresses
- Attach the results as a CSV file
- It’s totally free! ([Although, if you are looking for Splunk Services click here](http://discoveredintelligence.ca/splunk-services "DI Splunk Services")).

# Installation

The app is super simple to install.

1. Download the app from Splunkbase
2. Install the app on a search head or search head cluster.
3. Restart Splunk
4. Use the commmand in a search and/or create an alert with a Sendresults action!

# Usage

When using either the Search Command or Alert Action version of **Sendresults** there must be a field named `email_to` within the results that are being passed into **Sendresults**. Ideally data should be formatted in tabular format. The value of the `email_to` field will be used to group the results together. The value of this field must be a valid email address or a comma separated list of email addresses. If `email_subj` or ``email_body`` or ``email_footer`` fields are also present in the results, the first value of those fields for each `email_to` will set the corresponding field in the email.

## Search Command

The Search Command version of **Sendresults** supports the following syntax and optional arguments:

    sendresults [sender=string] [subject=string] [body=string] [footer=string] [maxrcpts=int] [msgstyle=string] [format_columns=string] [bcc=string] [showresults=boolean] [showemail=boolean] [showsubj=boolean] [showbody=boolean] [showfooter=boolean]

`sender`: The sender (from) address of the emails - requires quotes. Defaults to Splunk SMTP sender setting. The same sender is used for all emails sent and not customizable on a per-email basis.

`subject`: The subject of the emails - requires quotes. If set, will override any value in an `email_subj` field in the results. If no subject is defined it will default to: "Splunk Alert!".

`body`: The body of the emails – requires quotes. If set, will override any value in an `email_body` field in the results. If no body is defined then it will default to "You are receiving this e-mail because a set of sensitive events detected by a splunk search contained your e-mail as the responsible party. Auto-generated results compilation follows:".

`footer`: The footer of the emails - requires quotes. If set, will override any value in an `email_footer` field in the results. If no footer is defined it will default to nothing".

`maxrcpts`: Allows a limit to be provided that controls how many emails get sent out. This is to prevent an oversight that might result in a lot more people being emailed than imagined. Defaults to 200.

`msgstyle`: Allows inline CSS to be parsed to style the email going out to individuals – requires quotes. Defaults to “table {font-family:Arial;font-size:12px;border: 1px solid black;padding:3px}th {background-color:#4F81BD;color:#fff;border-left: solid 1px #e9e9e9} td {border:solid 1px #e9e9e9}”.

`format_columns`: A list of fields (comma separated) that will have an HTML class value applied based on the value of the corresponding *-class field (Optional).

`bcc`: A list of email addresses (comma separated) that all emails generated by sendresults will be BCC'd to.

`field_order`: Defines the order of the fields in the Email/CSV (comma separated). Only a partial list is required and the remaining fields will be filled in as they are in the data.

`sendcsv`: Allows the attachment of a CSV of the results to the email.

`addinfo`: Adds a sendresults_sent field to the events with the timestamp of when the message was sent. If the message failed to be sent it will return a -1. Default value is false.

`stoponerror`: Will cause sendresults to stop processing if an error occurs. Default value is true.

`showresults`: Show or hide the results table in the emails that are sent out. Accepted values are t or f; representing true or false respectively. Defaults to true (i.e. showresults=t).

`showemail`: Allows the `email_to` column of the results to be hidden in the emails that are sent out. Accepted values are t or f; representing true or false respectively. Defaults to true (i.e. showemail=t).

`showsubj`: Allows the `email_subj` column of the results to be hidden in the emails that are sent out. Accepted values are t or f; representing true or false respectively. Defaults to true (i.e. showsubj=t).

`showbody`: Allows the `email_body` column of the results to be hidden in the emails that are sent out. Accepted values are t or f; representing true or false respectively. Defaults to true (i.e. showbody=t).

`showfooter`: Allows the `email_footer` column of the results to be hidden in the emails that are sent out. Accepted values are t or f; representing true or false respectively. Defaults to true (i.e. showfooter=t).

## Alert Action

Configure an alert through the normal means (GUI or savedsearches.conf) and add a Sendresults action with the following options:

`Sender`: The sender (from) address of the emails - requires quotes. Defaults to Splunk SMTP setting. The same sender is used for all emails sent and not customizable on a per-email basis.

`Subject`: The subject of the emails. If set, will override any value in an `email_subj` field in the results. If no subject is defined it will default to: "Splunk Alert!"

`Message Body`: The body of the emails. If set, will override any value in an `email_body` field in the results. If no body is defined then it will default to "You are receiving this e-mail because a set of sensitive events detected by a splunk search contained your e-mail as the responsible party. Auto-generated results compilation follows:"

`Message Footer`: The footer of the emails - requires quotes. If set, will override any value in an `email_footer` field in the results. If no footer is defined it will default to nothing".

`Message Style`: Allows inline CSS to be parsed to style the email going out to individuals. Defaults to “table {font-family:Arial;font-size:12px;border: 1px solid black;padding:3px}th {background-color:#4F81BD;color:#fff;border-left: solid 1px #e9e9e9} td {border:solid 1px #e9e9e9}”

`Column Formatting`: A list of fields (comma separated) that will have an HTML class value applied based on the value of the corresponding *-class field (Optional).

`BCC Addresses`: A list of email addresses (comma separated) that all emails generated by sendresults will be BCC'd to.

`Max Recipients`: Allows a limit to be provided that controls how many emails get sent out. This is to prevent an oversight that might result in a lot more people being emailed than imagined. Defaults to 200.

`Field Order`: Defines the order of the fields in the Email/CSV (comma separated). Only a partial list is required and the remaining fields will be filled in as they are in the data.

`Send CSV`: Allows the attachment of a CSV of the results to the email.

`Show the results table`: When checked, will display the results table in the emails that are sent out.

`Show the "email_to" field`: When checked, allows the `email_to` column of the results to be visible in the emails that are sent out.

`Show the "email_subj" field`: When checked, allows the `email_subj` column of the results to be visible in the emails that are sent out.

`Show the "email_body" field`: When checked, allows the `email_body` column of the results to be visible in the emails that are sent out.

`Show the "email_footer" field`: When checked, allows the `email_footer` column of the results to be visible in the emails that are sent out.

# Examples

Example 1: Send web access search results with a method of "POST" to one email address and search results with a method of "GET" to another.

    ...| eval email_to=case(method=="GET","email_1@discoveredintelligence.ca",method=="POST","email_2@discoveredintelligence.ca")
    | sendresults subject="Splunk Internal Results" body="Here are the internal Splunk results for you to review" msgstyle="table {font-family:Arial;font-size:12px;border: 1px solid black;padding:3px}th {background-color:#AAAAAA;color:#fff;border-left: solid 1px #e9e9e9} td {border:solid 1px #e9e9e9}"

Example 2: Build the email address to send to from the user_id field in the results.

    …| eval email_to=user_id."@discoveredintelligence.ca" | sendresults

Example 3: Take the current email address and append a hardcoded CC address to the dynamic email address.

    …| eval email_to=email.",my_cc_email@discoveredintelligence.ca" | sendresults

Example 4: Send web access search results with 500 status codes to one email address and search results with 400 status codes to another with a customized email subject.

    …| eval email_to=case(status>=500,"email_1@discoveredintelligence.ca",status>=400,"email_2@discoveredintelligence.ca")
    | eval email_subj=case(status>=500,"Critical Severity Errors",status>=400,"High Severity Errors") | sendresults

Example 5: Specify a limit of 500 rather than the default of 200 and choose not to display the email column in the emails being sent out.

    …| sendresults maxrcpts=500 showemail=f

Example 6: Bring in a lookup containing values X and Y depending on the result, then send results containing an X to one email and results containing a Y to another.

    …| lookup field1 AS field1 OUTPUT xyfield AS xyfield
    | eval email_to=case(xyfield=="X","email_1@discoveredintelligence.ca", xyfield=="Y","email_2@discoveredintelligence.ca")
    | sendresults

Example 7: Highlight the "count" cells with a red backround which have a count > 10.

    ...| eval count-class=if(count>10,"alert","")
    | sendresults msgstyle="table {font-family:Arial;font-size:12px;border: 1px solid black;padding:3px}th {background-color:#4F81BD;color:#fff;border-left: solid 1px #e9e9e9} td {border:solid 1px #e9e9e9} .alert {background-color:red;}" format_columns="count"

Example 8: Order the fields in the email such that the time field is first, followed by status, with all other remaining fields added.

    …| sendresults field_order="time,status"

Example 9: Attach a CSV of the results to the email.

    …| sendresults sendcsv=true

_The above examples are for the command version of Sendresults, but to use with the Sendresults Alert Action remove the `| sendresults` portion of the search and configure the saved search as an alert with the Sendresults Alert Action added using the desired configuration options._

# Logging

Of course, this being Splunk, we have to include some logging for completeness! The sendresults command has a dedicated log file for your viewing and indexing pleasure. The location of the log file is SPLUNK_HOME/var/log/sendresults.log and it contains error logs, in addition to informational messages about how many results were sent out and to whom they were sent to.

Logs can be viewed using:

    index=_internal sourcetype=sendresults:log

# Troubleshooting

I get tons of fields in my emails, but only want to see a few

- You should declare the fields you want to see through the use of commands like `| fields`, `| table` or `| stats`.

I see a lot of _fields in the email results, but I do not want to see these_

- You can use something like `| fields - _*` to remove these fields and stop them being inserted into the email results. Bear in mind you might want to see the `_time` field, so you could `| rename` this field to `time` or similar, then do `| fields - _*` to eliminate the other underscored fields.

I don’t want to see the email fields in my results

- Command: Set the `showemail`, `showsubj`, or `showbody` arguments to `false` when crafting the search
- Alert Action: Uncheck the "Show the X" checkboxes in the action form
