# Lookout Mobile Threat Defense for Splunk

Integrate Lookout Mobile Threat Defense telemetry into Splunk SIEM.

**TODO**: link to user documentation documentation/install guide/etc.


# Binary File Declaration

The Lookout Mobile Threat Defense for Splunk app uses the Crypto library of the python module pycryptodome.
This library is used to encrypt and decrypt data stored in the KV_Store. As per the documentation,
all of the binaries and source code for pycryptodome are stored in the lib sub-directory within the app directory.

The full source code for pycryptodome can be found on github here: https://github.com/Legrandin/pycryptodome

The files stored in lib/crypto are the result of building pycryptodome from source using and cherry-picking just
the binaries/artifacts required for our purposes.
