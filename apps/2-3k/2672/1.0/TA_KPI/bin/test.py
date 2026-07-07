myET = ['nest_base', 'temperature_base', 'thermostat']
myKPIs = [ { "eventtype" : "nest_base", "kpis" : "temp_f:70", "_user" : "nobody", "_key" : "5509a168911c2775a74b8a51" }, { "eventtype" : "temperature_base", "kpis" : "temp_f:70", "_user" : "nobody", "_key" : "5509a168911c2775a74b8a52" }, { "eventtype" : "thermostat", "kpis" : "target_temperature:24;temp_c:25", "_user" : "nobody", "_key" : "5509a168911c2775a74b8a53" } ]
print "EventTypes: %s \nKPIS: %s"%(myET,myKPIs)
nresults = [s.split(";") for s in [r["kpis"] for r in [t for t in myKPIs if t["eventtype"] in myET]]]
results = {}
for n in nresults:
	for m in n:
		tmp = m.split(":")
		results[tmp[0]] = tmp[1]
print "\n\n%s"%results
#"%s"%filter([t for t in myKPIs if t.eventtype in myET], myKPIs)

