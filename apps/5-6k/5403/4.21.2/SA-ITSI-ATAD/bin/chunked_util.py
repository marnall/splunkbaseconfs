#!/usr/bin/env python

import sys
import json
import re
import csv
from io import StringIO

# Windows will mangle our line-endings unless we do this.
if sys.platform == "win32":
    import os
    import msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)


def read_chunk(f, logger):
    '''Attempts to read a single "chunk" from the given file.

    On error (e.g. exception during read, parsing failure), returns None

    Otherwise, returns [metadata, body], where
       metadata is a dict with the parsed contents of the chunk JSON metadata
       body is a string with the body contents
    '''

    try:
        header = f.readline()
    except:
        return None

    if not header or len(header) == 0:
        return None

    m = re.match(
        'chunked\s+1.0\s*,\s*(?P<metadata_length>\d+)\s*,\s*(?P<body_length>\d+)\s*\n', header)
    if m is None:
        logger.warn('Failed to parse transport header: %s' % header)
        return None

    try:
        metadata_length = int(m.group('metadata_length'))
        body_length = int(m.group('body_length'))
    except:
        logger.warn('Failed to parse metadata or body length')
        return None

    try:
        metadata_buf = f.read(metadata_length)
        body = f.read(body_length)
    except Exception as e:
        logger.warn('Failed to read metadata or body: %s' % str(e))
        return None

    try:
        metadata = json.loads(metadata_buf)
    except:
        logger.exception('Failed to parse metadata JSON')
        return None

    return [metadata, body]


def write_chunk(f, metadata, body):
    '''Attempts to write a single "chunk" to the given file.

    metadata should be a Python dict with the contents of the metadata
    payload. It will be encoded as JSON.

    body should be a string of the body payload.

    no return, may throw an IOException
    '''

    fs = FileStringHandler.getInstance()
    fp = fs.get_writer(f)
    metadata_buf = None
    if metadata:
        metadata_buf = fs.encode_string(json.dumps(metadata))
    encoded_body = fs.encode_string(body)
    fp.write(fs.encode_string('chunked 1.0,%d,%d\n' %
             (len(metadata_buf) if metadata_buf else 0, len(encoded_body))))
    if metadata:
        fp.write(metadata_buf)
    fp.write(encoded_body)
    fp.flush()


def add_message(metadata, level, msg):
    ins = metadata.setdefault('inspector', {})
    msgs = ins.setdefault('messages', [])
    k = '[' + str(len(msgs)) + '] '
    msgs.append([level, k + msg])


def die(metadata=None, msg="Error in external search commmand", search_msg=None):
    search_msg = search_msg or msg
    if metadata is None:
        metadata = {}

    metadata['finished'] = True
    add_message(metadata, 'ERROR', search_msg)
    sio = StringIO()
    writer = csv.writer(sio)
    writer.writerow(['ERROR'])
    writer.writerow([msg])
    write_chunk(sys.stdout, metadata, sio.getvalue())
    sys.exit(1)

class Singleton(object):
    '''
    A non-thread-safe helper class to ease implementing singletons.
    This should be used as a decorator -- not a metaclass -- to the
    class that should be a singleton.
    The decorated class can define an `__init__` function

    To get the singleton instance, use the `getInstance` method. Trying
    to use `__call__` will result in a `TypeError` being raised.

    Limitations: The decorated class cannot be inherited from itself.
    '''
    def __init__(self, decorated):
        self._decorated = decorated

    def __call__(self):
        raise TypeError('Use `getInstance()` to access the Singleton')

    def __instancecheck__(self, inst):
        return isinstance(inst, self._decorated)

    def getInstance(self, **kwargs):
        '''
        returns the singleton instance of the decorated object.
        When called first, call the init method of the decorated object
        Thereafter, return the object that was created first.
        '''
        try:
            return self._instance
        except AttributeError:
            self._instance = self._decorated(**kwargs)
            return self._instance

@Singleton
class FileStringHandler(object):
    """
    An utility class handles file and string encoding between py2 and py3 mode
    This class ensures the following:
        1. On Windows, the \n character at the end is mapped to \r\n instead.
           This causes the length of the string to be different than the length of the string
           reported in the transport header, which comes from calling len on the string while
           it only contains \n.
           The fix is to encode the string to ensure the a correct string len. The encoding
           is needed to also handle the unicode case anyway.
        2. Allocate the fp buffer when writing the encoded string.
    """
    def __init__(self):
        self.py3 = False
        if sys.version_info >= (3, 0):
            self.py3 = True

    def get_writer(self, fh):
        if fh is None:
            fh = sys.stdout
        return_fh = fh.buffer if self.py3 and hasattr(fh, 'buffer') else fh
        return return_fh

    def encode_string(self, s):
        return_s = s.encode('utf-8') if self.py3 else s
        return return_s
