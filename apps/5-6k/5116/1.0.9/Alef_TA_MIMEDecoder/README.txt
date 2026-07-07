Splunk MIME Decoder add-on allows for decoding MIME-encoded (URL-encoded) strings. It was developped to decode field values containing ciphered email subjects as a byproduct of pass-through Cisco ESA email proxy. Add-on provides a custom search command to do this. The main advantage of this command is that it is able to decode any MIME-encoded string in any charset, not just in UTF-8 which is a limitation of standard SPL eval function `urldecode`.

Originally the main purpose of of this 

# System Requirements

None

# Installation

Install on Splunk Search Head only.

# Configuration

No need to configure this app.

# Usage

Use command as per example below. Input and output fields may have the same name.

## Syntax:
`| mimedecode <field_with_encoded_text> <field_with_decoded_text>`

## Example:
`| makeresults count=1`
`| eval field1_in="=?UTF-8?Q?Alert_Google_=E2=80=93_Bank_of_England?="`
`| eval field2_in="=?ISO-8859-2?Q?RE=3A_Odpov=EC=EF=3A_Terasy_C1?="`
`| mimedecode field1_in field1_out`
`| mimedecode field2_in field2_out`

<table>\
<tr><td>Input String</td><td>Input MIME-encoded Charset</td><td>Output String</td>
<tr><td>=?UTF-8?Q?Alert_Google_=E2=80=93_Bank_of_England?=</td><td>UTF-8</td><td>Alert Google - Bank of England</td>
<tr><td>=?ISO-8859-2?Q?RE=3A_Odpov=EC=EF=3A_Terasy_C1?=</td><td>ISO-8859-2</td><td>RE: Odpověď: Terasy C1</td>
</table>

# Testing:
Add-on was successfully tested with these charsets: UTF8, Windows-1250, ISO-8859-2. However, it should work for many others charsets just as well. 

This add-on relies on Python and its `email` standard library (an email and MIME handling package). You can check details at https://docs.python.org/3/library/email.header.html.

# Bugs
There were some issue with Japanese charset. This has to be investigated more.

# Release Notes
1.0.0    
    - initial release
1.0.1
    - fixed cosmetic issues
1.0.2
    - fixed an issue: command failed when an event does not contain a field being decoded (exception)
1.0.3
    - fixed an issue: command failed in Splunk 8.1.1 (python 3.7.8) for not following strictly case-sensitive class names
1.0.4
    - fixed an issue: upgraded Splunk python SDK to version 1.6.15 to fix a bug SPL-194426 
1.0.5
    - skipped
1.0.6
    - fixed an issue: decoding function was failing on strings beginning with "space" after '?Q?' sequence
    - upgrade: upgraded Splunk Python SDK to version 1.7.2
1.0.7
    - regenerated via Splunk Add-on Builder 4.1.3 to comply with the most recent Splunk Cloud App Inspect vetting checks
1.0.8
    - regenerated via Splunk Add-on Builder 4.2 to comply with the most recent Splunk Cloud App Inspect vetting checks
1.0.9
    - No longer maintained in Splunk Add-on builder 
    - update splunk-sdk to 2.1.1
    - tested in Splunk 10.0.2


