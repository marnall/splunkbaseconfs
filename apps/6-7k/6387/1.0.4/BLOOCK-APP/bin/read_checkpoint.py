import sys as A,os
A.path.insert(0,os.path.join(os.path.dirname(__file__),'..','lib'))
from splunklib.searchcommands import dispatch as D,GeneratingCommand as E,Configuration as B,Option as C,validators
H=os.path.basename(__file__)
F='../../../../var/BLOOCK-APP/'
@B()
class G(E):
	license=C(require=True);index=C(require=True)
	@B()
	def generate(self):
		B=self.license+'_'+self.index
		try:
			with open(F+B,'r')as C:A=C.read()
		except IOError:A=1
		yield{'checkpoint':A}
if __name__=='__main__':D(G,A.argv,A.stdin,A.stdout,__name__)