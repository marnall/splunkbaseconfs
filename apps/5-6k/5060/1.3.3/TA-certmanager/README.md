# TA-certmanager
  
Manages Splunk's cacert.pem so that custom certs can be added. Takes certs from the app's "cert" directory and appends 
them to cacert.pem.

## Supported Splunk versions
7.3, 8.0, 9.0, 9.1

### Fixing expiring Sectigo certificates on older versions of Splunk

Follow the below installation instructions, and for step 2 download [the latest certifi cacert.pem](https://raw.githubusercontent.com/certifi/python-certifi/master/certifi/cacert.pem).

## Installation

1. Install app on a forwarder or search head (wherever you're making HTTPS connections that require a custom SSL 
certificate).
2. Place necessary certificates in TA-certmanager/cert. 
3. (As of version 1.2.0 this step should be automated when possible) If Splunk is not running as root you will need to give write access to the user running Splunk. For Splunk 7:
<pre>chmod u+w $SPLUNK_HOME/lib/python2.7/site-packages/requests/cacert.pem</pre>
For Splunk 8: 
<pre>chmod u+w $SPLUNK_HOME/lib/python2.7/site-packages/certifi/cacert.pem
chmod u+w $SPLUNK_HOME/lib/python3.7/site-packages/certifi/cacert.pem</pre>
4. Restart Splunk.
5. Run the following command to verify that cacert.pem was updated: Splunk 7:
<pre>diff $SPLUNK_HOME/lib/python2.7/site-packages/requests/cacert.pem $SPLUNK_HOME/lib/python2.7/site-packages/requests/cacert_orig.pem</pre>
Splunk 8+:
<pre>diff $SPLUNK_HOME/lib/python3.7/site-packages/certifi/cacert.pem $SPLUNK_HOME/lib/python3.7/site-packages/certifi/cacert_orig.pem</pre>
If the diff shows no difference between those two files, or if cacert_orig.pem doesn't exist, something went wrong. 
Check the log for details with this search:
<pre>index="_internal" sourcetype="certmanager" ERROR</pre>

## Changelog

- Version 1.3.1 limits the app cert scanning to apps, manager-apps, and master-apps directories.
- Version 1.3.0 of this app adds support for managing the CA cert bundles in apps themselves. It is becoming more and more common for apps to ship with a copy of certifi rather than using Splunk's copy. This version also adds support deploying this app via a deployment server on Splunk 9.0+ (earlier versions already supported), and moves logging to a dedicated "certmanager" sourcetype.