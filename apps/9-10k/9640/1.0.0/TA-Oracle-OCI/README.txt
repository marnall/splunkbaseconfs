================================================================
TA-Oracle-OCI
Technology Add-on for Oracle Cloud Infrastructure (HEC push + API key pull)
Version: 1.0.0
Author: Helmi | Nexagate Sdn Bhd.
================================================================

INDEPENDENT, THIRD-PARTY ADD-ON
--------------------------------
This add-on is not affiliated with, endorsed by, certified by, or
supported by Oracle Corporation or Splunk Inc. "Oracle", "Oracle Cloud
Infrastructure", "OCI", "Splunk", and associated marks are trademarks
of their respective owners, used here only to describe compatibility.
Support is provided by the author (see SUPPORT below), not by Oracle
or Splunk.

OVERVIEW
--------
This add-on ingests Oracle Cloud Infrastructure (OCI) logs into Splunk
and provides field extractions, sourcetypes, and Common Information
Model (CIM) tagging for them.

It replaces the archived "Splunk Addon for OCI" (Splunkbase app 5222)
and "Splunk Cloud Addon for OCI" (app 7021), both capped at Splunk
platform 9.2 because their bundled OCI SDK binaries were compiled
against Python 3.7. This add-on contains no compiled binaries, so it
is not tied to Splunk's embedded Python version and stays compatible
across future platform upgrades without a rebuild.

Supported Splunk platform (declared range): Enterprise 9.4.0 - 10.4.0,
and Splunk Cloud, based on this add-on having no compiled Python
binaries and no hardcoded interpreter version.

Actually verified so far: Splunk Enterprise 10.2.7 only, Python 3.13,
on-prem/standalone. The rest of the declared range is a reasonable
technical claim, not a tested one -- if you deploy to a different
platform version, treat it as unverified until confirmed there too.

TWO WAYS TO GET DATA IN (pick one)
-----------------------------------
1. Push (HTTP Event Collector)
   An OCI Function posts events to Splunk HEC. No OCI API credentials
   are stored in Splunk. Requires standing up OCI Functions and a
   Service Connector Hub on the OCI side. Supports OCI Logging,
   Streaming, Alarms, and Notifications sources.

2. Pull (native modular input, API key auth)
   bin/oci_stream.py polls an OCI Stream directly using the same
   Tenancy/User OCID, Fingerprint, and private key .pem fields the
   original archived add-on (5222) used. Runs on a Splunk heavy
   forwarder. Supports OCI Streaming/Logging sources only (not
   Alarms/Notifications).

On Splunk Cloud, the pull method's one dependency (the `oci` Python
SDK) has compiled C extensions that cannot be installed on the
Cloud-managed multi-tenant tier. Use a self-managed, on-prem or
in-VPC heavy forwarder for the pull method on Cloud, or use the push
method instead, which has no such restriction.

PACKAGE CONTENTS
-----------------
  app.manifest              app metadata, dependencies
  README.txt                this file
  README.md                 full setup guide with copy-pasteable
                             commands, troubleshooting, and CIM
                             extension notes
  README/
    inputs.conf.spec        parameters for the oci_stream modular input
    props.conf.spec         sourcetypes this app ships
    eventtypes.conf.spec    eventtypes this app ships
    tags.conf.spec          CIM tag assignments this app ships
  bin/
    oci_stream.py           pull-method modular input implementation
    requirements.txt        Python dependency (the `oci` SDK)
  default/
    app.conf                app metadata
    inputs.conf              python.version/python.required declaration
                             only -- no input stanzas are shipped
    props.conf               sourcetype definitions
    eventtypes.conf          event categorization
    tags.conf                CIM tag assignments
    data/ui/nav/             app navigation (opens to the Inputs tab)
    data/ui/views/           in-app Inputs landing page
    data/ui/manager/         customized create/edit form for the
                             oci_stream modular input
  metadata/
    default.meta             sharing and permissions
  static/
    appIcon.png / appIcon_2x.png / appIconAlt.png / appIconAlt_2x.png
                             app icons for Splunkbase and Splunk Web
  oci-function/
    func.py, func.yaml, requirements.txt
                             companion code for the push method --
                             deployed separately to OCI Functions, not
                             installed in Splunk

CONFIGURATION
-------------
No setup wizard is shipped in this package (Splunk Cloud vetting does
not permit an app-provided setup.xml screen). Configure inputs from
inside the app itself: install this add-on, open it from the Splunk
Web app switcher, and use the Inputs tab, or go to Settings > Data
Inputs > OCI Stream (API Key Pull) directly.

Full step-by-step instructions, including the required `oci` SDK
install command, private key placement, and HEC/ACS token setup, are
in README.md.

SUPPORT
-------
Author: Helmi | Nexagate Sdn Bhd.
For issues, consult README.md's troubleshooting notes first, then
contact the author through the Splunkbase listing page.

CHANGE HISTORY
--------------
1.0.0  Initial release.
