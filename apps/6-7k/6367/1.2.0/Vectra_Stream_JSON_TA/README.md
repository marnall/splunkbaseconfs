# Vectra Stream JSON TA

**Author:** Vectra AI (TME)

## Version

- 1.1.0

## Supported products

- Vectra Stream

## Supported CIM Version

- >=4.0.0

## Supported CIM Datamodels

- Network Traffic (isession metadata)
- Network Resolution (dns metadata)
- Email (smtp metadata)
- dhcp (Network Sessions)
- httpsessioninfo (Web)

## Sourcetypes

- vectra_isession
- vectra_ssl
- vectra_x509
- vectra_dns
- vectra_beacon
- vectra_http
- vectra_dhcp
- vectra_radius
- vetcra_smbfiles
- vectra_smbmapping
- vectra_kerberos
- vectra_ntlm
- vectra_dcerpc
- vecta_ldap
- vectra_ssh
- vectra_smtp
- vectra_match

## Add-on contains

Search and Parsing-Time configuration

## Input requirements

This release requires Vectra Stream to send data in syslog format over TCP.

## Using this Technology Add-on

The add-on has to be installed on Search Heads
If data is collected through Intermediate Heavy Forwarders, it has to be installed on Heavy Forwarders, otherwise on indexers
The add-on expects an initial sourcetype named vectra:stream:json, the sourcetype will be transformed to match to the metadata name.
A sample inputs.conf is provided (default/inputs.conf.sample)

## Release Notes

1.2.0 / 2024-11-07 mbo

 - Add tags for for SMTP and SSL data models

1.1.1 / 2024-08-01 mbo

 - [TM-4403] Add tags for intrusion detection data model (CIM)


1.1.0 / 2024-07-22 mbo

 - [TM-4344] Add Vectra Match support

1.0.1 / 2022-10-03 mbo

- [TM-1470] bug fix: Missing eventtypes.conf
- [TM-1471] bug fix: Incorrect aliases in props.conf

1.0.0 / 2022-03-19 mbo

- Initial release