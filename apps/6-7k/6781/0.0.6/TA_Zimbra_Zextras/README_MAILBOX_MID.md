# SOAP QUERY

A script called _name2mid.py_ has been placed in *bin* folder. This Python script query SOAP Zimbra service in order
to select the mailbox_id of a given mailbox name.

IMAP log doesn't show the mailbox name, because _auth name_ and _authz name_ are not the _mailbox name_.
Zimbra SOAP doesn't offer a way to lookup the _mailbox name_ from _mailbox mid_ and _hostname_.
But you can provide the _mailbox name_ and lookup the _mailbox mid_ and _hostname_, then you can perform your query with them.

Another lookup script is _acct2name.py_ and perform a similar work for the account_id from account name. A reverse lookup works.

Finally, a command _name2info.py_ provides a way to query SOAP API in order to extract many info on Zimbra account.

## Install

You have to make your configuration in the file *zimbra.conf*, in particular write your Zimbra credentials.
We suggest to copy the file in your "local" folder and then modify it as needed.
On Splunk Cloud you can configure *zimbra.conf* by the setup page.

### Test

Create a test.csv in a test folder with this content

```
mailbox_name,mbox_server,mailbox_id
<a valid mailbox name>
```

then:

```
sudo -u splunk LD_LIBRARY_PATH=$SPLUNK_HOME/lib $SPLUNK_HOME/bin/python3 $SPLUNK_HOME/etc/apps/TA_Zimbra_Zextras/bin/name2mid.py mailbox_name mbox_server mailbox_id < test/test.csv
```

If all is fine you will see something like:

```
<mailbox name>,<hostname of the mailbox>,<mailbox numeric mid>
```

Create a atest.csv in a test folder with this content

```
account_name,account_id
<a valid mailbox name>
,<a valid account id>
```

then:

```
sudo -u splunk LD_LIBRARY_PATH=$SPLUNK_HOME/lib $SPLUNK_HOME/bin/python3 $SPLUNK_HOME/etc/apps/TA_Zimbra_Zextras/bin/acct2name.py account_name account_id < test/atest.csv
```

If all is fine you will see something like:

```
<account name>,<account id>
<account name>,<account id>
```


These python script depends on

- [Python Zimbra](https://github.com/Zimbra-Community/python-zimbra)
- [Splunk Enterprise SDK for Python](https://dev.splunk.com/enterprise/docs/devtools/customsearchcommands/createcustomsearchcmd#Install-the-Splunk-Enterprise-SDK-for-Python-in-your-app)

### Note For developers
You can install Python Zimbra with
`sudo -u splunk LD_LIBRARY_PATH=$SPLUNK_HOME/lib HTTPS_PROXY=proxy.example.com:80 $SPLUNK_HOME/bin/pip3 install --target=$SPLUNK_HOME/etc/apps/TA_Zimbra_Zextras/bin/zimbralib python-zimbra`.

You can install _splunklib_ following the instruction in _Splunk Enterprise SDK for Python_. So:
copy and paste the __/splunklib__ directory from the _Splunk Enterprise SDK for Python_ into the bin directory of your app. For example, copy the __/splunklib__ directory into __$SPLUNK_HOME/etc/apps/app_name/bin__.


## USAGE

If you want to see operations on a mailbox and you know the mailbox name you can do the following:

`| makeresults | eval name="<your mailbox name>" | lookup midlookup name as mailbox_name OUTPUT mbox_server mailbox_id | map search="search index=mailbox mailbox_mid=$mailbox_id$ mbox_server=$mbox_server$ ...`


If you want to see the account name from an account id stored in `target_account_id` field, then you can do the following:

`index=mailbox target_account_id=34aac069-9105-424e-a768-470d058d3bc2 | lookup acctlookup account_id as target_account_id OUTPUT account_name`

and the `account_name` will appear as a new result field.
