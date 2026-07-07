# Numeral system macros for Splunk

## Summary

This app provides macros and lookups for converting units and displaying numbers
in each language's numeral system.

* various conversion of units. (e.g. Square killometer to Square mile, etc.)
* bytes to human readable size. (e.g. KiB, MiB, GiB, ...)
* large number to SI symbol expressions.(e.g. K, M, G, T,...)
* large number to language specific expressions.(e.g. million, etc.)
  * multi languages.
    * English
    * Chinese, Korean, Japanese
    * Spanish
    * South Asia English (Indian)
    * French
    * Portuguese
    * Nederlands
* IP Address (CIDR) to Network Address, Netmask, Prefix, Broadcast Address, IPVer
* ratio (0.00 - 1.00) to a color code that looks like a heat.
* Hex-String to Human-Readable String.
* Macros for regular expressions for IPv4 addresses, IPv6 addresses, and URIs.
* Macros for using Detection Summaries / Details dashboards.

## The purpose of the add-on and a general description of how it works.

 * Provide reusable macros for frequently used numeric conversions.
 * Macros for displaying large numbers in human readable representation.
 * Most conversions are working with only macros that includes basic eval functions. (Not required any other libraries)
 * UI dashboards to find macros and check their usage are provided, and if you do not need the UI, you can hide it and still use macros.
 * A lookup files are included for use with the dashboard, but it is set up so that it is not bundled and distributed with the Indexer so as not to impose even a trivial load.
 * Provide an external lookup ipcalclookup for enabling calculations for ip addresses.
 * Provide macros for regular expressions for IPv4 addresses, IPv6 addresses, and URIs.

## Usage1: Large numbers to human readable

### Sample usage for display on a Single Value panel

Sample for Japanese speakers

```
| makeresults
| eval val=1234567890123, val=`numeral_jp(val)`
| table val
```

1兆2345億6789万123

Sample for English speakers

```
| makeresults
| eval val=1234567890123, val=`numeral_en(val)`
| table val
```

1 trillion 234 billion 567 million 890 thousand 123

Sample for Portuguese speakers

```
| makeresults
| eval val=1234567890123, val=`numeral_pt(val)`
| table val
```

1 bilhão 234,567 milhões 890 mil 123

Sample of binary symbols

```
| makeresults
| eval bytes=1234567890123, bytes=`numeral_bin(bytes,2)`
| table bytes
```

1.12TiB


### Sample usage for display on a Statistics Table

```
| makeresults count=35
| streamstats count as digit
| eval val=pow(10,digit-1), en=val
| table digit val en
| fieldformat en=`numeral_en(en)`
```

```
1
10
100
1 thousand 
10 thousand 
100 thousand 
1 million 
10 million 
100 million 
1 billion 
10 billion 
100 billion 
1 trillion 
10 trillion 
100 trillion 
1 quadrillion 
10 quadrillion 
100 quadrillion 
1 quintillion 
10 quintillion 
100 quintillion 
1 sextillion 
10 sextillion 
100 sextillion 
1 septillion 
10 septillion 
100 septillion 
1 octillion 
10 octillion 
100 octillion 
1 nonillion 
10 nonillion 
100 nonillion 
1000 nonillion 
10000 nonillion
```

Macros for binary symbols(KiB, MiB, GiB, TiB, PiB, EiB, ZiB, YiB, RiB, QiB) are available since version 1.1.1.

```
| makeresults count=35
| streamstats count as digit
| eval bytes=pow(10,digit-1), bytes=bytes+((random())%bytes)
| foreach si_name si_name2 si si2 binary [eval <<FIELD>>=bytes]
| table bytes si_name si_name2 si si2 binary
| fieldformat bytes=tostring(bytes,"commas") 
| fieldformat si_name=`numeral_si_name(si_name)`
| fieldformat si_name2=printf("% 15s",`numeral_si_name(si_name2,1)`) 
| fieldformat si=`numeral_si(si)`
| fieldformat si2=printf("% 9s",`numeral_si(si2,1)`)
| fieldformat binary=printf("% 9s",`numeral_bin(binary,1)`)
```

```
bytes      si_name              si_name2    si           si2     binary
        1                    1         1.0            1    1.0     1.0B  
       14                   14        14.0           14   14.0    14.0B  
      107                  107       107.0          107  107.0   107.0B  
    1,166           1 kilo 166    1.2 kilo       1k 166    1.2K    1.1KiB
   19,411          19 kilo 411   19.4 kilo      19k 411   19.4K   19.0KiB
  113,587         113 kilo 587  113.6 kilo     113k 587  113.6K  110.9KiB
1,213,593  1 mega 213 kilo 593    1.2 mega  1M 213k 593    1.2M    1.2MiB
```


