# Description: Template Manager, manage all the tempalate and generate the parse string.
# Created by: Matthew Gao
# Copyright 2013 Dell, Inc.

from ipfix_def import *
from struct import *
from ipfix_def import *
import sys

class TemplateManager:
    def __init__(self, output = sys.stdout, error = sys.stderr):
        self.templateMap={}
        self.fmtMap={}
        self.templateHdrAndField_st=Struct('!HH')
        self._msghdr_st=Struct("!HHLLL")
        self._sethdr_st = Struct("!HH")
        
        self.fmtMap[int(TEMPLATE_AVT_RESOUCRE)]="!128s128s64s20s256s16s16sQQIII"
        self.fmtMap[int(TEMPLATE_AVT_SESSION_END)]="!36sI"
        self.fmtMap[int(TEMPLATE_AVT_SESSION_START)]="!36s128s128sI40s16s"



        self.fmtMap[int(TEMPLATE_ANTI_SPYWARE)]="!I96sI96sI"
        self.fmtMap[int(TEMPLATE_APPLICATION)]="!II96sI96sIBBHIB"
        self.fmtMap[int(TEMPLATE_COLUMN_MAP)]="!I32sII"
        self.fmtMap[int(TEMPLATE_CORE_STAT)]="!HH"
        self.fmtMap[int(TEMPLATE_DEVICES)]="!II6s40s"
        self.fmtMap[int(TEMPLATE_FLOW_EXTN)]="!II6s6sIIIIIIQQHHIIIIIIIIIIHBBIQIIIIIIIIII"
        self.fmtMap[int(TEMPLATE_GAV)]="!I96sI"
        self.fmtMap[int(TEMPLATE_IF_STAT)]="!IIIIIIIIBBBI32sH6sIB32s"
        self.fmtMap[int(TEMPLATE_IPS)]="!I96sI96sI"
        self.fmtMap[int(TEMPLATE_LOCATION_MAP)]="!II32s32s"
        
        self.fmtMap[int(TEMPLATE_LOCATION)]="!II64s"
        #self.fmtMap[int(TEMPLATE_LOG)]="!"
        self.fmtMap[int(TEMPLATE_MEMORY)]="!IIIIIIIII"
        self.fmtMap[int(TEMPLATE_RATING)]="!I32s"
        self.fmtMap[int(TEMPLATE_SERVICES)]="!80sBHH"
        self.fmtMap[int(TEMPLATE_SPAM)]="!QIIBB80s80s"
        self.fmtMap[int(TEMPLATE_TABLE_MAP)]="!I32s"
        self.fmtMap[int(TEMPLATE_TOPAPPS_STAT)]="!I96sI"
        self.fmtMap[int(TEMPLATE_URL_RATING)]="!128sBBBB"
        self.fmtMap[int(TEMPLATE_URL)]="!II128sI"

        self.fmtMap[int(TEMPLATE_USER)]="!Q129s129sQII"
        self.fmtMap[int(TEMPLATE_VOIP)]="!IIBB80s80sIIIIII"
        self.fmtMap[int(TEMPLATE_VPN)]="!QQ40sIIIBBBBII"

        self.fmtMap[int(TEMPLATE_IPV6_FLOW_EXTN)]="!II6s6s16s16s16s16sIIQQHHIIIIIIIIIIHBBIQIIIIIIIIII"
        self.fmtMap[int(TEMPLATE_IPV6_USER)]="!Q129s129sQ16sI"
        self.fmtMap[int(TEMPLATE_IPV6_URL)]="!II128s16s"
        self.fmtMap[int(TEMPLATE_IPV6_LOCATION)]="!16sI64s"
        self.fmtMap[int(TEMPLATE_IPV6_SPAM)]="!QII16sBB80s80s"
        self.fmtMap[int(TEMPLATE_IPV6_DEVICES)]="!I16s6s40s"
        self.fmtMap[int(TEMPLATE_IPV6_VPN_TUNNELS)]="!QQ40s16s16sIBBBBII"
        self.fmtMap[int(TEMPLATE_IPV6_IF_STAT)]="!IIIIIIIIBBBI32sH6s16sB32s"
        
        self.fmtMap[int(TEMPLATE_IPV6_TOPAPPS)]="!I96sI"

        self.fmtMap[int(TEMPLATE_FLOW_OPEN_TYPE_V2)]="!II6s6sIIIIIIHHBI"
        self.fmtMap[int(TEMPLATE_IPV6_FLOW_OPEN_TYPE_V2)]="!II6s6s16s16s16s16sIIHHBI"
        self.fmtMap[int(TEMPLATE_FLOW_CLOSE_TYPE_V2)]="!IIIIIIIIQB"
        self.fmtMap[int(TEMPLATE_THREAT_UPDATE_TYPE_V2)]="!IIBI"
        self.fmtMap[int(TEMPLATE_VPN_UPDATE_TYPE_V2)]="!IIQQ"
        self.fmtMap[int(TEMPLATE_USER_UPDATE_TYPE_V2)]="!IIQ"
        self.fmtMap[int(TEMPLATE_APP_UPDATE_TYPE_V2)]="!III"
        self.fmtMap[int(TEMPLATE_BYTES_UPDATE_TYPE_V2)]="!IIQQIIIIBIQIII"

        self._out = output
        self._err = error
    """
    # Not build as a universal IPFIX processor right now.
    def addTemplate(self,templateBuf,setLen):

        offset=self._msghdr_st.size+self._sethdr_st.size
        length=setLen+self._msghdr_st.size
        lens=0

        _tmphdr_st = Struct("!HH")
        _fldhdr_st = Struct("!HH")
        while length>=(offset+lens):
            print ""
            lens=_tmphdr_st.size
            mbuf=templateBuf[offset:offset+lens]

            (tmpID,fldCount)=_tmphdr_st.unpack_from(mbuf,0)

            print "tmpID: %d"%tmpID
            print "fldCount: %d"%fldCount
            fieldList=[]
            while fldCount>0:
                
                offset=offset+_tmphdr_st.size
                lens=_fldhdr_st.size
                mbuf=templateBuf[offset:offset+lens]
                (fldtype,fldlens)=_fldhdr_st.unpack_from(mbuf,0)

                fieldList.append([fldtype,fldlens])
                
                print "fldtype: %d"%fldtype
                print "fldlens: %d"%fldlens

                fldCount=fldCount-1
            self.templateMap[tmpID]=fieldList
            offset=offset+_tmphdr_st.size
            self.structFormater(tmpID)
            print "offset: %d"%offset
            print self.templateMap


    

    def structFormater(self,templId):
        feildList=self.templateMap[templId]
        fmtstr=''
        for feild in feildList:
            fldType=feild[0]
            fldLength=feild[1]
            
            if(fldType==IPFIX_FTYPE_STRING):
                
                if(fldLength==1):
                    fmtstr=fmtstr+'s'
                else:
                    fmtstr=fmtstr+str(fldLength)+'s'

            
            if(fldType==IPFIX_FTYPE_UNSIGNED32):
                    fmtstr=fmtstr+'I'
            if(fldType==IPFIX_FTYPE_UNSIGNED64):
                    fmtstr=fmtstr+'Q'
            if(fldType==IPFIX_FTYPE_TIMESTAMP):
                    fmtstr=fmtstr+'I'
        fmtstr='!'+fmtstr
        print fmtstr
        self.fmtMap[templId]=fmtstr
    """

    def getFmtStr(self):
        return self.fmtMap
    
    def log(self, severity, message):
        """Logs messages about the state of this modular input to Splunk.
        These messages will show up in Splunk's internal logs.

        :param severity: ``string``, severity of message, see severites defined as class constants.
        :param message: Message to log.
        """

        self._err.write("%s %s\n" % (severity, message))
        self._err.flush()            
