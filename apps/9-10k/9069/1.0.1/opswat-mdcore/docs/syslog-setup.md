# MetaDefender Core → Splunk (syslog / CEF)

MD Core sends scan activity to Splunk as **CEF over syslog**. The app parses it as
`sourcetype = opswat:mdcore:cef`. No credentials or API keys are involved.

## 1. MD Core side — add a Splunk syslog connection
In MetaDefender Core, add a syslog connection and choose connection type **Splunk**
("OPSWAT MetaDefender app"). Splunk-typed connections are labeled `[Splunk]` in the connection list.
- Protocols: **TCP, UDP, TCPS** (TLS over TCP). Local syslog is not supported on Windows.
- Default port: **1514** (direct), or forward via Splunk Connect for Syslog (SC4S).

## 2. Splunk side — get the syslog into Splunk as `opswat:mdcore:cef`
Pick the path for your deployment:

- **Splunk Enterprise / distributed** — use **Splunk Connect for Syslog (SC4S)**. Route the MD Core
  source to `sourcetype=opswat:mdcore:cef` and your chosen index (SC4S `splunk_dest_*` /
  vendor-product mapping).
- **Splunk Cloud** — receive the syslog on a **Universal Forwarder** (or SC4S container) and set the
  input's `sourcetype = opswat:mdcore:cef` before forwarding to Cloud.

The app ships the parsing (`props.conf` / `transforms.conf`), so once events land under
`opswat:mdcore:cef` the CEF header and `OMS*` fields extract automatically. Index is **not** created
by the app (Cloud-managed); choose an existing index and select it in each dashboard.

## 3. Verify
```
index=<your_index> sourcetype=opswat:mdcore:cef | head 20
```
Then open the app — the **Executive Overview** dashboard should populate. Pick your index in the
dashboard's **Index** selector (defaults offered: `main`, `opswat`).

## Air-gapped
Download the `.spl` from Splunkbase and use **Apps → Install app from file**.
