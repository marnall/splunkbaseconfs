#docodoco-for-splunk

##OVERVIEW
You can get local information and organizational infomation from IP address by using this add-on. 


##NOTICE
・It is necessary to contaract with "DocoDoco"(Paid services) separately to use this add-on.
　http://www.docodoco.jp/en/index.html
・Must be able to access the Internet.
  (To request to "api.docodoco.jp".)


##INSTLLATION
1 - Install docodoco-for-splunk Add on
    Download from http://splunkbase.splunk.com

2 - Get "DocoDoco" API key
    How To
    http://www.docodoco.jp/en/areatargeting/howto.html

3 - Set "DocoDoco"API Key in the configuration file
    configuration file
    $SPLUNK_HOME$\etc\apps\docodoco/bin/config.ini
        section "docodoco" key1 = docodoco API key 1
        section "docodoco" key2 = docodoco API key 2
        section "process" parameter "count" is number of parallel requests.


##EXAMPLE
| lookup docodoco ipaddr as clientip
| lookup docodoco ipaddr as clientip output PrefJName OrgName DomainName

The data returned by "DocoDoco" are based on return parameters of "DocoDoco". 
Look at the following URL about return parameters. 
http://www.docodoco.jp/areatargeting/rest.htmlml

In the case of Third party data, it will be "Parameter@Parent node name".
-corporate number
|lookup docodoco ipaddr as clientip output OrgCode@HoujinBangou_3 HoujinBangou@HoujinBangou_3 HoujinName@HoujinBangou_3 HoujinAddress@HoujinBangou_3 HoujinLastUpdate@HoujinBangou_3

-Anonymized Network Data
http://www.docodoco.jp/fraud/index.html
|lookup docodoco ipaddr as clientip output Name@AnonymousNetwork_5 Score@AnonymousNetwork_5 Info@AnonymousNetwork_5

-wether
In the case of Weather forecast ,Temperature forecast,Chance of rain or Wind direction forecast  ,"WeatherA"
In the case of  Current weather situation or Ultraviolet forecast ,"WeatherP"
|lookup docodoco ipaddr as clientip output TodayWeather@WeatherA Weather@WeatherP


##Performance
・6 core cpu and 10 parallel : about 1000 req/min
# Binary File Declaration
# Binary File Declaration
