### Troubleshooting Connection Issues

**Error - Could not generate an access token**

If you see this error be sure to synchronize the time on your Phantom host machine. Cylance uses a
time-based authorization and will deny API requests if the clock on your Splunk Phantom server has
drifted. For example, the following command can be used to update your system time:

sudo ntpdate -u ntp.ubuntu.com

### JWT

This app uses the python-jwt module, which is licensed under the MIT License, Copyright (c) 2015
José Padilla.\
PyJWT is a Python library which allows you to encode and decode JSON Web Tokens (JWT). JWT is an
open, industry-standard (RFC 7519) for representing claims securely between two parties.
