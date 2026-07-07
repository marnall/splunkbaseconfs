# Splunk Addon - SA-erlangB
Splunk Supporting Add-on which provides command to use erlangB calculation. 

More details about erlang: https://en.wikipedia.org/wiki/Erlang_(unit)

Parameters:
field (mandatory) = name of field which contains traffic size. Traffic size value(s) needs to be an integer or float value
blocking_factor (optional) = blocking factor as float value (default=0.0001) 
result (optional) = name of result column (default=trunks)

Splunk search example:

```| stats count | eval traffic_field=47.759 | erlang field=traffic_field blocking_factor=0.01 result=trunks```

Support: https://github.com/thories/SA-erlangB/issues/new

---

Credits:

* Splunk SDK: https://github.com/splunk/splunk-sdk-python
* Icon: https://www.iconfinder.com/icons/1055102/calculation_calculator_math_mathematics_icon

