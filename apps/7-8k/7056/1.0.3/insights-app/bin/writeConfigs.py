import os
import sys
import splunk.Intersplunk
import json
from helper.log_helper import LoggerClass
class ConfigWriter:
    def writetoJson(self,logger): 
        results = []
        try:
            logger.info("Writing Config")        
            base_folder = os.environ['SPLUNK_HOME']  

            config_name = sys.argv[2]   
            data_folder = sys.argv[1]   

            path = os.path.join(base_folder,"etc","apps","insights-app", "local", data_folder)  
            isExist = os.path.exists(path)
            if not isExist: 
                os.makedirs(path)    
            filePath= os.path.join(path, config_name +".json")           
            with open(filePath, "w") as file:
                     file.write(sys.argv[3])
                     file.write("\n")  
           
                 
        except:
            import traceback
            stack =  traceback.format_exc()      
            logger.critical("Error Code 361 : Traceback: " + str(stack))
            results = splunk.Intersplunk.generateErrorResults("Error Code: "+ str(361))
            splunk.Intersplunk.outputResults( results )
    
if __name__ == "__main__":
    loggerObj = LoggerClass()  
    logger = loggerObj.setup_logging()
    file_writer_object= ConfigWriter()
    file_writer_object.writetoJson(logger)
    