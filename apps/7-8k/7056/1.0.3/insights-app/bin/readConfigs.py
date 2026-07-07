import os
import sys
import json
import splunk.Intersplunk
from helper.log_helper import LoggerClass

class ConfigReader:
    def readJson(self, logger):
        results = []
        result={} 
        merged_content =[]       
        try:  
            logger.info("Reading Config")           
            base_folder = os.environ['SPLUNK_HOME']         
            data_folder = sys.argv[1]          
            path = os.path.join(base_folder,"etc", "apps", "insights-app", "local", data_folder) 
            isExist = os.path.exists(path)           
            if not isExist: 
                logger.info("Path is not found: " + path)  
            
            
            for file_name in [file for file in os.listdir(path) if file.endswith('.json')]:
                ##filePath = os.path.join(path, "CustomerInformation_OrderInformation.json") 
                with open(os.path.join(path, file_name)) as json_file:
                    merged_content.extend(json.load(json_file))     
                
            
            splunk.Intersplunk.outputResults(merged_content)  
        except:
            import traceback
            stack =  traceback.format_exc()
            logger.critical("Error 325: Traceback: " + str(stack))
            results = splunk.Intersplunk.generateErrorResults("Error Code: "+ str(325))            
            splunk.Intersplunk.outputResults( results )
     
if __name__ == "__main__":
    loggerObj = LoggerClass()  
    logger = loggerObj.setup_logging()
    file_reader_object= ConfigReader()
    file_reader_object.readJson(logger)
    
    