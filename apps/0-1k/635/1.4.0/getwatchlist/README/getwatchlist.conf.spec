[global]
isbad = bool
url = string
delimiter = char                                                                    
comment = char
auth_ptr = string
relevantFieldName = string
relevantFieldCol = int
categoryCol = int
referenceCol = int
dateCol = int
ignoreFirstLine = bool
filetype = txt
autoExtract = bool
credential = string
is_provided = bool

[abusech-urlhaus]
url = string
comment = char
relevantFieldName = string
relevantFieldCol = int
spam = string
testval = bool

[DShield]
url = string
relevantFieldName = string
ignoreFirstLine = bool
referenceCol = int

[spamhaus]
url = string
delimiter = char
relevantFieldName = string
relevantFieldCol = int
referenceCol = int
ignoreFirstLine=bool
comment = char

[phishtank]
url = string
delimiter = string
relevantFieldName = string
relevantFieldCol = int
referenceCol = int
dateCol = int
categoryCol = int
ignoreFirstLine = bool
isbad = bool

[bogons]
url = string
isbad = bool

[emergingthreats]
url = string
isbad = bool

[malc0de]
url = string
comment = char
isbad = bool


[csv]
filetype = string
delimiter = string
autoExtract = bool

[xls]
filetype = string
delimiter = string
autoExtract = bool

[xlsx]
filetype = string
delimiter = string
autoExtract = bool

[txt]
filetype = string

[json]
filetype = string
delimiter = string
autoExtract = bool


[archive]
filetype = archive
delimiter = ","
autoExtract = true

[gz]
filetype = gz
delimiter = ","
autoExtract = true