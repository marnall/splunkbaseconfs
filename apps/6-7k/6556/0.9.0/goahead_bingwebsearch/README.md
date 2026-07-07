# Bing Web Search App by GoAhead 

## Introduction

Bing Web Search App is an API wrapper tool of Microsoft Bing Web Search API (v7).
This App requests to "https://api.bing.microsoft.com/v7.0/search".
Bing Web Search API Key is needed for utilize.
`binghostinfo` can be used for checking the suspicious IP address is also used as a web site hosting server.:)

## Installation

The Bing API Key is needed to utilize this App.
1. Install this App package
2. Create the APK Key on your Azure. Ref) https://docs.microsoft.com/en-us/bing/search-apis/bing-web-search/create-bing-search-service-resource#create-your-bing-resource 
3. Set up the API Key on the App Setup Page. 
4. Restarting splunk search head instance may be sometimes possibly needed for activating these custom search commands and loading this app's icon. 
5. App Install user needs "admin_all_objects" privilege and Splunk search users need "list_storage_passwords" privilege in order to utilize "Secret storage".

## Usage

1. **bingwebsearch**
    - GeneratingCommand as Bing Web Search API(v7) wrapper.
    - Options (Please refer to Bing API docs for detail.)
        - **q** (Required)      :        search query following bing operator rules. 
        - **count**             :        (Optional) response result count, default 10, max 50. 
        - **offset**            :        (Optional) offset to retrieve subsequent pages, default 0. 
        - **mkt**               :        (Optional) One market code like en-US, ja-JP, No mkt setting is by default. 
        - **responseFilter**    :        (Optional) responseFilter comma separated list for including the content category and minus(-) means that of excluded. e.g. Webpages,-Images,-Videos. No filter is by default. We just have completed to test about the single category and let me notify that comma separeted list and minus operators were not succeeded on our free API env.
        - **safeSearch**        :        (Optional) filter webpages for adult content, choice from Off/Moderate/Strict. Moderate is by default.
        - **others**            :        (Optional) other query parameters combined with & , e.g. answerCount=,promote=,cc=,freshness=,setLang=,textDecorations,textFormat
    - Output field name
        - ALL output names are the same to the API response fields.
        - In addition, "app_status" field is appended for checking this command result.
    - Example  
        - ` | bingwebsearch q="site:google.com hogehoge" count=10 offset=0 mkt=ja-JP responseFilter=Webpages,-Images,-Videos safeSearch=Strict others="setLang=en-US&freshness=2020-01-01..2022-04-01"`

```
| bingwebsearch q="site:google.com apple" mkt="en-US"
| spath input=relatedSearches
| spath input=webPages
| spath input=rankingResponse
| table queryContext totalEstimatedMatches mainline.items{}.answerType value{}.url value{}.name value{}.text value{}.language value{}.dateLastCrawled
```


2. **binghostinfo**
    - StreamingCommand to append the web site hosting info for target ip or domain via Bing Web Search API(v7). The const parameters are "count=50", "offset=0" and responseFilter=Webpages.
    - Options
        - **input_field** (Required):  Target field name to input, ip or domain is expected as the field value.
        - **mode**        (Required):        Select "ip" or "domain" , these mean Bing API's search query Operators of "ip:" or "domain:" 
        - **mkt**                   :        (Optional) One market code like en-US, ja-JP, No mkt setting is by default. Please refer to Bing API docs for detail.
        - **apisaver**              :        (Optional) API amount saver, **default: true**. This app raises exception if the amoount of your events passed to this command  are over 50. Please set "apisaver=false" explicitly to avoid this limit.
    - Output field name
        - ALL output names are the same to the API response fields.
    - Example  
        - `...| fields ipfield | binghostinfo input_field=ipfield mode=ip`

```
| makeresults 
| eval ipv4 = "8.8.8.8"
| binghostinfo input_field=ipv4 mode=ip mkt="en-US" 
| table Bing_hostcount Bing_hostinfo app_status *
```


Command usages are also described in searchbnf.conf, thus you can see it on search window by writing the command name on. 

Some errors are dumped to the command result fields and the command exception will be dumped in search.log.
Especially, Request URL string and its HTTP response code will be dumped in search.log for debugging.

## Bing API Docs

- [Bing Web API v7 Reference](https://docs.microsoft.com/en-us/rest/api/cognitiveservices-bingsearch/bing-web-api-v7-reference)

## Included 3rd party's additional import modules

None

## Similar App

https://splunkbase.splunk.com/app/3355/

- Up to Splunk 7.x

- This former app uses API endpoint of https://api.cognitive.microsoft.com/bing/v5.0/(search/news)

- The API endpoint is older and the app is not supported by developer, thus we develop this new app appending a custom capability for IP/Domain diagonosis of `binghostinfo` command.


## Attention to begin to use this app

We are not responsible for charges due to BingAPI consumption or disadvantages due to using up the free quota.

Please note monthly 1000 API query is the main limit if you use Bing API in free subscription.


## Support

Splunk 9.x or later, this app codes are written in Python3.

## License

[APACHE LICENSE, VERSION 2.0](https://www.apache.org/licenses/LICENSE-2.0)

## Copyright

Copyright 2025 GoAhead Inc.
