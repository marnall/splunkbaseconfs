Generic LLM Connector
=====================

This add-on lets Splunk administrators configure reusable LLM providers and
connections, then call them from a customized search command named `llm`.

Provider
--------

A provider stores the transport details needed to reach an LLM API:

- name
- provider type (`OpenAI-compatible` or `Anthropic-compatible`)
- API endpoint
- API key

Connection
----------

A connection stores the runtime selection details used by the search command:

- name
- provider reference
- default model name
- max tokens (optional, defaults to `1024`)
- global default flag

Only one connection can be marked as the global default. If the `llm` command
is called without `connection=<name>`, the add-on uses that default connection.

Use `Test Connection` in the connection dialog to validate the selected
provider, model, and max tokens before saving. The test uses the current
unsaved form values and surfaces the backend error message directly in the UI
when validation fails.

Customized Search Command
-------------------------

The add-on exposes a streaming custom search command named `llm`.

Arguments:

- `prompt` (required): prompt template text sent to the LLM
- `connection` (optional): connection name override
- `model` (optional): model name override

If `prompt` contains `{fieldname}`, the command replaces that placeholder with
the current event field value. Missing or empty fields are replaced with an
empty string.

The search command uses the connection's configured `max_tokens` value. If the
connection leaves that field blank, the command uses the default value `1024`.

The command writes the returned text to `llm_response`.

Examples
--------

Default connection:

| makeresults
| eval message="Summarize this alert in one sentence."
| llm prompt="Summarize {message}"

Explicit connection and model:

| makeresults
| eval message="Explain why this event matters."
| llm prompt="Explain {message}" connection=prod_claude model=claude-3-5-sonnet