### Sample usage for using various provided macros.

 * With rounding lowest 3 digit if over 6 digit.

```
| makeresults count=35
| streamstats count as digit
| eval val=replace(substr("1234567890123456789012345678901234567890",1,digit+2),"(\d{2})$",".\1")
| foreach si_name si bin en es pt in_en in_en2 jp kr cn_t cn nl fr [eval <<FIELD>>=val]
| table digit val si_name si bin en es pt in_en in_en2 jp kr cn_t cn nl fr
| fieldformat val=tostring(val,"commas")
| fieldformat si_name=`numeral_si_name(if(log(si_name,10)>6,round(si_name,-3),si_name))`
| fieldformat si=`numeral_si(if(log(si,10)>6,round(si,-3),si))`
| fieldformat bin=printf("% 10s",`numeral_bin(bin,2)`)
| fieldformat en=`numeral_en(if(log(en,10)>6,round(en,-3),en))`
| fieldformat es=`numeral_es(if(log(es,10)>6,round(es,-3),es))`
| fieldformat pt=`numeral_pt(if(log(pt,10)>6,round(pt,-3),pt))` 
| fieldformat in_en=`numeral_in_en(if(log(in_en,10)>6,round(in_en,-3),in_en))`
| fieldformat in_en2=`numeral_in_en2(if(log(in_en2,10)>6,round(in_en2,-3),in_en2))`
| fieldformat jp=`numeral_jp(if(log(jp,10)>6,round(jp,-3),jp))`
| fieldformat kr=`numeral_kr(if(log(kr,10)>6,round(kr,-3),kr))`
| fieldformat cn_t=`numeral_cn_t(if(log(cn_t,10)>6,round(cn_t,-3),cn_t))` 
| fieldformat cn=`numeral_cn(if(log(cn,10)>6,round(cn,-3),cn))`
| fieldformat nl=`numeral_nl(if(log(nl,10)>6,round(nl,-3),nl))`  
| fieldformat fr=`numeral_fr(if(log(fr,10)>6,round(fr,-3),fr))`
```

 * With rounding to 2 decimal places of maximum unit. (Since version 1.2.0)

```
| makeresults count=35
| streamstats count as digit
| eval val=replace(substr("1234567890123456789012345678901234567890",1,digit+2),"(\d{2})$",".\1")
| foreach si_name si bin en es pt in_en in_en2 jp kr cn_t cn nl fr [eval <<FIELD>>=val]
| table digit val si_name si bin en es pt in_en in_en2 jp kr cn_t cn nl fr
| fieldformat val=tostring(val,"commas")
| fieldformat si_name=`numeral_si_name(si_name,2)`
| fieldformat si=`numeral_si(si,2)`
| fieldformat bin=printf("% 10s",`numeral_bin(bin,2)`)
| fieldformat en=`numeral_en(en,2)`
| fieldformat es=`numeral_es(es,2)`
| fieldformat pt=`numeral_pt(pt,2)` 
| fieldformat in_en=`numeral_in_en(in_en,2)`
| fieldformat in_en2=`numeral_in_en2(in_en2,2)`
| fieldformat jp=`numeral_jp(jp,2)`
| fieldformat kr=`numeral_kr(kr,2)`
| fieldformat cn_t=`numeral_cn_t(cn_t,2)` 
| fieldformat cn=`numeral_cn(cn,2)`
| fieldformat nl=`numeral_nl(nl,2)`  
| fieldformat fr=`numeral_fr(fr,2)`
```


### provided macros

 * numeral_si_name(1) : SI name. kilo, mega, giga, tera, peta, exa, zetta, yotta
 * numeral_si_name(2) : SI name with an arg for rounding digits.
 * numeral_si(1) : SI symbol. K, M, G, T, P, E, Z, Y
 * numeral_si(2) : SI symbol with an arg for rounding digits. 
 * numeral_bin(2) : Binary symbol with an arg for rounding digits. KiB, MiB, GiB, TiB, PiB, EiB, ZiB, YiB, RiB, QiB
 * numeral_bin(1) : same as numeral_bin(bytes,0)

 * numeral_en(1) : Short Scale for English speaker
 * numeral_en(2) : with an arg for rounding digits.
 * numeral_jp(1) : 万進法 for Japanese speaker. 千, 万, 億, 兆
 * numeral_jp(2) : with an arg for rounding digits.
 * numeral_kr(1) : for Korean speaker. 千, 萬, 億, 兆
 * numeral_kr(2) : with an arg for rounding digits.
 * numeral_cn_t(1) : Chinese with Traditional Chinese characters. 千, 萬, 億, 兆
 * numeral_cn_t(2) : with an arg for rounding digits.
 * numeral_cn(1) : Chinese with Simplified Chinese characters. 千, 万, 亿, 兆
 * numeral_cn(2) : with an arg for rounding digits.
 * numeral_in_en(1) : for India, South Asia English. thousand, lakh, crore, lakh crore
 * numeral_in_en(2) : with an arg for rounding digits.
 * numeral_in_en2(1) : for India, South Asia English. thousand, lakh, crore, arab
 * numeral_in_en2(2) : with an arg for rounding digits.
 * numeral_nl(1) : Long Scale for  Nederlands. duizend, miljoen, miljard, biljoen
 * numeral_nl(2) : with an arg for rounding digits.
 * numeral_fr(1) : Long Scale for French. mille, million, milliard, billion
 * numeral_fr(2) : with an arg for rounding digits.
 * numeral_es(1) : Long Scale for Spanish speaker. mil, millón, millardo, billón
 * numeral_es(2) : with an arg for rounding digits.
 * numeral_pt(1) : Long Scale for Portuguese speaker. mil, milhão, bilhão, trilhão
 * numeral_pt(2) : with an arg for rounding digits.


