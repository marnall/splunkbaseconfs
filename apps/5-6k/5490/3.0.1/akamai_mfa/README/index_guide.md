# Index Guide

This app ships with a dedicated index: `akamai_mfa` (180-day retention).
To use a different index name or retention:
- From README/examples/ copy `indexes.conf.example` to `local/indexes.conf` and `macros.conf.example` to `local/macros.conf`.
- Update the index code block and adjust `frozenTimePeriodInSecs`.
- Update the macro akamai_mfa in local/macros.conf to match your index name.

## Restrict access to index
- Create a role, e.g. `akamai_mfa_splunk_user`.
- Copy metadata/default.meta to local/default.meta.
Add the following code for the index to `local/default.meta`:
```
[akamai_mfa]
access = read : [ admin, akamai_mfa_splunk_user ], write : [ admin ]
export = system
```

## Access the data from index
Run below code in search bar to get data from `akamai_mfa` index.
```
index="akamai_mfa" sourcetype="akamai_mfa_resource_action"
```
Adding `index="akamai_mfa"` before queries makes sure data is being obtained from `akamai_mfa` index.

## Fallback to main
Starting with version 2.0.0, this app writes to a dedicated index (akamai_mfa) instead of main.
If you have custom searches, dashboards, or alerts that query only by sourcetype, you must add index=akamai_mfa.
Alternatively, update the provided macro akamai_mfa_index to point to your preferred index and update searches to use it.