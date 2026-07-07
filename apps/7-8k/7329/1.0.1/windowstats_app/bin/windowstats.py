import sys
import os
splunkPath = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkPath, 'etc', 'apps', 'windowstats_app', 'lib'))
from splunklib.searchcommands import dispatch, Option, Configuration, EventingCommand
import time
import math





number=0;

def stdev(temp):
 length=len(temp)
 if  length <=1:
  return 0
  
 average = avg(temp)
 std=0
 for r in temp:
  std=std+(float(r)- average)**2
 std=math.sqrt(std/float(length-1))
 return std

def numbering(temp):
 global number
 number=number+1
 return number

def avg(temp):
     return sum(temp) / len(temp)
     
def maximum(temp):
 return max(temp)  

def minimum(temp):
 return min(temp)   

def list_f(temp):
 return str(temp) 

def median(temp):
 temp.sort() 
 return temp[math.floor(len(temp)/2)]
 
def summ(temp): 
 return sum(temp)


def values(temp):
 unique=set(temp)
 return str(list(unique))
 
def dc(temp):
 return len(set(temp))

def mode(temp):
 listcount=list(map(temp.count,temp))
 most=max(listcount) 
 for i in range(len(temp)):
  if listcount[i]== most:
   return temp[i]


def calculate(ftemp,function):
 
   if function == "avg":
    compute= avg(ftemp)
   elif function == "max":
    compute= maximum(ftemp)        
   elif function == "min":
    compute= minimum(ftemp)  
   elif function == "list":
    compute= list_f(ftemp)            
   elif function == "median":
    compute= median(ftemp)
   elif function == "values":
    compute= values(ftemp)
   elif function == "sum":
    compute= summ(ftemp)
   elif function == "mode":
    compute= mode(ftemp)
   elif function == "dc":
    compute= dc(ftemp) 
   elif function == "stdev":
    compute= stdev(ftemp) 
   elif function == "number":
    compute= numbering(ftemp)  
   return compute 
 
@Configuration()
class windowstats(EventingCommand):

    field = Option(doc="field name", require=True, default=None)
    function = Option(doc="function name", require=False, default="avg")
    rename = Option(doc="new created field name", require=False, default="windowstats_result"+"_"+str(time.time()))
    window = Option(doc="window size", require=False, default=100)
    style = Option(doc="group, dynamic or gradual", require=False, default="group") 
    

    def transform(self,records): # records type is: <class 'generator'>
    
      try:
       result = []
       ftemp= []
       stemp= []
       functions= ["avg","stdev","max","min","median","values","sum","list","dc","mode","number"]
       field=self.field 
       function=self.function 
       rename=self.rename 
       window=self.window
       style=self.style
       recordslist= list(records)
       findex=0
       size=len(recordslist)


   
       if function not in functions:
          raise ValueError("wrong function: %s" % function)           


       if  (not window.isnumeric() and window!="-1") or ( int(window)<1 and int(window)!=-1):
          raise ValueError("wrong number: %s" % window) 


       if function not in functions:
          raise ValueError("wrong function: %s" % function)
       
       if  window =="-1" or int(window) > size:
        window = str(size)       


       window=int(window)
       if style == "group":
           for record in recordslist:                       #record type is: <class 'collections.OrderedDict'>
              
              findex=findex%window
              if field not in record:
                    raise ValueError("Missing field: %s" % field)
                   
              stemp.append(record)       
              for key, val in record.items():         # print(record.items()) will be odict_items([('host', 'we8105desk'), ('EventCode', '4689'), ('Process_Name', 'C:\\Program Files\\SplunkUniversalForwarder\\bin\\splunk-winprintmon.exe')]) 
                 if key == field:
                  ftemp.append(int(val))
                  
              if findex+1 == window or recordslist[size-1] == record:
               compute=calculate(ftemp,function)             

                
               
               for r in stemp:
                 r[rename]=compute
                 result.append(r)             
               
               ftemp= []
               stemp= []           

              findex= findex+1
              
              

       elif style == "dynamic":
         left=math.floor(window/2)
         right=window-left 
         if window < size:
          window=window+1
         
         for i in range(right+1):
          ftemp.append(int(recordslist[i][field]))
         
         for i in range(len(recordslist)):
           if i>0 and i+right < len(recordslist):
              ftemp.append(int(recordslist[i+right][field]))
              ftemp.pop(0)
           elif i+right >= len(recordslist)-1 :   
              ftemp.pop(0)
           if i > 0 and left >0:
            if len(stemp)== left and len(stemp)>0:
             stemp.pop(0)
            stemp.insert(len(stemp),int(recordslist[i-1][field])) 
           
           compute=calculate(ftemp+stemp,function) 
           recordslist[i][rename]=compute
           result.append(recordslist[i])
           
           
        
       elif style == "gradual":
         left=math.floor(window/2)
         right=window-left 
         if window < size:
          window=window+1
         
         for i in range(window):
          ftemp.append(int(recordslist[i][field]))
         
         
         for i in range(len(recordslist)):
          mid=ftemp[math.ceil((len(ftemp))/2)]
          if ( i>0 or window==1) and int(recordslist[i][field])==mid and i+right < len(recordslist):
              ftemp.append(int(recordslist[i+right][field]))
              ftemp.pop(0)
          compute=calculate(ftemp,function)
          recordslist[i][rename]=compute
          result.append(recordslist[i])    
              

       
           
       return result  
       
      except Exception as e:
        raise ValueError(e)




if __name__=="__main__":
 dispatch(windowstats,sys.argv, sys.stdin, sys.stdout, __name__) 

  