# Upgrade Notes

On any upgrade of these packages, make note of the changes required, and why.

## `botocore`

### `session.py`

Line 284 triggered AppInspect for UDP Communications.

Change the line from 

    socket=socket.socket(socket.AF_INET, socket.SOCK_DGRAM),

to 

    socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM),

to bypass the AppInspect check for UDP Protocols.
This will probably break something if AWS is used in anyway, but it is only a dependency of the `cbc_sdk` package.

## CBC SDK

The updated CBC SDK (v1.5.0) is built using Python 3.8, which breaks compatibility with Splunk's packaged python (3.7) in Splunk versions 9.0 and 9.1.
These are the additional steps used to upgrade to CBC SDK 1.5 while using Splunk Python 3.7.
These are all done from the `<APP_HOME>/lib` folder.

### urllib3

`/opt/splunk/bin/splunk cmd pip3 install --upgrade -t . urllib3==1.26.18`


### jsonschema

`/opt/splunk/bin/splunk cmd pip3 install --upgrade -t . jsonschema==4.17.3 `

This "fixes" an error with the `rpds` module. 

### typing-extensions

`/opt/splunk/bin/splunk cmd pip3 install --upgrade -t . typing-extensions==4.7.1`

File: `lib/reference/_core.py` was updated to have the following imports for `Protocol` (near-abouts line 4).

    from typing import Any, Callable, ClassVar, Generic, TypeVar
    from typing_extensions import Protocol

File: `lib/reference/typing.py` was updated to have the following imports for `Protocol` (near-abouts line 6)

    from typing import TYPE_CHECKING, TypeVar
    from typing_extensions import Protocol

### validators

`/opt/splunk/bin/splunk cmd pip3 install --upgrade -t . validators==0.20.0`

### backports

Run from Splunk. 
Linux is supported via packaged ".so" file.
To fix for windows, run the following command from the "lib" folder.

#### This is 9.1 on Linux
`/opt/splunk/bin/splunk cmd python3.7 -m pip  install --upgrade -t . backports._datetime_fromisoformat==2.0.1`

#### This is on Windows

##### Splunk versions >= 9.2.X
`cd "C:\Program Files\Splunk\etc\apps\<APP>\lib"`
`"C:\Program Files\Splunk\bin\splunk.exe" cmd python3 -m pip install --upgrade -t . backports._datetime_fromisoformat==2.0.1`

### rpds

* RESOLVED WITH `jsonschema==4.17.3`