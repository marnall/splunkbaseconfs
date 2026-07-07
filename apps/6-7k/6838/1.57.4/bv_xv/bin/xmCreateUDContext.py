# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
import sys
import saUtils
import splunk.Intersplunk as si
import os
import logging

logging.basicConfig(level=logging.ERROR, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

def usage(message):

    if len (message) > 0:
        sys.stderr.write (message + "\n");

    usageStatement = "xmCreateUDContext application app name <contextName> container <contextContainer> class <contextClass> type (domain|average_centered|median_centered) terms [term1,term2,...] avg <avgValue> count <countValue> shape <shape> endshape <endShape> max <maxValue> median <medianValue> min <minValue> notes <notes> read <readValue> write <writeValue> search <searchValue> size <sizeValue> uom <uomValue>"
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    lastArg = ''
    application=''
    containerName=''
    contextName=''
    className=''
    type=''
    terms=''
    avg=''
    count=''
    shape=''
    endShape=''
    min=''
    max=''
    median=''
    read=''
    write=''
    notes=''
    search=''
    size=''
    width=''
    uom=''
    doSave='true'
    doUpdate='false'
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmCreateUDContext starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) < 2:
            usage ("Not enought arguments!")

        containerName = sys.argv[1];

        for arg in sys.argv[1:]:
            if arg.lower() == "container":
                lastArg="container"
            elif arg.lower() == "name":
                lastArg="name"
            elif arg.lower() == "application":
                lastArg="application"
            elif arg.lower() == "class":
                lastArg="class"
            elif arg.lower() == "terms":
                lastArg="terms"
            elif arg.lower() == "type":
                lastArg="type"
            elif arg.lower() == "avg":
                lastArg="avg"
            elif arg.lower() == "count":
                lastArg="count"
            elif arg.lower() == "shape":
                lastArg="shape"
            elif arg.lower() == "endshape":
                lastArg="endShape"
            elif arg.lower() == "min":
                lastArg="min"
            elif arg.lower() == "max":
                lastArg="max"
            elif arg.lower() == "median":
                lastArg="median"
            elif arg.lower() == "read":
                lastArg="read"
            elif arg.lower() == "write":
                lastArg="write"
            elif arg.lower() == "notes":
                lastArg="notes"
            elif arg.lower() == "search":
                lastArg="search"
            elif arg.lower() == "size":
                lastArg="size"
            elif arg.lower() == "width":
                lastArg="width"
            elif arg.lower() == "uom":
                lastArg="uom"
            elif arg.lower() == "save":
                lastArg="save"
            elif arg.lower() == "update":
                lastArg="update"
            elif lastArg == "application":
                application = arg
                lastArg=''
            elif lastArg == "container":
                containerName = arg
                lastArg=''
            elif lastArg == "name":
                contextName = arg
                lastArg=''
            elif lastArg == "class":
                className = arg
                lastArg=''
            elif lastArg == "type":
                type = arg
                lastArg=''
            elif lastArg == "terms":
                terms = arg
                lastArg=''
            elif lastArg == "avg":
                avg = arg
                lastArg=''
            elif lastArg == "count":
                count = arg
                lastArg=''
            elif lastArg == "shape":
                shape = arg
                lastArg=''
            elif lastArg == "endShape":
                endShape = arg
                lastArg=''
            elif lastArg == "min":
                min = arg
                lastArg=''
            elif lastArg == "max":
                max = arg
                lastArg=''
            elif lastArg == "median":
                median = arg
                lastArg=''
            elif lastArg == "read":
                read = arg
                lastArg=''
            elif lastArg == "write":
                write = arg
                lastArg=''
            elif lastArg == "notes":
                notes = arg
                lastArg=''
            elif lastArg == "search":
                search = arg
                lastArg=''
            elif lastArg == "size":
                size = arg
                lastArg=''
            elif lastArg == "width":
                width = arg
                lastArg=''
            elif lastArg == "uom":
                uom = arg
                lastArg=''
            elif lastArg == "save":
                doSave = arg
                lastArg=''
            elif lastArg == "update":
                doUpdate = arg
                lastArg=''
            else:
                usage ("Invalid Argument:" + arg)

        if len(containerName) > 0:
            argList.append("-N")
            argList.append(containerName)
        else:
            usage ("Missing argument: CONTAINER containerName");

        if len(contextName) > 0:
            argList.append("-n")
            argList.append(contextName)
        else:
            usage ("Missing argument: CONTEXT contextName");

        if len(application) > 0:
            argList.append("-A")
            argList.append(application)

        if len(className) > 0:
            argList.append("-b")
            argList.append(className)

        if len(terms) > 0:
            argList.append("-b")
            argList.append(className)
        else:
            usage ("Missing argument: CLASS className");

        if len(terms) > 0:
            argList.append("-t")
            argList.append(terms)
        else:
            usage ("Missing argument: CLASS className");

        if len(type) > 0:
            argList.append("-z")
            argList.append(type)

        if len(avg) > 0:
            argList.append("-a")
            argList.append(avg)

        if len(count) > 0:
            argList.append("-c")
            argList.append(count)

        if len(shape) > 0:
            argList.append("-p")
            argList.append(shape)
        else:
            usage ("Missing argument: SHAPE <shape>");

        if len(endShape) > 0:
            argList.append("-e")
            argList.append(endShape)
        else:
            usage ("Missing argument: ENDSHAPE <shape>");

        if len(min) > 0:
            argList.append("-m")
            argList.append(min)

        if len(max) > 0:
            argList.append("-x")
            argList.append(max)

        if len(median) > 0:
            argList.append("-M")
            argList.append(median)

        if len(read) > 0:
            argList.append("-R")
            argList.append(read)

        if len(write) > 0:
            argList.append("-W")
            argList.append(write)

        if len(notes) > 0:
            argList.append("-o")
            argList.append(notes)

        if len(search) > 0:
            argList.append("-S")
            argList.append(search)

        if len(search) > 0:
            argList.append("-S")
            argList.append(search)

        if len(size) > 0:
            argList.append("-d")
            argList.append(size)

        if len(width) > 0:
            argList.append("-w")
            argList.append(width)

        if len(uom) > 0:
            argList.append("-u")
            argList.append(uom)

        if doUpdate.lower() == "true":
            argList.append("-U")

        if len(uom) > 0:
            argList.append("-s")
            argList.append(doSave)

        logging.info("Calling xmCreateUDContext with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmCreateUDContext", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)
