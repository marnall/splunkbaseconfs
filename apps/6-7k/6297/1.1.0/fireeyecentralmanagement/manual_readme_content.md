[comment]: # " File: README.md"
[comment]: # "  Copyright (c) 2022-2024 Splunk Inc."
[comment]: # "  Licensed under the Apache License, Version 2.0 (the 'License');"
[comment]: # "  you may not use this file except in compliance with the License."
[comment]: # "  You may obtain a copy of the License at"
[comment]: # "      http://www.apache.org/licenses/LICENSE-2.0"
[comment]: # "  Unless required by applicable law or agreed to in writing, software distributed under"
[comment]: # "  the License is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,"
[comment]: # "  either express or implied. See the License for the specific language governing permissions"
[comment]: # "  and limitations under the License."
[comment]: # ""
### On-Poll Configuration

For the on-poll product filter asset configuration, optionally provide a comma separated list of
products to include during polling. If not set, all alerts are ingested. Possible Values:

-   EX
-   NX
-   AX

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the FireEye Central Management server.
Below are the default ports used by the Splunk SOAR Connector.

| SERVICE NAME | TRANSPORT PROTOCOL | PORT |
|--------------|--------------------|------|
| http         | tcp                | 80   |
| https        | tcp                | 443  |
