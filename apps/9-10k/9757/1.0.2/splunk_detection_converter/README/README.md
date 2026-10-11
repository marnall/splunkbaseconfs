# Detection YAML Converter

Converts Splunk saved searches into contentctl or custom YAML, individually or as a ZIP. Install the tar.gz through Manage Apps, then open Detection YAML Converter. ES isn't required. It reads saved searches using your permissions; it doesn't run or change them.

This is a work in progress. Check the output in your own content repository before using it. If the app isn't quite working for your setup, adapting `helper_scripts/savedsearchdotconftoyaml.py` might be easier. It's a separate script you can copy out and run locally, with no Splunk or pip dependencies:

```bash
python3 savedsearchdotconftoyaml.py savedsearches.conf --out converted
```

Add `--placeholders` for blank macro and lookup/tuning files referenced in the SPL. Comments and descriptions are ignored. Settings and an edit hook are at the top of the script. Use a new output folder each time; it won't overwrite your files.

The helper uses flat scheduling fields from the original migration script. You may need to edit contentctl's models/templates to read a cron from each detection instead of using deployment scheduling. The app's classic profiles use inline deployments; custom YAML lets you change the mapping.

MIT licence. Required dependency notices are in `README/`. Cloud approval is subject to Splunk's hosted validation.
