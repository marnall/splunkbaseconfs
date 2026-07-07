import os
import sys

import splunk.Intersplunk
from helper.log_helper import LoggerClass

class AnalysisDeleter:
    def deleteAnalysis(self, logger):
        results = []
        output=[]                
        try:  
            logger.info("Deleting Analysis")             
            base_folder = os.environ['SPLUNK_HOME']        
            data_folder = sys.argv[1]
            analysis_name =  sys.argv[2]            
            path = os.path.join(base_folder,"etc", "apps", "insights-app", "local", "saved_analysis", data_folder) 
            filePath = os.path.join(path, analysis_name + ".json")    
            isExist = os.path.exists(filePath)           
            if not isExist: 
                logger.info("Path is not found: " + filePath) 
            else: 
                os.remove(filePath)
                output.append({'result' : "successful deletion of " + analysis_name})
                splunk.Intersplunk.outputResults(output)
                logger.info("deleted analysis " +  analysis_name)
                     
        except:
            import traceback
            stack =  traceback.format_exc()
            logger.critical("Error 3998: Traceback: " + str(stack))
            results = splunk.Intersplunk.generateErrorResults("Error Code: "+ str(3998))            
            splunk.Intersplunk.outputResults( results )
     
if __name__ == "__main__":
    loggerObj = LoggerClass()  
    logger = loggerObj.setup_logging()
    analysis_delter_object= AnalysisDeleter()
    analysis_delter_object.deleteAnalysis(logger)
    
    