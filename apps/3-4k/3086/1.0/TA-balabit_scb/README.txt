######################################################
#
# Balabit Shell Control Box Add-On for Splunk
#
######################################################

To setup the basic functionality of the app:

1.) enable the balabit_scb index
    (see default/indexes.conf as example)

2.) index SCB logs in Splunk; use the following settings
    in the relevant stanzas of inputs.conf:

      index = balabit_scb
      sourcetype = BalaBit:ShellControlBox

    (see default/inputs.conf as example)

To collect SNMP data, the following additional steps must be done:

1.) enable the balabit_scb_snmp index
    (see default/indexes.conf as example)

2.) install SNMP Modular Input (snmp_ta) app
    https://splunkbase.splunk.com/app/1537/

3.) convert the relevant MIBs for use in snmp_ta:

      cd /opt/splunk/etc/apps/snmp_ta/bin/mibs/
      build-pysnmp-mib -o HOST-RESOURCES-MIB.py /usr/share/mibs/ietf/HOST-RESOURCES-MIB
      build-pysnmp-mib -o IF-MIB.py /usr/share/mibs/ietf/IF-MIB
      build-pysnmp-mib -o UCD-SNMP-MIB.py /usr/share/snmp/mibs/UCD-SNMP-MIB.txt

    On Debian/Ubuntu, the MIBs can be downloaded with the snmp-mibs-downloader package.

4.) enable SNMP data collection according to the examples in default/inputs.conf.
    Note: collection of different data points are split into 6 different stanzas, you
    need to setup all of the following stanzas per each SCB:

      [snmp://example_netif]
      [snmp://example_storage]
      [snmp://example_sysstat]
      [snmp://example_load]
      [snmp://example_sysinfo]
      [snmp://example_processes]

