## Explanation of the Asset Configuration Parameters

Following is the explanation of asset configuration parameters.

- **Device IP/Hostname:** The IP/Hostname of the Firepower Management Center instance.
- **Verify server certificate:** Validate server certificate.
- **User with access to the Firepower node:** Username of the user with access to the Firepower
  node.
- **Password:** Password for the above mentioned username.
- **Firepower Domain:** The Firepower domain you want to run the actions on.
- **Network Group Object:** The network group object you want to run the actions on.

## Authentication

The app uses token-based authentication. The 'test connectivity' action fetches a new token in
exchange for the provided username and password. The app uses this token for authentication. The
newly fetched token is encrypted and stored in the state file for future use. If the stored token
expires or gets corrupted, the app automatically generates a new one.

## Port Information

The app uses HTTP/HTTPS protocol for communicating with the Cisco Firepower Server. Below are the
default ports used by Splunk SOAR.

| Service Name | Transport Protocol | Port |
|--------------|--------------------|------|
| http | tcp | 80 |
| https | tcp | 443 |
