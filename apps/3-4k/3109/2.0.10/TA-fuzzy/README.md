# Change Log
## 1.0
+ Initial Release

## 1.1
+ Minor changes to try to increase performance of the script
+ Verified app continued to function with splunk 6.5

## 1.2
+ Added searchbnf.conf
+ Added minor error checking in case a user provides a bad delim regex

## 1.2.1
+ No one told me there was an error in the script and I guess I didn't test it fully. Stupid typo. :(

## 1.2.2
+ I changed the default behavior of the script. If you don't want to specify a delimiter, it will no longer try to split the input. If a bad delimiter is given, it will default to a newline.

## 2.0
+ Migrated from intersplunk to the Splunk SDK for Python.
+ Updated fuzzywuzzy library to latest release
+ Updated readme file to markdown syntax
+ Verified compatibility with Splunk 7.0
+ Set option `local = True` to force the command to only run on the search head
+ Made a number of workflow improvements, trying to increase command performance.
+ Now only bothers to track the maximum ratio matched instead of also tracking the minimum.

## 2.0.1
+ Bug fixes to support multivalue input fields again

## 2.0.2
+ Documentation updates based on appinspect output.

## 2.0.3
+ Added appicon images for compatibility with certification.

## 2.0.4
+ Added user requested feature to supply a wordlist from a field in a given event
+ Confirmed compatibility with Splunk 7.1

## 2.0.5
+ Removed configuration to force command to run locally to support distributed streaming
+ Tested compatibility with Splunk 7.2

## 2.0.6
+ Updated fuzzywuzzy library to 0.17
+ Minor code update for future py3 compat
+ Tested compatibility with Splunk 7.3

## 2.0.7
+ Tested compatibility with Splunk 8.0 with python3 environment

## 2.0.8
+ Attempted to make library import more dynamic to fix a possible issue with distributed searching.

## 2.0.9
+ Updated splunk-sdk to 1.6.14
+ Updated fuzzywuzzy to 0.18.0
+ Tested compatibility with Splunk 8.1

## 2.0.10
+ Updated splunk SDK
+ Tested compatibility with Splunk 8.2

# Prerequisites
This search command is packaged with the following external libraries:
+ Splunk SDK for Python (http://dev.splunk.com/python)
+ FuzzyWuzzy (https://github.com/seatgeek/fuzzywuzzy)

Nothing further is required for this add-on to function.

# Installation

Follow standard Splunk installation procedures to install this app.

Reference: https://docs.splunk.com/Documentation/AddOns/released/Overview/Singleserverinstall
Reference: https://docs.splunk.com/Documentation/AddOns/released/Overview/Distributedinstall

# Usage
## Using a static wordlist provided as input
```
| fuzzy wordlist="svchost.exe" type="simple" compare_field="tester" output_prefix="fuzz" delims="(\\\\)"
```

+ Wordlist is a comma separated list of words you want to check for fuzzy matches.
+ Type is the type of matching. Reference the library documentation, acceptable values are: simple, partial, token_sort, token_set
+ Compare_field defaults to _raw and is the field you want to do your fuzzy matching in.
+ Output_prefix defaults to 'fuzzywuzzy_'. 
+ Delims accepts a regex string, escaped splunk style, and defaults to `(\\\\|/|\s+|;|-)`

## Using a field based wordlist (Version 2.0.4 and later)
```
| fuzzy wordlist=Creator_Process_Name compare_field=New_Process_Name
```

+ Wordlist is a field that exists in each event containing a comma separated list of words
+ All other options are the same

## Sample Use Cases / Searches
### Look for process names similar to svchost.exe
```
eventtype=win_process_new New_Process_Name=* | fuzzy wordlist="svchost.exe" compare_field="New_Process_Name"
```

### Search for Proxy Logs with domainms similar to your company
```
eventtype=proxy_logs domain=* | fuzzy wordlist="companydomain1.com,companydomain2.com,companydomain3.com" compare_field="domain"
```

# Performance Considerations

There is a nested loop of death whereby the provided wordlist is split and the given input is split. You can improve your performance in the following ways:

- Keep your wordlist to a minimum
- Keep the regex splitting delimeters to a minimum
- Try to filter data before passing it to this command (i.e. don't pass in useless junk)

I use this command in production and will continue to work on improvements but considering the looping that is done, it may always have performance issues.

# How it works (basically):

1. The wordlist is separated
2. The comparison field is separated by the delimeter string provided
3. The two are compared
4. And add the following values to the event output:
* prefix_max_match_word
* prefix_max_match_ratio

The ratio will contain a value, 0 to 100, where 100 is a perfect match. The word values will contain what actually matched in the input/wordlist combination.

# Support
If support is required or you would like to contribute to this project, please reference: https://gitlab.com/johnfromthefuture/TA-fuzzy. This app is supported by the developer as time allows.
