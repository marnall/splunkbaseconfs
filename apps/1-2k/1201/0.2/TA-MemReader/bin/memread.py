from ctypes import *
from ctypes.wintypes import *

OpenProcess = windll.kernel32.OpenProcess
ReadProcessMemory = windll.kernel32.ReadProcessMemory
CloseHandle = windll.kernel32.CloseHandle
PROCESS_ALL_ACCESS = 0x1F0FFF

def GetPointerAddress ( PROGPid, BaseAddress, Offset=0, HexOrDec="Dec"):
	"""This function will follow a pointer and return the memory space
	that the pointer is targeting.  Specify Hex or Dec for how the offsets
	are currently being passed. Defaults to Decimal
	"""

	if HexOrDec == "Hex":
		BaseAddress = int(str(BaseAddress), 16)
		Offset = int(str(Offset), 16)
	try:
		bytes=4
		buffer= c_uint()
		bufferSize = bytes
		bytesRead = c_ulong(0)
		processHandle = OpenProcess(PROCESS_ALL_ACCESS, False, PROGPid)
		ReadProcessMemory(processHandle, BaseAddress, byref(buffer), sizeof(buffer), byref(bytesRead))
		FinalValue=buffer.value + Offset
		CloseHandle(processHandle)
		if HexOrDec == "Hex":
			FinalValue = "0x%0.8X" % FinalValue
			return FinalValue
		else:
			return FinalValue
	except:
		print "Failed on GetPointerAddress"
		CloseHandle(processHandle)

def ReadMemory ( PROGPid, TargetAddress, Bytes=8, HexOrDec="Dec", BufferType="String" ):
	"""This function will follow an address and return the values in memory
	that are starting at the TargetAddress and count up the number of bytes.
	Specify Hex or Dec for how the Addresses
	are currently being passed. Defaults to Decimal
	BufferType is for returning either the string represintation in memory, or
	for returning the value of the memory location.  Currently c_uint is only 8
	bytes till I figure out how to specify the integer max length.
	Specifying a value higher then 8 and a value other then string will crash.
	"""
	try:
		Bytes = long(Bytes)
		if HexOrDec == "Hex":
			TargetAddress = long(str(TargetAddress), 16)
		if BufferType == "String" or BufferType == "string":
			buffer = create_string_buffer(Bytes)
		else:
			buffer = c_uint()
		bufferSize = int(Bytes)
		bytesRead = c_ulong(0)
		#Get target data
		processHandle = OpenProcess(PROCESS_ALL_ACCESS, False, PROGPid)
		ReadProcessMemory(processHandle, TargetAddress, byref(buffer), Bytes, byref(bytesRead))
		FinalValue=buffer
		CloseHandle(processHandle)
		return FinalValue
		
	except:
		print "Failed on GetMemoryBlock"
		CloseHandle(processHandle)