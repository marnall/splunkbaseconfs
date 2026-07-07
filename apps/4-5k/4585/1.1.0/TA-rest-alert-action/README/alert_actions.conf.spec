
[send_custom_rest_request]
param.payload = <string> Payload.  It's default value is data={host}.
param.qs_params = <string> Query String Params.  It's default value is test=123&example=true.
param.endpoint = <string> Endpoint. It's a required parameter. It's default value is https://example.com.
param.timeout = <string> Timeout. It's a required parameter. It's default value is 30.
param.verify = <bool> Verify SSL Certificate.
param.response_index = <string> Ingest response to index.  It's default value is main.
param.custom_headers = <string> Custom Headers.  It's default value is header-1=true&x-forwarded-for={host}.
param.method = <list> HTTP Method. It's a required parameter. It's default value is post.
param.ingestion_safety_max_size = <string> Ingestion Safety Max Size.

