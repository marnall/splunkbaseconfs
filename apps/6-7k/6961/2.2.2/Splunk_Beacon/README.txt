# Guard Detect Add-on for Splunk

## References

For more detailed information, please refer to the following resources:

- Atlassian Guard Premium Documentation: https://www.atlassian.com/software/guard/guard-premium
- Atlassian Account API Token: https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/
- Guard Detect Add-on for Splunk Documentation: https://splunkbase.splunk.com/app/6961

## Proxy support

If your Splunk instance must use an outbound proxy to reach the internet, you can configure a proxy specifically for the Guard Detect Add-on:

1. In Splunk, go to Apps → Splunk Guard Detect Add-on → Configuration → Proxy.
2. Set Enable proxy to Enabled.
3. Enter your HTTPS proxy URL, e.g.:
   - https://proxy.example.com:8443
   - Enter your credentials if necessary in the proxy username and proxy password sections.
4. Save.

Notes:
- This proxy setting applies only to outbound requests from the Guard Detect Add-on (it does not change the global Splunk proxy).
- Supported scheme for now: https (the same URL is applied to HTTPS and HTTP requests made by the add-on if needed).
- After saving, verify success under the Input Health dashboard. If misconfigured, errors will indicate proxy connection or authentication failures.