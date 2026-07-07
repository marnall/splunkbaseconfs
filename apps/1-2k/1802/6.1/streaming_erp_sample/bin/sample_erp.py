"""
This is a sample script which can be used as an external result provider.  
"""

import sys
import os
import json
import time
import StringIO
import gzip
from erpwriter import ChunkedWriter

def _serializeEvents(results):
    import splunk.Intersplunk
    strio = StringIO.StringIO()
    splunk.Intersplunk.outputStreamResults(results, outputfile=strio)
    result = strio.getvalue()
    strio.close()
    return result

def generateEvents(chunk_writer, count):
    results = []
    t = time.time()
    for i in xrange(count):
        r = {'_time' : t, '_raw': time.strftime("%a, %d %b %Y %H:%M:%S %Z", time.localtime(t)) + " - this is event number " + str(i) }
        results.append(r)
        if len(results) > 1000:
           cw.write(None, _serializeEvents(results))
           results = []
        t -= 1
    cw.write(None, _serializeEvents(results))               

def generateRaw(chunk_writer, count):
    body = []
    size = 0
    t = time.time()
    for i in xrange(count):
       if size > 64*1024:
          body.append('') # so there can be a trailing NL
          chunk_writer.write(None, '\n'.join(body))
          body = []
          size = 0
       event = time.strftime("%a, %d %b %Y %H:%M:%S %Z", time.localtime(t)) + " - this is event number " + str(i) 
       size += len(event)
       body.append(event)
       t  -= 1

    if len(body) > 0:
       body.append('') # so there can be a trailing NL
       chunk_writer.write(None, '\n'.join(body))

def setupHeader(args):
    header = {}
    # set some fields:
    # 1. index  is a required field, otherwise events will be thrown away during the filtering step
    # 2. source is a highly recommended field so we can bootstrap the config from props.conf 
    header['field.index']      = args["conf"]["indexes"][0]["name"]

    if isGenerating(args):
        # set some fields:
        header['field.source']     = '/path/to/some/source'
        header['field.sourcetype'] = 'albanian_magic'
        header['field.host']       = 'windbag.example.com'
        header['field.speed']      = 'fast'

        # search time props
        header['props.EXTRACT-foo']  = 'number (?<number>\\d+)$'
        header['props.KV_MODE']      = 'NONE'

        # "index time" props
        header['props.TIME_FORMAT'] = '%a, %d %b %Y %H:%M:%S %Z'
        header['props.TIME_PREFIX'] = '^'
        header['props.MAX_TIMESTAMP_LOOKAHEAD'] = '30'
        header['props.SHOULD_LINEMERGE'] = 'false'
        header['props.ANNOTATE_PUNCT']   = 'false'
        #header['props.DATETIME_CONFIG']  = 'NONE'

    # add fields defined in indexes.conf for this index
    for k,v in args["conf"]["indexes"][0].iteritems():
       if k.startswith("field."):
          header[k] = v

    return header


def outputGenerated(args):
    header = setupHeader(args)

    # now generate as many events as required by this index 
    events = 1000
    try:
       events = int(args["conf"]["indexes"][0]["event.count"])
    except:
       pass

    mode = args["conf"]["indexes"][0].get("data.mode", "raw")

    # print header only once per source/sourcetype/host
    cw = ChunkedWriter(mode)
    cw.write(header, None)

    if mode == "raw":
       generateRaw(cw, events)
    elif mode == "events":
       generateEvents(cw, events)
    else:
       raise Exception("Unknown mode=" + mode)

def sendRaw(cw, header, file_path):
    # add additional fields to the header
    header['field.source'] = file_path
    cw.write(header, None)

    # write the chunks
    body = []
    size = 0
    if os.path.splitext(file_path)[1] == '.gz':
        openfct = lambda x: gzip.open(x)
    else:
        openfct = lambda x: open(x)

    with openfct(file_path) as f:
        for line in f:
            if size > 64*1024:
                cw.write(None, ''.join(body))
                body = []
                size = 0
            size += len(line)
            body.append(line)
    if len(body) > 0:
        cw.write(None, ''.join(body))

def getFiles(files, path):
    if os.path.isfile(path):
        files.append(path)
    elif os.path.isdir(path):
        for f in os.listdir(path):
            getFiles(files, os.path.join(path, f))
    else:
        sys.stderr.write('ERROR  path {0} is not a file or a directory\n'.format(path))

def isGenerating(args):
    return ("data.path" not in args["conf"]["indexes"][0])

# sample header line 
# {"action":"search","conf":{"provider":{"family":"windbag","mode":"stream"},"indexes":[{"name":"sample_vix",

# parse args passed to us as a single line json object
line = sys.stdin.readline()
args = json.loads(line)

if ("data.path" in args["conf"]["indexes"][0]):
    # get data from path
    path = os.path.expandvars(args["conf"]["indexes"][0]["data.path"])

    cw = ChunkedWriter("raw")
    header = setupHeader(args)
    files = []
    getFiles(files, path)
    for f in files:
        sys.stderr.write("DEBUG  reading file {0}\n".format(f))
        sendRaw(cw, header, f)
else:
    sys.stderr.write("INFO virtual index has no vix.data.path, generating "
                     "events\n")
    outputGenerated(args)

