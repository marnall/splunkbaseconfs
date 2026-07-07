# URLParser

URLParser is a custom search command designed to parse URLs. Compared to UTBox, URLParser is faster, extract more fields and is easier to use.


```
 ... | urlparser [field=<fieldname>] [listname="*|iana|mozilla|<name>"] [mode=[simple|extended]]
```

Because it relies on the new chuncked protocol, URLParser is compatible starting with Splunk 6.4.0 and above.

URLParser is a Community Supported app.


# Extracted fields

URLParser will extract the following fields form the submitted URLs:

* url\_domain
* url\_domain\_without\_tld
* url\_fragment
* url\_hostname
* url\_netloc
* url\_params 
* url\_password
* url\_path
* url\_port
* url\_query
* url\_scheme
* url\_subdomain
* url\_subdomain\_depth
* url\_subdomain\_parts
* url\_tld
* url\_username

The field url\_subdomain\_parts can also be processed by Splunk spath command to access to individual parts of the subdomain (url_subdomain.1, url_subdomain.2, ...).

# Usage

The command signature is the following:

```
... | urlparser [field=<fieldname>] [mode=[simple|extended]] [listname="<listname1|listname2|...>"]
``` 

All arguments are optional and default values are set to the following:
- field: url
- mode : extended
- listname: mozilla

The simplest way to call urlparser is as follow:

```
... | urlparser
``` 

In the previous example, urlparser will automatically works with the field 'url', load the 'mozilla' suffix list and perform an 'extended' extraction of the fields.


# Example

This example demonstrates the parsing of a 'complex' URL and how the Splunk spath command can be used to leverage the url\_subdomain\_parts field.

```
 | stats count
 | fields - count
 | eval url = "hTTp://je@n:pass:w@rd@images.www.gOOGle.Co.uk:256/iDNex.php?var=CALue32&ouech=gros#pouet"
 | urlparser
 | spath input=url_subdomain_parts
 | transpose
```

This simple example also illustrates that the case of the input URL is unchanged by URLParser, which is a fundamental to work with URLs containing Base64 data for example (exfiltration scenarios and alike). Users willing to normalize URL in lower case can easily do it by using Splunk's eval command and it's lower() function.

# Pro Tips

It is a good habit to filter URLs prior sending them to urlparser to avoid empty url fields, or url set as '-' (often seen in proxy logs).

```
... | search url=* url!="-" | urlparser
``` 

In some situation, using the stats command to deduplicate repeted url can be desirable.

# Scripted Lookup

URLParser is also accessible as a scripted lookup. This will be useful for situations where the custom search command cannot be used like if you are building a datamodel. The scripted lookup is slower than the custom search command.

```
... | eval list="iana|mozilla" | lookup urlparser_lookup url list
```

To pass a string argument to a scripted lookup, a little trick need to be used as illustrated with the previous example. In this example, the lists to use are set to 'iana' and 'mozilla' by a prelimerary call to the Splunk eval command.

# Where are the statistical functions from UTBox?

URLParser will focus on everything about URL Parsing. In short, computing the shannon entropy of a word, whether that'd be a domain name or not, is not part of the process of parsing a URL. 


# Options

## mode

The mode option, admit two values: 'simple', or 'extended' so it's usage is straightforward:
- mode=simple
- mode=extended

In case of an unknown submission, the default mode 'extended' is used.

The mode 'simple' only call python's method urlparse() to extract basic elements from URLs and the mode 'extended' extract many more elements like the TLD, the subdomain, the domain without the TLD, etc.


## listname

The listname option allows to specify one or more lists of known TLDs to load. URLParser is shipped with two default lists, the IANA list and the Mozilla Public Suffix List but users can define their own custom lists to either complement, or replace, the default lists. Multiple lists can be loaded by specifying the separator "|" (pipe). 

Examples:
- listname="iana"         : load the TLD from the list 'iana' (one of the default lists)
- listname="custom"       : load the TLD from the list 'custom' (user defined list)
- listname="mozilla|iana" : load the TLD from both 'iana' and 'mozilla' lists (default provided lists)
- listname="iana|pouet"   : load the TLD from the list 'iana' (default list) and the list 'pouet' (user defined list)
- listname="iana|pouet|custom|mylist" : load the TLD from the lists 'iana', 'pouet', 'custom' and 'mylist'
- listname="\*"           : load the TLD from all available lists (lists present in the suffix\_lists directory)

There is no limit to the number of lists one can load and the TLDs present in multiple lists are loaded only once (the underneath logic is a boolean OR).


Lists files are stored under the application directory ($APP\_DIR/suffix\_lists) and must be named following this syntax: suffix\_list\_\<name lowercase\>.dat

Examples: 
- suffix\_list\_mozilla.dat
- suffix\_list\_iana.dat
- suffix\_list\_custom.dat
- suffix\_list\_pouet.dat

# Creating a custom list

This section describes what is the formalism expected for the content of a custom list:

* One TLD per line
* Comments are ignored (lines starting by "#" or "//")
* TLD must NOT start with a dot (".com" is wrong, "com" is correct)
* Support the Mozilla Suffix List logic (wildcards and question marks)

Example:

```
// This is my custom list
pouet
\*.yata
!coco.yata
```


Line 1: define "pouet" as a TLD.

	* www.domain.pouet: TLD=pouet, Domain=domain.pouet

Line 2: define that everything under ".yata" is part of the TLD 

	* www.domain.cw.yata: TLD=cw.yata, Domain=domain.cw.yata
	* www.domain.hehe.yata: TLD=hehe.yata, Domain=domain.hehe.yata

Line 3: define an exception for the .yata TLD: coco.yata is NOT a TLD.

	* www.domain.coco.yata: TLD=yata, Domain=coco.yata


# Is it fast?

Those tests are just an indication of performances and were realized on a MacBook Pro over a sample dataset of proxy logs with Splunk 6.5.1.


URLParser (scripted lookup)

```
search> url!=- url=* | head 200000 | eval list="mozilla|iana"| lookup urlparser_lookup url list

This search has completed and has returned 5,123 results by scanning 204,129 events in 81.6 seconds
```

URLParser (custom search comand)

```
search> url!=- url=* | head 200000 | urlparser listname="mozilla|iana"

This search has completed and has returned 5,123 results by scanning 204,129 events in 26.91 seconds
```

As a reference point for comparaison, here are the results with UTBox:

```
search> url!=- url=* | head 200000 | eval list="*" | lookup ut_parse_extended_lookup url list

This search has completed and has returned 5,123 results by scanning 204,129 events in 83.123 seconds
```

# Troubleshooting

URLParser execution logs can be found under $SPLUNK\_HOME/var/log/splunk/urlparser.log


# History

* v1.0, December 2016
	* First release


