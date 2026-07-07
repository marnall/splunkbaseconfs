
import os

import splunk.entity
import splunk.Intersplunk as sis

import logging as logger

logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s %(message)s',
                   filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','cross_correlation_helper.log'),
                   filemode='a')



def execute():
    try:
        resultRows,dummy,settingsDict = sis.getOrganizedResults()
        keywordList, optionsDict = sis.getKeywordsAndOptions()

        args = {}
        args.update(settingsDict)
        args.update(optionsDict)

        for result in resultRows:

            for field in result:
                if (field.find("population_dc_")==0):
                    continue
                if ("population_dc_" + field in result) :
                    result[field] = str(result[field]) + ":" + str(result["population_dc_" + field])
                    del result["population_dc_" + field]

        sis.outputResults(resultRows, {})

    except Exception, e:
        logger.error(e)
        sis.generateErrorResults(str(e))



if __name__ == '__main__':
    execute()

