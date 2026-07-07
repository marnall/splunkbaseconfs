##### PACKAGING

Before uploading the app to Splunkbase, follow these instructions to properly package it.
This will install the required dependencies and package the app into the parent directory as duo_splunkapp.spl.

`$ make build`

For builds created on Apple, use:
`$ make buildmac`

---

##### TESTING
To run the test suite located in duo_splunkapp/bin/test, first run

`$ pip install -r test-requirements.txt`

This will install the needed dependencies in your virtualenv.
Afterwards, run `tox` as usual to go through the entire test suite.

