Two commands so far.

matchfieldfromcsv:
Given the path to a csv file somewhere in SPLUNK_HOME, tag all events passed in with the values found in the specified field. 
This is useful for counting matches of certain terms in raw in events, even if they can't easily be extracted into fields.
The raw text of each event will be tested for each value of field in the csv file, and if a match is found, that field is attached the event.

Example:
  * | matchfieldfromcsv csv="/etc/apps/foo/test.csv" field="bar"
Example 2:
  * [|inputlookup users | rename username as search | fields + search | format ] | matchfieldfromcsv csv="etc/apps/search/lookups/users.csv" field=username | stats count by username



emailcsvs:
Given a list of csvs that have been created with outputcsv, each of the csv files is attached to a message and mailed to the address provided.

Example:

my great search | outputcsv foo.csv | emailcsvs to="you@there.com" csvs="foo.csv"

or more complicated:

my great search | outputcsv foo.csv | append maxtime=3600 [search my other great search | outputcsv bar.csv] | emailcsvs to="you@there.com" csvs="foo.csv,bar.csv" delete_on_exit=true

I will add other commands as it comes up, or per suggestion.

Cheers,
Vincent
vbumgarner@splunk.com

