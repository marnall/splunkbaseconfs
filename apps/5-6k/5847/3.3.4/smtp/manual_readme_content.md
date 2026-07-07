## Backward compatibility

- In the version 3.0.0, a new configuration parameter “Authentication type” is added. Once the
  connector is upgraded from any of the previous version to 3.0.0, the default value “Automatic”
  will be set in “Authentication type” parameter and it will behave as stated below in the
  document.
- After the app is upgraded to v3.0.0, it is suggested to update the value of “Authentication
  type” parameter to the suitable value by editing and re-saving the asset, in order to ensure
  test connectivity works as expected

## Authentication Type parameter

- In the version 3.0.0 of the connector, we have added the new asset configuration parameter
  “auth_type”. This is an optional parameter and it is used to determine the type of
  authentication to use for test connectivity.

<!-- -->

- The “Authentication type” parameter has four options:
  - Automatic (default)
  - OAuth/Interactive Authentication
  - Basic
  - Passwordless

<!-- -->

- **Automatic (default)** :
  - For automatic auth_type priority of authentication flow is in decreasing order as follows:
    1. OAuth
    1. Basic
    1. Passwordless
  - First, the required parameters for the OAuth will be checked, if provided, the connector
    will try to establish the connection using the OAuth authentication.
  - If OAuth authentication fails, the required parameters for the Basic Authentication will be
    checked, if provided, the connector will try to establish the connection using the Basic
    Authentication.
  - If the Basic authentication also fails, then the connection will be established using the
    passwordless authentication. If the connection for passwordless also fails, the test
    connectivity will be considered unsuccessful for Automatic Authentication.
- **OAuth** :
  - If this option is selected, the connector will explicitly use the OAuth mechanism to connect
    with the given server.
  - First the required parameters for the OAuth will be verified, if all the required parameters
    are entered, the connector will try to establish the connection with the server. If the
    connection is successful, test connectivity will pass.
  - Required parameters for the OAuth Authentication are:
    - Username
    - Client ID
    - Client Secret
    - OAuth Authorization URL
    - OAuth Token URL
  - If any of the above mentioned parameter is missing the test connectivity will fail.
- **Basic** :
  - If this option is selected, the connector will explicitly use the Basic Authentication to
    connect with the given server.

  - First the required parameters for the basic authentication will be verified, if all the
    required parameters are entered, the connector will try to establish the connection with the
    server. If the connection is successful, test connectivity will pass.

  - Required parameters for the Basic Authentication are:

    - Username
    - Password

    If any of the above mentioned parameter is missing the test connectivity will fail.
- **Passwordless** :
  - If this option is selected, the connector will explicitly use the Passwordless
    Authentication to connect with the given server.

  - No parameter is required to establish the connection using the passwordless mechanism. If
    the provided server is valid SMTP server the test connectivity will pass.

    **Note:** When using the Passwordless Authentication, it may happen that the test
    connectivity will pass but the send email action may fail, this can happen due to the server
    expecting user authentication to send the email, and in passwordless we are only validating
    the server.

## General Points

- Attachments and HTML formatting are supported

- The asset configuration parameter **Enable SMTPUTF8 support (Check this only if the SMTP server
  supports SMTPUTF8 option)** should be disabled if the SMTP server does not support the SMTPUTF8
  configuration option. For the SMTP servers supporting SMTPUTF8, please enable this parameter. If
  this parameter is kept disabled for the SMTP servers supporting SMTPUTF8, all the actions having
  Unicode characters in TO, CC or BCC attributes will fail due to encoding issues in Python 3
  installation of the app due to a known SDK behavior.

