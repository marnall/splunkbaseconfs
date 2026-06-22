# Fleak OCSF Mapper for Splunk

AI-powered mapping from custom and long-tail log sources to the [Open Cybersecurity Schema Framework (OCSF)](https://ocsf.io/). Generate, test, and deploy mapping rules inside Splunk without hand-writing regex or transforms.

## What it does

- **Generate OCSF mappings from sample logs** using Fleak's AI service — no manual schema work required
- **Test mappings in Splunk** against real events before deploying
- **Apply mappings at search time** via the custom `| fleakmapping` search command, which routes events through the [Zephflow](https://github.com/fleaktech/zephflow-core) engine and returns OCSF-normalized fields

## Requirements

- Splunk Enterprise 10.2+ or Splunk Cloud (custom search command requires Python 3.13)
- A [Fleak](https://fleak.ai) account — sign up at https://app.ocsf.fleak.ai and create an API key from **Settings → API Keys → New API Key**
- A reachable Zephflow endpoint — either:
  - your own Zephflow deployment (pull `fleak/zephflow-httpstarter` from Docker Hub; setup guide: https://docs.fleak.ai/zephflow/getting-started#running-zephflow-as-an-http-backend), or
  - the Fleak-hosted public endpoint — request the matching API token by emailing contact@fleak.ai

## Installation

1. Download the `.tar.gz` from Splunkbase
2. In Splunk Web → **Apps → Manage Apps → Install app from file**, upload the archive
3. Restart Splunk when prompted

## Setup

On first launch, the app opens the setup page. Fill in:

- **Fleak API key** — created at app.ocsf.fleak.ai → **Settings → API Keys → New API Key**; starts with `flk_`
- **Zephflow base URL** — e.g. `https://zephflow.api.fleak.ai` or your self-hosted URL
- **Zephflow API token** — optional; only needed if your Zephflow endpoint requires auth

Secrets are stored in Splunk's encrypted password store (`/storage/passwords`), never in plain-text config files.

## Usage

### Mapping Studio

Open **Apps → Fleak OCSF Mapper → Mapping Studio** to:
- Paste sample logs and describe the source
- Let Fleak AI generate a parser and an OCSF mapping expression
- Preview results, edit the expression, and save as a named rule

### Search command

Once a rule is saved, use it in any search:

```
index=firewall sourcetype=asa | fleakmapping rule_name="asa_to_ocsf"
```

The command streams events through Zephflow, flattens the OCSF output into Splunk fields, and preserves `_time` and `_raw` so the Events tab renders normally. If Zephflow is unreachable, raw events pass through untouched.

## Data handling

When generating a mapping, the app sends the **sample logs you provide** to the Fleak AI service at `api.ocsf.fleak.ai` for schema inference. Sample logs may contain sensitive fields — review before sharing. See the [Fleak Privacy Policy](https://fleak.ai/privacy-policy) for details on data retention.

At search time the `| fleakmapping` command sends your search events to the Zephflow endpoint you configured. Point this at a Zephflow instance you trust (hosted or self-hosted).

## Support

- Email: contact@fleak.ai
- Docs: https://docs.fleak.ai
- Issues: report via the Splunkbase page

## License

Apache License 2.0 — see the `LICENSE` file in the app directory.

Copyright 2026 Fleak Tech Inc.
