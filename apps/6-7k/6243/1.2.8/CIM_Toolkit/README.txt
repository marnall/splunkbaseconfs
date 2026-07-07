ReadMe
CIM Toolkit 1.2.8

Copyright (C) 2020-2023 Splunxter, Inc. All rights reserved.

* For Support contact Gregg Woodcock: Woodcock@Splunxter.com

# This app & the slide deck referenced below were developed independantly, but
# there is a great deal of common concepts & overlap so it is a pefect primer:
# https://foren6.files.wordpress.com/2020/12/splunk-es-correlation-searches-best-practices-v1.0-rev2.pdf

# This app contains/creates:
# 1: 32 Macros
# 2: 6 Correlation Searches (all disabled)
# 3: 1 UI Navigation
# 4: 8 Workflow Actions
# 5: 1 Lookup definition
# 6: 1 Lookup file (not installed but created/deleted by correlation search)
# 7: 2 Eventtypes (repair for 'Splunk_SA_CIM')
# 8: Some other work-in-progress, not-done-yet stuff (props/transforms)


# So:
# 1: Install app on Search Head.
# 2: If deployed w/ Deployment Server, use "restartSplunkd=true".
# 3: Tune and Enable the Schedule Search Content.
# 4: PROFIT!

### Prerequisites

The pre-requisites for the add-on are as follows;

```
Search Head(s): version 8.2 or greater (using "json_array_to_mv" function)
Search Head(s): Splunk Common Information Model (Splunk_SA_CIM), any version
```

### Installing & Deploying the App

Installation instructions are as follows;
1) Ensure that your Search Head has "Splunk_SA_CIM" installed and
2) Some CIM datamodels are accelerated.
3) Deploy/Install "CIM_Toolkit" (this) app.
4) Configure each of the "*_SETTING_*" macros.
5) Test, tune, then enable the Schedule Saved Searches (installed with 'disabled=1')

```
Splunk Indexers:
DO NOT DEPLOY TO INDEXERS
```

### Testing & Troubleshooting

Any schedule searches that you enable (and tune) will generate 3 things:
1: A "Triggered Alert".
2: An "ES" notable.
3: An "Alert Manager Enterprise" event.

If the alert suggests that you "shrink" your macro, BEWARE!  It may be that:
1: You have very sparsely/randomly-generated events. If so, to get accuracy,
you will need to widen the TimPeicker for the search from the default value of
"Last 7 days".
2: If you have had a long-ago relocation of data from one index/sourcetype
to another, and the older location of the data is still within the
acceleration window of the datamodel, and it needs to continue to be included,
you will have to hardcode this into the SPL of the search until it ages out.
3: Perhaps it is correct!

If the CIM app (Splunk_SA_CIM) isn't installed, several searches will generate errors.

In the GUI's search window you will see these errors:
* The following error(s) and caution(s) occurred while the search ran. Therefore, search results might be incomplete.
* Unexpected status for to fetch REST endpoint uri=https://<YOUR_HOST_HERE>:<YOUR_PORT_HERE>/servicesNS/-/Splunk_SA_CIM/data/models?count=0 from server=https://<YOUR_HOST_HERE>:<YOUR_PORT_HERE> - Not Found
* [subsearch]: Unexpected status for to fetch REST endpoint uri=https://<YOUR_HOST_HERE>:<YOUR_PORT_HERE>/servicesNS/-/Splunk_SA_CIM/configs/conf-macros?count=0 from server=https://<YOUR_HOST_HERE>:<YOUR_PORT_HERE> - Not Found
* [subsearch]: Failed to fetch REST endpoint uri=https://<YOUR_HOST_HERE>:<YOUR_PORT_HERE>/servicesNS/-/Splunk_SA_CIM/configs/conf-macros?count=0 from server https://<YOUR_HOST_HERE>:<YOUR_PORT_HERE>. Check that the URI path provided exists in the REST API. Learn More 
* [subsearch]: The REST request on the endpoint URI /servicesNS/-/Splunk_SA_CIM/configs/conf-macros?count=0 returned HTTP 'status not OK': code=404, Not Found.

In the job inspector you will see these errors:
* No matching fields exist.
* [subsearch]: No matching fields exist.
* Unexpected status for to fetch REST endpoint uri=https://<YOUR_HOST_HERE>:<YOUR_PORT_HERE>/servicesNS/-/Splunk_SA_CIM/data/models?count=0 from server=https://<YOUR_HOST_HERE>:<YOUR_PORT_HERE> - Not Found

If you would like to see exactly how we envision that this app's macros
should be used inside of your SIEM's correlation searches and drilldowns,
simply enable the following scheduled search (installed as 'disabled'):
CIM_Toolkit: DEMO: All-in-One Brute Force Authentication Attacks - Rule

## Authors

* **Gregg Woodcock** - Woodcock@Splunxter.com
