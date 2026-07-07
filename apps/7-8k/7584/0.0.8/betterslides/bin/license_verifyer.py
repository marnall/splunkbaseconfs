import os,sys,io,platform
#load own libs from ../lib

# Import the correct version of cryptography
# https://pypi.org/project/cryptography/
os_platform = platform.system()
py_major_ver = sys.version_info[0]

# Import the correct version of platform-specific libraries
if os_platform == 'Linux':
	path_prepend = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib', 'py3_linux_x86_64')
elif os_platform == 'Darwin': # Does not work with Splunk Python build. It requires code signing for libs.
	path_prepend = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib', 'py3_darwin_x86_64')
elif os_platform == 'Windows':
	path_prepend = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib', 'py3_win_amd64')
sys.path.append(path_prepend)
print(path_prepend)


from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature
from datetime import datetime

class LicenseVerifier:
    def __init__(self):
        # CA public key (replace with your actual CA public key)
        self.ca_public_key_pem = b"""
        -----BEGIN PUBLIC KEY-----
        MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAu1SU1LfVLPHCozMxH2Mo
        4lgOEePzNm0tRgeLezV6ffAt0gunVTLw7onLRnrq0/IzW7yWR7QkrmBL7jTKEn5u
        +qKhbwKfBstIs+bMY2Zkp18gnTxKLxoS2tFczGkPLPgizskuemMghRniWaoLcyeh
        kd3qqGElvW/VDL5AaWTg0nLVkjRo9z+40RQzuVaE8AkAFmxZzow3x+VJYKdjykkJ
        0iT9wCS0DRTXu269V264Vf/3jvredZiKRkgwlL9xNAwxXFg0x/XFw005UWVRIkdg
        cKWTjpBP2dPwVZ4WWC+9aGVd+Gyn1o0CLelf4rEjGoXbAAEgAqeGUxrcIlbjXfbc
        mwIDAQAB
        -----END PUBLIC KEY-----
        """
        self.ca_public_key = x509.load_pem_public_key(self.ca_public_key_pem)

        # Trial license (replace with your actual trial license)
        self.trial_license_pem = b"""
        -----BEGIN CERTIFICATE-----
        MIIDazCCAlOgAwIBAgIUBRkBHhEe6FVrRbYVBwqxZVZUwJswDQYJKoZIhvcNAQEL
        BQAwRTELMAkGA1UEBhMCQVUxEzARBgNVBAgMClNvbWUtU3RhdGUxITAfBgNVBAoM
        GEludGVybmV0IFdpZGdpdHMgUHR5IEx0ZDAeFw0yMzA4MDMxNTIzMTlaFw0yNDA4
        MDIxNTIzMTlaMEUxCzAJBgNVBAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEw
        HwYDVQQKDBhJbnRlcm5ldCBXaWRnaXRzIFB0eSBMdGQwggEiMA0GCSqGSIb3DQEB
        AQUAA4IBDwAwggEKAoIBAQC7VJTUt9Us8cKjMzEfYyjiWA4R4/M2bS1GB4t7NXp9
        8C3SC6dVMvDuictGeurT8jNbvJZHtCSuYEvuNMoSfm76oqFvAp8Gy0iz5sxjZmSn
        XyCdPEovGhLa0VzMaQ8s+CLOyS56YyCFGeJZqgtzJ6GR3eqoYSW9b9UMvkBpZODS
        ctWSNGj3P7jRFDO5VoTwCQAWbFnOjDfH5UlgoGPKSQnSJP3AJLQNFNe7br1XbrhV
        //eO+t51mIpGSDCUv3E0DDFcWDTH9cXDTTlRZVEiR2BwpZOOkE/Z0/BVnhZYL71o
        ZV34bKfWjQIt6V/isSMahdsAASACp4ZTGtwiVuNd9tybAgMBAAGjUzBRMB0GA1Ud
        DgQWBBTpHdFqWqRxZkXcLFdXOPNQFXpKvzAfBgNVHSMEGDAWgBTpHdFqWqRxZkXc
        LFdXOPNQFXpKvzAPBgNVHRMBAf8EBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQB8
        t/VtBqUcZuLUjVjz6FVeEsDFO4gKnA/T6ZBrpDdDfWjUw/yX7vMjZGZK1dOEDRXx
        4QEaGZZgHgLXPRCTy0BM7OuZtBQJq6X0XKZfHWtLzZ7Z7OkUWHWkHhOEDfVfFYcw
        N9GXqkZJ1vcqXxH8UDn+mjPdtVQs9yj2Qy9RVbjRdXMWBLMdXVMjZVJHgZc7pYb7
        QZNjdvGz/8mLZQlB9TlZDNYqWvHmZ5hBz8TfUdkHHfuLcpBXyx4Ks3aSbGXgSqsf
        KvZrH0kvNwdTWxZFbZQZNWoWmF3YyYO9zDZLtTFjpsp6NxkPXl7z1/9qHHjNaqzq
        Yl5rnXHYwCmkKoKgXHxr
        -----END CERTIFICATE-----
        """
        self.trial_license = x509.load_pem_x509_certificate(self.trial_license_pem)

    def verify_certificate(self, cert_pem=None):
        if cert_pem is None:
            cert = self.trial_license
        else:
            cert = x509.load_pem_x509_certificate(cert_pem)

        # Check if the certificate has expired
        if datetime.utcnow() > cert.not_valid_after:
            return "expired"

        # Verify the certificate signature
        try:
            self.ca_public_key.verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                cert.signature_hash_algorithm,
            )
        except InvalidSignature:
            return "invalid"

        # If we've made it this far, the certificate is valid
        if cert_pem is None:
            return "trial"
        else:
            return "licensed"