- The Gmail server's policy set is to use the username associated with the login credentials as
  the 'from' address by default. To send the email from a different address follow the given
  [steps](https://support.google.com/mail/answer/22370?hl=en&authuser=1#zippy=) to configure the
  email address on Gmail server.\
  Note - Uncheck 'Treat as an alias' while adding email address for sending email from another
  email address.

- The **username** and **password** fields for an SMTP Asset are optional because some SMTP
  servers do not require any authentication to accept mail. The **ssl_config** and **port** fields
  are related, but only the field **port** is optional. This is because each of the ssl_config
  options has an associated default port number, and you only have to specify the port if you want
  to override that default. For example, the default SMTP port for StartTLS-style encryption is
  587, but it's also possible to do start TLS on port 25. So in that case, you may want to select
  StartTLS and specify port 25. The default port numbers are listed in this table:

  |         SSL Method | Port |
  |-----------------------|------|
  |          **None** | 25 |
  |          **SSL** | 465 |
  |          **StartTLS** | 587 |

- Splunk SOAR (Cloud) does not provide access to TCP port 25 \[
  [link](https://docs.splunk.com/Documentation/SOAR/current/ServiceDescription/SplunkSOARService#Differences_Between_Splunk_SOAR_.28Cloud.29_and_Splunk_SOAR)
  \]. However, Splunk SOAR (On-premises) does and will provide outbound access for cloud-to-cloud
  connections for appropriate SMTPS ports like 587, 465, or a customized port. If there is a
  requirement to access TCP port 25 SMTP on Splunk SOAR (Cloud) then it can be achieved within the
  internal environments through the Automation Broker.

  To obtain the required parameters, please check the document of the service provider

  Here we have attached links for the most used mail services to find parameters values:

  GOOGLE

  [Setting up OAuth2.0](https://support.google.com/cloud/answer/6158849?hl=en) [Using OAuth2.0 to
  access google
  API's](https://developers.google.com/identity/protocols/oauth2#1.-obtain-oauth-2.0-credentials-from-the-dynamic_data.setvar.console_name-.)

  MICROSOFT

  [Authentication for
  SMTP](https://learn.microsoft.com/en-us/exchange/client-developer/legacy-protocols/how-to-authenticate-an-imap-pop-smtp-application-by-using-oauth)
  [Authorization code flow for
  OAuth2.0](https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow)

  Note: Service providers might have html/css rendering issues.

## Playbook Backward Compatibility

- The behavior of the following action has been modified. Hence, it is requested to the end-user
  to please update their existing playbooks by re-inserting the corresponding action blocks or by
  providing appropriate values to these action parameters to ensure the correct functioning of the
  playbooks created on the earlier versions of the app.

  - Send RawEmail - To run this action, provide the **raw_email** parameter as a string
    separated using the new line character ('\\n' between headers like to, from, cc, bcc,
    subject) ('\\n\\n' before providing the body text or HTML after the headers). The example
    value for the same has been provided in the **Examples for Send RawEmail** section below.
    The action can also be executed using the playbook.\
    To run the action using playbook, the user can also provide the **raw_email** parameter as a
    multi-line string, i.e., any string enclosed within three double-quotes ("""some-string""")
    or three single-quotes ('''some-string''')

## Actions Key Points

- Send Email

  - For email consisting of HTML body to be processed correctly as HTML, it must start with
    either "\<!DOCTYPE html" declaration or "&lthtml" and the tag should end with ">"

- Send Email and Send HTMLEmail

  - For emails consisting of Unicode characters, set the **encoding** asset configuration flag
    to true.

- Send RawEmail

  - The **encoding** asset configuration flag does not apply to this action.

## Examples for Send RawEmail

- The **raw_email** action parameter can be provided in the following ways.

  - Example 1\
    **raw_email** =
    to:receiver@testdomain.com\\nfrom:sender@testdomain.com\\nsubject:Test\\n\\nThis is body
    text
  - Example 2:\
    **raw_email** =
    to:receiver@testdomain.com\\nfrom:sender@testdomain.com\\nContent-type:text/html\\nsubject:HTML
    Test\\n\\n\<html>\<body>\<h2>This is test\</h2>\<br>This is some üñîçøðé
    data.\</body>\</html>
  - Example 3:\
    **raw_email** =
    to:receiver1@testdomain.com,receiver2@testdomain.com\\nfrom:sender@testdomain.com\\nsubject:CommaSeparated
    Recipients Test\\n\\nThis is test data.