## Usage2: Conversion of units

This add-on provides over thousand macros to interconvert the value of each unit to another unit within the same category.

### syntax of macros for conversion of units

```
`numeral_<<from_unit>>_to_<<to_unit>>(<<from_value>>)`
```

* above macro will return <<to_value>>

* Please select <<from_unit>> and <<to_unit>> the list below.

```
 e.g.) | eval km2=10, sq_yd=`numeral_km2_to_sq_yd(km2)`
```

### Categories and unit names

* Area
  * Jyou, Tsubo, ac, ha, km2, m2, sq_ft, sq_in, sq_mi, sq_yd

* Data Transfer Rate
  * Bs, GBs, Gbps, GiBits, KBs, KiBits, KiBs, MBs, Mbps, MiBits, MiBs, TBs, Tbps, TiBits, TiBs, bps, kbps

* Digital Storage
  * GB, Gbit, GiB, GiBit, KB, Kbit, KiB, KiBit, MB, Mbit, MiB, MiBit, PB, Pbit, PiB, PiBit, TB, Tbit, TiB, TiBit, bit, bytes

* Energy
  * Btu, J, W_h, cal, eV, ft_lbf, kJ, kW_h, kcal, thermUS

* Frequency
  * GHz, Hz, MHz, kHz

* Fuel Economy
  * kmL, l100km, mpg_Imp, mpg_US

* Length
  * cm, ft, in, km, m, mi, mm, nm, nmi, um, yd

* Mass
  * g, kg, lb_av, long_tn, mg, oz_av, sh_tn, st, t, ug

* Plane Angle
  * arcdegree, arcminute, arcsecond, grad, rad, u

* Pressure
  * Pa, Torr, atm, bar, psi

* Speed
  * fps, kmh, kn, mph, ms

* Temperature
  * C, F, K

* Time
  * C, d, decade, h, min, mo, ms, ns, s, us, wk, y

* Volume
  * US_fl_oz, c_Imp, c_US, cu_ft, cu_in, fl_oz_Imp, gal_Imp, gal_US, l, m3, ml, pt_Imp, pt_US_fl, qt_Imp, qt_US, tbsp_Imp, tbsp_US, tsp_Imp, tsp_US


### About dashboards.

Please utilize the dashboards to investigate available macros.
If you do not need the UI, you can hide it and still use macros.

How to hide UI:

"Apps" -> "Manage Apps"
-> "Numeral system macros for Splunk" -> "Edit properties"

Set "Visible" : No.

Press "Save" button.


## Usage3: Calculate Network Address, Broadcast address from CIDR ('ip/mask' or 'ip/prefix').

An external command lookup ipcalclookup is available since version 2.1.0.

```
| makeresults
| eval ip=split("192.0.2.17/255.255.255.240,192.0.2.30/28,2001:db8:1234::1/64",",")
| mvexpand ip
| lookup local=t ipcalclookup Address as ip OUTPUT Network Netmask Prefix Broadcast IPVer
| table ip Network Netmask Prefix Broadcast IPVer
```

```
ip                              Network         Netmask              Prefix    Broadcast                           IPVer
192.0.2.17/255.255.255.240      192.0.2.16      255.255.255.240       28       192.0.2.31                           4
192.0.2.30/28                   192.0.2.16      255.255.255.240       28       192.0.2.31                           4
2001:db8:1234::1/64             2001:db8:1234::	ffff:ffff:ffff:ffff:: 64       2001:db8:1234:0:ffff:ffff:ffff:ffff  6
```

### provided an external command lookup

 * ipcalclookup Address OUTPUT Network Netmask Prefix Broadcast : for calculating Network address, Broadcast address.


