# JellyFisher

JellyFisher is a Splunk custom search command that leverage the excellent jellyfish library for python [1]. JellyFisher aims to a) compute a distance between 2 given words, and b) compute a phonetic encoding of a given word.


Ex:
- The Levenshtein distance between "kitten" and "sitting" is 3.
- The soundex representation of both "Robert" and "Rupert" is "R163"


JellyFisher uses Chunked Protocol for custom search commands, meaning that decent performances should be achieved (but no testing were performed to confirm that or not).

The supported algorithms are:

**distance alogrithms:**
- levenshtein_distance
- damerau_levenshtein_distance
- jaro_distance
- jaro_winkler
- match_rating_comparison
- hamming_distance

**phonetic alogrithms:**
- soundex
- nysiis
- match_rating_codex
- metaphone
- porter_stem


## Usage:

The generic usage is straightforward:

```
... | jellyfisher <algorithm>(<arguments>)
```

Examples:

```
... | jellyfisher levensthein_distance(sourcetype,source)
... | jellyfisher jaro_distance(user,sourcetype)
... | jellyfisher soundex(sourcetype)

```


## Inputlookup

The following search is given as demonstration purpose to load a bunch of words (process names) from a CSV lookup file and then compute their distances using the map() command. This is not the perfect implementation, but a good example to start from :)

```
| inputlookup processNames.csv  
| map search="search index=windows | head 10 | stats count by process | eval pName = $processName$ | jellyfisher levenshtein_distance($processName$, process)" 
| table process, pName, levenshtein_distance
```



## References

[1] https://pypi.python.org/pypi/jellyfish


## Credits

Icon made by <a href="https://www.freepik.com" title="Freepik">Freepik</a> from <a href="https://www.flaticon.com/" title="Flaticon">www.flaticon.com</a>