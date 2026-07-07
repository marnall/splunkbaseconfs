OVERVIEW
===========
pointerset <target_field> pointer=<ptrField> ptrFieldFilter="<srcField-1|srcField-2|src*" default=<default value>

target_field:
 - The field to create and set
 - Required

pointer:
 - The field that points to the name of the field with the value
 - Required

ptrFieldFilter:
 - This option can accept basic patterns for mattching with a *, no other wildcard characters are available.
 - Optional, default value is * (all fields)
 - Warning: Performance over large datasets almost requires you to specify the ptrFieldFilter option.  This list should only contain field names that 'pointer' can point to.

default:
 - Optional, default value is ""

Example Search: 
======================================================================================================
| tstats count where index=* OR index=_*  earliest=-30d@d by index, sourcetype, _time span=1h@h
| stats count AS trust_factor min(count) AS min perc5(count) AS perc5 perc25(count) AS perc25 perc50(count) AS perc50 perc75(count) AS perc75 perc95(count) AS perc95 perc97(count) AS perc97 perc99(count) AS perc99 max(count) AS max stdev(count) AS stdev by index, sourcetype
| eval IQR=perc75-perc25
| eval lower_outlier_threshold=perc25-(IQR*1.5)
| eval lower_outlier_threshold=if(lower_outlier_threshold<0,0,lower_outlier_threshold)
| eval upper_outlier_threshold=perc75+(IQR*1.5)
| foreach perc* stdev IQR
    [eval <<FIELD>>=round(<<FIELD>>,1)]
| sort - stdev
| lookup pointerset_threshold_example.csv index,sourcetype OUTPUT
| fillnull value=upper_outlier_threshold threshold_field
| pointerset threshold pointer=threshold_field default=0 ptrFieldFilter="perc*|*outlier_threshold"




