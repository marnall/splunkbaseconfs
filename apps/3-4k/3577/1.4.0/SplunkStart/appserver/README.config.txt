By: David MacDonald

This document explains the code behind the SplunkStart App.  More in depth comments on how each piece of code works
can be found in line comments in the code itself.

<---Dashboards--->
All of the dashboards of the app can be found in the .xml files ending in "_dashboard"
The simple xml code behind the dashboards can be found at
http://docs.splunk.com/Documentation/SplunkCloud/6.6.0/Viz/PanelreferenceforSimplifiedXML

<---Configure Splunk Start App Menu--->
This menu contains all of the forms created to modify the apps saved searches and titles, as well as the forms
to add a new macro, saved search, dashboard page, or panel.
All the data objects created in this app, like saved searches and macros, are meant to be local to this app.

<---App Setup Workflow--->
The front end code for this page is located in app_setup.xml, app_setup.html, and app_setup.js

The page is simply a combination of the get_apps.html, input_data.html, modify_macros.html, and change_dashboard_titles.html
pages.  The JS is simply a combination of those four pages JS pages as well, with some modifications to the IDs of the
page elements so that there were no naming conflicts.

Since this workflow is basically just a combination of other pages, I won't go into depth about how it works.  The only
thing to note is that the other "pages" within this page are either hidden or shown based on whether or not the user
is on that part of the workflow.  The "next" and "back" buttons control what parts are hidden or not.

<---App Prerequisites Page--->
The front end code for this page can be found in get_apps.xml, get_apps.html, and get_apps.js

This page is simply a list of apps you need installed to use all the visualizations in SplunkStart.  Unfortunately, these
apps cannot be packaged with SplunkStart.

<---Modify Macros Page--->
The front end code for this page can be found in modify_macros.xml, modify_macros.html, and modify_macros.js
The back end code for this page can be found in controllers/app_setup.py and bin/controller_services/file_operations.py

-Page Setup-
When this page is first setup, a call is made to get a bunch of data about each dashboard page in order to setup this page's
tabs, titles, and input boxes.  A call is also made to determine if the "Show SPL" checkbox that controls the
"Show SPL" buttons on the dashboards should be checked or not.

IF a dashboard has a search that is not made from a saved search in this app's context, then the input box to modify
that panel's search will be disabled.  The get_panel_info code on the backend is able to get inline search data, and
the front end page will recognize that the search is inline, but since saving that inline search back to the xml file
would be difficult, an effort was not made to allow the user to actually edit the inline search.

-Basic Macro Edit (default view of the page)-
A user can edit the arguments of a macro.  The error checking makes sure that the macro starts with "_mac", has the
correct number of arguments, and has both opening and closing parenthesis.
NOTE: If the user removes part of the macro name that is not the "mac_" part, the user will be allowed to submit the
macro, but nothing will be updated since the name of the macro will not be able to be found.
NOTE: Only the arguments in the macros can be changed, editing the macro itself can only be done in the normal Splunk way.

How it works:
When a user submits changes to the saved searches, a list of all the searche macros present on the page is generated, and then
that list is submitted to the backend.  On the backend, the names of the macros are compared to the macros already
present in the saved searches and if two names match, the submitted macro will replace the old one.  All these
changes are stored in the local/savedsearches.conf file

-Add/Remove "Show SPL" checkbox-
This controls whether or not the "Toggle Comments" and "Show SPL" buttons on the dashboard panels will be displayed.
This is done by either adding or removing those buttons from the xml files directly.

How it works:
The buttons in the xml have an ID that corresponds to the saved search they are associated with, so that the saved
search can be pulled up along with the macro definition and the SPL displayed.

-Advanced Macro Edit-
This view presents a way for users to edit saved searches with macros typed directly into a text box.  A user can either
choose a preexisting macro file, or write their own macro file and then submit it.

How it works:
When a file is submitted, it is first saved to the src/macros directory.  Then, the file is parsed and a list of updated
searches is obtained.  Once the list is obtained, the search macros are saved the same way that they are in the basic edit.

<---Change Dashboard Titles--->
The front end code for this page can be found in the change_dashboard_titles.xml, change_dashboard_titles.html, and
change_dashboard_titles.js pages.
The back end code can be found in the controllers/app_setup.py and the controller_services/file_operations.py files

-Page Setup-
Like the modify macros page, a call to the get_panel_info function is made to set the page up.  The code to actually
set up the page is very similar to the modify_macros page.

-Basic Title Edit-
A user can edit a dashboard title in an input box and then submit it.  The title can be anything.

How it works:
All of the titles are collected from the input boxes and submitted to the backend, along with the files each title
is associated with.  The format of the data can be found in comments in the actual code.  The program then grabs all
the old title info.  The program will then go into each xml file and write over the old titles with the new titles.

-Advanced Title Edit-
A user can edit dashboard titles using a csv in the format of old_title,new_title.  They can either make their own
csv or choose from an existing titles.csv file located in the src/titles directory

How it works:
A list of all the lines in the text box that are not blank and have old_title,new_title pairs are collected and sent
to the backend.  Since the data is formatted differently than in the basic edit, a different function is called the
looks at all the xml files and replaces the old titles with the new titles.

<---Add Entities--->
The front end code for this page can be found in the add_entity.xml, add_entity.html, and add_entity.js pages.
The back end code can be found in the controllers/add_objects.py and controller_services/file_operations.py files.

The user can add a macro, saved search, dashboard page, and dashboard panels on this page.

-Add Macro-
In this tab, the user can add a macro to this app context.

How it works:
The user defines the macro search string and the macro name.  They then have the option of changing the field names before
submitting the macro.  The macro name and definition are sent to the backend where they are appended to the local/macros.conf
file.

-Add Saved Search-
In this tab, the user can add a new saved search.

How it works:
The user enters the saved search name and chooses a macro to base the search off of and fills in the arguments with data.
NOTE: it is recommended to use a new macro or else changes to a macro already being used will be reflected in this
search as well.

-Add Dashboard Page-
In this tab, the user can add a new dashboard page to the app.

How it works:
A new xml file is created with the entered dashboard name and label.  If "Show SPL" buttons are on, then the code that
allows that is also added to the new dashboard, including the "Toggle Comments" button.

-Add Panel-
In this tab, the user can add a panel to an existing dashboard.

How it works:
A dashboard is selected, along with a saved search, type of panel, and panel title.  The panel is then added to that
dashboard's xml file in a new row.  If the "Show SPL" buttons exist, they are added to the new panels as well.