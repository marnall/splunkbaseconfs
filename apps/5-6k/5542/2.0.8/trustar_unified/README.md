# Binary File Declaration
(For SplunkBase / SPlunkCloud appinspect teams....)
While running the Appinspect CLI tool, it noted these binaries that are all
included in the "aob_py3" dependencies given to our app by AOB-4:
  - bin/trustar_unified/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so
  - bin/trustar_unified/aob_py3/setuptools/cli-64.exe
  - bin/trustar_unified/aob_py3/setuptools/gui-64.exe
  - bin/trustar_unified/aob_py3/setuptools/cli.exe
  - bin/trustar_unified/aob_py3/setuptools/cli-32.exe
  - bin/trustar_unified/aob_py3/setuptools/gui-32.exe
  - bin/trustar_unified/aob_py3/setuptools/gui.exe
  - bin/trustar_unified/aob_py3/markupsafe/_speedups.c
  - bin/trustar_unified/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so

# Appinspectors:
- 'splunklib' library ships with AOB 4's "aob_py3" dir, but causes CLI appinspect 
  tool to throw warning.  TruSTAR left it there intentionally.
  
