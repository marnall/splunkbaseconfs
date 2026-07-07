# TA-pps_decoder


Proofpoint will encode URLs as click-time protection. Proofpoint URL Defense rewrites URLs in messages to point to the URL Defense Redirector serviceu. Although this is good, it makes it difficult especially in a SIEM environment when correlation is needed.

# What is it?

A custom search command for decoding ProofPoint URL Defender Links.This TA contains a custom command `ppsdecode` as well as a input script to decode Proofpoints encoded link.

# Pre-requisites.

* An instance of Splunk where you can install the command.
* Splunk 8.0+ as this is only python3 compatible 

# Setup

* Copy this application to a new folder in your `$SPLUNK_HOME$\etc\apps\` folder.
* Restart your splunk instance so the the app is loaded.
* Global Permission so that the custom command and script is accessible

# ppsdecode Command 101

This command is straightforward. At minimum, you just need to specify the field that contains the encoded URL

Decode the link in the field "url" and place defanged value in default "pps_decoded"
```
index=... | ...| ppsdecode input_field="url" 
```

Decode the link in the field "url" and put the defanged output as "decoded_url"
```
index=... | ...| ppsdecode input_field="url"  output_field="decoded_url"
```

Decode the link and disable defang feature 


# Parameters

The following is the list of parameters. Any values that contain spaces, must be within double quotes.

*  "input_field"   - [required]  Specify the field that contains encoded url
*  "output_field"  - [optional]  Specify where the field you want to display the decoded string (default: pps_decoded)
*  "defang"        - [optional]  Specify if you want the field to decoded field to be defanged (default: True)


# License

The TA-pps_decoder is licensed under the MIT . Details can be found in the file LICENSE.
