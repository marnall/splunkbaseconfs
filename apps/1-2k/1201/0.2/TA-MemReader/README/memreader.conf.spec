############
# Settings #
############

Below you'll find a list of all options currently supported by the memreader.
Example use cases will be expanded on at a future date

sendudp = [0|1]
* When set to 1, memreader will attempt to print the selected memory contents to a udp port.
* Default: disabled

sendstdout = [0|1]
* When set to 1, memreader will attempt to print the selected memory contents to stdout.
* Default: Enabled

udpip = <string>
* Used to specify what IP Address to attempt to send UDP information to
* Default: 127.0.0.1

udpport = <port number>
* Used to specify what port to connect UDP to.
* Default: 5006

bit = <integer>
* Used to specify what type of memory allocation bit size is used when reading your target process' memory
* Default: 32

base_process = <string>
* Used to specify the full name of the application process you wish to attach to.  Case-Sensitive.
* Example: MineSweeper.exe

read_bytes = <integer>
* Used to specify how many bytes of memory to read from your target address.
* Example: 8 

query_mode = <ctypes object>
* Specifies the cytpes data object to use.
* Valid options String, Hex, c_bool, c_char, c_wchar, c_byte, c_ubyte, c_short, c_ushort, c_int, c_uint, c_long, c_ulong, c_longlong, c_ulonglong, c_float, c_double, c_longdouble, c_char_p, c_wchar_p, c_void_p 
* ctypes objects should be suffixed with method brackets () to complete the data object.  Not needed for "Hex" or "String"

output_mode = <float_4_byte|string|string_null_break|hex_address_4_byte>
* Specifies how the data should be formatted before sending to splunk.
* float_4_byte will return a floating point number from a 4 byte hex object
* string will return an ascii set of characters 
* string_null_break will return a new line of ascii characters any time a null "00" hex byte is encountered.
* hex_address_4_byte will return a 4 byte hex address

target_address = <string>
* Used to specify a single address that will be the target start point for memory reading
* Example: 04A75600

print_x_lines = <integer>
* When a multi-line output is selected, this value will limit the number of lines sent out from the memlogreader
* Default: 0 - no limit

offset_mode = <hex|dec>
* Used when referencing memory offsets.  offset_mode tells the memreader that you are either entering memory offsets in a hexidecimal or decimal form.
* There is no default for this option and must be specified when using offsets.

offset.<int> = <memory offset string or int>
* offsets can reference either a short number or an offset from the base address.
* offsets will be followed in numerical order starting from 0 and ending at the highest number.
* Example, in windows 7 minesweeper (this address may be different on your installation of windows) the following will give the offset to the "timer"
offset.0 = minesweeper.exe+000AAD70
offset.1 = 250 
offset.2 = 38
offset.3 = 20
print_x_lines = 1


############
# Examples #
############

* This first example will dump the timer from the target address found in cheat engine
* Please note, this address will change everytime minesweeper is started and you will need to update the address.

[minesweeper]
base_process = MineSweeper.exe
read_bytes = 8 
query_mode = c_uint()
output_mode = float_4_byte
target_address = 07E0E080
print_x_lines = 1

* This example will dump the timer from the a pointer address found in cheat engine
* Please note, this address may be different based on your version of minesweeper

[minesweeper_pointer]
base_process = MineSweeper.exe
read_bytes = 8 
query_mode = c_uint()
output_mode = float_4_byte
offset_mode = hex
offset.0 = minesweeper.exe+000AAD70
offset.1 = 250 
offset.2 = 38
offset.3 = 20
print_x_lines = 1

* This example will dump the "log" contents from the MMO Final Fantasy XI
* It will read 800 bytes, and break at any new "chat" line found, and will only print the first 2 lines.
* Each new chatline will have a new timestamp

[FFXINULL]
base_process = pol.exe
read_bytes = 800 
query_mode = string
output_mode = string_null_break
offset_mode = hex
offset.0 = FFXiMain.dll+0x00458064
offset.1 = 4
offset.2 = CC
offset.3 = 0
print_x_lines = 2

* This example will dump the "log" contents from the MMO Final Fantasy XI
* It will read 800 bytes, and will be treated as 1 long line.  There will only be 1 line outputed from this stanza.

[FFXISTRING]
base_process = pol.exe
read_bytes = 200 
query_mode = string
output_mode = string
offset_mode = hex
offset.0 = FFXiMain.dll+0x00458064
offset.1 = 4
offset.2 = CC
offset.3 = 0