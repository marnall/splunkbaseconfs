# Telegram App for Splunk

## About

**Telegram App** is a custom alert action for Splunk, created by **CyberFox** (Astana, Kazakhstan).

It allows you to send Splunk correlation search results and alerts directly to Telegram — to private chats, group chats, or threads (topics) in supergroups.

The idea is simple: **whatever Splunk detects, your team instantly sees in Telegram** via a controlled and flexible channel — with or without proxy.

---

## What this app does

- Sends Splunk alert notifications to a Telegram bot, including:
  - alert title (Title),
  - severity level (Severity),
  - alert text (Message),
  - optional link to the Splunk search results (Result Link).

- Works with both regular chats and supergroup topics:
  - `chat_mode = regular` — regular chat or group;
  - `chat_mode = super` + `topic_id_or_link` — send into a specific thread/topic.

- Network and security features:
  - can send traffic to `api.telegram.org` directly;
  - can send traffic to `api.telegram.org` through a configured HTTP/HTTPS proxy;
  - proxy usage can be enabled or disabled from the dedicated **Telegram App Settings** page in Splunk Web;
  - supports proxy scheme selection: `http` or `https`;
  - supports configurable request timeout for Telegram API requests;
  - SSL certificate verification is controlled by the `verify_ssl` flag in the global config.

- Easy integration:
  - minimal configuration from the Splunk UI for alert parameters;
  - global network settings in `telegram.conf` under the `[connection]` stanza;
  - proxy and connection settings can be managed from the Splunk Web UI without editing Python code.

---

## How it works (in short)

1. You create a Splunk alert and enable the **Telegram App** alert action.

2. When the alert fires, Splunk builds a JSON payload and passes it to:

```text
bin/telegram_app.py
```

3. The script reads alert parameters:

- `bot_id` – Telegram Bot API token;
- `chat_id` – target chat ID;
- `title` – alert title;
- `message` – alert message;
- `severity` – alert severity;
- `result_link` – whether to attach a link back to Splunk search results;
- `chat_mode` – `regular` or `super`;
- `topic_id_or_link` – numeric topic ID or Telegram topic link for supergroups with topics.

4. The script loads global network settings from:

```text
telegram.conf
```

under the `[connection]` stanza:

- `verify_ssl = true|false` – whether to verify the TLS certificate of `api.telegram.org`;
- `proxy_enabled = true|false` – whether to use a proxy;
- `proxy_scheme = http|https` – proxy protocol used to connect to the proxy server;
- `proxy_ip` – proxy host or IP address;
- `proxy_port` – proxy port;
- `request_timeout` – timeout for Telegram API requests in seconds.

5. The script builds a formatted HTML message and sends it to the Telegram Bot API.

---

## Connection logic

### Without proxy

If proxy is disabled:

```ini
proxy_enabled = false
```

The app ignores proxy host, port, and scheme values.

The flow is:

```text
Splunk Alert
→ Telegram App alert action
→ telegram_app.py
→ api.telegram.org
→ Telegram chat
```

### With proxy

If proxy is enabled:

```ini
proxy_enabled = true
```

and both `proxy_ip` and `proxy_port` are configured, all requests go through the configured proxy.

The flow is:

```text
Splunk Alert
→ Telegram App alert action
→ telegram_app.py
→ Proxy Server
→ api.telegram.org
→ Telegram chat
```

If proxy is enabled but proxy settings are incomplete, the app falls back to direct connection.

---

## Telegram App Settings page

Proxy and connection settings can be configured from Splunk Web:

```text
Apps → Telegram App → Telegram App Settings
```

Available settings:

- `Proxy enabled` — enables or disables proxy usage;
- `Proxy scheme` — proxy protocol: `http` or `https`;
- `Proxy host / IP` — proxy server hostname or IP address;
- `Proxy port` — proxy server port;
- `Request timeout` — timeout for Telegram API requests in seconds;
- `Verify SSL` — enables or disables SSL certificate verification.

The settings are saved into:

```text
$SPLUNK_HOME/etc/apps/telegram_app/local/telegram.conf
```

---

## Example configuration without proxy

```ini
[connection]
proxy_enabled = false
proxy_scheme = http
proxy_ip =
proxy_port =
request_timeout = 10
verify_ssl = true
```

In this mode, the app sends requests directly to:

```text
https://api.telegram.org
```

---

## Example configuration with HTTP proxy

Example for a standard HTTP proxy, such as Squid:

```ini
[connection]
proxy_enabled = true
proxy_scheme = http
proxy_ip = 127.0.0.1
proxy_port = 3128
request_timeout = 10
verify_ssl = true
```

For most corporate proxy servers, `proxy_scheme = http` is correct even when Telegram is accessed over HTTPS.

Example:

```text
HTTP proxy → CONNECT api.telegram.org:443 → Telegram HTTPS API
```

