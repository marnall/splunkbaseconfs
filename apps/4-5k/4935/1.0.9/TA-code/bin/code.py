import sys
import os
import logging
import codecs
import re
from base64 import b64decode, b64encode, b32decode, b32encode, b85decode, b85encode
from binascii import hexlify, unhexlify
from html import unescape
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import splunk
import urllib.parse


@Configuration()
class code(StreamingCommand):
    """
        Encode the data in a field via the prescribed encoding method

        | code field=<fieldname> method=(base32|base64|base85|hex|url|rot) action=(encode|en|decode|de) destfield=<fieldname> offset=<int>
    """

    field = Option(name='field', require=True)
    method = Option(name='method', require=True)
    action = Option(name='action', require=True)
    dest_field = Option(name='destfield', require=False, default='coded_data')
    offset = Option(name='offset', require=False, default=13)
    enckey = Option(name='key', require=False, default='abc123')
    altlib = Option(name='altlib', require=False, default=None)

    def stream(self, events):
        def setupLogging():
            # Define the logger
            logger = logging.getLogger(__name__)
            SPLUNK_HOME = os.environ['SPLUNK_HOME']

            LOGGING_DEFAULT_CONFIG_FILE = os.path.join(
                SPLUNK_HOME, 'etc', 'log.cfg')
            LOGGING_LOCAL_CONFIG_FILE = os.path.join(
                SPLUNK_HOME, 'etc', 'log-local.cfg')
            LOGGING_STANZA_NAME = 'python'
            LOGGING_FILE_NAME = "code.log"
            BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
            LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
            splunk_log_handler = logging.handlers.RotatingFileHandler(
                os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a', maxBytes=1048576, backupCount=3)
            splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
            logger.addHandler(splunk_log_handler)
            splunk.setupSplunkLogger(
                logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
            return logger

        # Encoding methods are defined here.

        def base32Encode(self, event):
            codeLogger = setupLogging()
            try:
                return b32encode(str.encode(event)).decode()
            except Exception as e:
                codeLogger.exception(
                    'Error has occurred in base32Encode function.  Stack trace to follow:')

        def base32Decode(self, event):
            codeLogger = setupLogging()
            try:
                if len(event) % 8 != 0:
                    event += '=' * (8 - (len(event) % 8))
                temp = b32decode(event)
                return ''.join(chr(i) for i in bytearray(temp))
            except Exception as e:
                codeLogger.exception(
                    'Error has occurred in base32Decode function.  Stack trace to follow:')

        def base85Encode(self, event):
            codeLogger = setupLogging()
            try:
                return b85encode(str.encode(event), pad=True).decode()
            except Exception as e:
                codeLogger.exception(
                    'Error has occurred in base85Encode function.  Stack trace to follow:')

        def base85Decode(self, event):
            codeLogger = setupLogging()
            try:
                temp = b85decode(bytearray(str.encode(event)))
                return ''.join(chr(i) for i in bytearray(temp))
            except Exception as e:
                codeLogger.exception(
                    'Error has occurred in base85Decode function.  Stack trace to follow:')

        def base64Encode(self, event):
            codeLogger = setupLogging()
            try:
                return b64encode(str.encode(event)).decode()
            except Exception as e:
                codeLogger.exception(
                    'Error has occurred in base64Encode function.  Stack trace to follow:')

        def base64Decode(self, event):
            codeLogger = setupLogging()
            try:
                if self.altlib is not None:
                    chars = self.altlib
                    charRanges = re.findall('\w\-\w', chars)
                    for charset in  charRanges:
                        (c1,c2) = charset.split('-')
                        x = [ chr(i) for i in range(ord(c1), ord(c2)+1) ]
                        chars = chars.replace(charset, ''.join(x))
                if len(event) % 4 != 0:
                    event += "=" * (4 - (len(event) % 4))
                temp = b64decode(event)
                return ''.join(chr(i) for i in bytearray(temp))
            except Exception as e:
                codeLogger.exception(
                    'Error has occurred in base64Decode function.  Stack trace to follow:')

        def hexEncode(self, event):
            codeLogger = setupLogging()
            try:
                return hexlify(str.encode(event)).decode()
            except Exception as e:
                codeLogger.exception(
                    'Error has occurred in hexEncode function.  Stack trace to follow:')

        def hexDecode(self, event):
            codeLogger = setupLogging()
            try:
                event = event.replace(" ", "")
                event = event.replace("\\x", "")
                temp = unhexlify(event)
                return ''.join(chr(i) for i in bytearray(temp))
            except Exception as e:
                codeLogger.exception(
                    'Error has occurred in hexDecode function.  Stack trace to follow:')

        def xorCode(self, event):
            codeLogger = setupLogging()
            try:
                xor_data = []
                data = event
                xor_key = self.enckey
                for i in range(len(data)):
                    xor_data.append(hex(ord(data[i]) ^ ord(
                        xor_key[i % len(xor_key)]))[2:].zfill(2))
                temp = codecs.decode(''.join(xor_data), "hex")
                return ''.join(chr(i) for i in bytearray(temp))
            except Exception as e:
                codeLogger.exception(
                    'Error has occurred in xorCode function.  Stack trace to follow:')

        def urlEncode(self, event):
            codeLogger = setupLogging()
            try:
                return urllib.parse.quote(str(event))
            except Exception as e:
                codeLogger.exception(
                    'Error has occurred in urlEncode function.  Stack trace to follow:')

        def urlDecode(self, event):
            codeLogger = setupLogging()
            try:
                return urllib.parse.unquote(str(event))
            except Exception as e:
                codeLogger.exception(
                    'Error has occurred in urlDecode function.  Stack trace to follow:')

        def rotCode(self, event):
            codeLogger = setupLogging()
            try:
                temp = ''
                rot_in = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
                caps_in = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                low_in = 'abcdefghijklmnopqrstuvwxyz'

                rot_out = caps_in[int(self.offset):] + caps_in[:int(self.offset)] + \
                    low_in[int(self.offset):] + low_in[:int(self.offset)]
                for i in event:
                    # Index would be the same thing, but I want the -1's on a ValueError
                    i_index = rot_in.find(i)
                    if i_index == -1:
                        temp += i
                    else:
                        temp += rot_out[i_index]
                return temp
            except Exception as e:
                codeLogger.exception(
                    'Error has occurred in rotCode function.  Stack trace to follow:')

        def ProofPointDecode(self, event):
            codeLogger = setupLogging()
            url = event[self.field]
            try:
                if 'urldefense.proofpoint.com' in url and '?' in url:
                    ver = url.split('/')[3]
                    if 'v1' in ver or 'v2' in ver:
                        urlParamsStr = url.split('?')[1]
                        urlParams = dict([(a.split('=')[0], a.split('=')[1])
                                          for a in urlParamsStr.split('&')])
                        encodedURL = urlParams['u']
                        if 'v2' in ver:
                            ppTranslation = str.maketrans('-_', '%/')
                            encodedURL = encodedURL.translate(ppTranslation)
                        encodedURL = urllib.parse.unquote(encodedURL)
                        decodedURL = unescape(encodedURL)
                        return decodedURL
                    else:
                        if 'v3' in ver:
                            codeLogger.exception('Proofpoint URL v3 is not yet supported, coming soon though!')
                            pass
                        else:
                            return url
            except Exception as e:
                codeLogger.exception(
                    'Error has occurred in ProofPointDecode function.  Stack trace to follow:')

        def safeLinkDecode(self, event):
            url = event[self.field]
            try:
                if "safelinks.protection.outlook.com" in url and "?" in url:
                    urlParamsStr = url.split('?')[1]
                    if urlParamsStr:
                        urlParams = dict([(a.split('=')[0], a.split('=')[1])
                                        for a in urlParamsStr.split('&')])
                        if 'web' in urlParams:
                            return urllib.parse.unquote(urlParams['web'])
                        else:
                            return event[self.field]
                    else:
                        return event[self.field]
                else:
                    return event[self.field]
            except Exception as e:
                codeLogger.exception(
                    'Error has occurred in safeLinkDecode function.  Stack trace to follow:')

        # Methods and Actions (self.method/self.action) are defined here for utilization in the primary loop below.
        coderFunction = {
            "base64": {
                "encode": base64Encode,
                "en": base64Encode,
                "decode": base64Decode,
                "de": base64Decode,
            },
            "base32": {
                "encode": base32Encode,
                "en": base32Encode,
                "decode": base32Decode,
                "de": base32Decode,
            },
            "base85": {
                "encode": base85Encode,
                "en": base85Encode,
                "decode": base85Decode,
                "de": base85Decode,
            },
            "hex": {
                "encode": hexEncode,
                "en": hexEncode,
                "decode": hexDecode,
                "de": hexDecode,
            },
            "url": {
                "encode": urlEncode,
                "en": urlEncode,
                "decode": urlDecode,
                "de": urlDecode,
            },
            "xor": {
                "encode": xorCode,
                "en": xorCode,
                "decode": xorCode,
                "de": xorCode,
            },
            "rot": {
                "encode": rotCode,
                "en": rotCode,
                "decode": rotCode,
                "de": rotCode,
            },
            "safeLinkDecode": {
                "decode": safeLinkDecode,
                "de": safeLinkDecode
            },
            "proofpoint": {
                "decode": ProofPointDecode,
                "de": ProofPointDecode
            }
        }

        if self.method not in coderFunction:
            codeLogger = setupLogging()
            codeLogger.error(
                "Unauthorized method called, please chose from approved methods.  For more detail, please refer to documentation")
            raise Exception(
                "Unauthorized method called, please chose from approved methods.  For more detail, please refer to documentation")

        if self.action not in coderFunction[self.method]:
            codeLogger = setupLogging()
            codeLogger.error(
                "Unauthorized action called, actions are either encode/en or decode/de and case sensitive.")
            raise Exception(
                "Unauthorized action called, actions are either encode/en or decode/de and case sensitive.")

        for event in events:
            if self.field in event:
                try:
                    func = coderFunction[self.method][self.action]
                    if isinstance(event[self.field], list):
                        temp = []
                        for item in event[self.field]:
                            temp.append(func(self, item))
                        event[self.dest_field] = temp
                    else:
                        event[self.dest_field] = func(self, event[self.field])
                except Exception as e:
                    codeLogger = setupLogging()
                    codeLogger.exception(
                        'An error has occurred while attempting to call the requested Coding Function.  Stack trace to follow:')
                    print(e)
            yield event


dispatch(code, sys.argv, sys.stdin, sys.stdout, __name__)
