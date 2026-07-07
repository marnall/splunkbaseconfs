_C='event_index'
_B=True
_A=False
import sys,os,psc_exec_anaconda
psc_exec_anaconda.exec_anaconda()
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','lib'))
from splunklib.searchcommands import dispatch,ReportingCommand,Configuration,Option,validators
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','lib','bloock_lib'))
import bloock
from bloock.client.client import Client
from bloock.client.builder import RecordBuilder
import time
SOURCE=os.path.basename(__file__)
SECRET_REALM='bloock_app_realm'
CHECKPOINT_PATH='../../../../var/BLOOCK-APP/'
def get_encrypted_license_token(search_command,s_realm,s_name):
	secrets=search_command.service.storage_passwords
	for secret in secrets:
		if secret.realm==s_realm and secret.username==s_name:return secret.clear_password
	raise Exception('Invalid license. Did you mistype it? Or add it using the licenses section.')
def dividir_lista(lista,n):
	for i in range(0,len(lista),n):yield lista[i:i+n]
@Configuration()
class sendRecords(ReportingCommand):
	wait=Option(require=_A,validate=validators.Boolean(),default='true');license=Option(require=_B);field_cd=Option(require=_B,default='_cd');field_bkt=Option(require=_B,default='_bkt');update_checkpoint=Option(require=_A,validate=validators.Boolean(),default='false');reg_size=Option(require=_A,validate=validators.Integer(),default=100);checkpoint_value=0;error=_A
	def send_records(self,regs,audit):
		C='license';B='source';A=None;ts=time.time();results=[]
		try:
			s_name=self.license;bloock.api_key=get_encrypted_license_token(self,SECRET_REALM,s_name);client=Client()
			if regs is A or len(regs)==0:return results
			send_receipt=client.send_records(regs);anchor=A
			if self.wait and len(send_receipt)>0:anchor=client.wait_anchor(send_receipt[0].anchor)
			for i in range(len(send_receipt)):
				d={'_time':ts,B:SOURCE};d_receipt=vars(send_receipt[i])if send_receipt[i]is not A else{}
				for key in d_receipt:d.update({str(key):str(d_receipt[key])})
				d_anchor=vars(anchor)if anchor is not A else{}
				for key in d_anchor:
					if type(d_anchor[key])is list:
						for el in d_anchor[key]:el=str(el)
						d.update({str(key):d_anchor[key]})
					else:d.update({str(key):str(d_anchor[key])})
				d.update(audit[i]);d.update({C:s_name});results.append(d)
			if self.update_checkpoint and not self.error:self.escribir_checkpoint(audit)
		except Exception as e:
			results=[];self.error=_B
			for i in range(len(regs)):d={'error':str(e),'status':'Failed',B:SOURCE,C:s_name};d.update(audit[i]);results.append(d)
		return results
	def escribir_checkpoint(self,audit):
		checkpoint_file=self.license+'_'+audit[0].get(_C)
		if not os.path.isdir(CHECKPOINT_PATH):os.mkdir(CHECKPOINT_PATH)
		try:f=open(CHECKPOINT_PATH+checkpoint_file,'w');f.write(str(self.checkpoint_value));f.close()
		except:raise Exception('Error al escrbir checkpoint: '+str(self.checkpoint_value))
	@Configuration()
	def map(self,records):return records
	def reduce(self,records):
		A='_indextime';records_list=[]
		for record in records:records_list.append(record)
		segs=dividir_lista(records_list,self.reg_size);seg_n=0
		for seg in segs:
			regs=[];audit=[]
			for record in seg:regs.append(RecordBuilder.from_string(record['_raw']).build());audit.append({'event_cd':record[self.field_cd],'event_bkt':record[self.field_bkt],_C:record['index'],'event_time':record['_time'],'event_index_time':record[A],'batch_num':str(seg_n)});self.checkpoint_value=int(record[A])+1 if int(record[A])>self.checkpoint_value else self.checkpoint_value
			result=self.send_records(regs,audit)
			for r in result:yield r
			if self.error:break
			seg_n+=1
if __name__=='__main__':dispatch(sendRecords,sys.argv,sys.stdin,sys.stdout,__name__)