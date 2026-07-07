# Strutils App for Splunk by GoAhead 

## Introduction

Strutils includes five strings utility custom search commands in order to encode or decode string values and detect random string.


## Installation

Strutils is a standard Splunk App and requires no special configuration.
Restarting splunk search head instance may be possibly needed for activating these custom search commands. 

## Usage
1. **baseutil**
    - StreamingCommand for base converting for input string, base2(bin), base8(oct), base16(hex), base32, base64 and base85 are available.
    - Options
        - **input_field** (required): target field name passed by the previous pipe (|)  
        - **mode** (required):         "encode" or "decode"  
        - **base**:                   2 or 8 or 16 or 32 or 64 or 85  
        - **coding**:                 coding name for python3 encode() or decode() before and after the base converting, which is utf-8 by default.  
    - Output field name
        - "base" + *base option* + *mode option* + "\_" + *input_field name*
        - e.g.  base64decode_message   
    - Example  
        - ` ...| baseutil input_field=message mode=decode base=64 coding=sjis`
        

2. **rotutil**
    - StreamingCommand for rot converting for input string, From ROT47 decode to ROT47 encode are available. It also has bruteforce converting option.
    - Options
        - **input_field** (required): target field name passed by the previous pipe (|)  
        - **num**:                    integer number from -47 to 47, negaive num means reverse right rotation, positive num means right rotation, which is 13 by default
        - **brute**:                  true or false, ALL ROT bruteforce conversion between ROT-*num* and ROT*num*, which is "false" by default.  
    - Output field name
        - (brute) + "rot" + *num option* + "\_" + *input_field name* 
        - e.g. rot13_message 
    - Specification detail
        - Only alphabet rotation between -13 and 13, the outer is alphabet + numeric + symbol between ord(33) and ord(126).  
    - Example  
        - ` ...| rotutil input_field=message num=13 brute=true`
        
       
3. **codingutil**
    - StreamingCommand for char coding checking and converting for input string. The output of char coding checking is based on that of chardet.detect(). Two output fields will appear in total when "decoding" option is given.
        - **input_field**  (required): target field name passed by the previous pipe (|) 
        - **encoding**:               coding name to python3 encode() e.g. utf-8,sjis,ascii,cp432,cp932 etc. default: utf-8 
        - **decoding**:               coding name to python3 decode() e.g. utf-8,sjis,ascii,cp432,cp932 etc.
    - Output field name
        - "codinginfo" + "\_" + *input_field name* 
        - e.g.  codinginfo_message   
        - (with decoding option) 
            - "decoding" + "\_" + *codename*  + "\_" + *input_field name*
            - e.g. decoding_sjis_message
    - Example  
        - ` ...| codingutil input_field=message`
        
        - ` ...| codingutil input_field=message encoding=cp432 decoding=cp932`
        

4. **maskutil**
    - StreamingCommand for masking multi-byte char like Japanese letters, Kanji etc excluding ascii to "□", one input field is necessary and additional multi fields can be set to mask.
        - **input_field** (required): target field name passed by the previous pipe (|)  
    
        - **additional_input_fields**: list of additional input field names comma(,) separated and passed by the previous pipe (|).  Note) comma separated list should be quoted.
        
    - Output field name
        - "masked" + "\_" + *input_field name* 
        - e.g.  masked_message   
        - (with additional_input_field option) 
            - "masked" + "\_" + *one of additional field name*
            - e.g. masked_fieldA
    - Example  
        - ` ...| maskutil input_field=message`
        
        - ` ...| maskutil input_field=message (additional_input_fields="fieldA,fieldB,fieldC"`), in case of three additional fields. The total amount of output fields are four.
        

5. **randomutil**
    - StreamingCommand for randomness checker for input string.
    - Options
        - **input_field** (required): target field name passed by the previous pipe (|)  
        - **mode** (required):         "shannon" or "nostril" or "texttrans"  
        - **th**:                     int or float value for threshold to judge the randomness, default: 3.5 for shannon, 0.05 for texttrans, nostril doesn't need th option because of the built-in. 
    - Output field name
        - "is_random" + "\_" + *mode* + "\_" + *th* + "\_" + *input_field name*
        - e.g.  is_random_shannon_\>th3.5_message
        - e.g.  is_random_nostril_message
        - e.g.  is_random_texttrans_\<th0.05_message    
    - Mode charactoristic and Benchmark
        - shannon mode is from shannon entoropy based on char histogram in the string
        - nostril mode is from nostril library's nonsense_detector method based on the results of the similarity against english words
        - texttrans mode is from texttrans prob method based on the state transition probability
        - more faster order: shannon > texttrans >> nostril
    - Example  
        - ` ...| randomutil input_field=message mode=shannon th=3.5`

        - ` ...| randomutil input_field=message mode=nostril`

        - ` ...| randomutil input_field=message mode=texttrans th=0.05`
          

6. **escapeutil**
    - StreamingCommand for escape and unescape about "unicode-escape","xmlcharref" and "urlpercent" encoding
        - **input_field**  (required): target field name passed by the previous pipe (|)  
        - **escape**:               "unicode-escape" or "xmlcharref" or "urlpercent" for escape mode converting from readable to escape str.
        - **unescape**:              "unicode-escape" or "xmlcharref" or "urlpercent" for unescape mode converting from escape str to readable.        
    - Output field name
        - r"(escape|unescape)" + "\_" + r"(unicode-escape|xmlcharref|urlpercent)" + "\_" + *input_field name* 
    - Example  
        - ` ...| escapeutil input_field=message unescape="unicode-escape"`
        
        - ` ...| escapeutil input_field=message escape="xmlcharref"`      


7. **renameutil**
    - StreamingCommand for multi field name converter for single or comma separated list or wildcard field names. Choose one style, prestub= is needed for only "replace" stype as replaced part. fixstub= is needed for "prefix", "suffix" and "replace" style as new str. It will sometimes be useful when built-in "rename" command cannot handle your tricky demand. 
        - **field**  (required): target fields passed by the previous pipe (|), single or comma separated list or wildcard field names are available. Note) comma separated list should be quoted.
        - **style**  (required): rename style select in "replace" or "upper" or "lower" or "prefix" or "suffix"              
        - **prestub** : The field str replaced
        - **fixstub** : The field str to append or replace,  "__upper__" and "__lower__" are special ,which is a particial case conversion for the matched field.
    - Output field name
        - It depends on this rename operation result.
    - Example  
        - ` ...| renameutil field=src.* style=replace prestub="user" fixstub="idnum"`
        
        - ` ...| renameutil field="username,useremail,iduser,idmessage" style=prefix fixstub="osintintelA_"`

        - ` ...| renameutil field=*_* style=lower `

        - ` ...| renameutil field=* style=replace prestub="id" fixstub="__upper__"`


Command usages are also described in searchbnf.conf, thus you can see it on search window by writing the command name on. The errors against each input value are dumped to the output field and the command exception will be dumped in search.log if it happens.

## Included 3rd party's additional import modules

For codingutil command,

- [chardet](https://pypi.org/project/chardet/)

For randomutil command,

- [nostril](https://github.com/casics/nostril)

- [texttrans](https://pypi.org/project/texttrans/)


## Support

Splunk 8.x, this app codes are written in Python3.


## License

[LGPLv3](https://www.gnu.org/licenses/lgpl-3.0.en.html)

## Copyright

Copyright 2023 GoAhead Inc.

