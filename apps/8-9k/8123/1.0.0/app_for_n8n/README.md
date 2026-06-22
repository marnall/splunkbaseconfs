
# App for n8n

Splunk app to visualise workflow and audit activity logged by AI workflow automation platform [n8n](https://n8n.io/).

![Overview Dashboard](./screenshots/screenshot_app_for_n8n_main_dash.png)

## Deployment

1. Deploy the app on a search head and either the indexing tier or Heavy Forwarder if used
2. Customise the `n8n_index` macro as required - by default it's set to `index::n8n OR index::main`
3. Send n8n logs to Splunk (see Getting Data In)

Deploying to the indexing tier / HF is optional but recommended, as it explicitly instructs splunk to use the `ts` json field as the timestamp. It also increases the default value of `TRUNCATE` due to the `ts` field appearing at the end of large events e.g. those of type ` n8n.ai.llm.generated`.

## Getting Data In

Either:

1. Use a Splunk Universal Forwarder (UF) to monitor `n8nEventLog.log` or
2. Use n8n's Log Streaming to send equivalent events to a Splunk HEC endpoint

### Universal Forwarder - Example inputs.conf

```
[monitor:///path/to/n8n/n8nEventLog.log]
disabled = 0
sourcetype = n8n:json
index = n8n
```

### HEC

HEC requires authentication. Whilst not tested, n8n appears to support authentication settings for webhook log sinks, in addition to custom HTTP headers.

Point the webhook at `https://your-splunk:8088/services/collector/raw` and ensure an `Authorization` header value of `Splunk <hec_token_guid>` is included.

## Observability - APM and Infrastructure Monitoring

This app is for processing n8n's application logs only - primarily audit logs and basic workflow execution activity only.

If self-hosting n8n, consider using the [OpenTelemetry Collector](https://github.com/open-telemetry/opentelemetry-collector) to collect host metrics and send to Splunk [Observability Cloud](https://www.splunk.com/en_us/products/observability-cloud.html).

Also consider collecting APM data using OpenTelemetry's [auto-instrumentation](https://opentelemetry.io/docs/platforms/kubernetes/operator/troubleshooting/automatic/). Previous work in this area:
- https://community.n8n.io/t/n8n-successfully-instrumented-with-opentelemetry/78468
- https://www.linkedin.com/pulse/shedding-light-n8n-monitoring-from-guesswork-said-rodrigues-qn59f

## Known Issues

**CIM compliance**: authentication events are tagged `authentication` but we don't have enough data to properly comply with this data model.

**LLM Token Usage**: developed against an integration with Google Gemini - other models may report token usage using different fields in the response. 

## Support

Raise a GitHub issue or submit a PR if you have a fix or improvement.

https://github.com/gf13579/app_for_n8n

Greg Ford ([@gf13579](https://www.github.com/gf13579))

## License

[MIT](https://choosealicense.com/licenses/mit/)

