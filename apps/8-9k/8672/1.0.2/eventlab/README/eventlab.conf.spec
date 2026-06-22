# EventLab Configuration Specification
# This file documents all settings available in eventlab.conf

# The hec stanza configures HEC (HTTP Event Collector) connectivity
[hec]
token = <string>
  * HEC authentication token for event submission
  * Required for data ingestion
  * Default: (empty)

host = <string>
  * HEC endpoint hostname or IP address
  * Default: localhost

port = <positive_integer>
  * HEC endpoint port number
  * Default: 8088

ssl = <boolean>
  * Enable SSL/TLS for HEC connections
  * Default: true

verify_ssl = <boolean>
  * Verify SSL certificates for HEC connections
  * Set to false for self-signed certificates
  * Default: false

batch_size = <positive_integer>
  * Number of events per batch submission
  * Default: 50
  * Range: 1-1000

max_workers = <positive_integer>
  * Maximum concurrent worker threads for event submission
  * Default: 10
  * Range: 1-100

# The ai stanza configures AI/LLM provider settings
[ai]
provider = <string>
  * AI provider type (azure_openai, ollama, anthropic)
  * Default: azure_openai

provider_type = <string>
  * AI provider type (set by Settings UI)
  * Alias for provider field used by the REST handler
  * Default: (empty)

model = <string>
  * Model identifier or name
  * Default: gpt-4o

temperature = <float>
  * Temperature parameter for model responses (0.0-2.0)
  * Controls randomness/creativity in generation
  * Default: 0.3
  * Range: 0.0-2.0

max_tokens = <positive_integer>
  * Maximum tokens per model response
  * Default: 16384
  * Range: 1-32768

max_turns = <positive_integer>
  * Maximum conversation turns in chat interactions
  * Default: 8
  * Range: 1-100

endpoint = <string>
  * Azure OpenAI endpoint URL
  * Required for azure_openai provider
  * Default: (empty)

api_key = <string>
  * API key for the provider (Azure OpenAI or Anthropic)
  * Stored in Splunk credential storage for security
  * Default: (empty)

deployment = <string>
  * Azure OpenAI deployment name
  * Required for azure_openai provider
  * Default: (empty)

api_version = <string>
  * Azure OpenAI API version
  * Optional for azure_openai provider
  * Default: (empty)

base_url = <string>
  * Base URL for Ollama API
  * Optional for ollama provider
  * Default: http://localhost:11434

timeout = <positive_integer>
  * Request timeout in seconds
  * Optional for all providers
  * Default: 30

# The generation stanza controls synthetic event generation behavior
[generation]
default_count = <positive_integer>
  * Default number of events to generate per request
  * Default: 1000
  * Range: 1-1000000

default_rate = <positive_integer>
  * Default event generation rate (events per second)
  * Default: 100
  * Range: 1-10000

max_duration = <positive_integer>
  * Maximum generation job duration in seconds
  * Default: 86400 (24 hours)
  * Range: 60-604800

default_index = <string>
  * Default index for generated synthetic events
  * Default: synthetic_events

# The quality stanza defines quality assessment thresholds
[quality]
excellent_threshold = <number>
  * Minimum score for "excellent" quality rating
  * Default: 90
  * Range: 0-100

good_threshold = <number>
  * Minimum score for "good" quality rating
  * Default: 75
  * Range: 0-100

acceptable_threshold = <number>
  * Minimum score for "acceptable" quality rating
  * Default: 60
  * Range: 0-100

sample_size = <positive_integer>
  * Number of events to sample for quality analysis
  * Default: 1000
  * Range: 10-100000

# The logging stanza configures application logging
[logging]
level = <string>
  * Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  * Default: INFO

max_file_size_mb = <positive_integer>
  * Maximum log file size in megabytes before rotation
  * Default: 25
  * Range: 1-1000

# The rate_limiting stanza controls API request throttling
[rate_limiting]
chat_max_requests = <positive_integer>
  * Maximum chat API requests per window
  * Default: 30

chat_window_seconds = <positive_integer>
  * Time window in seconds for chat rate limiting
  * Default: 60

health_max_requests = <positive_integer>
  * Maximum health API requests per window
  * Default: 60

health_window_seconds = <positive_integer>
  * Time window in seconds for health rate limiting
  * Default: 60
