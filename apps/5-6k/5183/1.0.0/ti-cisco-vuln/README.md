# Cisco PSIRT openVuln API Add-on for Splunk

_(Last Updated: 20200812)_

## Overview

This Add-on is a Custom Modular Input for ingesting data from the [**Cisco PSIRT openVuln API**](https://developer.cisco.com/psirt/) into Splunk.

This API allows you to programmatically obtain the latest Cisco Vulnerability Security Advisories. These advisories provide invaluable information such as CVSS Scores, CVEs, etc. Vital information for assessing risk to products within your own infrastructure.

The Add-on provides CIM mapping for the Vulnerabilities Data Model.

## Cisco openVuln API Credentials

To use the [**Cisco PSIRT openVuln API**](https://developer.cisco.com/psirt/), you will need credentials, in the form of a **client_id** and **client_secret**.

These can be obtained from the [**Cisco API Console**](https://apiconsole.cisco.com/).

The high-level steps are:

1. Log in to the [**Cisco API Console**](https://apiconsole.cisco.com/)
2. Click on **My Apps & Keys**
3. Click **Register a New App**
4. Give it a name (so something like, _SplunkAPIAccess_)
5. Under the **OAuth2.0 Credentials** section, tick **Client Credentials** (this bit is very important, as the Add-on uses this flavour of Auth)
6. Under the **Select APIs** section, scroll down and tick **Cisco PSIRT openVuln API**
7. At the bottom of the page, you'll need to agree to the _Terms of Service_ and finally click the **Register** button

If all goes well, you should be able to go back to the **My Apps & Keys** section in the Console, to see you Credentials.

It should look something like this:

| **API** | **KEY** | **CLIENT SECRET** | **STATUS** |
| :---    | :---    | :---              | :---       |
| Cisco PSIRT openVuln API | hnkwga6jaxcjcesdkwyf437j | 8Q4smpXPGZswSVqxEpTjECcm | active |

Detailed steps on how to obtain credentials can be found in the [**Cisco API Console User Guide (PDF)**](https://apiconsole.cisco.com/files/APIx_Platform_User_Guide.pdf). If you already have a **_Cisco CCO ID_**, you should be able to skip to Chapter 3 in the guide and go from there.


## Splunk Installation

Ideally, the Add-on should be installed on a Heavy Forwarder (for ingestion) and Search Heads (for search time extractions).

You can install directly onto an Indexer(s), but this is not recommended.

The Add-on does not support installation via the Deployment Server. This is because after configuration (I.e. Creating and input), the `local/inputs.conf` would be overwritten if you pushed a new version from the Deployment Server. Well, that's not entirely true... You can work around this if you know how to use the `excludeFromUpdate` directive in [**serverclass.conf**](https://docs.splunk.com/Documentation/Splunk/latest/Admin/Serverclassconf), but that's beyond the scope of this document. 😉


## Configuration

### Configuration - Input

Once you have **API Credentials** the **Add-on** is installed, you simply need to create a new **Input** from the Splunk **Settings/Data inputs** menu.

1. Select the **Cisco PSIRT openVuln API Add-on for Splunk** from the App menu, to make sure you're working in the app context
2. In the **Local inputs** section, look for **Cisco PSIRT openVuln API - Advisories**
2. Click the **+ Add new** button
3. Enter the required information, which is:
    * **name**: The name of your input (I'd recommend no spaces)
    * **Auth URL Endpoint**: This should be pre-populated with the default of `https://cloudsso.cisco.com/as/token.oauth2`
    * **Auth Client ID**: This is the **KEY** from your app in the **Cisco API Console**
    * **Auth Client Secret**: This is the **CLIENT SECRET** from your app in the **Cisco API Console**
    * **Advisories Base URL**: This should be pre-populated with the default of `https://api.cisco.com/security/advisories`
    * **Advisories Window (Days)**: This is have far back (in days) the input will request Advisories for. A value of 1 would be, _"Look back 1 day, plus today"_, so would be Advisories first published or updated yesterday and today. I'd recommend a value of 6
    * **Advisories Plain Text Summary**: If set to True (True, true or 1) a plain text version of the HTML Summary field will be created. (Default is: false)
    * **Advisories Type (EXPERIMENTAL)**: This will be used change the type of advisories. Between all, ios, nxos, etc. It is NOT implemented yet, so leave as default. (Default is: all)
    * **Debug Logging**: You can enable debug logging (which goes to Splunk `_internal` index) by checking the box. But **ONLY** do this for development or testing, as the resulting logs **WILL** include the Auth Client ID and the Auth Client Secret. (Default is: false)
4. If you then tick the **More settings** box, you can enter:
    * **Interval**: This is either the number of seconds to wait before running the command again, or a valid cron schedule. I'd recommend a cron schedule of once a day
    * **Source type**: You can set your own **sourcetype** here, or use the default of `cisco:vuln:advisories`. I'd strongly recommend leaving this as the default, otherwise most of the Splunk \*.conf elements will not work
    * **Host**: By default this the name of the **Splunk server** where the **Add-on** is installed
    * **Index**: Select an **index** from the list to send events to. The items in the list depend on what **index** definitions exist on the Splunk instance where the **Add-on** is installed. The default is `main`
5. When you've finished entering all of the information, click **Next** at the top of the page


### Configuration - Indexes and Macros

The **Add-on** makes extensive use of **macros**. If you want to use a custom **index** for your event, you'll need to create a `local/macros.conf` in the **Add-on** and change the `definition` in the stanza:
```text
[cisco_advisory_indexes]
definition = index::main
```

Replacing `index::main` with `index::[your custom index name]`.


### Configuration - Limits

As the Cisco PSIRT openVuln Security Advisory as large events, you will likely need to adjust the `spath/extraction_cutoff` value in `limits.conf`.

The Splunk default for this is 5000 bytes. So for events which are larger than this, Search time field extraction will stop after the first 5000 bytes. ☹️

It is Splunk best practice (as per [**Splunk AppInspect**](https://dev.splunk.com/enterprise/docs/developapps/testvalidate/appinspect/appinspectreferencetopics/splunkappinspectcheck#Limitsconf-file-standards)) that a `limits.conf` is **not** included in the **Add-on**.

Always check with your Splunk Administrator first, but you should be able to a `local/limits.conf` file to the **Add-on** with the following:
```text
[spath]
extraction_cutoff = 100000
```

This is only required on Search Heads.


## Data

Below are some notes on the data returned by the **Cisco openVuln API**.

By default, the **Add-on** will create that following **sourcetypes**:

* **cisco:vuln:advisories**
  * These are the Security Advisories return by the Cisco PSIRT openVuln API

For each Security Advisory, there is additional (and valuable) information which is downloaded and ingested per advisory. Each advisory has a `cvrfUrl`, which points to a public XML document. The **Add-on** goes and grabs that data too, breaks it up (as it's way too long for a single event), and creates these addition **sourcetypes**:

* **cisco:vuln:advisories:cvrf:summary**
  * This is the high-level CVRF information
* **cisco:vuln:advisories:cvrf:note**
  * This is the detailed CVRF information, broken down into multiple events
* **cisco:vuln:advisories:cvrf:vuln**
  * This is additional vulnerability information, mainly detailing affected Product IDs
* **cisco:vuln:advisories:cvrf:product**
  * This is very useful Product ID to Product Name mappings

The `advisoryId` field from the `cisco:vuln:advisories` event is added to every `cisco:vuln:advisories:cvrf:*` event. This is gives you a key with which to correlate all the data together.

Detailed information about the **CVRF Data** can be found in the [`README/docs`](./README/docs) folder in the **Add-on**.

### Data - Security Advisory (Default Sourcetype: cisco:vuln:advisories)

This is an example of the **JSON** data returned from the API and ingested into Splunk:
```json
{
  "advisoryId":"cisco-sa-sdbufof-h5f5VSeL",
  "advisoryTitle":"Cisco SD-WAN Solution Software Buffer Overflow Vulnerability",
  "bugIDs":[
    "CSCvt11538"
  ],
  "cves":[
    "CVE-2020-3375"
  ],
  "cvrfUrl":"https://tools.cisco.com/security/center/contentxml/CiscoSecurityAdvisory/cisco-sa-sdbufof-h5f5VSeL/cvrf/cisco-sa-sdbufof-h5f5VSeL_cvrf.xml",
  "cvssBaseScore":"9.8",
  "cwe":[
    "CWE-119"
  ],
  "firstPublished":"2020-07-29T16:00:00",
  "hash":"eae592fdb8873e186a9c565ad53881477456bb2d9970b5860e3ccd3b5e54afa9",
  "inputIngestTime": "1596212402.197",
  "ipsSignatures":[
    "NA"
  ],
  "lastUpdated":"2020-07-30T17:13:13",
  "productNames":[
    "Cisco SD-WAN vManage ",
    "Cisco IOS XE SD-WAN Software ",
    "Cisco IOS XE SD-WAN Software 16.9 16.9.0",
    "Cisco IOS XE SD-WAN Software 16.9 16.9.1",
    "Cisco IOS XE SD-WAN Software 16.9 16.9.2",
    "Cisco IOS XE SD-WAN Software 16.9 16.9.3",
    "Cisco IOS XE SD-WAN Software 16.9 16.9.4",
    "Cisco IOS XE SD-WAN Software 16.10 16.10.0",
    "Cisco IOS XE SD-WAN Software 16.10 16.10.1",
    "Cisco IOS XE SD-WAN Software 16.10 16.10.2",
    "Cisco IOS XE SD-WAN Software 16.10 16.10.3",
    "Cisco IOS XE SD-WAN Software 16.10 16.10.3a",
    "Cisco IOS XE SD-WAN Software 16.10 16.10.3b",
    "Cisco IOS XE SD-WAN Software 16.10 16.10.4",
    "Cisco IOS XE SD-WAN Software 16.11 16.11.0",
    "Cisco IOS XE SD-WAN Software 16.11 16.11.1a",
    "Cisco IOS XE SD-WAN Software 16.12 16.12.0",
    "Cisco IOS XE SD-WAN Software 16.12 16.12.1b",
    "Cisco IOS XE SD-WAN Software 16.12 16.12.1d",
    "Cisco IOS XE SD-WAN Software 16.12 16.12.1e",
    "Cisco IOS XE SD-WAN Software 16.12 16.12.2r"
  ],
  "publicationUrl":"https://tools.cisco.com/security/center/content/CiscoSecurityAdvisory/cisco-sa-sdbufof-h5f5VSeL",
  "sir":"Critical",
  "summary":"\r\n\u003cp\u003eA vulnerability in Cisco\u0026nbsp;SD-WAN Solution Software could allow an unauthenticated, remote attacker to cause a buffer overflow on an affected device.\u003c/p\u003e\r\n\u003cp\u003eThe vulnerability is due to insufficient input validation. An attacker could exploit this vulnerability by sending crafted traffic to an affected device. A successful exploit could allow the attacker to gain access to information that they are not authorized to access, make changes to the system that they are not authorized to make, and execute commands on an affected system with privileges of the \u003cem\u003eroot\u003c/em\u003e user.\u003c/p\u003e\r\n\u003cp\u003eCisco has released software updates that address this vulnerability. There are no workarounds that address this vulnerability.\u003c/p\u003e\r\n\u003cp\u003eThis advisory is available at the following link:\u003cbr\u003e\u003ca href=\"https://tools.cisco.com/security/center/content/CiscoSecurityAdvisory/cisco-sa-sdbufof-h5f5VSeL\" target=\"_blank\" rel=\"noopener\"\u003ehttps://tools.cisco.com/security/center/content/CiscoSecurityAdvisory/cisco-sa-sdbufof-h5f5VSeL\u003c/a\u003e\u003c/p\u003e\r\n"
}
```

### Data - Security Advisory - Interesting Fields / CIM Mappings

Some of the key fields to look out for are:

* **firstPublished**: When the Advisory was first created (not ingested or indexed - see below)
* **lastUpdated**: When the Advisory as last updated (will be the same as `firstPublished` if not updates since the original)
    * This is used as the Event `_time` in Splunk
* **cves**: CVEs for the Advisory
    * Mapped to `cve` as per the Splunk Vulnerability Common Information Model
* **cvssBaseScore**: CVSS for the Advisory
    * Mapped to `cvss` as per the Splunk Vulnerability Common Information Model
* **publicationUrl**: The public URL for viewing the Advisory
    * Mapped to `url` as per the Splunk Vulnerability Common Information Model
* **inputIngestTime**: This is not part of the original Advisory, but added by the **Add-on** during the input process
    * This is to help assist in any troubleshooting as `_time` and `_indextime` don't actually tell you _when_ the _input_ ran
    * Mapped to `ingesttime` (epoch) and `ingesttime_nice` (friendly)
* **summary**: This is the detail of the advisory in HTML, exactly as returned from the API
    * As the HTML formatting is not create for reading, the **Add-on** has an option to create a **plain text** version on ingestion
    * The is enabled when you create the input (see the _Configuration - Input_ section above)

### Data - Duplication

As Advisories are revised, it is normal to expect events in Splunk with the same `advisoryId`. When working with the data, you want to make sure that you're searching for the _latest_ `advisoryId`.

The **Add-on** contains the **macro** ``cisco_advisory_latest()`` as a quick way return the _latest_ advisory.

An example would be:
```text
`cisco_advisory_latest(cisco-sa-sdbufof-h5f5VSeL)`
```

The macro is effectively doing:
```text
`cisco_advisory_indexes` `cisco_advisory_sources` `cisco_advisory_sourcetypes` advisoryId::cisco-sa-sdbufof-h5f5VSeL
| sort - _time, ingesttime
| head 1
```

**NOTE**: The **macro** references the ``cisco_advisory_indexes`` **macro**. If you're using a different **index**, then you simply need to update the ``cisco_advisory_indexes`` macros with your specific **index**.

When working all of the advisories, such as if you wanted a table, then you need to have a strategy to find the _latest_ of every advisory.

The SPL command `eventstats` is your friend here and can be used identify the _latest_ of each advisory. This is used in the **macro** ``cisco_advisory_table``.

This **macros** does the follow:
```text
`cisco_advisory_indexes` `cisco_advisory_sources` `cisco_advisory_sourcetypes`
| stats values(*) as *, latest(_time) as _time by hash, ingesttime
| eventstats latest(hash) as l_hash, latest(ingesttime) as l_ingesttime by advisoryId
| where (hash == l_hash) AND (ingesttime == l_ingesttime)
| table ingesttime, _time, lastUpdated, firstPublished, advisoryId, advisoryTitle, severity, cvss, ingesttime_nice
| sort 0 - _time, ingesttime
| fields - _time, ingesttime
```

* `eventstats` is used to identify the `latest()` **hash** and **ingesttime**, by **advisoryId**
* Then `where` is used to simply keep the advisories which have these _latest_ fields/value pairs

You could use `dedup advisoryId`, but `dedup` is often quite an expensive operation in Splunk if using it across a large dataset.

I'm sure that there are lots of other approaches (this is the beauty of **Splunk**!), so find a way which works best for you.


## Troubleshooting

### Troubleshooting - Logs

The **Add-on** uses **Splunk's** standard method of logging to `$SPLUNK_HOME/var/log/splunk/splunkd.log` on the instance it is installed on.

This means that you can search for the **Add-on's** logs in Splunk itself. For example:
```text
index=_internal sourcetype=splunkd source=*splunkd.log ExecProcessor ti-cisco-vuln
```

For each input run, look for messages between:
```text
The TI Cisco Vuln Input has started
```

And:
```text
The TI Cisco Vuln Input has ended
```

On a normal (successful) run, look for this message:
```text
Advisory Counts: firstpublished=11, lastpublished=14, final=14
```

The information is:

* **firstpublished**
    * Number of advisories after querying the `/all/firstpublished` endpoint
* **lastpublished**
    * Number of advisories after querying the `/all/lastpublished` endpoint and de-duplicating against first set of results
* **final**
    * Number of advisories after de-duplicating against the _state_ file, which contains hashes of already ingested advisories

(**NOTE**: It's on the list to add some better logging info at more stages.)

It's very normal to see results like:
```text
firstpublished=11, lastpublished=14, final=0
```

Which would indicate that there are no new or updated advisories to ingest.

---

## Developer Notes

This section has some detail which may be of interest to Developers, but isn't really needed for day to day use.

### Modular Input - XML Configuration Stanza

When Splunk runs the modular input binary, it sends the configuration stanza as a block of **XML** on stdin. The binary need to be wating to accept this, then process it for all of the required config elements.

An example would be:
```xml
<input>
  <server_host>myHost</server_host>
  <server_uri>https://127.0.0.1:8089</server_uri>
  <session_key>123102983109283019283</session_key>
  <checkpoint_dir>/opt/splunk/var/lib/splunk/modinputs/ti-cisco-vuln</checkpoint_dir>
  <configuration>
    <stanza name="ti-cisco-vuln:advisories://input_name">
        <param name="auth_url">https://cloudsso.cisco.com/as/token.oauth2</param>
        <param name="auth_client_id">7srxxtpfxt3p8s7r58tdjmqv</param>
        <param name="auth_client_secret">GmvwxWA4kTVmqwpR83g5na3W</param>
        <param name="advisories_url">https://api.cisco.com/security/advisories</param>
        <param name="advisories_window">6</param>
        <param name="advisories_summary_plain">1</param>
        <param name="advisories_type">all</param>
        <param name="disabled">0</param>
    </stanza>
  </configuration>
</input>
```

For more information on how this works, take a look at the docs here: <https://docs.splunk.com/Documentation/Splunk/latest/AdvancedDev/ModInputsScripts#Read_XML_configuration_from_splunkd>


### Modular Input - State File

To avoid duplicate data, the **Add-on** uses a _State File_ to store information regarding which advisories have already been ingested.

Each line of the _State File_ is a comma separated list of:

* **firstPulished**: Taken from the Advisory
* **lastUpdated**: Taken from the Advisory
* **advisoryId**: Taken from the Advisory
* **hash**: A sha256 hash **of the original Advisory**

Each new Advisory from the API is hashed and compared to this _State File_. If it already exists, it is dropped. If it doesn't exist, it is ingested by Splunk and it's hash is appended to the file.

You would think that you could just hash the `advisoryId` and the `lastUpdated` fields. However, during testing I often saw Advisories which had been changed (usually some minor formatting in `summary`), **without** the `lastUpdated` field being change.

This means that only way to get 100% guarantee of uniqueness is to hash the whole **JSON** payload of each Advisory.

**IMPORTANT**: This _State File_ is stored on the **Splunk** instance running the **Add-on input**. If you set-up the input on a new / different instance, the it's **very likely** that you will get some duplicate data.

With some careful planning you could work around this by moving the _State File_ to the new instance. You'll find the file in `$SPLUNK_DB/modinputs/ti-cisco-vuln/_ti-cisco-vuln-state`. 

### Bugs

These are things I need to fix!

* **DONE** - Add time parsing of `lastUpdated` to code
* **DONE** - State file truncation
    * Technically the state file will grow indefinitely
    * This feels like a bad thing
    * Need some maintenance code to truncate the thing (based on size or age of hash)
* Go Test Code
    * I need to write the `ti-cisco-vuln_testing.go` code
    * These would be basic unit tests, which can then be run as part of the automated build

### Future Features

These are things which would be nice to add:

* Add an `ingestTime` key/value pair to each Advisory
    * It's always sucks having to figure out _when_ an event was _actually_ ingested
* `firstpublished` vs `lastpublished` research
    * I'm still not 100% clear if we need to grab both
    * May need to have the process running for multiple days to see what the behaviour is
* Timing / Summary log line
    * How long the whole ingest took, how many advisories added, etc
* **DONE** - Text version of the `summary` field
    * Look at parsing the `summary` field into non-HTLM text
    * This may be a simple library to use: <https://github.com/k3a/html2text>

---

## Trademarks

For the avoidance of doubt, the creator of this **Add-on** is in no way affiliated to Cisco Systems, Inc. 

All of Cisco's tradmarks can be found here: <https://www.cisco.com/c/en/us/about/legal/trademarks.html>

As per Cisco's [**Tradmark Policy**](https://www.cisco.com/c/dam/en_us/about/ac50/ac47/downloads/logo/trademark.pdf):

> _"Cisco acknowledges that the use of Cisco trademarks, excluding any Cisco logos,_
> _may be necessary to refer to Cisco’s products or services or to describe the subject_
> _matter of some materials, products, and/or programs. All such use must be accurate_
> _and descriptive in nature and comply with this Policy and these Guidelines."_

This **Add-on** uses the word _Cisco_ to refer to the [**Cisco PSIRT openVuln API**](https://developer.cisco.com/psirt/). The **Cisco PSIRT openVuln API** is licensed under the MIT License (see below).

---

## License (MIT License)

**Copyright (c) 2020 Tiny Input Limited**

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Additional Code:

* [**html2text**](https://github.com/k3a/html2text) Package
    * Copyright (c) 2017 Mario K3A Hros (www.k3a.me)
    * Licensed under the MIT Licence (see GitHub repo for full license)

Cisco openVuln API License:

* [**Cisco openVuln API License**](https://github.com/CiscoPSIRT/openVulnAPI/blob/master/LICENSE.md)
    * Copyright (c) 2018, Cisco Systems, Inc.
    * Licensed under the MIT Licence (see GitHub repo for full license)

---

## Appendix

### External Links

These are some useful links:

* Cisco PSIRT openVuln API Introduction
    * <https://developer.cisco.com/psirt/>
* Cisco PSIRT openVuln API Docs
    * <https://developer.cisco.com/docs/psirt/>
* Cisco API Console
    * <https://apiconsole.cisco.com/>

More specific ones are:

* Cisco API Console User Guide (PDF)
    * <https://apiconsole.cisco.com/files/APIx_Platform_User_Guide.pdf>
* Cisco OAuth 2.0 Token Developer Guide (PDF)
    * <https://github.com/api-at-cisco/Images/blob/master/Token_Access.pdf?raw=true>
