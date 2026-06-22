**`Userful`**

Userful embedded dashboards add-on for Splunk. It starts a lightweight proxy that signs requests as a chosen Splunk user and exposes a REST helper to return embed-ready dashboard URLs so downstream systems can pull them without UI clicks. Credit to M. Uschmann for the original concept.

**What this app does**
- Listens on configurable TCP ports and authenticates clients as the configured Splunk user.
- Restricts access to a single client IP and blocks POST requests that are not searches.
- Provides `GET /services/userful/embeds` to list dashboards plus pre-built iframe URLs.
- Keeps all traffic local to Splunk Web (default 8000).

**Install**
- Copy to `$SPLUNK_HOME/etc/apps` and restart Splunk.

**Configure**
- From Splunk Web, go to Apps → Userful Infinity → Userful Infinity Passport Setup and fill username, allowed client IP, and port (this writes the default `userful_proxy://default` stanza via the JS SDK).
- Or copy `default/inputs.conf` to `local/` and edit the `userful_proxy` stanza with your username, allowed client IP, and port.
- Or configure via REST (no UI):
  ```sh
  curl -k -u admin:changeme \
    https://localhost:8089/servicesNS/nobody/Userful/data/inputs/userful_proxy/userful \
    -d username=userful_proxy -d connect_from=192.0.2.3 -d port=9000 \
    -d index=_internal -d sourcetype=splunkd_userful_access -d disabled=0
  ```
- Splunk Cloud: global Splunk Web SSO/trusted IP settings must be configured outside the app by an administrator.

**Programmatic usage**
- Fetch embed URLs:
  ```sh
  curl -k -u admin:changeme \
    'https://localhost:8089/services/userful/embeds?app=*' | jq .
  ```
  Via Splunk Web (SSO/proxy):
  ```sh
  curl -s -H 'Accept: application/json' \
    'http://your-host:9902/en-US/services/userful/embeds?app=*'
  ```
  Parameters: `app=<splunk_app>`, `stanza=<userful_proxy_stanza>`, `host=<public-hostname>`, `include_disabled=true`.
- Use each `embed_url` in an iframe, e.g. `http://your-host:9000/en-US/app/search/dashboard?display.page.embed=true`.

**Debug**
- Connections are logged to `index=_internal` with `sourcetype=splunkd_userful_access`.

**Known issues**
- The proxy process may continue after input disable; stop/restart Splunkd if needed.
- Use private browser windows when testing locally to avoid cookie collisions.

**Support**
- Open source; community support only. Credit: M. Uschmann.

**Version**
- `0.1.1-userful`
