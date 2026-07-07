import sys

from base64 import b64decode, b64encode

from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()

class B64Command(StreamingCommand):
    """
    Encode a string to Base64
    Decode a Base64 content
   
     | base64 [action=(encode|decode)] field=<field> [mode=(replace|append)]
     """

    field  = Option(name='field',  require=True)
    action = Option(name='action', require=False, default="encode")
    mode   = Option(name='mode',   require=False, default="replace")
    suppress_error = Option(name='suppress_error', require=False, default=False, validate=validators.Boolean())

    def stream(self, events):
		
	module = sys.modules['base64']

	if self.action == "decode" :
		fct = "b64decode"
	else:
		fct = "b64encode"

	if self.mode == "append" :
		dest_field = "base64"
	else:
		dest_field = self.field

	for event in events:
		
		if not self.field in event :
			continue

		try:
			ret = getattr(module, fct)( event[self.field] )

			# replace unpritable characters by their hexadecimal 
			# representation. Exemple: \x00
			event[ dest_field ] = ""
			for c in ret:
				x = c
				if c < ' ' or c > '~' :
					x = "\\x" + "{0:02x}".format(ord(c))
				event[ dest_field ] += x

		except Exception, e:
			if not self.suppress_error :
				raise e

		yield event

dispatch(B64Command, sys.argv, sys.stdin, sys.stdout, __name__)

