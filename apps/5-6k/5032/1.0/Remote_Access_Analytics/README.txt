This is where you put all your configurations for this app.

Introduction : 

This application is for monitoring all the users Remote Access This data is  based on VPN logs and Activitis of Users after connecting to their environments using their VPN Access Account.

Requirements :
    
    1)You should have data from Fortinet FortiGate Firewall collected by your Splunk environment.
    2)Make Sure that your Splunk Data Models is Accelerated ("Network Sessions","Network Traffic","Authentication").

                ########################################################################################

The following free Splunk Apps must be installed before you can start using Remote Access Analytics App :

    1) Splunk Common Information Model (CIM) : https://splunkbase.splunk.com/app/1621/
    2) Sankey Diagram visualization : https://splunkbase.splunk.com/app/3112/
    3) Timeline - Custom Visualization : https://splunkbase.splunk.com/app/3120/
    
                ########################################################################################
                
Some Tips After Downloading The Application : 

   Most of The Search Queries in The Application based on Data Model Acceleration : 
   
   There are some fields you may not be able to add them using "Add Extracted" option in your DataModel="Network Sessions" And DataSet=VPN
   So here is the method to add these fields using Regular Expression Option:
   
   First: 
   
    **Disable acceleration in order to edit the Data Model because Data Model cannot be edited if it is accelerated.
     
    **Here is the fields you have to add them first using Regular Expression before using the application.
   
         "tunnelip" field : 
            
            1)Go to Data Models > Network Sessions > VPN > Add Field > Regular Expression.
            2)in "Extract From" menu make it > "_raw"
            3)in "Regular Expression" bar type : .*tunnelip\=(?<tunnelip>([^\s]+))\s
            4)in "Display Name" keep it : tunnelip
            5)Type: IPV4.
            
         ########################################################################################## 
         
         "reason" field : 
         
            1)Go to Data Models > Network Sessions > VPN > Add Field > Regular Expression.
            2)in "Extract From" menu make it > "_raw"
            3)in "Regular Expression" bar type : .*reason\=\"(?<reason>([^\"]+))\".*
            4)in "Display Name" keep it : reason
            5)Type: String.
        ###########################################################################################
        
        "msg" field : 
        
            1)Go to Data Models > Network Sessions > VPN > Add Field > Regular Expression.
            2)in "Extract From" menu make it > "_raw"
            3)in "Regular Expression" bar type : .*msg\=\"(?<msg>([^\"]+))\".*
            4)in "Display Name" keep it : msg
            5)Type: String.
            
        ###########################################################################################
        
        As I mentioned before that All fields should be CIM Compliant : 
        So you have to make sure that src_ip field appears in your Dataset "VPN" under "Network Sessions" DataModel.  
            
            
            
          
          
        
                