Use:

```ini
proxy_scheme = https
```

only when the proxy server itself expects HTTPS connections.

---

## Alert action parameters

When creating a Splunk alert, enable the **Telegram app** alert action.

The alert action supports the following parameters:

| Parameter | Description |
|---|---|
| `bot_id` | Telegram Bot API token |
| `chat_id` | Target Telegram chat ID |
| `title` | Alert title |
| `message` | Alert message |
| `severity` | Alert severity |
| `result_link` | Whether to include Splunk result link |
| `chat_mode` | `regular` or `super` |
| `topic_id_or_link` | Topic ID or Telegram topic link for supergroups |

---

## Bot token

The `bot_id` field must contain the full Telegram Bot API token.

Correct format:

```text
1234567890:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

It is not enough to provide only the numeric bot ID.

Bot tokens can be created and managed through:

```text
@BotFather
```

---

## Chat ID

For private chats, the `chat_id` is usually a positive number.

Example:

```text
535567362
```

For groups and supergroups, the `chat_id` is usually negative.

Example:

```text
-1003135273596
```

For Telegram supergroup topics, use:

```text
chat_mode = super
topic_id_or_link = <topic_id>
```

Example:

```text
chat_id = -1003135273596
chat_mode = super
topic_id_or_link = 336
```

A Telegram topic link can also be used if supported by the app logic.

Example:

```text
https://t.me/c/3135273596/336/22326
```

---

## Example Splunk alert search

Example test search:

```spl
| makeresults
| eval title="Telegram Test Alert"
| eval message="Test alert from Splunk Telegram App"
| eval severity="info"
| table title message severity
```

Example alert action fields:

```text
bot_id      = <Telegram Bot API token>
chat_id     = 535567362
title       = $result.title$
message     = $result.message$
severity    = $result.severity$
chat_mode   = regular
```

---

## Validation commands

Check effective Telegram app configuration:

```bash
$SPLUNK_HOME/bin/splunk btool telegram list connection --debug
```

Example output:

```text
$SPLUNK_HOME/etc/apps/telegram_app/local/telegram.conf   proxy_enabled = true
$SPLUNK_HOME/etc/apps/telegram_app/local/telegram.conf   proxy_scheme = http
$SPLUNK_HOME/etc/apps/telegram_app/local/telegram.conf   proxy_ip = 127.0.0.1
$SPLUNK_HOME/etc/apps/telegram_app/local/telegram.conf   proxy_port = 3128
$SPLUNK_HOME/etc/apps/telegram_app/local/telegram.conf   request_timeout = 10
$SPLUNK_HOME/etc/apps/telegram_app/local/telegram.conf   verify_ssl = true
```

Check Splunk alert action execution:

```bash
grep -R "sendmodalert" $SPLUNK_HOME/var/log/splunk/splunkd.log | tail -n 20
```

Check Telegram app execution logs:

```bash
grep -R "telegram_app" $SPLUNK_HOME/var/log/splunk/splunkd.log | tail -n 20
```

If proxy is used, check proxy logs. Example for Squid:

```bash
grep "api.telegram.org" /var/log/squid/access.log | tail -n 10
```

Successful proxy request example:

```text
TCP_TUNNEL/200 CONNECT api.telegram.org:443
```

---

## Configuration files

Main app configuration files:

```text
default/alert_actions.conf
default/app.conf
default/telegram.conf
default/data/ui/views/settings.xml
default/data/ui/nav/default.xml
appserver/static/telegram_settings.js
bin/telegram_app.py
README/telegram.conf.spec
README/alert_actions.conf.spec
```

Runtime/local configuration:

```text
local/telegram.conf
```

The `local/` directory should not be included when packaging the app for distribution.

---

## Packaging

Before packaging the app, remove backup files and exclude local runtime configuration.

Example:

```bash
cd $SPLUNK_HOME/etc/apps

tar \
  --exclude='telegram_app/local' \
  --exclude='telegram_app/metadata/local.meta' \
  --exclude='telegram_app/bin/*.bak' \
  -czvf /tmp/telegram_app_proxy_settings.tgz telegram_app
```

The final package will be created as:

```text
/tmp/telegram_app_proxy_settings.tgz
```

---

## Security notes

- Do not hardcode Telegram bot tokens in Python code.
- Do not share Telegram bot tokens in screenshots, chats, tickets, or documentation.
- If a token is exposed, revoke it immediately through `@BotFather`.
- Keep `verify_ssl = true` unless there is a specific controlled reason to disable it.
- Use proxy mode in environments where direct internet access from Splunk is not allowed.
- Restrict access to the Settings page and app configuration to trusted Splunk administrators.

---

## Who built it

This app was developed by **CyberFox** (Astana, Kazakhstan),
a team focused on SIEM, security operations, and real-world Splunk integrations.
