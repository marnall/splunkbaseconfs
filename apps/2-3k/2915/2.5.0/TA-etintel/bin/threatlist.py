#!/usr/bin/env python3
import sys
import os


class Threatlist:
    def __init__(self):
        pass

    def scheme(self):
        print('''<?xml version="1.0" encoding="UTF-8"?>
<scheme>
  <title>Threat List</title>
  <description>Reputation List</description>
  <use_external_validation>true</use_external_validation>
  <streaming_mode>xml</streaming_mode>
  <use_single_instance>false</use_single_instance>
  <endpoint>
    <args>
      <arg name="name">
        <title>Threat List Name</title>
        <description>Name of the threat list input</description>
      </arg>
    </args>
  </endpoint>
</scheme>''')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--scheme':
            Threatlist().scheme()
            sys.exit(0)
    sys.exit(0)