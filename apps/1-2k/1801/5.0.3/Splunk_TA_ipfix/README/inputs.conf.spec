# Copyright (c) 2013, 2014 Splunk, Inc.  All rights reserved

[ipfix://<name>]
* Streams flow events coming over the IPFIX binary protocol to a specific port

address = <value>
* The ip address of the interface to listen on, 0.0.0.0 to listen on all addresses

port = <value>
* The UDP port to listen on for incoming IPFIX traffic (remember this can't be a port that's in use)

buffer = <value>
* The size (in bytes) to force the network buffer to
* This value should be large enough to protect against flooding by your IPFIX data source(s)
* The default value is 10MB, but may be insufficient for burst traffic under load
