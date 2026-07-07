##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
@placement forwarder, search-head
[<name>]
adminRestApiUrl = <string>
* Provide url for rest api call.
* Example: https://access.securid.com/AdminInterface/restapi

access_id_of_api = <value>
* Provide the Access ID for RSA SecurID CAS.
* Example: 012345ab-4321-1234-abcd-123abc123abc

api_access_key = <value>
* Provide the API Access Key for RSA SecurID CAS.
* Example: -----BEGIN RSA PRIVATE KEY-----MIIEogIBAAKCAQEAmRBwxoEezoXkrxttLw3YxTc92TKNpRDqyR6PokV6kv4LdYsu3EiCTzzKyWl29Jm6uavdTBwMLxD3JrV-----END RSA PRIVATE KEY-----
