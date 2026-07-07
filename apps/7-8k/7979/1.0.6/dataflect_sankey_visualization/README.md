# Sankey Visualization by Dataflect

Documentation:
https://docs.dataflect.com/dataflect-sankey

## Sample Search

```
| makeresults
| eval flows="S1>A 10;S1>B 5;S2>A 3;S2>C 7;S3>B 8;A>X 9;A>Y 4;B>X 6;B>Y 5;C>Y 7;X>Z1 8;X>Z2 7;Y>Z2 9;Y>Z3 6"
| makemv delim=";" flows
| mvexpand flows
| rex field=flows "(?<source>[^> ]+)\s*>\s*(?<target>[^ ]+)\s+(?<value>\d+)"
| eval value=tonumber(value)
| table source target value
```
