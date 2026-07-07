# Change Log
## 1.0
+ Initial release

## 1.1
+ Added some additional error checking. If a user provides an initial regex that does not compile, the script reverts to the built-in default
+ The output field now supports multivalues so if a single line contains multiple LUHN verified matches, they will all be returned
+ The input field now properly supports multivalues as well
+ Confirmed the app works with 6.5

## 2.0
+ Refactored to use Splunk SDK for Python instead of intersplunk
+ Updated README to a markdown file better suited for the git repository
+ Extraction regex can be bypassed to speed up checking generally making the command better. (Set `disable_extraction=yes`. Best used when looking at individual fields of data.)
+ Added option `cc_regex` to allow control over this secondary regex (Reference Section: How it Works)
+ Option `output_field` was replaced with `output_prefix` allowing better/more consistent control over output fields.
+ Output fields are now `output_prefix`+`luhn_check` and `output_prefix`+`luhn_matches`
+ Fixed default metadata.
+ Added appicon images for compatibility with certification.

## 2.0.1
+ Removed configuration to force command to run locally to support distributed streaming
+ Tested compatibility with Splunk 7.2

## 2.0.2
+ Small code changes to better support py3 in the future
+ Tested compatibility with Splunk 7.3

## 2.0.3
+ Tested compatibility with Splunk 8.0 in a py3 environment

## 2.0.4
+ Tested compat with Splunk 8.1
+ Upgraded Splunk SDK to 1.6.14

## 2.0.5
+ Tested compat with Splunk 8.2
+ Upgraded Splunk SDKL

# Prerequisites
This search command is packaged with the following external library:
+ Splunk SDK for Python (http://dev.splunk.com/python)

Nothing further is required for this add-on to function.

# General Overview
This application intends to add a LUHN algorithm checking capability to Splunk Enterprise so you can easily search logs coming from PCI sources for potential credit card numbers. The goal is for administrators to find this data in order to properly mask it before it comes into Splunk. This command was created because regex checking for credit cards isn't enough.

Possible use cases for this command:

1. Checking indexed logs for valid credit card numbers
2. Checking an input file (CSV) for credit card numbers
3. Checking dashboard input for possible credit card numbers


# Command Usage
Using this command will result in two new fields in your data:

```
ta_luhn_matches		All values matched in the input data
ta_luhn_check			True|False
```

The command can be controlled with the following options:

| field | default | values | description |
|-------|---------|--------|-------------|
| disable_extraction | no | yes, no | Disables data extraction. Should be set to 'yes' when you do not require extraction of values from inside other text |
| input_field | _raw | string value | The field to evaluate for possible credit card numbers |
| output_prefix | ta_luhn_ | string value | Prefix for fields added to events |
| regex | `\d[\d\-\s]{13,30})` | regular expression | When extraction is enabled, this looks for all matches within a given data and extracts them for further analysis |
| ccpattern_regex | see below | regular expression | A credit card number is considered a valid match *if* it matches this regex *and* passes the LUHN check. |


ccpattern_regex:
```
(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|6(?:011|5[0-9][0-9])[0-9]{12}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|(?:2131|1800|35\d{3})\d{11})
```

## Search samples
Search raw data, extract any sequence of 13-30 characters comprised of digits, spaces, and/or dashes for potential credit card numbers:
```
sourcetype = pci_log_source | luhn
```

Look at a single field in a datasource, extraction not required:
```
sourcetype = pci_log_source | luhn input_field=cc_num_field disable_extraction="yes"
```

Specify your own regex for extraction:
```
sourcetype = pci_log_source | luhn disable_extraction="no" input_field=_raw regex="(\\d+)"
```

*NOTE:* You have to escape the regex when providing it via splunk search.

# How it works
It basically works like this:

1. Make sure the `input_field` exists in the data.
2. If so, do we need to extract values from it?
3. If yes, extract all values matching the `regex`
4. Loop through all extracted values and compare to `ccpattern_regex`
5. If extraction is disabled, skip steps 3-4. Compare the `input_field` directly to `ccpattern_regex`
6. If `ccpattern_regex` produces a match, compare to luhn algorithm
7. If LUHN is true, return the result.

If any match is found `ta_luhn_check` will be set to `True`. All found matches are stored in `ta_luhn_check`.

# Support
If support is required or you would like to contribute to this project, please reference: https://gitlab.com/johnfromthefuture/TA-luhn. This app is supported by the developer as time allows.
					
