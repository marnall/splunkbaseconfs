[ollama]
* Settings for connecting to a local Ollama instance

base_url = <string>
* Base URL for the Ollama API
* Default: http://localhost:11434 (set https://host:port if your Ollama deployment supports TLS)

timeout = <integer>
* Request timeout in seconds
* Default: 60

verify = <boolean>
* Whether to verify TLS certificates (only relevant when using HTTPS)
* Default: true

default_model = <string>
* Default Ollama model to use for generation
* Default: qwen2.5:1.5b-instruct
* Example values: qwen2.5:1.5b-instruct

log_level = <string>
* Logging level for oai.log
* Default: DEBUG
* Valid: DEBUG, INFO, WARNING, ERROR

persist_index = <string>
* Default index to use when persist=true
* Default: oai
* Can be any valid Splunk index