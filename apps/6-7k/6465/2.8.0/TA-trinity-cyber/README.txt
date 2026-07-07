# Trinity Cyber Add-on for Splunk

## Description

The Trinity Cyber Add-on provides a modular input to poll events from the
Trinity Cyber Customer Portal and index them into Splunk.

## Support

Contact your Trinity Cyber customer success manager for support using this add-on.

## Fields

The following fields are pulled from the Trinity Cyber API and are indexed into Splunk:

| Field                        | Description                                                                                                                                              |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id                           | Identifier for event in the Trinity Cyber API                                                                                                            |
| actionTime                   | Date/time that the event action was performed                                                                                                            |
| portalUrl                    | URL to view the event in the Trinity Cyber Portal                                                                                                        |
| sourceIp                     | Source address (IP address of the client that initiated the session)                                                                                     |
| destinationIp                | Destination address                                                                                                                                      |
| sourcePort                   | Source TCP/UDP port                                                                                                                                      |
| destinationPort              | Destination TCP/UDP port                                                                                                                                 |
| transportProtocol            | The transport protocol of the session (e.g. TCP / UDP)                                                                                                   |
| direction                    | Direction of the malicious activity detected by the formula                                                                                              |
| trustInitiated               | Indicates that the session was initiated by the trust side of the network (i.e. not the Internet)                                                        |
| customer                     | Customer this event triggered on                                                                                                                         |
| customer.name                | Customer name                                                                                                                                            |
| connector                    | Connector this event triggered on                                                                                                                        |
| connector.name               | Connector name                                                                                                                                           |
| device                       | The user device (if any) associated with this event. This is only available for VPN-connections or other devices registered in the Trinity Cyber Portal. |
| device.id                    | Device ID assigned by Trinity Cyber                                                                                                                      |
| device.clientDeviceId        | Device ID assigned by the client                                                                                                                         |
| device.deviceName            | Friendly device name                                                                                                                                     |
| device.deviceType            | Device type (e.g. Windows / iOS)                                                                                                                         |
| formula                      | List of formulas that matched                                                                                                                            |
| formula.formulaId            | Numeric formula ID                                                                                                                                       |
| formula.title                | Formula Title                                                                                                                                            |
| formula.background           | Background information about the threat                                                                                                                  |
| formula.tags                 | Formula tags                                                                                                                                             |
| formula.tags.category        | Tag category (e.g. ATT&CK Tactic)                                                                                                                        |
| formula.tags.value           | Tag value                                                                                                                                                |
| applicationProtocol          | The application protocol for this event                                                                                                                  |
| firstPayloadsSha256          | The SHA-256 hashes of the first payload objects below the protocol layer (e.g. file download)                                                            |
| firstPayloadsFilename        | The file names of the first payload objects, if known                                                                                                    |
| forwardProxyClientIdentifier | The forward proxy identifier header, if known                                                                                                            |
| forwardProxyClientIp         | The forward proxy IP header, if known                                                                                                                    |
| dnsHost                      | Host name                                                                                                                                                |
| emailFrom                    | MIME from header                                                                                                                                         |
| emailTo                      | MIME to header                                                                                                                                           |
| emailSubject                 | MIME subject header                                                                                                                                      |
| emailMessageId               | MIME message-id header                                                                                                                                   |
| emailReplyTo                 | MIME reply-to header                                                                                                                                     |
| emailDate                    | MIME date header                                                                                                                                         |
| emailXmailer                 | MIME x-mailer header                                                                                                                                     |
| httpRequestMethod            | HTTP request method                                                                                                                                      |
| httpRequestPath              | HTTP request path                                                                                                                                        |
| httpRequestHost              | Value of the HTTP host header                                                                                                                            |
| httpRequestUserAgent         | Value of the HTTP user agent header                                                                                                                      |
| httpResponseStatusCode       | HTTP status code                                                                                                                                         |
| httpResponseStatusString     | HTTP status message                                                                                                                                      |
| httpResponseServer           | Value of the HTTP response server header                                                                                                                 |
| httpResponseContentType      | Value of the HTTP response content-type header                                                                                                           |
| smtpServerBannerMessage      | SMTP banner messages                                                                                                                                     |
| smtpServerBannerStatusCode   | SMTP banner status code                                                                                                                                  |
| smtpMailFrom                 | SMTP MAIL FROM response                                                                                                                                  |
| smtpRcptTo                   | SMTP RCPT (recipient) TO response                                                                                                                        |
| tlsSniHost                   | Host name from the Server Name Indicator (SNI) TLS extension header                                                                                      |

## Libraries Included

This add-on was generated with the Splunk Add-on Builder and includes aob_py3 as a dependency.

# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-trinity-cyber/bin/ta_trinity_cyber/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-trinity-cyber/bin/ta_trinity_cyber/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
