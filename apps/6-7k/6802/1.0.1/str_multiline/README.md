# viz_str_multiline

string multiline

# screenshot


### query
```
| makeresults 
| eval text = split("test2-2,test2-2,test1234567-890", ",") 
| eval icon=split("car,bus,plane", ",") 
| eval color=split("red,blue,orange", ",") 
| table text icon color

```

![sample](./static/sample.png)


# Dependencies

