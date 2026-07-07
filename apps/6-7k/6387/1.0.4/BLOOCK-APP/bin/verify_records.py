G=False
E='lib'
import sys as A,os as B,psc_exec_anaconda as H
H.exec_anaconda()
A.path.insert(0,B.path.join(B.path.dirname(__file__),'..',E))
from splunklib.searchcommands import dispatch as I,ReportingCommand as J,Configuration as C,Option as D,validators as K
A.path.insert(0,B.path.join(B.path.dirname(__file__),'..',E,'bloock_lib'))
import bloock as F
from bloock.client.client import Client as L
from bloock.client.builder import RecordBuilder as M
from bloock.client.entity.network import Network as N
import requests as O,json
P=B.path.basename(__file__)
Q='bloock_app_realm'
def R(search_command,s_realm,s_name):B=search_command.service.storage_passwords;return next((A for A in B if A.realm==s_realm and A.username==s_name)).clear_password
def S(lista,n):
	A=lista
	for B in range(0,len(A),n):yield A[B:B+n]
def T(licencia):C='success';B='brand';D='https://api.bloock.com/credentials/v1/licenses/validate';E=O.post(D,json={'key':licencia});A=json.loads(E.text);F=A[B]if B in A else'';H=A[C]if C in A else G;return H&(F=='splunk')
@C()
class U(J):
	license=D(require=True);reg_size=D(require=G,validate=K.Integer(),default=100)
	def verify_record(A,regs):
		E='license';D='Result';F.api_key=R(A,Q,A.license);G=L()
		try:
			if T(F.api_key):B=G.verify_records(regs)
			else:B=G.verify_records(regs,N.GNOSIS_CHAIN)
			if B is None or B<=0:C={D:'Data not registered on the blockchain.',E:A.license}
			else:C={D:'Record is valid','ts':B,E:A.license}
		except Exception as H:C={D:'Error:'+str(H),'status':'Failed','source':P,E:A.license}
		return C
	@C()
	def map(self,records):return records
	def reduce(B,records):
		C=[]
		for A in records:C.append(A)
		E=S(C,B.reg_size)
		for F in E:
			D=[]
			for A in F:D.append(M.from_string(A['_raw']).build())
			G=B.verify_record(D);yield G
if __name__=='__main__':I(U,A.argv,A.stdin,A.stdout,__name__)