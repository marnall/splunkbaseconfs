import splunk.Intersplunk as si
import time



if __name__ == '__main__':
    try:
        keywords,options = si.getKeywordsAndOptions()
        results,dumb1, dumb2 = si.getOrganizedResults()

        now = time.time()
        # for each result
        for result in results:
            keys = []
            for key in result:
                if (result[key]) :
                    keys.append(key)
            keys.sort()
            result['fieldnames'] = ",".join(keys)
        si.outputResults(results)

    except Exception as e:
        si.generateErrorResults("Error occurred while running the custom command: '%s'" % str(e))
