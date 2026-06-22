## Authentication

### BeyondTrust API

To use the BeyondTrust API, ensure that the **Enable XML API** option is checked on the **Management > API Configuration** page of the **/login** administrative interface.

### Authenticate to the API

BeyondTrust's web APIs use OAuth as the authentication method.

To authenticate to the API:

- Create an API account on the **/login > Management > API Configuration** page
- The account must have **permission to access the Configuration API**

API requests require a token to first be created and then be submitted with each API request as HTTP authorization header.

#### Rate Limits

Requests are limited to 20 per second and 15,000 per hour.

This limit applies to all API endpoints, and is per API account.

## Port Details

The app uses HTTP/ HTTPS protocol for communicating with the BeyondTrust server. Below are the
default ports used by the Splunk SOAR Connector.

| Service Name | Transport Protocol | Port |
|--------------|--------------------|------|
| https | tcp | 443 |
