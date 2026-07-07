# HurricaneLabsContentPlus

Hurricane Labs Content+ is an app used to deploy security content from Hurricane Lab's content repository. It includes automated dependency checking to ensure that only compatible content is deployed. 

Full docs are here: https://hurricane-labs-content-docs.readthedocs.io/en/latest/

## Release History

### 1.3.6
- Handle UnicodeError so it throws an error instead of crashing

### 1.3.5

- Packaging-forking bugfix

### 1.3.4

- Minor Splunk app vetting fixes
- Fix 'Date deployed' on Content Overview dashboard incorrectly displaying the date a package was updated.

### 1.3.3

- Fixes an issue where searches with newlines are not deployed properly.

### 1.3.2

- Generate the "sourcetypes by index" metric in a more efficient way to avoid search timeouts

### 1.3.1

- Fix two typos in savedsearches.conf

### 1.3.0

- New package-forking funcionality
- Search functionality for Content Overview as well as additional details
- Bugfixes for prereq_packages, duplicate-stanza checking
- Performance improvements to Content Overview dashboard
- Metrics 

### 1.2.5
- Fixes a bug where index search constraints prevented compatibility checks from working properly.
- Fixes a bug where large amounts of sources/sourcetypes prevented compatibility checks from working properly.
- Updates Splunklib to latest version. 

### 1.2.4
- Changes scope of reload endpoints to just the HLCP app. This was causing errors in some cloud stacks when scoped globally.

### 1.2.3
- Fixes an accidentally-modified file from Splunklib so that hashes properly match.

### 1.2.2
- Fixes a bug which was causing local modifications of macros to be overwritten.

### 1.2.1 
- Fixes vizualization bug in the Content Overview dashboard.

### 1.2.0
- Completely reworked vizualizations using Splunk UI Toolkit
- `hlcpquota` command for checking an API key's quota.
- Content-installation search split into two: one for updates and critical packages, one for monthly content. 

### 1.1.0 

- Implements support for "AND" and "OR" in data prerequisites.
- Adds a timeout to post-deploy searches. . Timeout is 2 minutes and an error is logged when it happens. Package still deploys otherwise.
- Changes the auto-install search to let through any already-installed package. That way even if a package was installed manually, it will stay updated.
- Fixed a bug preventing views from being installed.
- Fixed a bug where whitespace in an API key would break the app.
