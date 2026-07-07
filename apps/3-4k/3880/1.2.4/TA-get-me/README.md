**`TA-get-me`**

Get web API data into Splunk

This Splunk Add-On is pure fun and was used in my Darksky Photographie talk at .conf 2017:

**Take a talk into the art of dark sky photography with a splunk ninja**

[https://conf.splunk.com/files/2017/slides/take-a-talk-into-the-art-of-dark-sky-photography-with-a-splunk-ninja.pdf]()

**Install:**

Install as usual in the Splunk web or copy into $SPLUNK_HOME/etc/apps (Pease don't use it on a prod system!)

**Configure:**

Copy 'default/inputs.conf' to 'local/'

**Moon API** - nothing to do here, move along.

**Weather API** - get your API key from http://api.openweathermap.org and use the Splunk web to configure the input.

**MapBox directions** - get your API key from https://www.mapbox.com and use the Splunk web to configure the input.

**Usage:**

Use the custom search command `get` to either get:

    moon data ( | get me=moon )
    Weather ( | get me=weather ... )
    Google directions ( | get me=directions ... )
    or to get the easter egg ;)

**Debug**

Debug option can be enabled in the Splunk Web using the settings in the data input,
and change the debug option in the `debug setting` stanza from `no` to `yes`.

**Support**

This is an open source project, no support provided, but you can ask questions
on answers.splunk.com and I will most likely answer it.
Github repository: https://github.com/M-u-S/TA-get-me

I validate all my apps with appinspect and the log can be found in the README
folder of each app.

**Version**

`17. August 2018 : 1.2.0 / Replaced Google map API with MapBox API`
`18. August 2018 : 1.2.1 / Fixed typos`
`07. February 2019 : 1.2.2 / Fixed Mapbox API call`
`14. February 2019 : 1.2.3 / No changes, uploaded for appInspect`
`17. February 2019 : 1.2.4 / No changes, uploaded for appInspect`
