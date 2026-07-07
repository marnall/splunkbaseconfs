# MQTT Topics Ingestor TA for Splunk

## Short Description

The MQTT Topics Ingestor is a Splunk modular input that leverages the paho MQTT library to ingest data from MQTT brokers into Splunk. It supports SSL/TLS 1-way authentication with a CA certificate and 2-way authentication with optional CA certificate usage.

## Author
Gary Croker

## Details

- **SSL/TLS**: The system uses 1-way authentication with a CA Certificate (normally provided by cloud instance) and supports 2-way authentication with a Certificate and Key. For 2-way authentication, the system CA certificates in `/etc/ssl/certs` are used if no CA Certificate is provided.

- **Client Name**: This TA allows you to set the client name to use. This can assist with setting up ACLs on Brokers etc.

- **Quality of Service (QoS)**: The QoS for MQTT connections is hard set to 1. see - https://www.emqx.com/en/blog/introduction-to-mqtt-qos. Splunk can easily dedup if required. 
 
- **Clean Start**: Clean start is used during setup; however, once the ingestion process is started (the Technology Add-on is running), there is no cleanstart to ensure all data is ingested without loss. You are in control of the client name.
 
- **Logging**: Comprehensive logging is in place and stored within Splunk's log directory, with distinctive logging for module setup and processing.

## Installation

1. Download and install this TA.
2. Install this modular input as you would typically install a Technology Add-on in Splunk. It is mean't to be installed on a HF.
3. Configure the input using Splunk Web or manually editing inputs.conf as appropriate. If editing inputs you know to do that local precedence not default.

## Configuration

Configure the following parameters in the modular input settings:

1. **MQTT Broker**: Hostname or IP of the MQTT broker.
2. **MQTT Port**: TCP port on which the MQTT broker is listening.
3. **Client Name**: Name used by Splunk to connect to the MQTT broker.
4. **Authentication**: Enter username and password credentials, if applicable.
5. **SSL/TLS**: Select and provide required fields for either 1-way or 2-way SSL/TLS authentication.
6. **Topics**: Specify one or more topics to subscribe to, separated by commas.
7. Set additional parameters like certificates as necessary. Ensure filesystem access is read.

## Troubleshooting

- Verify that the correct Python version is available on your splunk version - Python 3.
- Check Splunk's internal logs for errors related to this modular input. See TA's "Logs" navigation section with Splunk.
- Ensure network connectivity between the Splunk instance and the MQTT broker. Check firewalls.
- Validate SSL/TLS configurations and certificate paths and permissions.

## Library Dependencies/Included
Splunklib 2.0.2
Paho MQTT 2.1.1.dev0

## One-Way SSL/TLS Authentication

One-way SSL (Secure Socket Layer) or TLS (Transport Layer Security) authentication is a security protocol used to establish a secure connection between a client and a server over the internet. It ensures that the data exchanged between them is encrypted and prevents eavesdropping or tampering by third parties.

**How It Works:**
- The client requests access to a secured server (like an MQTT broker).
- The server presents its SSL/TLS certificate to the client. This certificate contains the server's public key and is signed by a trusted Certificate Authority (CA).
- The client verifies the server's certificate against the list of trusted CAs. If the CA is recognised and the certificate is valid, the client trusts the server.
- The client uses the server's public key to encrypt a "premaster secret" and sends this to the server.
- The server decrypts the premaster secret using its private key.
- Both the server and the client use the premaster secret to generate a symmetric session key, which is used to encrypt and decrypt the data exchanged during the session.
- Secure communication is established, and data can be transferred in a protected manner.

**Components Needed:**
- A valid SSL/TLS certificate signed by a trusted CA.
- A server configured to use HTTPS.
- A client capable of validating CA-signed certificates.

## Two-Way SSL/TLS Authentication (Mutual Authentication)

Two-way SSL/TLS authentication, also known as mutual SSL/TLS authentication, involves a two-sided verification process. Here, both the client and the server authenticate each other, ensuring that both parties are trustworthy.

**How It Works:**
- Just as with one-way SSL/TLS authentication, the server presents its certificate to the client for verification.
- Once the server is verified, the server then requests a certificate from the client.
- The client presents its own SSL/TLS certificate to the server, which was also signed by a trusted CA.
- The server verifies the client's certificate against its list of trusted CAs. If the client's CA is recognised and the certificate is valid, the server trusts the client.
- After mutual verification, both the client and the server use the cryptographic keys present in their respective certificates to generate a shared secret, which is used to encrypt communication.

**Components Needed:**
- A valid SSL/TLS server certificate signed by a trusted CA.
- A client with a valid SSL/TLS client certificate signed by a trusted CA.
- A server and client configured to request and validate each other’s certificates.
- A CA infrastructure to issue and revoke certificates.

Both one-way and two-way SSL/TLS authentication require proper management of certificates and private keys to ensure that communications remain secure and that the involved parties can be authenticated. Two-way SSL/TLS authentication provides an additional layer of security by requiring both the client and the server to hold and exchange valid certificates.

## Summary: Configuration Choices for MQTT/Splunk Technology Add-on

When integrating MQTT brokers with Splunk, there are a multitude of configuration options and methodologies available. The chosen configuration approach for the MQTT/Splunk Technology Add-on (TA) has been carefully selected based on a fit-for-purpose strategy. This approach ensures that it not only aligns with industry best practices but also satisfies the specific requirements and constraints encountered in practical applications.

### Why This Configuration?

The implemented configuration methodology optimizes for several key factors:

- **Security**: Emphasizing robust security mechanisms, the TA offers both one-way and two-way SSL/TLS authentication to ensure data integrity and confidentiality during transmission.

- **Scalability**: Understanding that infrastructures can grow, the chosen setup is designed to scale seamlessly with increasing data volume and broker connections.

- **Usability**: By offering intuitive configuration choices that align with standard MQTT and Splunk setup processes, the solution reduces the learning curve and enables smooth integration.

- **Flexibility**: The configuration accommodates various deployment scenarios, from cloud-based to on-premises broker implementations, allowing for extensive compatibility across diverse environments.

- **Reliability**: The commitment to a 'no clean start' policy once the TA is running assures that data ingestion will continue uninterrupted, thereby preserving data continuity.

- **Compliance**: Care has been taken to ensure the configuration adheres to best practices and meets compliance requirements where applicable.

Each aspect of the TA's configuration has been evaluated against these considerations and has been integrated into the solution to provide an optimal balance of performance, security, and operational efficiency. While alternative methods could be employed, the chosen route serves the dual purpose of being both a robust framework for experienced users and an accessible starting point for new adopters, making it a suitable choice for a variety of Splunk data ingestion scenarios.

