import splunk.Intersplunk

try:
    results = []
    macro_file = open("my_macros1.txt", "r")
    for line in macro_file:
        line = line.lstrip()
        if line.startswith('m'):
            line = line.rstrip('\n')
            results.append({"macro": line})

    macro_file.close()

except:
    import traceback
    stack = traceback.format_exc()
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

splunk.Intersplunk.outputResults(results)
