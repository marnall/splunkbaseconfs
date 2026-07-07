KPIs

CURRENTLY ONLY STATIC IS AVAILABLE
eventtype : the Splunk eventtype to apply the KPI to.
kpi_description : description of the kpi
kpi_type : The type of KPI - for anything other than static, command must have "dynamic" option set.
	static: Evaluates a single event and compares it to a constant threshold
	aggregate: Evaluates a period of time and compares it to a constant threshold
	percentile: Evaluates a period of time and compares it to a percentile threshold 
	change: Evalutes a period of time and compares it to a percentage change threshold
kpi_compare : determines how to evaluate the kpi. Used only with "static" kpi_type
	gt: greater than
	lt: less than
	eq: equal to
kpi_field: the result field to apply kpi to
kpi_value: the value to compare with
kpi_ok: The value that will appear in the "<fieldname>_kpi_status" field if the kpi is ok. If you specify "diff" as the value, the difference in the values will be returned
kpi_violated: The value that will appear in the "<fieldname>_kpi_status" field if the kpi is violated. If you specify "diff" as the value, the difference in the values will be returned.