# Usage example:
verifier = LicenseVerifier()

# Verify the built-in trial license
result = verifier.verify_certificate()
print(f"Trial license status: {result}")

# Verify a custom certificate (replace with an actual certificate)
custom_cert_pem = b"""
-----BEGIN CERTIFICATE-----
MIIDazCCAlOgAwIBAgIUBRkBHhEe6FVrRbYVBwqxZVZUwJswDQYJKoZIhvcNAQEL
BQAwRTELMAkGA1UEBhMCQVUxEzARBgNVBAgMClNvbWUtU3RhdGUxITAfBgNVBAoM
GEludGVybmV0IFdpZGdpdHMgUHR5IEx0ZDAeFw0yMzA4MDMxNTIzMTlaFw0yNDA4
MDIxNTIzMTlaMEUxCzAJBgNVBAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEw
HwYDVQQKDBhJbnRlcm5ldCBXaWRnaXRzIFB0eSBMdGQwggEiMA0GCSqGSIb3DQEB
AQUAA4IBDwAwggEKAoIBAQC7VJTUt9Us8cKjMzEfYyjiWA4R4/M2bS1GB4t7NXp9
8C3SC6dVMvDuictGeurT8jNbvJZHtCSuYEvuNMoSfm76oqFvAp8Gy0iz5sxjZmSn
XyCdPEovGhLa0VzMaQ8s+CLOyS56YyCFGeJZqgtzJ6GR3eqoYSW9b9UMvkBpZODS
ctWSNGj3P7jRFDO5VoTwCQAWbFnOjDfH5UlgoGPKSQnSJP3AJLQNFNe7br1XbrhV
//eO+t51mIpGSDCUv3E0DDFcWDTH9cXDTTlRZVEiR2BwpZOOkE/Z0/BVnhZYL71o
ZV34bKfWjQIt6V/isSMahdsAASACp4ZTGtwiVuNd9tybAgMBAAGjUzBRMB0GA1Ud
DgQWBBTpHdFqWqRxZkXcLFdXOPNQFXpKvzAfBgNVHSMEGDAWgBTpHdFqWqRxZkXc
LFdXOPNQFXpKvzAPBgNVHRMBAf8EBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQB8
t/VtBqUcZuLUjVjz6FVeEsDFO4gKnA/T6ZBrpDdDfWjUw/yX7vMjZGZK1dOEDRXx
4QEaGZZgHgLXPRCTy0BM7OuZtBQJq6X0XKZfHWtLzZ7Z7OkUWHWkHhOEDfVfFYcw
N9GXqkZJ1vcqXxH8UDn+mjPdtVQs9yj2Qy9RVbjRdXMWBLMdXVMjZVJHgZc7pYb7
QZNjdvGz/8mLZQlB9TlZDNYqWvHmZ5hBz8TfUdkHHfuLcpBXyx4Ks3aSbGXgSqsf
KvZrH0kvNwdTWxZFbZQZNWoWmF3YyYO9zDZLtTFjpsp6NxkPXl7z1/9qHHjNaqzq
Yl5rnXHYwCmkKoKgXHxr
-----END CERTIFICATE-----
"""
result = verifier.verify_certificate(custom_cert_pem)
print(f"Custom certificate status: {result}")
