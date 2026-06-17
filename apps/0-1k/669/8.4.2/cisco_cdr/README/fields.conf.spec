
# if enabled for any field, then a health check will enforce that the values 
# are always single-valued on call-leg events.
# used for high-importance fields like site or group.  Also used for 
# user-defined "stages" for advanced call-flow analytics, where it is 
# essential that each call leg matches only one "stage".

check_single_value  =[true|false]