## Usage4: Convert the ratio to a color code that looks like a heat.

 * The macro `numeral_heatcolor(1)` can convert the ratio (0.00 - 1.00) to a color code that looks like a heat.
 * Some visualizations can show colors with color code that included in search results.
 * This macro is useful for automatically determining the display color based on percentages.


```
| makeresults count=11
| streamstats count current=f
| eval ratio=round(count/10,2), color=`numeral_heatcolor(ratio)`
| table ratio color
```

```
ratio	color
0.00	#0000ff
0.10	#004ef2
0.20	#0095ce
0.30	#00ce95
0.40	#00f24e
0.50	#00ff00
0.60	#4ef200
0.70	#95ce00
0.80	#ce9500
0.90	#f24e00
1.00	#ff0000
```

### provided macro

 * numeral_heatcolor(1) : ratio (0.00 - 1.00) to a color code (e.g. #ff0000 )


## Usage5: decode Hex-String

An external command lookup checkhexstringencoding and decodehexstring are available since version 2.2.0.
These lookups are useful when you need to convert a Hex-String (such as SMNP) into a human-readable string.

```
| makeresults
| eval hexstring=replace("ef bc a1 ef bc a2 ef bc a3 ef bc a4 ef bc a5 ef bc a6","\s+","")
| lookup local=t checkhexstringencoding hexstring OUTPUT encoding as detected_encoding
| eval adjusted_encoding=case(detected_encoding IN ("utf-8","EUC-JP","ISO-2022-JP"), detected_encoding, detected_encoding IN ("ISO-8859-1"), "EUC-JP", 1=1, "SHIFT_JIS")
| lookup local=t decodehexstring hexstring encoding as adjusted_encoding OUTPUT decodedstring
| table hexstring detected_encoding adjusted_encoding decodedstring
```

```
hexstring	detected_encoding	adjusted_encoding	decodedstring
efbca1efbca2efbca3efbca4efbca5efbca6	utf-8	utf-8	ＡＢＣＤＥＦ
```

### provided external command lookups

 * checkhexstringencoding hexstring OUTPUT encoding : for guessing what the encoding is used in hexstring.
 * decodehexstring hexstring encoding OUTPUT decodedstring : for decoding Hex-String to Human-Readable String.

## Usage6: Macros for extracting IPv4, IPv6 addresses and URI Element fields

### provided macro

 * IP4Regex(1) : A regular expression for extracting IPv4 address field.
 * IP6Regex(1) : A regular expression for extracting IPv6 address field.
 * URIRegex(7) : A regular expression for extracting URI Element fields.
 
### IPv4

```
| makeresults
| eval _raw=split("oid=.1.3.6.1.2.1.4.20.1.2.192.0.2.16 don't match
telnet://192.0.2.16:80/ match","
")
| stats count by _raw
| fields - count

| rex `IP4Regex(included_ipv4)`
```

### IPv6

```
| makeresults
| eval _raw=split("ldap://[2001:db8::b]/c=GB?objectClass?one match
since2001:db8::broken don't match","
")
| stats count by _raw
| fields - count

| rex `IP6Regex(included_ipv6)`
```

### URI

```
| makeresults
| eval uri=split("ftp://ftp.example.net/rfc/rfc1808.txt
http://www.example.net/rfc/rfc2396.txt
https://jsmith@[2001:db8::1]:8080/rfc/rfc3986.html#3-5--Fragment
ldap://[2001:db8::7]/c=GB?objectClass?one
mailto:John.Doe@example.com
news:comp.infosystems.www.example.net
telnet://192.0.2.16:80/
https://cnn.example.com&story=breaking_news@192.0.2.16/top_story.htm","
")
| stats count by uri
| fields - count
| rex field=uri `URIRegex(scheme,userinfo,host,port,path,query,fragment)`
```

## Usage7: Macros for detections

### provided macro

The following set of macros are provided from Detection1 to Detection9.

 * Detection1_name : Name of the detection.
 * Detection1_search : A search as a datasource of the detection.
 * Detection1_statsmethod : A stats function for counting the detection such as count, dc(fieldname), etc.
 * Detection1_splitfields : Fields (Comma separated) to split the detection in the "Detection Details" dashboard.
 * Detection1_displayfields : Other fields (Comma separated) to display in the "Detection Details" dashboard.

These macros are set as default values on forms in the "Detection summaries" dashboard.
The "Manage macros for detections" dashboard helps you to see and edit these macros.


## Any prerequisites or required dependencies.

 * No prerequisites.
 * No dependencies.

## Who developed the add-on.

 * Tomohisa Fujita <tfujita@splunk.com>

## Who to contact for add-on support.

 * Tomohisa Fujita <tfujita@splunk.com>