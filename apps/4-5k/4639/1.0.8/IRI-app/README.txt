IRI (Innovative Routines International) App For Splunk
Version 1.0.0
by Devon Kozenieski

To use the IRI App for Splunk, head to data inputs in your Splunk Enterprise instance, or click the link in the home dashboard. In the data inputs, specify your IRI Script location. Have the IRI script INFILE set to the absolute location of the infile, and then run the script. The output of the script should now be indexed automatically into Splunk. It is also possible to run additonal SortCL command line arguments with this app, specified in the modular input. These commands will run in addition to the /SPEC command to run the .scl file. If using an additonal command with an "=" at the end, make sure an additional file location is specified. If using no additional command or a command that does not end in "=", then this field should be left blank. Now you can search through the data in Splunk, create visualizations, and trigger alerts based on the data. 
For more information, visit IRI.com or contact voracity@iri.com
Credit to these third-party libraries that were used to help build this app:
Backbone.validation
Bootstrap
Decorator
functtools32
httplib2
Jinja2
jqTree
jQuery
jQuery-resize
jQuery UI
jsl
JSONPath RW
jsonschema
Lodash
LowPro for jQuery
Mako
markupsafe
Moment.js
munch
PLY
PySocks
Requests
sax-js
Schematics
Select2
simpleyaml
six
SortedContainers
splunk-sdk-python
Underscore.js