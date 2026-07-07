# Copyright (C) 2009-2017 Splunk Inc. All Rights Reserved.
#
# This file contains additional options for an inputs.conf file.  
#
# To learn more about configuration files (including precedence) please see the documentation 
# located at http://www.splunk.com/base/Documentation/latest/Admin/Aboutconfigurationfiles
#

[osquery://default]
* Configures an input for getting information from osquery clients.

port = <int>
* [Required] The port to run the server for listening for client information

address = <string>
* [Required] The server address to listen on

use_tls = <boolean>
* [Required] Whether to use TLS

enroll_secret = <string>
* The enrollment secret that clients must know to connect

key_file = <string>
* The path to the key file for the certificate
* Required if you use_tls is true 

cert_file = <string>
* The path to the certificate file
* Required if you use_tls is true 

ca_file = <string>
* The path to the certificate authority file
* Required if you use_tls is true 
