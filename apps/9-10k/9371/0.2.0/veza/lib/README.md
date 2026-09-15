# Bundled libraries

`splunklib/` (the Splunk Python SDK) is copied here at package time by
`controlp/modules/siemsplunk/package.sh`. It is not vendored in the
repository so we always ship the latest SDK without having to track a stale
copy in Git.

No other dependencies are bundled. Splunk Enterprise ships its own `requests`
and standard library; per Splunk Cloud compatibility rules, the TA must rely
on those rather than vendoring its own copies.
