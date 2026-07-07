# Observatory Add-on For Splunk

This app adds a modular input which uses Mozilla's Observatory to scan your websites for security issues.

### Sourcetype

Data from this input will go into the "observatory" sourcetype. 

### Installation

1. Install TA-observatory.
2. Create an "Observatory" input for each site you'd like to scan. If you'd like to use an index besides the default index, make sure to set one in the "more settings" section.