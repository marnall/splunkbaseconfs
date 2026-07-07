The JSON Web Token (JWT) Decoder is a custom search command that simplifies decoding and parsing tokens found in Splunk events.

### Usage

```
... | jwt field=string [secret=string] [filter=(True|False)] [wrap=(True|False)] [debug=(True|False)]
```

* `field`: Specify the field containing the Base64 encoded JWT token. Will automatically detect standard HTTP Authorization header containing JWT bearer token if present.
* `secret`: If specified, will validate the JWT signature against the provided secret (HMAC SHA-256 only). 
* `filter`: Optionally filter results to only include events which contain the specified field (default: False).
* `wrap`: Returned JSON structure will be wrapped with a "jwt" object to automatically export fully-qualified properties (e.g. jwt.header.alg) when passed through spath with no options (default: True).
* `debug`: Set to True to enable errors when decoding events (default: False).

The specified field can either contain only the encoded JWT value, or more commonly, it can be included as a bearer token value in a standard HTTP Authentication header:

```
Host: www.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6I....
Content-Type: application/json
```
The authorization header will automatically be detected and parsed to obtain the JWT value, and both muliline and mulivalue field types are supported.

The resulting JSON representation of the token will then be made available in a `jwt` field for further analysis, though in many cases it will be most desirable to use the `spath` command to access the properties directly. Without any additional arguments, simply passing the `jwt` field as the input to `spath` will result in fields being created for each property in the JWT token:

```
| jwt field="request_headers" | spath input=jwt
```

From this output, accessing the JWT values is as simple as referencing `jwt.header.alg` or `jwt.payload.name`.

However, more advanced use cases can be easily accomplished with the additional options provided. For example, to show only events which included a JWT token, validate the token's HMAC SHA-256 signature with a provided secret and target the validation result directly, the following query could accomplish this:

```
| jwt field="request_headers" secret="mySecret" wrap=false filter=true 
| spath input=jwt path=signature 
| search signature="Invalid"
```

### Roadmap

As is, this app is functional and tested with standard JWT tokens as described above. If there is interest, support for additional signature algorithms and enhanced functionality may be considered.