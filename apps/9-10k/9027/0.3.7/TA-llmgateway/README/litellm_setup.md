# Configuring LiteLLM to Send Logs to TA-llmgateway

This add-on collects LLM gateway telemetry from both Bifrost (SQLite/PostgreSQL log
store) and LiteLLM (HTTP Event Collector push). This document covers the LiteLLM path.

## Overview

LiteLLM ships logs to Splunk via a custom callback that POSTs each request to a Splunk
HTTP Event Collector (HEC) endpoint. Events land in `index=llmgateway` with
`sourcetype=llmgateway:litellm` and are parsed by this add-on's props.conf.

```
LiteLLM proxy  ->  custom_callbacks.py  ->  Splunk HEC (8088)  ->  index=llmgateway
```

## Step 1 - Create a HEC token in Splunk

Settings > Data Inputs > HTTP Event Collector > New Token

- Name:       litellm-gateway
- Source type: llmgateway:litellm
- Index:       llmgateway

Or via CLI:

    splunk http-event-collector create litellm-gateway \
        -index llmgateway -sourcetype llmgateway:litellm \
        -uri https://localhost:8089 -auth admin:<password>

Copy the generated token (UUID).

## Step 2 - Install the LiteLLM custom callback

Create `custom_callbacks.py` in your LiteLLM working directory. A reference
implementation is provided in this add-on at:

    $SPLUNK_HOME/etc/apps/TA-llmgateway/README/custom_callbacks.py

Edit the two constants at the top:

    HEC_URL   = "https://<your-splunk-host>:8088/services/collector/event"
    HEC_TOKEN = "<your-hec-token>"

## Step 3 - Reference the callback in config.yaml

The callback must be referenced using the `callbacks:` key (NOT success_callback),
and the instance must be named `proxy_handler_instance`:

    litellm_settings:
      callbacks: custom_callbacks.proxy_handler_instance

Full example config.yaml:

    model_list:
      - model_name: ollama/llama3.2
        litellm_params:
          model: ollama/llama3.2
          api_base: http://localhost:11434

    litellm_settings:
      callbacks: custom_callbacks.proxy_handler_instance

    general_settings:
      master_key: sk-litellm-local

## Step 4 - Start LiteLLM from the directory containing custom_callbacks.py

    cd <dir-with-custom_callbacks.py>
    litellm --config config.yaml --host 0.0.0.0 --port 4000

LiteLLM must be started from the directory containing custom_callbacks.py so Python
can import the module by name.

## Step 5 - Verify

Send a test request:

    curl -X POST http://localhost:4000/v1/chat/completions \
      -H "Authorization: Bearer sk-litellm-local" \
      -H "Content-Type: application/json" \
      -d '{"model":"ollama/llama3.2","messages":[{"role":"user","content":"test"}]}'

You should see `[SplunkHEC] OK ...` printed in the LiteLLM console. Then in Splunk:

    index=llmgateway sourcetype="llmgateway:litellm"
    | table _time, llmgateway_model, llmgateway_provider,
            llmgateway_tokens_total, llmgateway_latency_ms,
            llmgateway_input_prompt

## Fields produced

Core:  llmgateway_model, llmgateway_provider, llmgateway_model_group,
       llmgateway_deployment, llmgateway_status, llmgateway_call_type,
       llmgateway_stream, llmgateway_api_base, llmgateway_finish_reason
Tokens: llmgateway_tokens_input/output/total
Cost:   llmgateway_cost_total
Text:   llmgateway_input_prompt, llmgateway_output_text,
        llmgateway_system_prompt, llmgateway_tool_calls
Ident:  llmgateway_request_id, llmgateway_call_id, llmgateway_trace_id,
        llmgateway_user, llmgateway_key_name, llmgateway_team
Network: llmgateway_requester_ip, llmgateway_user_agent, llmgateway_route

## Notes

- For self-signed Splunk certs, the reference callback disables SSL verification.
  Remove that line in production and use a trusted cert.
- The callback also writes the full LiteLLM standard_logging_object nested under
  the `standard_logging_object` field for any deeper analysis.
