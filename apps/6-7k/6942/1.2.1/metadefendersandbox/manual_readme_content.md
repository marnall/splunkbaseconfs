[comment]: # " File: README.md"
[comment]: # "  Copyright (c) OPSWAT, 2024"
[comment]: # "Licensed under the Apache License, Version 2.0 (the 'License');"
[comment]: # "you may not use this file except in compliance with the License."
[comment]: # "You may obtain a copy of the License at"
[comment]: # "    http://www.apache.org/licenses/LICENSE-2.0"
[comment]: # "Unless required by applicable law or agreed to in writing, software distributed under"
[comment]: # "the License is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,"
[comment]: # "either express or implied. See the License for the specific language governing permissions"
[comment]: # "and limitations under the License."
[comment]: # ""
# MetaDefender Sandbox App

MetaDefender Sandbox (previously known as OPSWAT Filescan Sandbox) is a unique adaptive threat analysis technology, enabling zero-day malware detection and comprehensive Indicator of Compromise (IOC) extraction.

## What does this App do?

This app includes the MetaDefender Sandbox basic integration that does the following:

**Detonate file**  
Retrieve detonation analysis results for file

**Detonate URL**  
Retrieve detonation analysis results for URL

**Search report**  
Search for scan reports on MetaDefender Sandbox using parameters specified in the 'query' field.

**File reputation**  
Get the fast reputation for one given hash (returns the last 10 MetaDefender Sandbox reports)

**IP/Domain/URL reputation**  
Get the fast reputation for one given IOC. E.g.: IP, Domain or URL (returns the last 10 MetaDefender Sandbox reports)

This app requires a correctly set up MetaDefender Sandbox API key to use.

## Port Information

The app uses HTTPS protocol if it uses the MetaDefender Sandbox community server (default). You can deviate from this if you want to use your own, on-prem MetaDefender Sandbox server. Below are
the default ports used by Splunk SOAR.

|         Service Name | Transport Protocol | Port |
|----------------------|--------------------|------|
|         https        | tcp                | 443  |
