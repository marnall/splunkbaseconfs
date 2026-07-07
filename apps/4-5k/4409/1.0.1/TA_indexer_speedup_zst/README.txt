# TA for indexer speedup using zst compression

# This app is based on this slide deck:
# https://static.rainfocus.com/splunk/splunkconf18/sess/15230307008970013eU6/finalPDF/FN1303_RevealingTheMagic_1539123987021001TcI3.pdf

# It switches the default algorithm for compressing
# the raw data "journal" file on the indexers
# from the default of "gzip" to the hot new "zst".

# According to them, you should see:
# * Compression rate 4x improvement over Gzip
# * Decompression rate 3x improvement over Gzip
# * Average 5% space savings over Gzip
# * 30-43% faster search results

# So:
# 1: Deploy app to indexers
# 2: Restart all Splunk instances there
# 3: PROFIT!

### Perrequisites

The pre-requisites for the add-on are as follows;

```
Indexers: Splunk version 7.2 or higher
```

### Installing & Deploying the Add-On

Installation instructions are as follows;
1) Ensure that your Indexers are updated to Splunk version 7.2 or later.
Deploying to earlier versions will (depending on version):
EITHER Cause Indexers to refuse to start with a clear ERROR explanation why
OR Allow Indexers to start with WARNing that the setting is ignored and reverting to default (gz).
2) Deploy app.
3) Restart Splunk on each Indexer (rolling restart).

```
Splunk Indexers:
Add-on should be installed on Indexers ONLY.
Deploy from Master Node to slave-apps (clustered) or directly in apps (unclustered).
```

### Testing & Troubleshooting

If Indexers refuse to start, you are on a version earlier than 7.2.
This is the only possible problem that you will have.
You can debug/verify with these commands:
```
$SPLUNK_HOME/bin/splunk btool indexes list --debug | grep zst
splunkd.log in search or at $SPLUNK_HOME/var/log/splunk/splunkd.log
```

NOTE: This app fails AppInspect in these 2 unfixable (and unreasonable) areas:
[ failure ] Check that app does not contain any .conf files that create global definitions using the [default] stanza.
[ failure ] Check that the app does not create indexes.

## Authors

* **Gregg Woodcock** - *Yes, I created the 1 active line in indexes.conf!* - woodcock@Splunxter.com
