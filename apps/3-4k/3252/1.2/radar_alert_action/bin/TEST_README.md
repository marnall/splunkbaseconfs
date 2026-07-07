# RADAR Incident Creation Splunk Add-on Testing

## Prerequisites:

* Install Python 2 (version 2.7 or greater)
* Install `splunklib` Python package via `pip` and ensure its install directory is in your `PYTHONPATH`
* Install `radar_alert_action` Add-on to `$SPLUNK_HOME/etc/apps` (just extract archive and copy entire dir to that root)
* Edit `$SPLUNK_HOME/etc/apps/radar_alert_action/local/alert_actions.conf` to set `param.radar_url =
  https://api.local.radarfirst.com/` (under the section heading `[radar]`) so that it hits your local stack rather than
  production.
* RADAR installation with an organization account with a user that has generated an API token.
* The admin or a user with sufficient privileges has completed the initial setup of the Alert Action (Settings->Alert Actions->Setup RADAR Create Incident).
* When launching Splunk for testing, you'll probably want to disable SSL certificate verification for REST calls to
  Splunk and RADAR.
      * For calls to Splunk, you must configure the appropriate config value (see [main README](../README.md) -- it's
        configured to be disabled by default, so you shouldn't need to change anything).
      * For calls to RADAR, this can be done by setting environment variable `RADAR_API_SKIP_SSL_VERIFY=1`.

## Unit Test Usage:

Please note that the unit tests modify live configuration settings on the Splunk instance used for testing.
The tests are designed to restore the original settings after execution, but it's safest to double-check or
avoid using a production Splunk instance for testing if possible.

1. In shell, navigate to `$SPLUNK_HOME/etc/apps/radar_alerts/bin`
2. Ensure that the directory containing the `splunk` binary (`$SPLUNK_HOME/bin`) is in your `PATH`
3. Run the following command, adjusting environment variables as appropriate for your Splunk installation:
    `SPLUNK_USERNAME=admin SPLUNK_PASSWORD=changeme SPLUNK_URL=https://localhost:8089 RADAR_API_SKIP_SSL_VERIFY=1 splunk cmd python radar_test.py`
4. In shell, execute `splunk cmd python radar_test.py --execute`

### Expected Result
All tests pass. If a specific tests fails, it will be indicated in the script's shell output.

## Shell-level Invocation
1. In shell, navigate to `$SPLUNK_HOME/etc/apps/radar_alerts/bin`
2. Copy `radar_test.json.example` to `radar_test.json` and fill in relevant bits.
    1. To get session_key from Splunk:
        `curl -X POST --insecure https://localhost:8089/services/auth/login -d username=my_username -d password=my_password`
    2. `radar_url` is the base URL of the RADAR instance to target (e.g. `https://api.radarfirst.com`)
    3. Generate an API token for radar_api_token via RADAR "My Account" page. Be sure to check "Incidents Write" scope.
3. Execute `cat radar_test.json | splunk cmd python radar.py --execute`

### Expected Result
A new issue will have been created in the target RADAR instance, with the `radar_incident_name` and `radar_incident_description` specified in `radar_test.json`.

## Ad Hoc Search Language Invocation
In a SplunkWeb Search Dashboard, enter the following (after configuring settings specific to your RADAR account):

    | sendalert radar param.radar_incident_name="Test Incident Name" param.radar_incident_description="Test Incident Description"
        
### Expected Result
A new issue will have been created in the target RADAR instance, with the provided name and description.
