# OAI (Observalitics AI) - Ollama Integration for Splunk

A Splunk custom command for running prompts against a local [Ollama](https://ollama.com/) instance. The app defaults to the `qwen2.5:1.5b-instruct` model, but the setup UI will pull the available models from `ollama list` (via the Ollama `/api/tags` endpoint) so you can pick whatever is installed.

## Features

- Works entirely against a local Ollama server (no external API key required)
- Setup page defaults to `qwen2.5:1.5b-instruct` and offers a dropdown populated from `ollama list`
- Configurable base URL, SSL verification, and timeouts for remote/secure Ollama deployments
- Simple search syntax: `| oai "your question"`
- Optional `debug=true` flag to inspect the payload being sent
- Optional `persist=true` flag to also write the `_raw` output to a Splunk index (uses the search session)
- Optional `investigate=true` (or a prompt that starts with `investigate`) to self-collect stats from an index and summarize findings
- Returns Ollama `context` in results when present so you can continue conversations manually

## Requirements

- **Splunk Enterprise 8.0+** (uses Python 3.7+; tested on Splunk 9.x/10.x with Python 3.9)
- **Ollama** installed and running with at least one model pulled (e.g., `ollama pull qwen2.5:1.5b-instruct`)

## Installation

1. Install the app in your Splunk environment
2. Make sure Ollama is installed and running on the Splunk host (or reachable remotely)
3. Open the app and complete the Configuration page to set your Ollama base URL and default model

## Configuration

Settings are stored in `local/oai.conf` under the `[ollama]` stanza:

```ini
[ollama]
base_url = http://localhost:11434
default_model = qwen2.5:1.5b-instruct
timeout = 60
verify = true
```

- `base_url`: Ollama endpoint (include protocol/host/port)
- `default_model`: Model used when `model` is not provided in the search command
- `timeout`: Request timeout in seconds
- `verify`: TLS verification flag (only relevant if using HTTPS)

## Usage

### Simple Chat

```spl
| makeresults
| oai "What is machine learning?"
```

### Specify the Model

```spl
| makeresults
| oai model="qwen2.5:1.5b-instruct" prompt="Give me three bullet points about Splunk." 
```

### Inspect the Payload (debug mode)

```spl
| makeresults
| oai debug=true model="qwen2.5:1.5b-instruct" prompt="Summarize the latest Splunk release." 
```

### Persist the Output to an Index

```spl
| makeresults
| oai persist=true persist_index=oai "Store this answer in the oai index"
```

- `persist=true` posts `_raw` (and `_time`, `user`) to Splunk's receivers/simple endpoint using the search session key.
- `persist_index` overrides the target index (defaults to `oai`).
- Set `verify=false` in the setup page if splunkd uses a self-signed cert.

### Investigate an Index (no upstream events)

```spl
| oai investigate=true "investigate index=_internal for me and give me a report on amount of events, events per second, typical logs, and a brief summary"
```

- Runs a short, bounded set of Splunk searches using the current search time range.
- Collects total events, EPS, top sourcetypes/sources, and a handful of sample logs, then asks the model to summarize.
- Requires an `index=` term in the prompt and an authenticated search (the command uses the search session key).

### Classify or Review Events (streaming mode)

```spl
index=_internal | head 3 | oai "What can you tell me about these events? Classify them by severity and purpose."
```

- Pipe any events into the `oai` command to have the model analyze them.
- Each event's `_raw` field is passed as context along with your prompt.
- Useful for log classification, anomaly explanation, or summarizing event patterns.

## Response Fields

- `status_code`: HTTP status code returned by Ollama
- `response`: Formatted text returned by the model
- `context`: (Optional) Ollama context array if the model returns one
- `_raw`: Always populated with the returned response or error text
- `_time`: Unix epoch when the command ran (used when persisting)
- `user`: Search user (if available) added to persisted payload

## Requirements

- Splunk 8.0 or later
- Python 3.7 or later
- Ollama running with at least one model pulled (defaults assume `qwen2.5:1.5b-instruct`)

## Support

- Ensure Ollama is running: `ollama list`
- Verify the configured base URL matches the host/port where Ollama is listening
- Open an issue or reach out to your Splunk administrator for additional help

## License

This project is licensed under the MIT License - see the LICENSE file for details.