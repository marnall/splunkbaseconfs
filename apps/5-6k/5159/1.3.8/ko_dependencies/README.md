# Splunk knowledge objects dependencies
A splunk app for app developers to search and investigate dependencies between knowledge objects.

The app lists all dependencies between dashboards (views), prebuilt panels, saved searches, search macro's, lookup definitions and lookup tables. These are visualised in a tree-like manner. Dependencies can be viewed both upstream and downstream. Supported also are datasource dependencies, indicating that a KO uses data originating from another.

Also included are:
* an overview of broken references that developers may want to fix
* an overview of KO's without dependencies. Especially for KO's other than dashboards and saved searches this suggests they are unused and cleanup is in order.

The app is able to detect almost all KO references, but there are a few exceptions. Currently unsupported are links to reports, deprecated (as of 7.x) simple xml syntax and dynamic references using variable substitution.

## Installation
Install the Splunk app on your searchhead as normal. The supported Splunk enterprise versions are 7 and 8.

The app makes use of the Sankey Diagram custom visualisation add-on, which should also be installed: https://splunkbase.splunk.com/app/3112/

One extra requirement of the app is it requires liberal limits on regular expression processing. If these are not in place large knowledge objects, such as big dashboards, will not be fully parsed for dependencies. The following limits.conf settings should be sufficient for most environments:
```
[rex]
match_limit = 100000
depth_limit = 10000
```

Note that the app uses scheduled saved searches that need to run before any content will be visible. After installation, you need to wait until upto 30 minutes past the next top of the hour before the app will show content.

## Support
This app is provided as-is with limited developer support.
The project on Github: https://github.com/jthunnissen/splunk_ko_dependencies.
Developer contact: thatswhydata@gmail.com