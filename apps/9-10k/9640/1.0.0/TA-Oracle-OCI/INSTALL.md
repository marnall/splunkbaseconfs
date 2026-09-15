# Installing TA-Oracle-OCI

Quick note before you start: this only covers the pull method (the
modular input that polls OCI Streaming with an API key). We've
actually run this end to end on a Splunk 10.2.7 box and watched real
audit data land in `index=oci`, so this part we can vouch for. There's
also a push method in the package (OCI Function -> HEC) but we haven't
put it through a real test yet, so it's not covered here - check
README.md if you want to try it anyway.

## Installing the app

Upload the .spl through Apps > Manage Apps > Install app from file,
and restart when it asks you to - that's not optional, the modular
input won't register otherwise.

One thing that trips people up: install this on a Heavy Forwarder you
manage yourself, not on the Splunk Cloud-managed indexer/search head
side. If you're on Splunk Cloud, read the compatibility note in
README.md first.

## Getting the OCI SDK installed

We didn't bundle any compiled binaries with this app on purpose -
that's actually what killed the older archived OCI add-ons once
Splunk moved past Python 3.7. Instead you install the `oci` SDK
yourself, against whatever Python your Splunk instance is really
running.

And that "whatever Python" part matters more than you'd think. We hit
this ourselves: some boxes (especially ones upgraded in place from an
older Splunk) end up with two Pythons sitting side by side, and the
generic `splunk cmd python3` shortcut can quietly grab the wrong one.
Worth checking first:

```bash
$SPLUNK_HOME/bin/splunk cmd python3 -m pip --version
```

If you're on Splunk 10.x, that should be Python 3.13:

```bash
$SPLUNK_HOME/bin/python3.13 -m pip install --break-system-packages \
    --target=$SPLUNK_HOME/etc/apps/TA-Oracle-OCI/bin/lib \
    -r $SPLUNK_HOME/etc/apps/TA-Oracle-OCI/bin/requirements.txt
```

On 9.x it's Python 3.9 - same command, just swap in
`$SPLUNK_HOME/bin/python3.9`.

If the version pip reports doesn't line up with what Splunk itself is
actually running (you can check this in `index=_internal
source=*splunkd.log*`, any modular input's startup line shows the real
path), skip `splunk cmd python3` and call the `python3.1X` binary
directly like above.

## Your private key

The form asks for a file path, not a pasted key, so get the .pem onto
disk first:

```bash
mkdir -p $SPLUNK_HOME/etc/apps/TA-Oracle-OCI/local/keys
cp /path/to/client-key.pem $SPLUNK_HOME/etc/apps/TA-Oracle-OCI/local/keys/oci_api_key.pem
chmod 600 $SPLUNK_HOME/etc/apps/TA-Oracle-OCI/local/keys/oci_api_key.pem
chown splunk:splunk $SPLUNK_HOME/etc/apps/TA-Oracle-OCI/local/keys/oci_api_key.pem
```

## The passphrase (if your key has one)

Don't put this in inputs.conf - it goes into Splunk's own encrypted
storage instead:

```bash
$SPLUNK_HOME/bin/splunk add secret-storage-password \
    -realm TA-Oracle-OCI -name <stanza-name> -password '<passphrase>' \
    -auth admin:changeme
```

The input looks this up from `storage/passwords` when it runs, so
nothing sensitive ends up sitting in a config file.

## Setting up the input itself

Head to Settings > Data Inputs > OCI Streaming (API Key Pull) > New.
You'll need:

- Tenancy OCID, User OCID, Fingerprint, Region - all from OCI Console
  under Identity & Security, wherever you set up the API key
- The key file path from the step above
- Stream OCID and Stream Endpoint - OCI Console > Streaming, on your
  stream's details page
- An index to write to (create one beforehand if you haven't already)

If you'd rather skip the form, the same thing can be written straight
into `local/inputs.conf` - README.md has the exact stanza format under
"Pull method setup."

## Checking it worked

```
index=_internal source=*oci_stream.py*
```

should come back clean, no errors. Then:

```
index=<your index> | stats count by sourcetype
```

and you're looking for oci:audit, oci:flowlogs,
oci:cloudguard:problem, oci:loadbalancer, or oci:objectstorage. If
most of what you see is oci:log, sourcetype detection isn't matching
your data and something's off.

## If something's not working

README.md covers this in more depth under "Pull method setup" and
"Restricted/air-gapped servers" - the Python mismatch above is the
most common one we've actually run into, but there's also network
requirements and multi-stream setup covered there.
