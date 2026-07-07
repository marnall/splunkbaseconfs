Splunk Add-on for MT940 Formatting
Copyright (C) 2023 Splunk Inc. All Rights Reserved.

Installation instructions:
1. Install Add-on on Search Heads. 
2. Specify sourcetype at ingestion as MT940_v1. 
3. Search normally.

This version of the add-on supports European and US SWIFT formats. It can parse multiple MT940 messages in a single file or one per file.

If the parsing is not working - check that your sourcetype definition is set to "MT940_v1"
