# DX Search Audit

## About
This app was created to streamline the tedious and often mundane task of auditing end-user searches.  If you're ok with users being able to see each other's content (in a roundabout way), this can also be used as a self-audit tool.

***

## Minimum Configuration
There are 4 knowledge objects that need to be configured prior to use
- For the `dx_search_tier` macro, modify the host field to match the splunk host name where this app is installed.  If running on a search head cluster, match all cluster members.  Ex... `host=splunk-shc0*`.
- Enable the following saved searches after modifying the `dx_search_tier` macro.  Adjust the cron schedules as needed:
  - `Generating Lookup for dx_savedsearch_audit`
  - `Generating Lookup for dx_savedsearch_perf`
    - Optionally adjust the `earliest` time.  This will determine the time period performance statistics are calculated over.  The reccomended value is `-30d`.
  - `Generating Lookup for dx_dashboard_audit`

***

## Notes
By default, this app is visible to end users.  Only members of the `admin` and `sc_admin` roles can see all user content __*within the dashboard*__.  Users not in any of those roles can only see their own content __*within the dashboard*__.  These can be modified via the `dx_user_filter` macro.

* The above-mentioned content filtering __*only applies to the dashboard itself*__.  Access to the lookups is currently unrestricted within the app context.  If you want to be sure end users can't see each other’s private content, restrict read access to this app via `local.meta`.  I plan on addressing this in a future release/iteration of this app.
* If you want to make it more difficult for end users to get at the lookups, create the following files in local/data/ui/views with the below content: `alerts.xml`, `analytics_workspace.xml`, `dashboards.xml`, `datasets.xml`, `reports.xml`, and `search.xml`.
```
<?xml version="1.0"?>
<view template="dx_savedsearch_audit:/templates/redirect.html" type="html">
    <label>Saved Search Audit - Oops, you shouldn't be here...</label>
</view>
```

***

## Support
This app is currently in beta and is developer supported.  I'll do my best to assist anyone that reaches out.

Developer: Alan Shurack

Email: alan@dataknox.com

LinkedIn: https://www.linkedin.com/in/alan-shurack-399b279/

Public Splunk Slack: splunk-usergroups.slack.com

