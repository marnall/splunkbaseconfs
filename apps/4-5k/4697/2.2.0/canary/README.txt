# README for the Canary app. 

Documentation 
For all documentation see:
https://sideviewapps.com/apps/canary

Requirements 
  Splunk Enterprise 8.0 or higher, or Splunk Cloud 
  
  SEARCH HEAD(S)
    This app is to be installed on the Search Head.
    the "Sideview Utils" app is not required and should not be installed anywhere. 
    (Prior versions of Canary also required having Sideview Utils installed for 
    some functionality to work correctly.)
  
  INDEXER(S)
    This app is NOT to be installed on the indexers.

  FORWARDER(S)
    This app is NOT to be installed on any forwarders. 


Splunk Cloud compatibility 
  Yes. Canary has been Cloud-compatible for many versions now. 

Search Head Cluster Considerations
  None that we know of. Put this on your SHC and it should be fine. 

