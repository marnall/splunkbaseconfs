from ctypes import *
from ctypes.wintypes import *


# const variable
# Establish rights and basic options needed for all process declartion / iteration
TH32CS_SNAPPROCESS = 2
STANDARD_RIGHTS_REQUIRED = 0x000F0000
SYNCHRONIZE = 0x00100000
PROCESS_ALL_ACCESS = (STANDARD_RIGHTS_REQUIRED | SYNCHRONIZE | 0xFFF)
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
TH32CS_SNAPTHREAD = 0x00000004
TH32CS_SNAPALL = (TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32)

##  Create object definitions to story information in
class PROCESSENTRY32(Structure):
    _fields_ = [ ( 'dwSize' , DWORD ) ,
                 ( 'cntUsage' , DWORD) ,
                 ( 'th32ProcessID' , DWORD) ,
                 ( 'th32DefaultHeapID' , POINTER(ULONG)) ,
                 ( 'th32ModuleID' , DWORD) ,
                 ( 'cntThreads' , DWORD) ,
                 ( 'th32ParentProcessID' , DWORD) ,
                 ( 'pcPriClassBase' , LONG) ,
                 ( 'dwFlags' , DWORD) ,
                 ( 'szExeFile' , c_char * 260 ) ]

class MODULEENTRY32(Structure):
    _fields_ = [ ( 'dwSize' , DWORD ) , 
                ( 'th32ModuleID' , DWORD ),
                ( 'th32ProcessID' , DWORD ),
                ( 'GlblcntUsage' , DWORD ),
                ( 'ProccntUsage' , DWORD ) ,
                ( 'modBaseAddr' , c_void_p ) ,
                ( 'modBaseSize' , DWORD ) , 
                ( 'hModule' , HMODULE ) ,
                ( 'szModule' , c_char * 256 ),
                ( 'szExePath' , c_char * 260 ) ]

CreateToolhelp32Snapshot = windll.kernel32.CreateToolhelp32Snapshot
Process32First = windll.kernel32.Process32First
Process32Next = windll.kernel32.Process32Next
Module32First = windll.kernel32.Module32First
Module32Next = windll.kernel32.Module32Next
GetLastError = windll.kernel32.GetLastError
OpenProcess = windll.kernel32.OpenProcess
GetPriorityClass = windll.kernel32.GetPriorityClass
CloseHandle = windll.kernel32.CloseHandle

def ListProcessPid( ProcessName ):
	""" This method will return the PID for a process that matches
	the "ProcessName" passed into the function"""
	try:
		hProcessSnap = c_void_p(0)
		hProcessSnap = CreateToolhelp32Snapshot( TH32CS_SNAPPROCESS , 0 )
		pe32 = PROCESSENTRY32()
		pe32.dwSize = sizeof( PROCESSENTRY32 )
		ret = Process32First( hProcessSnap , pointer( pe32 ) )
		if ret == 0 :
			#print 'ListProcessPid() Error on Process32First[%d]' % GetLastError()
			CloseHandle( hProcessSnap )
			return False 
		global PROGPid
		PROGPid=False
		while ret:
			if pe32.szExeFile == ProcessName:
				hProcess = OpenProcess( PROCESS_ALL_ACCESS , 0 , pe32.th32ProcessID )
				dwPriorityClass = GetPriorityClass( hProcess )
				if dwPriorityClass == 0 :
					CloseHandle( hProcess )
				PROGPid=pe32.th32ProcessID
			ret = Process32Next( hProcessSnap, pointer(pe32) )
		CloseHandle(hProcessSnap)
		return PROGPid

	except:
		#print "Error in ListProcessPid"
		CloseHandle( hProcess )
		CloseHandle ( hProcessSnap )
		return False

def ListProcessModules( ProcessID, ModuleName ):
	""" This method will return a base virtual offset of the specified ModuleName
		It will only look for shared components that are started by ProcessID
	"""
	try:
		hModuleSnap = c_void_p(0)
		me32 = MODULEENTRY32()
		me32.dwSize = sizeof( MODULEENTRY32 )
		hModuleSnap = CreateToolhelp32Snapshot( TH32CS_SNAPALL, ProcessID )
		ret = Module32First( hModuleSnap, pointer(me32) )
		if ret == 0 :
			#print 'ListProcessModules() Error on Module32First[%d]' % GetLastError()
			CloseHandle( hModuleSnap )
			return False 
		global PROGMainBase
		PROGMainBase=False
		while ret :
			if me32.szModule == ModuleName:
				PROGMainBase=me32.modBaseAddr
			ret = Module32Next( hModuleSnap , pointer(me32) )
		CloseHandle( hModuleSnap )
		return PROGMainBase
	except:
		#print "Error in ListProcessModules"
		return False
