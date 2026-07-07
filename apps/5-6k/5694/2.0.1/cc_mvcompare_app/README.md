# cc_mvcompare
Splunk mvcompare command to compare two multi-value splunk fields or delimited string fields.

Version 2.0.1:
 - This update corrects an issue due to how splunk reads a field with a single string, as a string and not as a list as it does with multi-value fields.
 - This update allows the users to delimit a string in the command if they choose, as opposed to requiring this to be done prior with a makemv command. 