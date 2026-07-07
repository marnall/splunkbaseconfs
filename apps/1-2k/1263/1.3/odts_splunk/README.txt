Office Documents Template System (ODTS) for Splunk allows you to easily generate office documents with any Splunk search results inside. You could easily dump splunk results to new document(results are inserted as table) or use predefined templates with any complex formatting to insert results at predefined places or with predefined style.
Application supports several document formats. By default, documents generated in ODT/ODF format supported by OpenOffice/LibreOffice and Microsoft Office (starting with 2007 sp2 and later). Other supported types are: doc, pdf, rtf, txt. Support for doc, pdf, rtf, txt documents requires local OpenOffice/LibreOffice installation (discussed below). Support for docx/xls/xlsx and others may be provided in future. 
Application was tested on Windows/Linux(*nix) platforms
----
++ Using  Office Documents Template System for Splunk

The App provides a new command - "docgen" used to generate office documents. Command has some trivial arguments (discussed later) and accessible at any app

----
++ Case 1 - dump splunk results to new document
    Very often you just want to insert splunk results to a new document - in this simple case you just need to add docgen command to the end of splunk command's flow:

+++ Example 1:
{{ index=_internal source="*metrics.log" group="per_sourcetype_thruput" | head 20 | stats min(eps) avg(eps) max(eps) by series | docgen }}
   docgen's output provides information about file generated and where you could find it. By default it's SPLUNK_HOME\etc\apps\odts_splunk\results foder

+++ Example 2:
  Just another simple example:
 sourcetype=access* | top clientip | docgen 

+++ Example 3:
    What if you want generated document to be found in another folder(another than "results")? Just use  -ofile paremeter:
 sourcetype=access* | top clientip | docgen -ofile=d:\temp\out.odt 
    Generated file could be found in d:\temp folder and has name out_<timestamp>.odt

----
++ Case 3 - generate DOC, PDF, RTF, TXT documents(i.e. non-ODT)
   App could easily dump splunk results to different types of documents like DOC, PDF, RTF (other than ODT). To be able to do that you have to complete two points:
* 1) install OpenOffice/LibreOffice locally(make sure python-UNO option is checked) and launch OpenOffice/LibreOffice in server mode
    You launch OpenOffice/LibreOffice in server mode by running the command (under Windows):
"_path_to_soffice_\soffice" -invisible -headless "-accept=socket,host=localhost,port=2002;urp;"
    Under Linux(Unix) it may look like:
soffice -invisible -headless "-accept=socket,host=localhost,port=2002;urp;"
    2002 is a port number that you could change
* 2) open App's setup page and provide absolute path to OpenOffice python binary and (optionally) port number used.
   Path may look like(ex. for Windows): C:\Program Files\OpenOffice.org 3\program\python.exe
That's all, to generate document type you need add this type as an extension with ofile parameter, for ex. for doc:
 sourcetype=access* | top clientip | docgen -ofile=my.doc 

----
++ Case 2 - generate documents based on predefined template

Using this App you have ability to generate really complex office documents and place search results to specified places. You could do this by providing you own predefined templates.
To create your own templates or change existing you have to install OpenOffice/LibreOffice.
You could find some templates inside APP_HOME/templates(SPLUNK_HOME/etc/apps/odts_splunk/templates) folder:
* dump_table_custom.odt - simple template that could be change to suite you needs to dump splunk results as table at some places
* TableFields.odt - template used to insert splunk results as table with predefined style and columns 
* WithAnImage.odt - template with complex formatting (including images). Splunk results inserted as single values inside nested tables
* ForTable.odt - template where splunk results inserted as independent tables
* TableSection.odt  - template where splunk results not just one table, but table with sections
* dump_two_tables.odt - template used to insert several splunk results.

For all those templates you could find sample generated documents inside APP_HOME/results(SPLUNK_HOME/etc/apps/odts_splunk/results) folder to see how it looks like.
To start preparing you own templates or change existing I recommend you to read following article: 
[http://appyframework.org/podWritingTemplates.html How to prepare Basic Templates in Appy]
The App uses Appy framework internally and all principles of preparing templates in Appy are valid for ODTS. Just remember that in templates you could use "events" variable that represents splunk's results from main search flow(provided to docgen command).
Article provided and existing templates(from "templates" folder) would be a good starting point for changing or creating new templates.

To use created/changed template provide name of it to -tfile parameter:

+++Example 1: use docgen with some template (for ex.:TableFields.odt):
 index=_internal source=*metrics.log splunk_server="*" | eval MB=kb/1024 | search group = per_sourcetype_thruput |stats sum(MB) as sumMB by series, group | docgen -tfile=TableFields.odt
If relative path name is provided to docgen command than we are searching for templates in SPLUNK_HOME/etc/apps/odts_splunk/templates folder