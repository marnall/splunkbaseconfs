# SnapAttack Splunk Client App
## Features
- Automatically sync deployed Detections from SnapAttack as Saved Searches in Splunk
- View Detection Hits over time
- Perform Adhoc Hunk and Bulk ranking of Detections from within SnapAttack 

## Installation
1. Create a summary index (default name is `snapattack_results`) on the Splunk Indexer(s). This index will be used as the summary index for collecting hits from deployed detections
2. Install the snapattack_client_app.tgz package on the Splunk Search Head
3. Generate an Integration API Key for the desired detection compilation target language
4. In the Web UI, navigate to the app and enter the API Key in the configuration dialogue, as well as a summary index name if different than the default

### Setup Options
- `Contribute Detection Hit Statistics to SnapAttack`: Metadata about detection hits will be sent back to SnapAttack for reporting on Detection performance [default: enabled]
- `Include Full Log with Hits`: When submitting detection hits to SnapAttack, include the full matching log for use in false positive reduction and machine learning [default: disabled]

### Advanced Configuration
- To configure connection to SnapAttack API via a proxy server, edit the `PROXY` stanza in `snapattack_api.conf`, and specify the HTTP and HTTPS proxy URLs. If proxy authentication is required, currently basic authentication is supported by including the proxy username and password in the URL (e.g. `https://username:password@proxy.url`)

Additional configuration options are available within snapattack_api.conf. Reference `README/snapattack_api.conf.spec` for details.

## Usage
The detection sync is scheduled to run every 15 minutes by default, and can be initiated manually by navigating to
the `Deployed Detections` dashboard. Saved searches created by this app are scheduled to run every 15 minutes with
lookback period of -15m. Results of the searches are stored in the configured summary index.

The job scheduler checks for the existence of new jobs in SnapAttack every 1 minute. This schedule can be adjusted by modifying the `SnapAttack Job Scheduler` saved search in `savedsearches.conf`

## Support
For support and feedback, join the [SnapAttack Slack Workspace](https://join.slack.com/t/snapattackcommunity/shared_invite/zt-16mv51s8g-Dkzd8v8hprsce_tplLG~Hg)