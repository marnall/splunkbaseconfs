# Binary File Declaration
To address "check_for_binary_files_without_source_code"

Check that all executable binary files have matching source code. For any binary files, there\n should be a source code provided with the same name. Or, there should be a decalaration of what the\n binary file is all about in the app's REAMDE. Details for passing this check will be returned if you fail\n it.

source code for darwin_x86_64/bin/modinput_eventgen and linux_x86_64/bin/modinput_eventgen can be found here: https://cd.splunkdev.com/data-generation/eventgen-go-splunk-app

## Failure that warranted this section
For future reference:
```
FAILURE: is a binary file (Format: Mach-O 64-bit x86_64 
    executable, flags:<NOUNDEFS|DYLDLINK|TWOLEVEL>) but fail to find any 
    source file nor reference info. Please attach source code of this 
    binary in the package, OR create an App's README under root 
    directory and include any information of those binaries under "# 
    Binary File Declaration" section (You might need create one) in 
    README. We will manually review the source code of the binary. File: 
    darwin_x86_64/bin/modinput_eventgen
FAILURE: is a binary file (Format: ELF 64-bit LSB executable, 
    x86-64, version 1 (SYSV), statically linked, not stripped) but fail 
    to find any source file nor reference info. Please attach source 
    code of this binary in the package, OR create an App's README under 
    root directory and include any information of those binaries under 
    "# Binary File Declaration" section (You might need create one) in 
    README. We will manually review the source code of the binary. File: 
    linux_x86_64/bin/modinput_eventgen 
```

In summary, we must have a section called Binary File Declaration in the readme and provide the information about the binary there

# Check that no sensitive hostnames/IPs are stored in the app.
We get warnings for the following ips that are in our app:
```
WARNING: PRIVATE IP 10.0.0.0 is found in 
    darwin_x86_64/bin/modinput_eventgen:167782 File: 
    darwin_x86_64/bin/modinput_eventgen Line Number: 167782 
WARNING: PRIVATE IP 10.10.200.1 is found in 
    README/eventgen.conf.spec:466 File: README/eventgen.conf.spec Line 
    Number: 466 
WARNING: PRIVATE IP 10.0.0.0 is found in 
    linux_x86_64/bin/modinput_eventgen:179321 File: 
    linux_x86_64/bin/modinput_eventgen Line Number: 179321
```
These are all safe to disclose and are just used for tests and examples.

# sc_admin user in default.meta
added based on this warning
```
WARNING: In Splunk Cloud, customers have access to the sc_admin 
    role instead of the admin role. Your customers will not be able to 
    access knowledge objects where the only assigned role is admin. 
    Please consider also including the sc_admin role for compatibility 
    with Splunk Cloud. File: default.meta Line Number: 4 
```