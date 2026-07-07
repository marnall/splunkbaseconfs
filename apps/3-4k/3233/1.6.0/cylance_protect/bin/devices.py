"""
Description:
    Splunk entry point for CylancePROTECT devices

Authors:
    Peter Uys, Cylance Inc.
    Matt Maisel, Cylance Inc.
"""


import sys


from protect import get_data


def devices(session_key):
    """ Download Threat Data Report for devices and write data to Splunk. """
    get_data(session_key, 'devices', tracking=False)

if __name__ == '__main__':

    session_key = sys.stdin.read()
    devices(session_key)
