import ssl
from io import StringIO, BytesIO

# CA public key as string
ca_cert_pem = "-----BEGIN CERTIFICATE-----\nMIID7zCCAtegAwIBAgIURN6D8bQ+fWjeuLU+/dg0iHzdyJ8wDQYJKoZIhvcNAQEL\nBQAwgYUxCzAJBgNVBAYTAkNIMRQwEgYDVQQIDAtCYXNlbC1TdGFkdDEPMA0GA1UE\nBwwGUmllaGVuMRUwEwYDVQQKDAxLYXVzd2FnYW4uaW8xFTATBgNVBAMMDEthdXN3\nYWdhbi5pbzEhMB8GCSqGSIb3DQEJARYSc2FsZXNAa2F1c3dhZ2FuLmlvMCAXDTIz\nMDMwMTA4NDY0NVoYDzIwNTMwMjI4MDg0NjQ1WjCBhTELMAkGA1UEBhMCQ0gxFDAS\nBgNVBAgMC0Jhc2VsLVN0YWR0MQ8wDQYDVQQHDAZSaWVoZW4xFTATBgNVBAoMDEth\ndXN3YWdhbi5pbzEVMBMGA1UEAwwMS2F1c3dhZ2FuLmlvMSEwHwYJKoZIhvcNAQkB\nFhJzYWxlc0BrYXVzd2FnYW4uaW8wggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEK\nAoIBAQDIxjupVMd9nQdOuPi6+N36PRXZLZCHXiJVc+lWE4lVILfxINsfBNBR+bgq\n4WawYLwIIJwEci9dcczY6BFgu+GL1qjs14ie6Tol1P43za2s0BwpmLlppcYYD0RE\nSTrZiRr7ffYlOwqazb93Hzov1bgZAqNgAycbT0aBGcGYn/KKP5rAI9wKdS52BlON\nCsAGTG9YgM6AJEGP5gpl1VJCO9o+n2V97ZVHamWn+f0TnKnTvZDMD0ipc6kS8kdo\n5mn5Xdp2xQns+dmbbAS2Rz+w2PDg4saWJjpPwacOqFN79V0si78tZhsOh93FTAbE\nRh4kT692f6WZfFb8jw/fIYGflbq5AgMBAAGjUzBRMB0GA1UdDgQWBBT1xSr326CX\n12lCAiSaK5ShEMFvLjAfBgNVHSMEGDAWgBT1xSr326CX12lCAiSaK5ShEMFvLjAP\nBgNVHRMBAf8EBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQBtDBCAs51xP38OvRwm\nt3G0CjmXDdT3uavrSzA4eV0nPaguRqdyZ2rAiDI6RN+JpeenP5d06uGRUnjGQ0z8\nsfAe012fso77+dlZ1GqwzTG00eNJ/E2B7dkhwcQISEtxQ8+YE9122PL8S5I+kQYu\nCRGmy7Tp4GTbPyfWkSLv6R7xJ1ITitSMbOv/s48v9ReOZb0QMVeVyvP6OVbuq2Fc\ncB2fRDfQGRSgxp9mvfe3ycgwuA9SL3ZDA+N0QtwbQBPs8XAhwmzWa/MaxNEyROQc\n6apDgfxUemRCDuanN69Ofj0KN1HGBMfJ1NFq274m7DDSW/qXeLYEbbSJiCxGO7jx\n4eCn\n-----END CERTIFICATE-----"

# Trial license certificate as bytes
trial_license_pem = b"""-----BEGIN CERTIFICATE-----
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
-----END CERTIFICATE-----"""

# Create file-like objects for the certificates
ca_cert_file = StringIO(ca_cert_pem)
trial_license_file = BytesIO(trial_license_pem)

# Create an SSL context
context = ssl.create_default_context(cadata=ca_cert_file.getvalue())

try:
    # Load the CA certificate
    context.load_verify_locations(cadata=ca_cert_file.getvalue())
    
    # Create a certificate object from the trial license
    cert = ssl.PEM_cert_to_DER_cert(trial_license_file.getvalue().decode('utf-8'))
    x509 = ssl.DER_cert_to_PEM_cert(cert)
    
    # Verify the certificate
    store = context.get_cert_store()
    x509_obj = ssl._ssl._test_decode_cert(x509.encode())
    
    if context.verify_certificate(x509_obj, store):
        print("Certificate verification successful")
    else:
        print("Certificate verification failed")
except ssl.SSLError as e:
    print(f"Certificate verification failed: {e}")
except Exception as e:
    print(f"An error occurred: {e}")

# Close the file-like objects
ca_cert_file.close()
trial_license_file.close()
