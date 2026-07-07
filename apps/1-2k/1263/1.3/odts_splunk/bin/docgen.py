# Copyright (C) Dmitry Tomko
# email: dtomko@iba.by
# generate office documents
# v 1.0 Initial release. Only ODT type supported
# v 1.0
# v 1.1 add support to generate pdf, doc, txt, rtf
import sys, os.path, datetime, argparse, csv, urllib, copy
import splunk.Intersplunk, splunk.search, splunk.util, splunk.entity
import logging as logger
from appy.pod.renderer import Renderer
from appy.pod import PodError
from appy.pod.parts import OdtTable

csv.field_size_limit(10485760)
# helper function to get unique values for required fields
def unique(field, entries=None):
    global events
    if not entries:
        entries = events
    return dict.fromkeys([result[field] for result in entries if field in result]).keys()

# helper function to get only events where required field is equal to required value
def events_eq_value(field, value, entries=None):
    global events
    if not entries:
        entries = events
    return [result for result in entries if (field in result and result[field] == value)]


def decodeMV(s, vals):
    if len(s) == 0:
        return False

    tok = ""
    inval = False

    i = 0
    while i < len(s):
        if not inval:
            if s[i] == '$':
                inval = True
            elif s[i] != ';':
                return False
        else:
            if s[i] == '$' and i + 1 < len(s) and s[i + 1] == '$':
                tok += '$'
                i += 1
            elif s[i] == '$':
                inval = False
                vals.append(tok)
                tok = ""
            else:
                tok += s[i]
        i += 1
    return True


def readResultsAndFields():
    '''
    Read results and fields
    '''
    logger.debug("entering readResultsAndFields")
    input_buf = sys.stdin
    results = []
    MV_ENABLED = True
    settings = {} # dummy
    # until we get a blank line, read "attr:val" lines, setting the values in 'settings'
    attr = last_attr = None
    while True:
        line = input_buf.readline()
        line = line[:-1] # remove lastcharacter(newline)
        if len(line) == 0:
            break
        colon = line.find(':')
        if colon < 0:
            if last_attr:
                settings[attr] = settings[attr] + '\n' + urllib.unquote(line)
            else:
                continue
                # extract it and set value in settings
        last_attr = attr = line[:colon]
        val = urllib.unquote(line[colon + 1:])
        settings[attr] = val

    csvr = csv.reader(input_buf)
    header = []
    first = True
    mv_fields = []
    for line in csvr:
        if first:
            header = line
            first = False
            # Check which fields are multivalued (for a field 'foo', '__mv_foo' also exists)
            if MV_ENABLED:
                for field in header:
                    if "__mv_" + field in header:
                        mv_fields.append(field)
            continue
            # need to maintain field order
        result = splunk.util.OrderedDict()
        i = 0
        for val in line:
            result[header[i]] = val
            i = i + 1
        for key in mv_fields:
            mv_key = "__mv_" + key
            if key in result and mv_key in result:
                # Expand the value of __mv_[key] to a list, store it in key, and delete __mv_[key]
                vals = []
                if splunk.Intersplunk.decodeMV(result[mv_key], vals):
                    result[key] = copy.deepcopy(vals)
                    if len(result[key]) == 1:
                        result[key] = result[key][0]
                    del result[mv_key]
        results.append(result)
    fields = [field for field in header if not field.startswith("__mv_")]
    return results, settings, fields

# helper function to generate table
def dump_table(entries=None, header=None):
    logger.debug("entering dump_table")
    global events, fields
    if not entries:
        entries = events
    if not header:
        header = fields
    if entries:
        table = OdtTable(name="SplunkTable", paraStyle="podTable", cellStyle="podTableCell", nbOfCols=len(entries[0]),
            paraHeaderStyle="podTableHeaderCell", cellHeaderStyle="podHeaderCell")
        table.startTable()
        # dump header first
        table.startRow()
        for field in header:
            table.dumpCell(content=field, header=True)
        table.endRow()
        # dump rows
        for event in entries:
            table.startRow()
            for field in header:
                if event[field]:
                    table.dumpCell(event[field])
                else:
                    table.dumpCell("")
            table.endRow()
        table.endTable()
        return table.get()
    else:
        return ''


def dump_value(field=None, entries=None):
    logger.debug("entering dump_value")
    global events
    global fields
    if not entries:
        entries = events
    if not field:
        for fld in fields:
            if not fld.startswith("_"):
                return entries[0][fld]
    return entries[0][field]

