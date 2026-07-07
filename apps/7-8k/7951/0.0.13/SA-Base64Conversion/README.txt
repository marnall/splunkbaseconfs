
# SA-Base64Conversion

A small Splunk add-on to provide base64 conversion as a custom command.

Created because I mistakenly believed there were no supported base64 add-ons anymore on Splunkbase. Also as a reason to play with the [Universal Configuration Console](https://splunk.github.io/addonfactory-ucc-generator/).

Existing add-ons for base64 conversion include:
- [SA-base64](https://github.com/Kintyre/SA-base64)
- [TA-base64](https://github.com/cameronjust/TA-base64)



## Authors

- [@gf13579](https://www.github.com/gf13579)

## Usage/Examples

```
| makeresults | eval content="VGhpcyBpcyBhIHRlc3Qu" | b64 action=decode field=content
```


## Support

Raise a GitHub issue or submit a PR if you have a fix or improvement.


## Build

```bash
uv venv
source .venv/bin/activate
uv pip install pip
uv pip install splunk-add-on-ucc-framework

# skip this as we've created it already
# ucc-gen init --addon-name "SA-Base64Conversion"...
# or git clone this repo
# git clone https://github.com/gf13579/SA-Base64Conversion

cd SA-Base64Conversion
ucc-gen build --source package
ucc-gen package --path output/SA-Base64Conversion
```
