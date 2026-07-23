## Outbound Network Access

The custom alert action (heartbeat_dispatch) makes outbound HTTPS calls only to the Slack, Microsoft Teams, and generic webhook URLs the operator explicitly configures, and routes email through the Splunk instance's own SMTP relay via loopback. No data is sent to O11y Innovators Network or any third party not configured by the operator. See README.md for full details.