if __name__ == "__main__":
    # setup logging
    logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s %(message)s',
        filename=os.path.join(os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', 'docgen.log'), filemode='a')

    if len(sys.argv) < 1:
        splunk.Intersplunk.parseError("No sufficient arguments provided")

    parser = argparse.ArgumentParser()
    parser.add_argument('-tfile')
    parser.add_argument('-ofile')
    parser.add_argument('-t', action='store_true', default=True)
    parser.add_argument('-key')
    inputs = parser.parse_args()
    #list of variables for render.run method
    # initial list includes all helper functions
    var_list = {"unique":unique,"events_eq_value":events_eq_value,"dump_table":dump_table, "dump_value":dump_value}

    #if inputs.tfile:
    #	if not os.path.exists(inputs.tfile) and os.path.isabs(inputs.tfile):
    #		splunk.Intersplunk.parseError("Template file does not exist")
    if    inputs.tfile:
        if os.path.isabs(inputs.tfile):
            tfile_path = inputs.tfile
        else:
            tfile_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), ".." + os.sep + "templates" + os.sep + inputs.tfile))
    else:
        tfile_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), ".." + os.sep + "templates" + os.sep + "dump_table.odt"))

    if inputs.tfile:
        if not os.path.exists(tfile_path):
            splunk.Intersplunk.parseError("Template file does not exist")

    if inputs.ofile:
        if inputs.ofile[inputs.ofile.rfind(".") + 1:] not in ["odt", "pdf", "doc", "rtf", "txt"]:
            splunk.Intersplunk.parseError("This document type is not supported for generation")
        if os.path.isabs(inputs.ofile):
            ofile_path = inputs.ofile
        else:
            ofile_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), ".." + os.sep + "results" + os.sep + inputs.ofile))
    else:
        ofile_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), ".." + os.sep + "results" + os.sep + "results.odt"))

    if inputs.t:
        localtime = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        ofile_path = ofile_path[:ofile_path.rfind('.')] + '_' + localtime + "." + ofile_path[ofile_path.rfind('.') + 1:]

    if inputs.key:
        key_field = inputs.key
        logger.debug("key: " + key_field)

    logger.debug("ofile path: " + ofile_path)
    logger.debug("tfile path: " + tfile_path)


    # main
    try:
    #	collect main results
        #events,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
        (events, settings, fields ) = readResultsAndFields()
        var_list["events"] = events
        logger.debug("events:")
        logger.debug(events)
        logger.debug("settings:")
        logger.debug(settings)
        logger.debug("fields:")
        logger.debug(fields)
        is_OO = False
        # try to find out path to OO python binary
        if inputs.ofile:
            if not inputs.ofile.endswith(".odt"):
                is_OO = True
                # trying to get path to python oo binary from settings
                try:
                    entities = splunk.entity.getEntities(['odts_splunk', 'configendpoint', 'odts_config'],
                        namespace="odts_splunk",
                        owner='nobody', sessionKey=settings['sessionKey'])
                    logger.debug("entities:")
                    logger.debug(entities)
                    for i, c in entities.items():
                        if "oo_python_path" in c:
                            oo_python_path = c['oo_python_path']
                            logger.debug("oo_python_path = " + oo_python_path)
                        if "oo_python_port" in c:
                            oo_python_port = int(c['oo_python_port'])
                            logger.debug("oo_python_port = " + str(oo_python_port))
                        if (oo_python_path == "" or (
                            not os.path.exists(oo_python_path) and not os.path.exists(oo_python_path + ".exe"))):
                            splunk.Intersplunk.parseError("path to OO python binary is not valid (empty or not exist)")
                        if oo_python_port < 0 or oo_python_port > 65536:
                            splunk.Intersplunk.parseError("OO server port is not valid")
                except Exception, e:
                    splunk.Intersplunk.parseError("Problem accesing configuration for app")
                    #	get key_field used for several splunk results
        if inputs.key and key_field:
            logger.debug("unique values for key_field")
            logger.debug(unique(key_field, events))
            for elem in unique(key_field, events):
                elem_list = [result for result in events if (key_field in result and result[key_field] == elem)]
                #remove key_field elements
                map(lambda x: x.pop(key_field), elem_list)
                logger.debug("elem_list for:" + elem)
                logger.debug(elem_list)
                var_list[elem]=elem_list
            fields.remove(key_field)
        if is_OO:
            if os.name == "nt":
                import win32api
                if not oo_python_path.endswith(".exe"):
                    oo_python_path = oo_python_path + ".exe"
                oo_python_short_path = win32api.GetShortPathName(oo_python_path)
                renderer = Renderer(tfile_path, var_list, ofile_path, oo_python_short_path)
        else:
            renderer = Renderer(tfile_path, var_list, ofile_path)
        logger.debug("var_list:")
        logger.debug(var_list)
        renderer.run()
        # return results (information about generated document
        oresults = [{"gen_doc": os.path.abspath(ofile_path), "gen_time": datetime.datetime.now()}]
        logger.debug("oresults:")
        logger.debug(oresults)
        splunk.Intersplunk.outputResults(oresults)
    except PodError, pe:
    #	import traceback
    #	stack =  traceback.format_exc()
        splunk.Intersplunk.parseError("Error: " + str(pe))
        logger.debug("exception catched:")
        logger.debug(str(pe))