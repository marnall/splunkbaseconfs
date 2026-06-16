Author: Nimish Doshi

************************************************
SPECIAL NOTE: As of 2021, Splunk has removed Python 2 from its distribution.
Becauase of this, the aes.py module does not work in Python 3. Do not use
encryptfield2.py and decrypt2.py listed below as they will not work in a
Python 3 environment. Continue to use DES or triple DES as your default.
************************************************


The purpose of this distribution is to create an easy way to encrypt data
within events and decrypt data at search time depending on the role. The
distribution uses pyDes available at:
http://twhiteman.netfirms.com/des.html

and version 2.x of this distribution also ships aes.py created by
Markus Birth at http://wiki.birth-online.de/snippets/python/aes-rijndael

USE THIS AS IS as no warrantee is provided.

The basic idea is to first encrypt data within an event and produce a new file
with the same content as before, but with the data matching group(1) in a
regular expression encrypted and saved on disk using base64. The next thing
to do is index the newly required file into Splunk with a sourcetype.

At search time, you will then be able to decrypt the data within the event
based on your role's ability to run the decrypt command.

INSTALLATION

-Enable a role in $SPLUNK_HOME/etc/encryptdecrypt/metadata to access the
 the decrypt and decrypt2 command. You can make a copy of default.meta and
 call the new file local.meta and edit the permissions for read and write
 for the views and decrypt and decypyt2 commands. If you skip this step,
 the views avialable in this add-on/app are only accessible by the admin role
 and the decrypt and decrypt2 commands are avilable in all apps, but only
 within the admin role.

 If you are not familiar with local.meta formats, you can consult the Splunk
 docs or simply use the default.meta example provided in this distribution
 as a template.
-Although pyDES.py has been provided here for convience, it is better to
 download it and install it within your Python distibution

Usage:

The best way to understand this is through an example. An example log file
called credit.log has been provided to you for testing. First, encrypt data
using the encryptfield.py (or encryptfield2.py) script in the bin directory.

python encryptfield.py <filename> <Escaped REGEX (w/Group)> <8 char key>

Example: python encryptfield.py credit.log "creditcard=(\\d+)" DESCRYPT

Note: Use encryptfield2.py if you want AES encryption. The key does not have to
be 8 characters for this. You will then have to use decrypt2 to decrypt it.

This produces a file with a suffix of en.txt. You will then use this file
as input to Splunk to index. Create your inputs.conf within your app or
SPLUNK_HOME/etc/system/local and use credit.log.en.txt as an input to
monitor with a sourcetype, say credit. A sample disabled inputs.conf is
found in this app's default directory. Next, create a role that is
authorized to execute the search command, decrpyt or decrypt2, and login
as a user in that role. Within Splunk Web or within the command line,
pipe your search to decrypt (or decrypt2 if you used encryptfile2.py)

Example:

sourcetype="credit" |decrypt "creditcard=([^\s]*)" DESCRYPT

(or sourcetype="credit" |decrypt2 "creditcard=([^\s]*)" DESCRYPT)

This will create a new field at search time called decryptedField that you
can use for further search. Here's another example:

sourcetype="credit" |decrypt "creditcard=([^\s]*)" DESCRYPT|fields + decryptedField

(or sourcetype="credit" |decrypt2 "creditcard=([^\s]*)" DESCRYPT|fields + decryptedField)

Notice that \s is used instead of a space in the regex and that the same key
that was used to encrypt (DESCART) is used to decrypt. Also, use the
interesting fields view from the left side from Splunk Web to see the
decryptedField values.

Splunk View:

An experemental view has been created http://<splunkserver:port>/encryptdecrypt
that you can use as a GUI to decrypt your results. This comes as the only
views of this add-on/app and only allows the user to see the two dashboards
included with no drilldown.


Enhancements:

The normal decrypt uses DES. The decrypt2 uses AES, which is a more modern
encryption scheme. Use whichever one you want, but be consistent. If you
encrypted using encryptfile2.py, then decrypt using decrypt2.

Also, the most common use case is to encrypt one term in an event to decrypt.
If you need to encrypt more than one term in the event, change both
python programs to reflect multiple groups to encrypt and decrypt.
If the usage of regex within these files do not suite your needs, feel free
to use the Python re module to customize the data extractions.
