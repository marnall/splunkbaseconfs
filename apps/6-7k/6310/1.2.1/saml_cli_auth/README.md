saml_cli_auth
=============

An app for Splunk providing helpers for authenticating to Splunk on the CLI when using SAML for
logins to Splunk web.

To use:

1. Ensure app is installed. Restart Splunk if necessary.
2. Run `splunk cmd python $SPLUNK_HOME/etc/apps/saml_cli_auth/bin/saml_cli_auth.py`.
3. Open the provided URL in your browser, and proceed through SAML authentication.
4. Once authenticated, you can close the browser tab/window.
5. You should now be able to run CLI commands.

If necessary, you can pass `--hostname` and `--port` to `saml_cli_auth.py` to
manipulate the generated URL. The script will attempt to identify the best URL
for access, e.g. by checking the email `alert_action` for a custom URL. This is
useful if you are running an SHC behind a load balancer.

Configuring a base URL
----------------------

In some cases, `saml_cli_auth` may not be able to correctly generate a base URL
for logins. In this case, you can use the `saml_cli_auth.conf` config file to
set a static base URL.

```
splunk@splunkhf01:~$ cat $SPLUNK_HOME/etc/apps/saml_cli_auth/local/saml_cli_auth.conf
[cli]
base_url = https://splunkhf01.example.com
splunk@splunkhf01:~$
```

You do _not_ need to reload Splunk for this change to apply.

How it works
------------

`saml_cli_auth` is made up of three components:

* A custom web controller
* A custom REST endpoint
* A CLI-based Python script

The CLI script provides the user-interface for initiating a SAML-based login.
The script generates a unique ID, and provides the user a URL to login into.
This URL points to the custom web controller. Once login is successful, the
controller is loaded. The controller determines whether it is part of a search
head cluster or not. If not, it simply makes a local REST request to the custom
REST endpoint. If it _is_ an SHC member, it makes a REST request to the custom
REST endpoint on each SHC member. The custom REST endpoint writes the necessary
XML details to a predictable file path, based on the UUID provided in the URL.
The CLI script, meanwhile, polls the `retrieve` endpoint waiting for the
authentication data to be available. One available, it writes the data to the
correct location for the `splunk` binary to utilize. The custom REST endpoint
will wait several seconds for the CLI script to read the data, and then removes
the temporary file.

Search Head Cluster Note
------------------------

In a search head cluster, the custom controller needs to access the REST
endpoint exposing the list of SHC members. In order to do this, the
authenticated user must have the `list_search_head_clustering` capability
which, by default, is only granted to the `admin` role. Unpredictable results
are likely if a non-`admin` user attempts to authenticate on an SHC member.
Note that this scenario might work _if_ the user authenticates (by chance, or
intentionally using the `--hostname` option) to the same SHC member via
splunkweb that they are authenticating to on the CLI.

In short, SHC authentication is not officially supported for non-`admin` users.

Support
-------

Support for this app is provided on a best-effort basis. You may contact the
author at steve@mcmaster.io for assistance.
