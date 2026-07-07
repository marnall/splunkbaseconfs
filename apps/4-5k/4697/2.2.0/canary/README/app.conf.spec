
#These two stanzas are part of a convention we use in Sideview apps,  where a
# checklist.conf stanza can check whether:
# 1) the current Splunk version matches the required Splunk version we ship
# in the dependency:splunk key in app.conf
# 2) OR whether the current Canary version matches the required version we
# specify in the dependency;app:canary key

[dependency:splunk]
requiredVersion = <version string>

[dependency:app:<appname>]
requiredVersion = <version string>

# Deleted in late 2025 - review me
#[sideview_imports]
#importJavascriptFrom = <comma-separated list of apps>