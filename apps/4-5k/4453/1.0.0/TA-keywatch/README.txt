# README.txt

The TA-keywatch provides secure passive capture of ssh keys from Linux systems. This data is used to ensure compliance with encryption standards and password enforcements in secure environments. 

TA-keywatch was tested on CentOS5/6/7 and will not work on Windows platforms. Your Universal Forwarder must be running as root or another user which can read your home directories (consider setfacl for higher secuity)

By default the index=os is selected. Depending on your security requirements this may need to be adjusted. 

This app brings in Public Keys by default, but they are sort of useless. But this may assist you in any file integroty and monitoring requirement you have and was somewhat logically consistent with me bringing in the private key. 

Security Note
-----------
Private key is truncated by TRANSFORMS.CONF to prevent the key from being onboarded into Splunk. If you disable this you're gonna have a bunch of private keys in Splunk. 

Install 
-----------
1) Deploy the props.conf and transforms.conf to indexers (and/or heavy forwarders) first! This will provide filtration and prevent you from accidently onboarding a users ssh key. 
2) Restart indexers and heavy forwarders
2) Install the app to your search heads.
3) Restart search heads
4) Install app to Universal Forwarder installed on your Linux hosts. 
5) Restart the Universal forwarder

Usage
---------- 
1) You will find sourcetype=key:priv that have "Proc-Type: 4,ENCRYPTED" in them are using passwords on your keys. For reporting any key without that string should be suspect. 
2) If outdated encryption methods are you are now able to search for them e.g. DEK-Info: AES-128-CBC

FSCHANGE
---------- 
I have a couple lines of code using FSCHANGE in inputs.conf. Splunk forwarders at the time of this writing (3/29/2019 Splunk 7.2.5) support FSCHANGE inputs.conf. So I used it. Note that in the future this feature will go away. So just remove those stanzas. 