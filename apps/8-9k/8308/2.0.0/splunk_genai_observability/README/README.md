# GenAI Observability Platform

Enterprise-grade observability platform for GenAI/LLM applications built on Splunk.

## Version 2.0.0

## Features

### 📊 15+ Dashboards
- **Executive Dashboard** - C-level summary with cost, ROI, and trends
- **Operations Center** - Real-time monitoring with live metrics
- **Trace Explorer** - Debug individual requests with waterfall view
- **LLM Performance** - Model latency, throughput, and token analysis
- **RAG Analytics** - Retrieval quality and latency breakdown
- **Cost Management** - Token economics and optimization recommendations
- **Quality Metrics** - Relevance, faithfulness, hallucination tracking
- **Error Analysis** - Error trends and root cause investigation
- **Security Dashboard** - PII detection, prompt injection, audit trail
- And more...

### 🔔 20+ Pre-built Alerts
- High error rate alerts
- Latency spike detection
- Cost anomaly alerts
- Quality degradation warnings
- PII detection alerts
- Prompt injection detection

### 📈 Accelerated Data Models
- Fast searches on large datasets
- Pre-computed aggregations
- Optimized for dashboard performance

### 🔧 Python SDK
- Decorators for easy instrumentation
- Support for LLM, RAG, Agents, Tools
- PII detection and masking
- Batch export for performance

### 💰 Cost Tracking
- Real-time cost calculation
- Cost by model, workflow, team
- Optimization recommendations
- Budget alerts

### 🔐 Security & Compliance
- PII detection in prompts/responses
- Prompt injection detection
- Audit trail
- Access logging

## Installation

### 1. Install the App

```bash
# Extract the app
tar -xzf genai_observability_platform.tar.gz -C $SPLUNK_HOME/etc/apps/

# Restart Splunk
$SPLUNK_HOME/bin/splunk restart
```

### 2. Create Indexes

Create these indexes in Splunk:
- `genai_traces` - Individual trace/span data
- `genai_metrics` - Aggregated metrics
- `genai_evals` - Quality evaluations
- `genai_audit` - Security and audit logs
- `genai_summary` - Pre-computed summaries

### 3. Configure HEC

1. Go to **Settings > Data Inputs > HTTP Event Collector**
2. Create a new token
3. Enable indexer acknowledgement (optional)
4. Allow the token to write to genai_* indexes

### 4. Install Python SDK

Copy `bin/genai_telemetry.py` to your application or:

```bash
pip install splunk-genai-observability
```

## Quick Start

### Instrument Your Application

```python
from genai_telemetry import setup_splunk_telemetry, trace_llm, trace_chain
from openai import OpenAI

# 1. Initialize telemetry
setup_splunk_telemetry(
    workflow_name="my-chatbot",
    splunk_hec_url="https://splunk:8088",
    splunk_hec_token="your-token",
    splunk_index="genai_traces"
)

# 2. Create OpenAI client
client = OpenAI()

# 3. Add decorators to your functions
@trace_llm(model_name="gpt-4o", model_provider="openai")
def chat(message: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": message}]
    )
    return response.choices[0].message.content

# 4. Use normally - traces sent automatically!
answer = chat("What is Splunk?")
```

### RAG Pipeline Example

```python
@trace_retrieval(vector_store="pinecone")
def search_docs(query: str) -> list:
    return vector_store.query(query, top_k=5)

@trace_chain(name="rag_pipeline")
def rag_answer(question: str) -> str:
    docs = search_docs(question)
    context = "\n".join(d.text for d in docs)
    return chat(f"Context: {context}\n\nQuestion: {question}")
```

## Dashboards

### Executive Dashboard
High-level KPIs for leadership:
- Total requests, cost, latency
- Error rate trends
- Cost breakdown by model/workflow
- Quality score trends

### Operations Center
Real-time monitoring:
- Live request volume
- Current error rate
- Model status (health indicators)
- Recent errors

### Trace Explorer
Debug individual requests:
- Search by trace ID
- Waterfall visualization
- Span details
- Prompt/response inspection

### Cost Management
Token economics:
- Daily/monthly cost trends
- Cost by model comparison
- Optimization recommendations
- Budget tracking

### Quality Metrics
LLM output quality:
- Relevance, faithfulness, helpfulness scores
- Hallucination detection
- Quality trends over time
- Low-quality response alerts

## Search Macros

### Basic Queries

```spl
# All LLM spans
`genai_llm_spans`

# With time filter
`genai_llm_spans` `genai_last_24h`

# Latency statistics
`genai_llm_spans` | `genai_latency_stats`

# Cost calculation
`genai_llm_spans` | `genai_cost_lookup` | `genai_calculate_cost`
```

### Advanced Queries

```spl
# Error rate by model
`genai_llm_spans` | `genai_error_rate_by(model_name)`

# Quality stats by workflow
`genai_evals_index` | `genai_quality_stats_by(workflow_name)`

# Latency anomaly detection
`genai_llm_spans` | `genai_latency_anomaly(3)`

# Trace timeline
`genai_trace_timeline(abc123)`
```

## Alerts

### Performance Alerts
- `Alert - High Error Rate` - Error rate > 5%
- `Alert - High Latency P95` - P95 > 5000ms
- `Alert - Model Degradation` - Specific model errors spike

### Cost Alerts
- `Alert - Daily Cost Threshold` - Daily spend > $1000
- `Alert - Token Quota Warning` - Approaching quota
- `Alert - Cost Anomaly` - Unusual spending

### Quality Alerts
- `Alert - Quality Degradation` - Relevance/faithfulness < 0.7
- `Alert - High Hallucination Rate` - > 10% hallucinations

### Security Alerts
- `Alert - PII Detected` - PII in prompts/responses
- `Alert - Prompt Injection Attempt` - Security threat

## Data Schema

### Trace Fields

| Field | Type | Description |
|-------|------|-------------|
| trace_id | string | Unique trace identifier |
| span_id | string | Unique span identifier |
| span_type | string | LLM, RETRIEVER, EMBEDDING, TOOL, AGENT, CHAIN |
| name | string | Function/operation name |
| workflow_name | string | Application workflow |
| timestamp | datetime | Span start time |
| duration_ms | number | Execution time in milliseconds |
| status | string | OK or ERROR |
| is_error | number | 0 or 1 |
| model_name | string | LLM model name |
| model_provider | string | Provider (openai, anthropic, etc.) |
| input_tokens | number | Prompt tokens |
| output_tokens | number | Completion tokens |
| error_type | string | Error classification |
| error_message | string | Error details |

### Evaluation Fields

| Field | Type | Description |
|-------|------|-------------|
| relevance_score | number | 0-1 relevance rating |
| faithfulness_score | number | 0-1 faithfulness rating |
| helpfulness_score | number | 0-1 helpfulness rating |
| is_hallucination | number | 0 or 1 |
| eval_type | string | llm_judge, human_rating, etc. |

## Lookups

### genai_model_pricing.csv
Model pricing for cost calculation:
- model_name, input_price_per_1k, output_price_per_1k

### genai_providers.csv
Provider information:
- model_provider, provider_display_name, api_endpoint

### genai_error_categories.csv
Error classification:
- error_type, error_category, error_severity, error_resolution

## Support

For issues and feature requests:
- GitHub: https://github.com/yourorg/genai-observability-platform
- Documentation: https://docs.example.com/genai-observability

## License

Apache 2.0
