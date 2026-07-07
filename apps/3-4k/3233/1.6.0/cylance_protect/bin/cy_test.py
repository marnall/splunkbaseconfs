"""
Description:
    Splunk entry point for CylancePROTECT test

Authors:
    Peter Uys, Cylance Inc.
    Matt Maisel, Cylance Inc.
"""

import sys

from protect import get_data


input_types = [
    'devices',
    'events',
    'indicators',
    'threats']


def test(session_key, input_type):
    """
    Function:
      - downloads Threat Data Report (TDR) for threats by default
      - can be used as a test to verify that the TDR has been correctly configured in config.xml
      - outputs to stdout only i.e. no data flows into Splunk
      - does not perform tracking i.e. does not keep track of previous writes to Splunk
    """

    get_data(session_key, input_type, tracking=False)


if __name__ == '__main__':

    import splunk.auth as auth
    try:
        msg = 'Modify the username and password in test.py to match your Splunk installation.'
        session_key = auth.getSessionKey('admin','example_password')
    except Exception as e:
        print('Error: ' + e.message + '. ' + msg)
        exit()

    if (len(sys.argv) == 2):
        input_type = sys.argv[1]
        if input_type in input_types:
            test(session_key, input_type)
        else:
            print(input_type + ' is not a valid input type.')
            print('Valid input types are: ' + ', '.join(input_types))
    else:
        test(session_key, 'threats')
