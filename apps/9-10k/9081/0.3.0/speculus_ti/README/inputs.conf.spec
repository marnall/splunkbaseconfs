[speculus_mmdb_updater://<name>]
endpoint_url = <value>
* Full URL of the Speculus MMDB download endpoint (GET /v1/mmdb).
* Required.

api_key = <value>
* Speculus API key used as the Bearer token.
* Moved into Splunk secure storage (storage/passwords) and masked in this
* file on the first run.
* Required.

verify_ssl = <bool>
* Whether to verify the endpoint's TLS certificate.
* Set to 0 only for testing against self-signed endpoints.
* Default: 1
