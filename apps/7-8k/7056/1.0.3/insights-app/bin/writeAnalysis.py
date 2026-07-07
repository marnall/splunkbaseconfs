import os
import sys
import splunk.Intersplunk
from helper.log_helper import LoggerClass

class FileWriter:         
    
    def writetoJson(self, logger): 
        results = []
        try: 
            logger.info("Writing Analysis")    
            base_folder = os.environ['SPLUNK_HOME']     
            data_folder = sys.argv[1]
            analysis_name =  sys.argv[2]
            path = os.path.join(base_folder,"etc", "apps", "insights-app", "local", "saved_analysis", data_folder)  
            isExist = os.path.exists(path)
            if not isExist: 
                os.makedirs(path)    
            filePath= os.path.join(path, analysis_name)              
            with open(filePath , "w") as handle:
                handle.write(sys.argv[3])
                handle.write("\n")    
        except:
            import traceback
            stack =  traceback.format_exc()      
            logger.critical("Error 370 : Traceback: " + str(stack))
            results = splunk.Intersplunk.generateErrorResults("Error Code: "+ str(370))
            splunk.Intersplunk.outputResults( results )
   
    
if __name__ == "__main__":  
    loggerObj = LoggerClass()  
    logger = loggerObj.setup_logging()
    file_writer_object= FileWriter()
    file_writer_object.writetoJson(logger)
    