SOCRadar Incidents Add-on for Splunk
=====================================

This add-on collects security incidents from the SOCRadar platform.

## IMPORTANT: Security Notice

Never include credentials in the app package! The local/ folder should NOT be included when packaging this app.

## Installation & Configuration

1. Install the add-on through Splunk Web or by extracting to $SPLUNK_HOME/etc/apps/

2. Configure your SOCRadar credentials:
   - Navigate to Settings > Data inputs > SOCRadar Incidents Collector v4
   - Click "New" to create a new input
   - Enter your SOCRadar API Key and Company ID
   - Select the destination index (recommended: create a dedicated index)
   - Set the collection interval (default: 300 seconds)

3. Alternatively, create local/inputs.conf manually:
   - Copy default/inputs.conf.example to local/inputs.conf
   - Update with your credentials
   - Restart Splunk

## Packaging Instructions

IMPORTANT: Before packaging for distribution:
1. Ensure NO credentials are in any configuration files
2. Delete or exclude the entire local/ folder
3. Run app validation
4. Package only the default/, bin/, README/, metadata/, and static/ folders

## Security Best Practices

- Never commit credentials to version control
- Use Splunk's credential storage for API keys
- Regularly rotate API keys
- Monitor the add-on logs for any issues

This is an add-on powered by the Splunk Add-on Builder.
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-socradar-incidents/bin/ta_socradar_incidents/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-socradar-incidents/bin/ta_socradar_incidents/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
# Binary File Declaration
