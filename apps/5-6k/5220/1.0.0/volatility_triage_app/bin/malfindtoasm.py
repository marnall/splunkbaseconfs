from __future__ import division
from past.utils import old_div
import splunk.Intersplunk 
from capstone import *

#f = open("/tmp/malfind.log2","w+")

def parseHex(hexstring,baseAddress):
    
    #f.write(str(hexstring))
    #f.write("===");
    #f.write(str(baseAddress))
    #f.write("\n");
    shellcode = bytes.fromhex(hexstring)
    #shellcode=bytes.fromhex("0000000000000000903e991900000000903e9919000000000000991900000000000f181f000000000010181f0000000000201b1f000000000100000000000000")
    #0x1F180000

    asm = []
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for i in md.disasm(shellcode, baseAddress):
        asm_string = "0x%x:\t%s\t%s" %(i.address, i.mnemonic, i.op_str)
        #f.write(asm_string)
        #f.write("\n")
        asm.append(asm_string)

    return asm


# get the previous search results
results,unused1,unused2 = splunk.Intersplunk.getOrganizedResults()
# for each results convert the data
for result in results:
    result["asm"] = parseHex(result["data"],int(result["address"]))
# output results
splunk.Intersplunk.outputResults(results)
