
# Add-on for Caddy

The Add-on for Caddy provides props and transforms to intepret Caddy 2's json-based access logs.

## Installation

Install this add-on on indexers - or heavy forwarders if used.

Configure an inputs.conf to tail a Caddy 2 access log, e.g.

```
[monitor:///home/webapp/caddy_access.log]
disabled = false
index = web
sourcetype = caddy_access
```

## Configuration

The TA has been written based on Caddy 2's json log format - where `format json` is explicitly configured.

The following is an example logging configuration for a Caddyfile. Refer to Caddy's [documentation](https://caddyserver.com/docs/caddyfile/directives/log) for details of how to customise what information gets logged.

```
log {
        output file caddy_access.log {
                roll_size 1gb
                roll_keep 5
                roll_keep_for 720h
        }
        format json
}
```