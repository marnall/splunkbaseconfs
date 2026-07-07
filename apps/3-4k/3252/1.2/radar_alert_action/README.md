# RADAR Alert Action Add-on

## Introduction

The RADAR Alert Action Add-on allows Splunk to create incidents in RADAR.

## Requirements

To use the RADAR Alert Action Add-on, you will need a RADAR API token with Incidents Write scope.  You can create a token as a top-level RADAR administrator, or ask your local administrator to provide one for you.

## Installation and configuration

To install the RADAR Alert Action Add-on, follow the instructions in the [Splunk Add-ons](http://docs.splunk.com/Documentation/AddOns/latest/Overview/Installingadd-ons) documentation. Once the add-on is installed, perform the following steps:

1. Sign in to Splunk, click **Settings** in the top bar, then click **Alert Actions**. 
2. Click **Setup RADAR Alert Action Add-on** in the RADAR Alert Action row.
3. Create a RADAR API token. If you already have a RADAR API token with Incidents Write scope, skip to the next step.
    1. In a separate tab or browser window, sign in to RADAR, go to the **My Account** page under the user menu in the upper right, then click the **API Tokens** tab.
    2. Click **Add Token**, enter a name, then select the **Incidents Write** check box under **Scopes**.
    3. Click **Submit**. Do not navigate away from this generated token page until you complete the next step; otherwise you will need to generate a new token.
4. Copy the *entire* token text, and paste it into the **RADAR API token** field in the RADAR Alert Action configuration screen. 
5. If you wish, disable the checkbox labeled "Allow self-signed SSL certificate for token storage access." See more
   information about this [below](#ssl-certificate-verification).
6. Click **Save**. If the update is successful, you should see a Splunk success message.

## Usage

### Create an existing alert with the RADAR alert action

1. In the **Search & Reporting** app, run a search for your string.
2. Confirm that the search results look as you expect.
3. Click the **Save As** dropdown link above the right side of the search box, then select **Alert** from the menu that appears.
4. Enter a title for your alert, along with a description if desired, and configure the standard alert fields related to permissions, scheduling, and trigger conditions according to your needs.
5. Under **Trigger Actions**, click **+ Add Actions**, then select **RADAR Alert Action**.
6. Enter the incident name and description that you want RADAR to use when the alert is triggered, then click **Save**.  Your alert will be created, and Splunk will create an incident in RADAR any time it triggers.

### Add a RADAR action to an existing alert

1. In the **Search & Reporting** app, navigate to the **Alerts** tab and locate the existing alert.
2. Click **Edit**, then select **Edit Actions**.
3. Click **+ Add Actions**, then select **RADAR Alert Action Add-on**.
4. Enter the incident name and description that you want RADAR to use when the alert is triggered, then click **Save**. Spunk will now create an incident in RADAR any time the alert triggers.

## Advanced usage

### Default incident name and description

If you want a different default name or description for an incident, you can change this system-wide setting by manually editing a configuration file and restarting Splunk. 

The default values are defined in `$SPLUNK_HOME/etc/apps/radar_alert_action/default/alert_actions.conf`, but your changes go into the local configuration file that overrides these defaults: `$SPLUNK_HOME/etc/apps/radar_alert_action/local/alert_actions.conf`. 

If this file does not already exist, create it with contents such as the following:

```
[radar]

param.radar_incident_name = New default name for created incidents
param.radar_incident_description = New default description for created incidents
```

**Important**: Overriding default configuration values will affect any existing alerts that used the previous defaults.

### SSL certificate verification

The RADAR Alert Action Add-on uses HTTPS to communicate securely with RADAR. It also uses HTTPS to communicate
with Splunk's encrypted password store when it needs to save or retrieve your RADAR API token.

Default Splunk installations use a self-signed SSL certificate for these interactions, rather than a certificate signed
by a trusted authority. Because this is not secure, SSL certificate verification cannot succeed (unless you
[add the certificate to your system's keychain](#adding-the-default-splunk-certificates-to-your-systems-keychain), but
this approach is not officially supported). To prevent errors, SSL certificate verification is disabled by default for
interactions with Splunk's encrypted store.

#### Enabling certificate verification

If you have set up a non-self-signed certificate chain and wish to enable this additional layer of security, disable the
"Allow self-signed SSL certificate for token storage access" checkbox on the RADAR Alert Action Add-on configuration
screen.

Please note that because Splunk stores its secret key to that storage on the local file system anyway, the difference
this makes to actual system security is not profound.

See the
[Splunk documentation about SSL](http://docs.splunk.com/Documentation/Splunk/latest/Security/AboutsecuringyourSplunkconfigurationwithSSL)
for more on this topic.

#### Adding the default Splunk certificates to your system's keychain

_NOTE: This approach is not officially supported by RADAR._

One possible alternative to leaving SSL certificate verification disabled, or configuring Splunk with a certificate
signed by a trusted authority, is to add Splunk's self-signed certificates to your system's keychain. Although not as
secure as trusted certificates, using the default certificates is an option that can be made to work if for some reason
you cannot set up a properly secured certificate and do not want to disable verification entirely.

Since the process of adding certificates will depend on your system, this approach may be troublesome to get right and
cannot be officially supported by RADAR. Here are some tips that may be useful:

* The default Splunk certificates can be found at `$SPLUNK_HOME/etc/auth/cacert.pem`
* Depending on your system, you may need to provide an environment variable to Splunk when starting or restarting to tell Splunk where the certificates can be found. For example, `REQUESTS_CA_BUNDLE=$SPLUNK_HOME/etc/auth/cacert.pem splunk start`
* If you continue to experience errors in the browser, check `$SPLUNK_HOME/var/log/splunk/splunkd.log` for more information. Of course, you can always [contact us](#support) with any questions and we will do our best to help.

## Troubleshooting

### Error message when attempting to configure RADAR Alert Action

If you access the setup page and find an error message ("Cannot proceed while SSL cert verification is enabled. See
README.") in the **API token** text box, this means the RADAR Alert Action Add-on encounterd an SSL certificate
verification failure was not able to connect securely to Splunk when checking for any existing API token.  This
generally means that the Splunk instance is not configured with an SSL certificate signed by a trusted certificate
authority.

Please see the above sections under [SSL Certificate Verification](#ssl-certificate-verification) for information on
how to resolve this.  If you receive other kinds of errors or are unable to resolve the problem with the instructions in
this document, please [contact RADAR](#support).

### Server error when saving the add-on configuration

When you click **Save** on the add-on configuration page, the system connects to RADAR to verify the provided API token. If you receive an error, please double-check that your token was set up with the **Incidents Write** check box selected and that it has been copied and pasted correctly.

### Incidents not appearing in RADAR

If expected incidents do not appear in RADAR, check the following to narrow down the problem.

Every attempt to create an incident will be mentioned in `$SPLUNK_HOME/var/log/splunkd.log`. Check this file to confirm that incident creation is being attempted, keeping an eye out for any errors that may have been logged in case of failure.

It can also be helpful to monitor triggered alerts to confirm whether triggers are happening when expected. You can set this up in Splunk by adding an alert to a list of triggered alerts.

When you add an alert to a list of triggered alerts, you can see records of recently triggered alerts from the Triggered Alerts page or from an Alert Details page.  Any alerts that would have created incidents in RADAR will display here. 

If you continue to experience issues, please [contact RADAR](#support) and we will be happy to help.

## Support

Please feel free to contact RADAR for assistance with any questions about using the RADAR Alert Action Add-on.

Email: <support@radarfirst.com>

Phone: 855-733-9888

## License
The RADAR Alert Action Add-on is a licensed product of RADAR, Inc.
