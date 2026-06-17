import re,sys,os,math
import splunk.Intersplunk as si
import re

def buildnewresult(result,resultfieldname,copyfields,compiledpattern):
    newres = {}
    for cf in copyfields:
        newres[cf] = result.get(cf)
    matches = compiledpattern.match( resultfieldname )
    newres["delimitedfield_name"] = "".join( matches.groups() )
    newres["delimitedfield_value"] = result.get(resultfieldname)
    return newres

if __name__ == '__main__':
    try:
        keywords,options = si.getKeywordsAndOptions()

        prefix = options.get('prefix', None)
        suffix = options.get('suffix', None)
        pattern = options.get('pattern', None)
        if prefix == None and suffix == None and pattern == None:
            si.generateErrorResults("prefix and/or suffix, or pattern required, such as prefix=\"foo__\", suffix=\"_foo\", pattern=\"foo__(.*)_bar_(.*)_foo\"")
            exit(0)
        if pattern == None:
            pattern = "(.*)"
            if prefix != None:
                pattern = prefix + pattern
            if suffix != None:
                pattern = pattern + suffix
        compiledpattern = re.compile(pattern, re.I)

        copyfields = ["_time"]
        try:
            for cf in options.get('copyfields', 'None').split(','):
                copyfields.append(cf)
        except Exception, e:
            None

        results,dummyresults,settings = si.getOrganizedResults()

        newresults = []
        for result in results:
            for resultfieldname,resultfieldval in result.items():
                if compiledpattern.match(resultfieldname) and len(result.get(resultfieldname).strip()) > 0:
                    newresults.append(buildnewresult(result,resultfieldname,copyfields,compiledpattern))
        si.outputResults(newresults)
    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        si.generateErrorResults("Error '%s'. %s" % (e, stack))

