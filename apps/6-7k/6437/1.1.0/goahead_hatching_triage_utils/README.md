
# Hatching Triage App for Splunk by GoAhead 

## Introduction

Hatching Triage App is an API wrapper tool as the report utility for Hatching Triage sandbox's instance public instance('tria.ge') or private instance('private.tria.ge').
Please visit their official site ("https://hatching.io/triage/") for what Hatching Triage is.
**This app doesn't include report options to download the sample files, dropped files, dumped memory, raw pcap and pcapng payloads. This app downloads just report logs from triage cloud instance**

## Installation

The API Key is needed to utilize this App.
1. Install this App package
2. Create the APK Key on your given Triage sandbox dashboard. If you use private instance, "private.triage.ge" is the fqdn, otherwise you can use the public instance which the fqdn is "tria.ge" at the present. Researcher role is needed to create APK Key on "tria.ge".
3. Set up the API Key on the App Setup Page. Please remember that both API Keys cannot be set at the same time thus you have to switch if you change it to the certain API Key to match the instance. 
4. Restarting splunk search head instance may be possibly needed for activating these custom search commands. 
5. App Install user needs "admin_all_objects" privilege and Splunk search users need "list_storage_passwords" privilege in order to utilize "Secret storage".

## Usage

1. **triageindex**
    - GeneratingCommand to get sample index report via Triage Cloud API of "GET /samples"
    - Options
        - **instance** (required):        Choose "public" or "private" or "recordedfuture", "public" will access to *"https://api.tria.ge/v0/"* and "private" will access to *"https://private.tria.ge/api/v0/"*. "recordedfuture" will access to *"https://sandbox.recordedfuture.com/api/v0/"*
        - **subset**             :        (Optional) Choose "public" or "org" or "owned" following Triage Cloud API docs.
        - **limit**              :        Optional parameter following Triage Cloud API docs
        - **offset**             :        Optional parameter following Triage Cloud API docs
    - Output field name
        - ALL output names are the same to the API response fields.
    - Example  
        - ` | triageindex instance="public" subset="public" limit=10`

2. **triagesearch**
    - GeneratingCommand to search samples via Triage Cloud API of "GET /search"
    - Options
        - **instance** (required):        Choose "public" or "private" or "recordedfuture", "public" will access to *"https://api.tria.ge/v0/"* and "private" will access to *"https://private.tria.ge/api/v0/"*. "recordedfuture" will access to *"https://sandbox.recordedfuture.com/api/v0/"*
        - **query**    (required):        Search query with the spesific logic and search operators following Triage Cloud API docs.
        - **limit**              :        Optional parameter following Triage Cloud API docs
        - **offset**             :        Optional parameter following Triage Cloud API docs
    - Output field name
        - ALL output names are the same to the API response fields.
    - Example  
        - ` | triagesearch instance="public" query="family:emotet" limit=30`

3. **triagereport**
    - GeneratingCommand to get the sample report of your report option choice via Triage Cloud API 
    - Options
        - **instance** (required):        Choose "public" or "private" or "recordedfuture", "public" will access to *"https://api.tria.ge/v0/"* and "private" will access to *"https://private.tria.ge/api/v0/"*. "recordedfuture" will access to *"https://sandbox.recordedfuture.com/api/v0/"*
        - **report**   (required):        Report type following Triage Cloud API docs. "dynamic" means "report_triage.json" furthermore "ioc_extracted" and "proc_tree" are our custom options to filter to only extracted IOCs and create process tree on splunk statistics view.
        - **sampleID**           :        sampleID to get reports following Triage Cloud API docs.
        - **taskID**             :        Optional parameter following Triage Cloud API docs, which is needed when you select ["dynamic"|"proc_tree"|"onemon"|"pcap"|"pcapng" to report option. 
    - Output field name
        - Most of output names are the same to the API response fields. Custom field names are shown in errors or on "ioc_extracted" and "proc_tree" reports, however they are easy to understand.
    - Example
        - ` | triagereport instance="public" report="dynamic" sampleID="YYYYMMDD-cy7xkahgcr" taskID="behavioral1" `

4. **triageurlsubmit**
    - GeneratingCommand to submit "target_url" or "fetch sample from url" and "import sample from public triage" via Triage Cloud API of "POST /samples"
    - Options
        - **instance** (required):        Choose "public" or "private" or "recordedfuture", "public" will access to *"https://api.tria.ge/v0/"* and "private" will access to *"https://private.tria.ge/api/v0/"*. "recordedfuture" will access to *"https://sandbox.recordedfuture.com/api/v0/"*
        - **kind**             :        "import", "fetch", "url" following Triage Cloud API docs
        - **url**              :        target_url following Triage Cloud API docs
        - **profile_name**     :        Optional parameter profile_name following Triage Cloud API docs
    - Output field name
        - ALL output names are the same to the API response fields.
    - Example  
        - ` | triageurlsubmit instance="public" kind="url" url="http://example.org/"`


Command usages are also described in searchbnf.conf, thus you can see it on search window by writing the command name on. 

Some errors are dumped to the output error field and the command exception will be dumped in search.log or %SPLUNK_HOME%/var/log/goahead_hatching_triage_utils_app.log if it happens.


## Official Triage Cloud API docs

- [API docs in public instance](https://tria.ge/docs/cloud-api/conventions/)

- [API docs in private instance](https://private.tria.ge/docs/cloud-api/conventions/)


## Attention to begin to use this app

Following this app report options are beta versions. Unfortunately they are not stable yet and may happens some error by samples.

- *proc_tree*

- *ioc_extracted*

- *magic*

In addition, **pcap** and **pcapng** report options do NOT download the files and are just for showing the cURL command line with masked APIKey to download them in your safe isolated environment.

**This app doesn't include report options to download the sample files, dropped files, dumped memory, raw pcap and pcapng payloads. This app downloads just report logs from triage cloud instance**


## Included 3rd party's additional import modules

+ for "onemon" report's ndjson response

[requests-2.27.1](https://pypi.org/project/requests/)

[ndjson-0.3.1](https://pypi.org/project/ndjson/)


## Support

Splunk 9.x


## License

[GPLv3](https://www.gnu.org/licenses/gpl-3.0.en.html)


## Special Thanks

[Hatching International B.V.](https://hatching.io)

Hatching has already provided Triage App for Splunk Phantom by themselves.

Their official blog (https://hatching.io/blog/triage-splunk-xsoar/) is useful when you are in [Splunk Phantom](https://www.splunk.com/en_us/software/splunk-security-orchestration-and-automation.html).


## Copyright

Copyright 2025 GoAhead Inc.
