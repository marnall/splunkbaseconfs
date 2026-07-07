## Overview
This add-on provides morphological analysis functions for Japanese sentences using MeCab, an open source morphological analysis engine. Specifically, it can perform the following processes provided by MeCab.

- Word segmentation (tokenization)
- Word processing (stemming, lemmatization)
- Part-of-speech tagging

## Getting Started

This add-on is bundled with unidic as a dictionary, so you can start using it without downloading a dictionary at first.

### Usage(morphological analysis)

```bash
| morph field="<src_field>" outfield="<out_field>"
```

`outfield` is optional; if not specified, the `morph` field is used.

### Usage(Word segmentation)

```bash
| wakati field="<src_field>" outfield="<out_field>"
```

`outfield` is optional; if not specified, the `wakati` field is used.
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-mecab/lib/MeCab/_MeCab.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-mecab/lib/charset_normalizer/md.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-mecab/lib/charset_normalizer/md__mypyc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
