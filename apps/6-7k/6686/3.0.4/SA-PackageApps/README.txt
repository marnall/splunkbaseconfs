PackageApps for Splunk
================================

The goal of this project is to tarball the contents of the etc/app along with local and lookups directory from the SH and publish on the customer provided AWS S3 bucket/ Azure Container Storage

packageapps
-----------
This command is a generating command and takes in two input parameters
    APP: which is the list of apps that needs to be packaged - This is a mandatory field and does not support regular expressions
    LOCALONLY: Boolean value - Specify if you want to download the whole directory or only the local directory from the folder. 
               Default value of this parameter is 'False'(Download whole directory)
    AZURE: Boolean value - Specify if the package apps needs to be sent to the Azure Container Storage
           Default value of this parameter is 'False'(Send it to AWS S3 Bucket)

The list of apps provided are then packaged and sent to the AWS S3 bucket/ Azure Container Storage provided during the initial setup.

Example:
`| packageapps APP="app1"`
`| packageapps APP="app1,app2" LOCALONLY=True`
`| packageapps APP="app1,app2" AZURE=True`
`| packageapps APP="app1,app2" AZURE=True LOCALONLY=True`

All Logs are generated in the $SPLUNK_HOME/var/log/splunk/package_apps.log

License
=======
* Copyright 2021-2022 assigned to Splunk, Inc. [Splunk General Terms](https://www.splunk.com/en_us/legal/splunk-general-terms.html) apply. This extension is NOT SUPPORTED by Splunk support, but solely on a best effort basis by this extension's developers. See authors in app.conf.

Acknowledgements
================
* Includes a copy of the [AWS SDK for Python - boto3](https://github.com/boto/boto3) licensed under the Apache License, Version 2.0
* Includes a copy of the [Splunk Python SDK](https://github.com/splunk/splunk-sdk-python) licensed under the Apache License, Version 2.0
* Includes a copy of the [cryptography](https://github.com/pyca/cryptography/) licensed under the Apache License, Version 2.0
* Includes a copy of the [cffi] licensed under the MIT License (MIT)
* Includes a copy of the [azure_storage_blob] licensed under the MIT License (MIT)
* Includes a copy of the [azure_core] licensed under the MIT License (MIT)
* Includes a copy of the [msrest] licensed under the MIT License (MIT)
* Includes a copy of the [typing_extensions] licensed under the Python Software Foundation License
* Includes a copy of the [six] licensed under the MIT License (MIT)
* Includes a copy of the [requests](https://github.com/psf/requests) licensed under the Apache License, Version 2.0
* Includes a copy of the [requests_oauthlib] licensed under the BSD License (ISC)
* Includes a copy of the [certifi](https://github.com/certifi/python-certifi) licensed under the Mozilla Public License 2.0 (MPL 2.0) (MPL-2.0)
* Includes a copy of the [isodate]  licensed under the BSD License (BSD)
* Includes a copy of the [charset_normalizer] licensed under the MIT License (MIT)
* Includes a copy of the [urllib3](https://github.com/urllib3/urllib3) licensed under the MIT License (MIT)
* Includes a copy of the [idna](https://github.com/kjd/idna) licensed under the BSD License
* Includes a copy of the [oauthlib] OSI Approved,licensed under the BSD License (BSD)
* Includes a copy of the [pycparser] licensed under the BSD License
* Includes a copy of the [botocore](https://github.com/boto/botocore) licensed under the Apache License, Version 2.0
* Includes a copy of the [deprecation] OSI Approved, licensed under the Apache Software License
* Includes a copy of the [jmespath] OSI Approved, licensed under the MIT License
* Includes a copy of the [packaging] OSI Approved, licensed under the MIT License, Apache Software License
* Includes a copy of the [python_dateutil] licensed under the Apache Software License, BSD License (BSD)
* Includes a copy of the [s3transfer] OSI Approved, licensed under the Apache Software License

# Binary File Declaration

Contains following Binary Files: 
_cffi_backend.cpython-38-x86_64-linux-gnu.so

These binary files are part of the cffi packages
