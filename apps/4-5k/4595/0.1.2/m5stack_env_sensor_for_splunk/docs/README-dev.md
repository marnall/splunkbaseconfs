# References

  * Developing your app
    - splunk>dev [Develop an app or add-on](http://dev.splunk.com/view/SP-CAAAFD7)
    - splunk>dev [Splunk AppInspect overview](http://dev.splunk.com/view/appinspect/SP-CAAAE9U)
  * Submitting your app
    - splunk>docs [Before you submit content to Splunkbase](https://docs.splunk.com/Documentation/Splunkbase/splunkbase/Splunkbase/Aboutsubmittingcontent)
    - splunk>docs [Submit content to Splunkbase with the web UI](https://docs.splunk.com/Documentation/Splunkbase/splunkbase/Splunkbase/SubmitcontenttoSplunkbase)

# Enable HTTP Event Collector

Settings - Data, Data Inputs - Local inputs, HTTP Event Collector - Glocal Settings
  * All Tokens 'Enabled"
  * HTTP Port Number: 8088 (default)

# Enable appinspect CLI locally

For details, you can show offifial document 
[Install AppInspect](http://dev.splunk.com/view/SP-CAAAFAK).

1. Download the package from [DOWNLOAD button](http://dev.splunk.com/view/SP-CAAAFAK).

2. Create a `virtualenv`.

    $ virtualenv env27

3. Activate `virtualenv` and install the package with `pip`.

    $ source env27/bin/activate
    $ pip install splunk-appinspect-1.7.1.tar.gz

