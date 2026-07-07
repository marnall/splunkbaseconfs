import os
import sys
import json
import splunk.Intersplunk
from helper.log_helper import LoggerClass

class FileReader:
    def readJson(self, logger):
        results = []
        result={}        
        try: 
            logger.info("Reading Analysis")             
            base_folder = os.environ['SPLUNK_HOME']        
            data_folder = sys.argv[1]
            analysis_name =  sys.argv[2]            
            path = os.path.join(base_folder,"etc", "apps", "insights-app", "local", "saved_analysis", data_folder)  
            isExist = os.path.exists(path)           
            if not isExist: 
                logger.info("Path is not found: " + path) 
                   
            filePath = os.path.join(path, analysis_name)         
           
            output=[]
            selected_fields=[]
            aggregation=[]
            filter_data=[]
            
            with open(filePath) as handle:
                result = json.load(handle)
                selected_fields = result[0]['Selected Fields']
                aggregation = result[0]['Aggregation']
                filter_data = result[0]['Filter']
                output.append({'userName' : result[0]['UserName']})
                output.append({'Name' : result[0]['Name']})
                
                for sf in selected_fields:  
                    
                    output.append(sf)
                    
                for ag in aggregation:
                    output.append(ag)
                    
                for fl in  filter_data:
                    output.append(fl)                    
             
                splunk.Intersplunk.outputResults(output)  
        except:
            import traceback
            stack =  traceback.format_exc()      
            logger.critical("Error Code 363: Traceback: " + str(stack))
            results = splunk.Intersplunk.generateErrorResults("Error Code: "+ str(363))
            splunk.Intersplunk.outputResults( results )
     
if __name__ == "__main__":
    loggerObj = LoggerClass()  
    logger = loggerObj.setup_logging()
    file_reader_object= FileReader();
    file_reader_object.readJson(logger)
    
    