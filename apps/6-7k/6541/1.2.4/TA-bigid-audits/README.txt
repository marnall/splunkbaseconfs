This add-on takes audit logs from your BigID instance and ingest them into splunk.

For this you need to provide the Base URL for your BigID instance (E.g. https://sandbox.bigid.tools), and the name and value of the Token to authenticate with BigID.

After adding a new Data Input with these values, you should be able to see the results by searching by 'sourcetype="bigid:audit:logs"'.
# Binary File Declaration
/Applications/Splunk/var/data/tabuilder/package/TA-bigid-audits/bin/ta_bigid_audits/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-bigid-audits/bin/ta_bigid_audits/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
