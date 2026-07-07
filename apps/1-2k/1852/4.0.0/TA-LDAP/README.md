**`TA-LDAP`**

This is a Add-on for Splunk to enable native python LDAP within Splunk.


**What this app does?**
The app uses a modular input to provide a configuration UI, and runs the LDAP
response test using the configured stanzas.
The app provides a custom search command `ldap` that you can either provide
search results, use options and use any stanza from `inputs.conf`.

All options that can be used:
server="STANZA"           specify LDAP server to be used, defaults to [default]
port="PORT"               specify LDAP port to be used, defaults to port in [default]
scope="SCOPE"             specify LDAP scope to be used in the search, defaults to sub
--filter="LDAP_FILTER" specify LDAP filter to be used in the search
basedn="BASEDN"           specify LDAP basedn to be used in the search, defaults
                          to basedn in [default]
timelimit="TIMEOUT"       specify LDAP search timeout to be used, defaults to 30
                          seconds
sizelimit="LIMIT"         specify LDAP size limit to be used in the search,
                          defaults to 5000 entries
attrs="ATTRS"             provide comma separated LDAP attributes to be
                          returned, defaults to all

**Install:**

Install as usual in the Splunk web or copy into $SPLUNK_HOME/etc/apps and
restart Splunk.

IMPORTANT NOTE:
If you upgrade from an older version, save the `inputs.conf` AND DELETE the
old app.

**Configure:**

Copy `default/inputs.conf` to the `local` folder, configure the input stanzas
(Remember the password must be a base64 value).

**Debug**

Both script provide debugging option that can be enabled and disabled in the
script.

**Known issues**


**Support**

This is an open source project, no support provided, but you can ask questions
on answers.splunk.com and I will most likely answer it.

I validate all my apps with Appinspect and the log can be found in the README
folder of each app.

Running Splunk on Windows? Good Luck, not my problem.


**Things to-do / Future ideas**

- `¯\_(ツ)_/¯`  

**Version**

`17. August 2019 : 4.0.0 / Complete re-wrote the app`
