import time,sys,os,traceback,random

#Define debug log
connection_log = open(os.path.join(os.environ["SPLUNK_HOME"], 'var', 'log', 'splunk',"seed_lookups.log"),"a")



def logger(string):
	connection_log.write(time.asctime() + ' - ' + string + "\n")
	connection_log.flush()
	print time.asctime() + ' - ' + string
	return 0



#Define Lookup Path
lookupPath = os.path.join(os.environ["SPLUNK_HOME"], 'etc','apps','SplunkforXenDesktop','lookups')

#Define Lookup Names
lookups = ['farm_lookup.csv','geo_info.csv','group_lookup.csv','sid_lookup.csv',]

#check for file if none then cp in seed file

for file in lookups:
	filepath =  os.path.join( os.environ["SPLUNK_HOME"], 'etc','apps','SplunkforXenDesktop','lookups',file )
	logger("Checking for lookup file! filename="+filepath)
	if os.path.exists(filepath):
		logger("Lookup file exists! filename="+filepath)
	else: 
		seedFilepath = os.path.join( os.environ["SPLUNK_HOME"], 'etc','apps','SplunkforXenDesktop','lookups',file+".seed" )
		logger("file="+filepath+" not found. Checking for seed file!")
		if os.path.exists(seedFilepath):
			
			logger("file="+filepath+".seed found. Copying to:"+filepath)
			seed_txt = seedFilepath.readlines()
		else:
			logger("No seed file exists! filename="+filepath)