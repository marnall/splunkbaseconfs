# DV AI Assistant

AI-powered security operations app for Splunk with natural-language SPL generation, manual and automatic notable-event triage, Knowledge Base context, multi-LLM providers, chat history, audit views, and guarded IP block/unblock actions.

## Supported LLM providers

- Ollama
- OpenAI
- Gemini
- Custom HTTP endpoints

Provider configuration is stored in `ai_providers.conf`. API keys and integration secrets are stored through Splunk `storage/passwords` and are not shipped with the app.

## Requirements

- Splunk Enterprise with Python 3
- Splunk Enterprise Security for notable-event triage features
- Network access from the Splunk Search Head to the selected LLM provider

## Fresh installation

1. Install the app from **Apps > Manage Apps > Install app from file**.
2. Restart Splunk if requested.
3. Open **Providers** and add at least one LLM provider.
4. Open **Settings** and select the response language and optional automatic triage settings.
5. Review the default Knowledge Base and adapt it to the customer's Splunk environment before relying on environment-specific query generation.
6. Assign `dv_ai_user` to standard app users, `dv_ai_admin` to app administrators, and `dv_ai_action` only to users who should be allowed to perform IP block/unblock actions.

The package intentionally contains no provider records, API keys, ES integration credentials, local overrides, previous triage state, audit data, or blocked IP entries.


## App roles

- `dv_ai_user`: Access to AI Chat and AI Alert Triage.
- `dv_ai_admin`: Access to AI Chat, AI Alert Triage, AI Providers Configuration, Data Context Mapping, Audit views, and App Settings & Authentication.
- `dv_ai_action`: Adds the `block_ip` capability for IP block/unblock actions. Assign it together with `dv_ai_user` or `dv_ai_admin` as needed.
- Built-in `admin` and `sc_admin` retain full app access.

## Security

- Generated SPL is checked server-side by the read-only guardrail before autonomous execution.
- IP block/unblock actions require explicit confirmation and authorization.
- Private/protected IPv4 ranges and configured allowlists are protected from blocking.
- Remote TLS verification is enabled by default.
- Chat history is accessed through the authenticated server-side history handler.
- AI audit logs use sourcetype `dv_ai_assistant:ai_audit` in `_internal`.
