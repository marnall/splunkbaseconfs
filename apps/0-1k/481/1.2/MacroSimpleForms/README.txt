Unpack into the $SPLUNK_HOME/etc/apps

Notable files/Contents:
$SPLUNK_HOME/etc/apps/MacroSimpleForms/local/macros.conf
$SPLUNK_HOME/etc/apps/MacroSimpleForms/default/data/ui/views/forms_inputs.xml

Problem Summary:  
Macros are used to pass arguments to searches.
However, macros only take a fixed number of arguments.  In other words,
if a macro expects to see 5 arguments, but you only want to
give it 1 or 3...it will error out.

WorkAround:
This App contains 10 similar but different macros that accept between 1 and 5
arguments.  The macros UserGroup and EventCode contains a stanza definition for each possible input (up to 5).

Dummy Data:
If you want to change the definition of the macros to work on your data, you'll just need to change the sourcetype=cisco_firewall to your sourcetype.

***********IMPORTANT INFORMATION TO FOLLOW********************

If you want to use the dummy data below to see how this works:

1-Just go to manager-->Data inputs-->Files & Directories
-->New-->Upload a local file and navigate to $SPLUNK_HOME/etc/apps/MacroSimpleForms/dummy_logs/dummy.log

2-Leave Host values as is

3-Change Source Type to cisco_firewall...heres how:  -->
Set Sourcetype --> manual and input cisco_firewall

4-Keep the default for all other options.  Save and close.

After the data is index, play around by entering multiple EventCode and UserGroup combinations and examine the results.

Example Event Codes: 605,805,705,105
Example User Groups: NHL,ESS,SAS,HR,NCA


Thanks:
Dave Croteau, CISSP
SE, Splunk

tar czf MacroSimpleForms.tar.gz MacroSimpleForms/

