# SendToElement

**SendToElement** is a custom Splunk app developed by **Cyberfox**, headquartered in Astana, Kazakhstan. This application enables seamless delivery of Splunk alerts directly into Element rooms, providing real-time notifications to your teams.

The app provides a custom Splunk alert action that sends alert notifications from Splunk Enterprise to Matrix / Element rooms.

---

## Features

- Send Splunk alert notifications to Matrix / Element rooms
- Configure Matrix / Element homeserver URL
- Configure Matrix room ID
- Configure Matrix access token
- Customize alert title
- Customize alert message body
- Include alert severity in the message
- Optionally include Splunk results link
- Enable or disable SSL certificate verification

---

## Requirements

- Splunk Enterprise
- Python 3 runtime provided by Splunk
- Network connectivity from the Splunk Search Head to the Matrix / Element homeserver
- Matrix / Element access token with permission to send messages to the target room
- Matrix room ID

---

## Installation

1. Copy the app package to the Splunk server.

2. Extract the app into `$SPLUNK_HOME/etc/apps/`:

   ```bash
   tar -xzf send-to-element.tgz -C $SPLUNK_HOME/etc/apps/
   ```

3. Set correct ownership:

   ```bash
   chown -R splunk:splunk $SPLUNK_HOME/etc/apps/SendToElement
   ```

4. Restart Splunk:

   ```bash
   $SPLUNK_HOME/bin/splunk restart
   ```

---

## Configuration

After installation, create or edit a Splunk alert and add the **Send to Element** alert action.

Fill in the required fields in the alert action configuration.

| Field | Description |
| --- | --- |
| Server URL | Matrix / Element homeserver URL. Example: `https://matrix.example.org` |
| Access Token | Matrix access token used to send messages |
| Room ID | Target Matrix room ID. Example: `!abc123:matrix.example.org` |
| Title | Alert message title |
| Message | Alert message body |
| Severity | Alert severity value |
| Result Link | Optionally include a Splunk results link in the message |
| Verify SSL | Enable or disable SSL certificate verification |

---

## Matrix / Element Room ID

The Matrix room ID usually starts with `!`.

Example:

```text
!abc123def456:matrix.example.org
```

Make sure that the Matrix user related to the access token has permission to send messages to this room.

---

## Access Token

The access token must belong to a Matrix / Element user that has permission to send messages to the target room.

If the token is invalid, expired, or belongs to a user that is not joined to the room, message delivery may fail.

---

## Message Placeholders

The alert title and message can use Splunk alert tokens and result fields where supported by Splunk alert configuration.

Example:

```text
Host: $result.host$
User: $result.user$
Source IP: $result.src_ip$
```

This allows alert messages to include useful values from the triggered search result.

---

## Logs

Application logs are written to:

```bash
$SPLUNK_HOME/var/log/splunk/sendtoelement.log
```

Use the following command for troubleshooting:

```bash
tail -f $SPLUNK_HOME/var/log/splunk/sendtoelement.log
```

---

## 🔐 SSL Verification Troubleshooting

If your Element server uses a **self-signed** or **invalid SSL certificate**, the alert may fail to send due to SSL verification errors.

By default, SSL certificate verification is enabled:

```conf
param.verify_ssl = true
```

If you need to disable SSL certificate verification, use one of the following options.

### Option 1: Disable SSL verification in the alert action configuration

When creating or editing a Splunk alert, open the **Send to Element** alert action settings and set:

```text
Verify SSL = false
```

This is the recommended option if the field is available in the alert configuration UI.

---

### Option 2: Disable SSL verification using local configuration

Create or edit the following file:

```bash
$SPLUNK_HOME/etc/apps/SendToElement/local/alert_actions.conf
```

Add the following configuration:

```conf
[sendtoelement]
param.verify_ssl = false
```

Then restart Splunk:

```bash
$SPLUNK_HOME/bin/splunk restart
```

---

### Option 3: Default configuration note

If the app contains the following line in:

```bash
$SPLUNK_HOME/etc/apps/SendToElement/default/alert_actions.conf
```

```conf
param.verify_ssl = true
```

it can be commented out to allow the parameter to be controlled from the alert configuration:

```conf
# param.verify_ssl = true
```

However, editing files under the `default` directory is not recommended for production environments, because these files may be overwritten during app upgrades.

---

## Troubleshooting

### Alert action does not send a message

Check the following:

- Matrix / Element homeserver URL is correct
- Room ID is correct
- Access token is valid
- Splunk server can reach the Matrix / Element server
- The Matrix user has permission to send messages to the room
- SSL certificate verification settings are correct
- Splunk internal logs do not show Python or alert action errors

---

### SSL certificate error

If the Matrix / Element server uses a self-signed or internal certificate, SSL verification may fail.

Check the certificate configuration on the Matrix / Element server or disable SSL verification only if this is acceptable for your environment.

---

### 403 or forbidden error

A `403` response usually means that the Matrix user does not have permission to send messages to the room.

Check the following:

- the access token belongs to the correct Matrix user;
- the Matrix user is joined to the target room;
- the Matrix user has permission to send messages;
- the room ID is correct.

---

### Invalid access token

If the access token is invalid or expired, generate a new token for the Matrix / Element user and update the alert action configuration.

---

### No logs appear

Check that Splunk can write to:

```bash
$SPLUNK_HOME/var/log/splunk/
```

Also check ownership of the app directory:

```bash
ls -ld $SPLUNK_HOME/etc/apps/SendToElement
ls -l $SPLUNK_HOME/etc/apps/SendToElement/bin/
```

---

## Validation

You can validate the Python syntax with:

```bash
$SPLUNK_HOME/bin/splunk cmd python3 -m py_compile \
$SPLUNK_HOME/etc/apps/SendToElement/bin/SendToElement.py
```

You can also check whether required Python modules are available in the Splunk Python runtime:

```bash
$SPLUNK_HOME/bin/splunk cmd python3 - <<'PY'
import json
import ssl
import urllib.request
import urllib.parse

print("Basic Python modules are available")

try:
    import requests
    print("requests module is available")
except Exception as e:
    print("requests module check failed:", e)

try:
    import urllib3
    print("urllib3 module is available")
except Exception as e:
    print("urllib3 module check failed:", e)
PY
```

---

## Upgrade Notes

This update improves documentation and Splunkbase package readiness.

No changes are made to the Matrix / Element message sending logic.

---

## Support

For issues, questions, or improvement requests, contact Cyberfox support or the app maintainer.
