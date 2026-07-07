# Copyright (C) 2013 Consist Software Solutions GmbH. All Rights Reserved. Version 0.2, 2013-03-07.
# This work is licensed under the Creative Commons Attribution 3.0 Unported License. To view
# a copy of this license, visit http://creativecommons.org/licenses/by/3.0/ or send a letter to
# Creative Commons, 444 Castro Street, Suite 900, Mountain View, California, 94041, USA.
import re
import splunk.Intersplunk as si

if __name__ == '__main__':
    try:
        keywords,options = si.getKeywordsAndOptions()
        scale = options.get('scale', None)
        if scale == None:
            scaleField = options.get('field', None)
            if scaleField == None:
                si.generateErrorResults("'scale' or 'field' argument required, such as scale=x or field=foo")
                exit(0)
        else:
            scaleField = None
            try:
                scale = float(scale)
            except:
                si.generateErrorResults("'scale' argument must be numerical")
                exit(0)
        pattern = options.get('pattern', None)
        if pattern == None:
            si.generateErrorResults("'pattern' argument required, such as pattern=y")
            exit(0)
        inverse = options.get('inverse', None)
        digits = options.get('round', None)
        results,dummyresults,settings = si.getOrganizedResults()
        for result in results:
            if scaleField != None:
                try:
                    scale = float(result[scaleField])
                except:
                    pass
            for field, value in result.iteritems():
                if re.search(pattern, field) != None:
                    try:
                        value = float(result.get(field, None))
                        if inverse:
                            result[field] = value * scale
                        else:
                            result[field] = value / scale
                        if digits != None:
                            result[field] = round(result[field], int(digits))
                    except:
                        pass
        si.outputResults(results)
    except Exception, e:
        import traceback
        stack = traceback.format_exc()
        si.generateErrorResults("Error '%s'. %s" % (e, stack))
