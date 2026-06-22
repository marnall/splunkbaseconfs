# Splunk Native Embedder

**Version:** 3.0.7  
**Compatible with:** Splunk Enterprise 9.x+  
**License:** See LICENSE file  
**Author:** Sanjeev Kumar (ksanjeev284@gmail.com)  
**App ID:** splunk_native_embedder

## Overview

Splunk Native Embedder enables native dashboard embedding using Splunk's
`?embed=1` mode. The app does not run a proxy. It focuses on:

- Enabling iframe rendering by adjusting Splunk Web headers
- Providing a small UI for embedding-related cookie settings
- Maintaining a legacy modular input (`embedder://`) for upgrade compatibility

## Key Components

- `default/web.conf` only exposes app REST endpoints (AppInspect compliant).
- `appserver/static/embedder_config.js` powers the Configure Embedding dashboard.
- `bin/embedder.py` is a no-op modular input placeholder (native mode).

## Requirements

- Splunk Enterprise 9.x or later
- HTTPS for cross-site embedding (recommended)
- Splunk Cloud is not supported

## Installation

1. Copy `splunk_native_embedder` into `$SPLUNK_HOME/etc/apps/`.
2. Restart Splunk.
3. Open **Splunk Native Embedder** -> **Configure Embedding**.

## Configuration

### Embedding Headers

Use the Configure Embedding UI to enable or disable the required headers. The
UI writes to `local/web.conf`:

```ini
[settings]
x_frame_options_sameorigin = false
dashboard_html_allow_iframes = true
dashboard_html_allow_embeddable_content = true
```

Restart Splunk after changing these values.

### Embedding Cookie Mode

- **HTTPS embedding:** set `cookieSameSite = none` (requires HTTPS)
- **HTTP login safe:** set `cookieSameSite = not_specified`

You can toggle this in the Configure Embedding UI or set it in
`local/web.conf`:

```ini
[settings]
cookieSameSite = none
```

### Reverse Proxy (TLS Termination)

If TLS terminates at nginx or another proxy, Splunk may still think it is HTTP.
Force Secure cookies:

```ini
[settings]
tools.sessions.secure = true
```

This is also available in the Configure Embedding UI. Restart Splunk after
changing settings.

## Usage

Use native embedding:

```
https://<host>:8000/en-US/app/<app>/<dashboard>?embed=1
```

For cross-site iframes, ensure:

- Splunk Web is HTTPS
- `cookieSameSite = none`
- Your browser allows third-party cookies for the Splunk host

## Legacy Inputs

The `embedder://` modular input is deprecated in v3.x. It is retained only to keep
existing inputs valid after upgrades. Inputs do not start any proxy and have no
runtime effect beyond keeping Splunk satisfied.

## Build

Run:

```
.\build_package.ps1
```

Output:

```
E:\splunk_native_embedder-Release\splunk_native_embedder-3.0.7.tgz
```

## Support

Email: ksanjeev284@gmail.com

## Changelog

### 3.0.7
- Native embedding mode (no proxy).
- Embedding and cookie configuration UI.
- Rebranded app metadata and support contact.

## License

See LICENSE file for details.
