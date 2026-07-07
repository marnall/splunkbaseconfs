TA_Zimbra_Zextras
----------------

This project has inspired by the work of Simon Richardson, the add-on [TA Zimbra](https://splunkbase.splunk.com/app/5704).

GETTING ZIMBRA DATA IN
----------------------
The follwing add-on could be useful:

Splunk-TA-nix (https://splunkbase.splunk.com/app/833/).  This will help parsing on syslog data.

Of course you could install Universal forwarder on each Zimbra server and configure inputs.conf.

If you like (we suggest this), you can forward all logs to the Splunk machine.
Then you tell Splunk to monitor local logs.
A model of syslog aggregation server is [described here](README_rsyslog.md).


GLOBAL LOGS (configure on your syslog central server local to Splunk)
--------------------------------------
This is the default _inputs.conf_:
```
[monitor:///var/log/zimbra]
disabled = false
index = mailbox
sourcetype = zimbra:zsyslog
whitelist = ^\/var\/log\/zimbra\/(mail|mailbox|audit|sync|zmconfigd)\.log$

[monitor:///var/log/zimbra/mtaout.log]
disabled = false
index = main
sourcetype = zimbra:zsyslog
```

INSTALL
------------------------------------
At the first run a setup page helps to configure many configuration parameters of _zimbra.conf_ file.

Then you must manually insert the lookup files that are useful if you also use the _Splunk for Zimbra with Zextras_ app.

To add the lookup files you can use the [Splunk App for Lookup Editing](https://splunkbase.splunk.com/app/1724), or simply perform these searches from the search page of this add-on:

```
| makeresults format=csv data="dest_ip,dest_type
127.0.0.1/32,local
<net/mask>,zimbra"
| outputlookup dest_type.csv
```

and

```
| makeresults format=csv data="mta_server,src_type
<submit_mta_name>,outbound
<inbound_mta_name>,inbound"
| outputlookup orig_type.csv
```

`<net/mask>` is the subnet of your mailbox servers. Ie: "10.10.10.0/24"

`<submit_mta_name>` is the hostname (as shown in mta_server field) of your outbound servers. It can contains wildcard (\*) if you have multiple servers to match.

`<inbound_mta_name>` is the hostname (as shown in mta_server field) of your inbound servers. It can contains wildcard (\*) if you have multiple servers to match.

An example of submit or inbound mta_name is _myoutboundzimbraserver*_, which could match

- myoutboundzimbraserver1
- myoutboundzimbraserver2
- myoutboundzimbraserverA

It's important that you perform the two above seaarches **from the search page of this add-on**.

ZIMBRA SOAP
-----------
We interface with Zimbra Admin server in order to ask some useful info.

## midlookup
With `midlookup` you can ask the _mailbox id_ and _mailbox server_ starting from the _mailbox name_.
In this way you can link the _mailbox name_ to the _mailbox_id_ which you find in the logs.

Usage:
```| makeresults | eval name="<your mailbox name>" | lookup midlookup name as mailbox_name OUTPUT mbox_server mailbox_id | map search="search index=mailbox mailbox_mid=$mailbox_id$ mbox_server=$mbox_server$ ...```

## acctlookup
With `acctlookup` you can ask the _account id_ starting from the _account name_ or the _account name_ starting from the _account id_.

Usage example:
```index=mailbox target_account_id=34aac069-9105-424e-a768-470d058d3bc2 | lookup acctlookup account_id as target_account_id OUTPUT account_name```

and the _account name_ will appear as a new result field.

## name2info
With `name2info` you can ask to Zimbra many mailbox info. You provide the mailbox name in the mandatory `field`, which could be one of
_user_, _authz_name_ or _name_ value.

Usage:
```| makeresults count=1 | eval authz_name=<your mailbox name> | name2info field=authz_name```

Other queries are:
- find members of distribution lists. A `member` multivalue attribute is returned.

Ie:

`| makeresults count=1 | eval name="_grp_rw_animals@example.com" | name2info field="name" get="list"`

returns many attributes describing the distribution list "_grp_rw_animals@example.com". In particular, the `member` multivalue attribute contains the members of the distribution list.


- find which distribution list the account is member of. A `memberOf` JSON multivalue attribute is returned.

Ie:

`| makeresults count=1 | eval authz_name="marco@example.com" | name2info field="authz_name" get="memberOf" | mvexpand memberOf | spath input=memberOf | table authz_name name dynamic via`

returns a table where `name` values are the distribution list subscribed by marco@example.com.


More info to configure these interfaces can be found [here](README_MAILBOX_MID.md).

BUILD NOTES
-----------
This add-on was built on Splunk Enterprise v9.0.3.
This add-on was configured against a multi-server Zimbra Open Source installation running v8.8.15_GA_4372
