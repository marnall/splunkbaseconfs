# mvtable 1.0 works kinda
# 1.01 adapted to Python 3 on splunk 8
# Dominique Vocat (curious.sle@gmail.com)

import sys,splunk.Intersplunk

# define empty lists
result_set = []
results = []

#named options
try:
    keywords, options = splunk.Intersplunk.getKeywordsAndOptions()
    mvfields = options.pop('mvfields','') #fields to loop over
    mvdelim = options.pop('mvdelim','') # not needed anymore i think
    keepfields = options.pop('keepfields','*')
    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()

    mvfields = mvfields.split(',')
    fieldone = mvfields[0] # we just take the first field and later count the number of items in the field (cardinality)
    keepfields = keepfields.split(',')

except Exception as e:
    import traceback
    stack =  traceback.format_exc()
    splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))

try:
    for result in results:
        if isinstance(result[fieldone], list):
            yardstick = len(result[fieldone])
            for i in range(0, yardstick):
                new_result = {}
                for field in mvfields:
                     try:
                         tmp = result[field][i]
                     except:
                         tmp = "NULL"
                         print >> sys.stderr, "we have no value " + str(i) + " in field " + str(field)
                     new_result[field] = tmp
                if keepfields[0] == "*":
                    for field in result:
                        if field not in mvfields:
                            new_result[field] = result[field]
                else:
                    for field in keepfields:
                        new_result[field] = result[field]
                result_set.append(new_result)
        else:
            new_result = {}
            for field in mvfields:
                new_result[field] = result[field]
            if keepfields[0] == "*":
                for field in result:
                    if field not in mvfields:
                        new_result[field] = result[field]
            else:
                for field in keepfields:
                    new_result[field] = result[field]
            result_set.append(new_result)

    splunk.Intersplunk.outputResults( result_set )

except Exception as e:
    import traceback
    stack =  traceback.format_exc()
    splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))
