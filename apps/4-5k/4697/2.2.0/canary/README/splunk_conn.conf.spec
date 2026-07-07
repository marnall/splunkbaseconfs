# This defines how this app should communicate with splunkd

[connection_info]
ssl_verification_path = <pathname>
* Accepts an absolute path to a cert file that the app should use when
  connecting to Splunk's management port.
* This is data used when verifying the server-provided cert, it is not
  presented during negotiation by the client.
* This is necessary in the same cases where your custom Splunk certificates would
  need to be distributed to endpoints (clients) for a web browser to connect to
  and trust the splunkd management port https cert.  Typically, this is needed when 
  using a custom self-signed certificate, or if the public key infrastructure
 (PKI) is not reachble from the nodes where the app runs.  
* If this value is unset, the app will naively try to connect behaving like a
  browser, first,  
* If the naive connection fails, the app will fall back to looking for a splunk
  auto-generated self-signed cert located on the filesytem at the default
  location.
* When set, no fallback behavior will occur, it will simply work or fail with
  the specified certificate file.
* No default.
