This is an add-on powered by the Splunk Add-on Builder.

# SSE Connector
The Integration team is working on a Splunk integration.
The goal is to enable customers to query a Splunk instance through the SSE API Proxy.
In order to achieve that they code a splunk plugin:
 - the plugin allows registering a Splunk instance to the SSE gateway
 - the plugin exposes an API that is compatible with SSE API Proxy commands and the IROH Relay contracts
 - The plugin authenticates with Splunk using the credentials of the Splunk instance.
The relay module currently supports querying Devices through the SSE proxy but only using the :sse-jwt auth-type.
In order to support such integrations, we need to decouple the SSE payload auth from the http request auth.
to summarize, we need to have the module able to authenticate to the SSE API Proxy using the generated sse-jwt while also passing a bearer token in the payload map on the headers key.
# Binary File Declaration
# Binary File Declaration
# Binary File Declaration
